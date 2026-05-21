"""Client self-service profile API."""

from __future__ import annotations

import errno
import uuid

import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.verification_token import mint_email_verification_token
from app.main import app

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CLIENT_PASSWORD = "clientpass1"


def _skip_if_unreachable(exc: BaseException) -> None:
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, ConnectionRefusedError):
            pytest.skip(f"infra unreachable: {exc}")
        if isinstance(cur, OSError) and getattr(cur, "errno", None) == errno.ECONNREFUSED:
            pytest.skip(f"infra unreachable: {exc}")
        cur = cur.__cause__


def _verification_token(user_id: str, email: str) -> str:
    from uuid import UUID

    settings = get_settings()
    return mint_email_verification_token(
        secret=settings.security.secret_key,
        user_id=UUID(user_id),
        email=email,
        ttl_seconds=settings.security.email_verification_ttl_seconds,
    )


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    return {CSRF_HEADER: token}


def _csrf_headers_with_ip(client: TestClient) -> dict[str, str]:
    return {
        **_csrf_headers(client),
        "X-Forwarded-For": f"10.72.{int(uuid.uuid4().hex[:2], 16)}.{int(uuid.uuid4().hex[2:4], 16)}",
    }


def _issue_csrf(client: TestClient) -> None:
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200, resp.text


def _register_verified_client(client: TestClient, *, email: str, display_name: str) -> None:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register-client",
        json={"email": email, "password": CLIENT_PASSWORD, "client_display_name": display_name},
        headers=_csrf_headers_with_ip(client),
    )
    assert reg.status_code == 201, reg.text
    verify = client.post(
        "/api/auth/verify-email",
        json={"token": _verification_token(reg.json()["id"], email)},
        headers=_csrf_headers(client),
    )
    assert verify.status_code == 200, verify.text


def test_client_profile_without_card_returns_404() -> None:
    email = f"profile_empty_{uuid.uuid4().hex[:8]}@example.com"
    try:
        with TestClient(app) as client:
            _register_verified_client(client, email=email, display_name="No Card Yet")
            resp = client.get("/api/client/profile")
            assert resp.status_code == 404, resp.text
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_new_client_api_paths_registered() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/client/profile")
        assert resp.status_code != 404 or resp.json().get("detail") != "Not Found"


def test_client_profile_patch_after_invitation_accept() -> None:
    suffix = uuid.uuid4().hex[:8]
    master_email = f"master_prof_{suffix}@example.com"
    client_email = f"client_prof_{suffix}@example.com"

    try:
        with TestClient(app) as client:
            _issue_csrf(client)
            master_reg = client.post(
                "/api/auth/register-master",
                json={
                    "email": master_email,
                    "password": "masterpass1",
                    "master_display_name": "Profile Test Studio",
                },
                headers=_csrf_headers_with_ip(client),
            )
            assert master_reg.status_code == 201, master_reg.text
            client.post(
                "/api/auth/verify-email",
                json={"token": _verification_token(master_reg.json()["id"], master_email)},
                headers=_csrf_headers(client),
            )

            invite = client.post("/api/invitations", json={}, headers=_csrf_headers(client))
            assert invite.status_code == 201, invite.text
            token = invite.json()["token"]

            client.post("/api/auth/logout", headers=_csrf_headers(client))
            _register_verified_client(client, email=client_email, display_name="ignored")

            accept = client.post(
                f"/api/invitations/{token}/accept",
                json={"display_name": "Before Edit", "phone": "+375290000001"},
                headers=_csrf_headers(client),
            )
            assert accept.status_code == 200, accept.text

            get_prof = client.get("/api/client/profile")
            assert get_prof.status_code == 200, get_prof.text
            assert get_prof.json()["display_name"] == "Before Edit"

            patch = client.patch(
                "/api/client/profile",
                json={"display_name": "After Edit", "phone": "+375290000099"},
                headers=_csrf_headers(client),
            )
            assert patch.status_code == 200, patch.text
            assert patch.json()["display_name"] == "After Edit"
            assert patch.json()["phone"] == "+375290000099"

            me = client.get("/api/auth/me")
            assert me.status_code == 200, me.text
            assert me.json()["client_display_name"] == "After Edit"
            assert me.json()["client_phone"] == "+375290000099"
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise
