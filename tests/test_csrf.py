import errno
import uuid
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.verification_token import mint_email_verification_token
from app.main import app

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def _skip_if_unreachable(exc: BaseException) -> None:
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, ConnectionRefusedError):
            pytest.skip(f"infra unreachable: {exc}")
        if isinstance(cur, OSError) and getattr(cur, "errno", None) == errno.ECONNREFUSED:
            pytest.skip(f"infra unreachable: {exc}")
        cur = cur.__cause__


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    return {CSRF_HEADER: token}


def _csrf_headers_with_ip(client: TestClient) -> dict[str, str]:
    return {
        **_csrf_headers(client),
        "X-Forwarded-For": f"10.40.{int(uuid.uuid4().hex[:2], 16)}.{int(uuid.uuid4().hex[2:4], 16)}",
    }


def _issue_csrf(client: TestClient) -> None:
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200, resp.text
    assert resp.json()["csrf_token"] == client.cookies.get(CSRF_COOKIE)


def _register_verified_master(client: TestClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"csrf_master_{suffix}@example.com"
    password = "longpassword1"
    settings = get_settings()

    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "master_display_name": "CSRF Test Studio",
        },
        headers=_csrf_headers_with_ip(client),
    )
    assert reg.status_code == 201, reg.text
    token = mint_email_verification_token(
        secret=settings.security.secret_key,
        user_id=UUID(reg.json()["id"]),
        email=email,
        ttl_seconds=settings.security.email_verification_ttl_seconds,
    )
    verify = client.post("/api/auth/verify-email", json={"token": token}, headers=_csrf_headers(client))
    assert verify.status_code == 200, verify.text


def test_auth_sets_csrf_cookie_after_session_is_created():
    try:
        with TestClient(app) as client:
            _register_verified_master(client)

            assert client.cookies.get("session_id")
            assert client.cookies.get(CSRF_COOKIE)
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_authenticated_mutation_rejects_missing_or_invalid_csrf_token():
    try:
        with TestClient(app) as client:
            _register_verified_master(client)

            missing = client.post("/api/invitations", json={})
            assert missing.status_code == 403, missing.text
            assert missing.json()["detail"] == "CSRF token missing or invalid"

            invalid = client.post("/api/invitations", json={}, headers={CSRF_HEADER: "wrong-token"})
            assert invalid.status_code == 403, invalid.text
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_authenticated_mutation_accepts_matching_csrf_token():
    try:
        with TestClient(app) as client:
            _register_verified_master(client)

            created = client.post("/api/invitations", json={}, headers=_csrf_headers(client))
            assert created.status_code == 201, created.text
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise
