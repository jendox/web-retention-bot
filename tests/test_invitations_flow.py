import errno
import uuid
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.verification_token import mint_email_verification_token
from app.main import app

MASTER_PASSWORD = "masterpass1"
CLIENT_PASSWORD = "clientpass1"
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


def _verification_token(user_id: str, email: str) -> str:
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
        "X-Forwarded-For": f"10.50.{int(uuid.uuid4().hex[:2], 16)}.{int(uuid.uuid4().hex[2:4], 16)}",
    }


def _issue_csrf(client: TestClient) -> None:
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200, resp.text


def _register_verified_master(client: TestClient, *, email: str, display_name: str) -> dict:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register-master",
        json={
            "email": email,
            "password": MASTER_PASSWORD,
            "master_display_name": display_name,
        },
        headers=_csrf_headers_with_ip(client),
    )
    assert reg.status_code == 201, reg.text
    verify = client.post(
        "/api/auth/verify-email",
        json={"token": _verification_token(reg.json()["id"], email)},
        headers=_csrf_headers(client),
    )
    assert verify.status_code == 200, verify.text
    master = client.get("/api/master/profile")
    assert master.status_code == 200, master.text
    return master.json()


def _register_verified_client(client: TestClient, *, email: str) -> dict:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register-client",
        json={
            "email": email,
            "password": CLIENT_PASSWORD,
        },
        headers=_csrf_headers_with_ip(client),
    )
    assert reg.status_code == 201, reg.text
    verify = client.post(
        "/api/auth/verify-email",
        json={"token": _verification_token(reg.json()["id"], email)},
        headers=_csrf_headers(client),
    )
    assert verify.status_code == 200, verify.text
    return verify.json()


def test_open_invitation_accept_creates_client_link():
    suffix = uuid.uuid4().hex[:8]
    master_email = f"master_open_{suffix}@example.com"
    client_email = f"client_open_{suffix}@example.com"
    master_name = f"Open Invite Studio {suffix}"

    try:
        with TestClient(app) as client:
            master = _register_verified_master(client, email=master_email, display_name=master_name)

            created = client.post("/api/invitations", json={}, headers=_csrf_headers(client))
            assert created.status_code == 201, created.text
            token = created.json()["token"]

            landing = client.get(f"/api/invitations/{token}")
            assert landing.status_code == 200, landing.text
            landing_data = landing.json()
            assert landing_data["master_display_name"] == master["display_name"]
            assert landing_data["invite_kind"] == "open"
            assert landing_data["accepted_at"] is None
            assert landing_data["linked_client_id"] is None

            assert client.post("/api/auth/logout", headers=_csrf_headers(client)).status_code == 204
            _register_verified_client(client, email=client_email)

            accepted = client.post(
                f"/api/invitations/{token}/accept",
                json={"display_name": "Open Invite Client", "phone": "+375291112233"},
                headers=_csrf_headers(client),
            )
            assert accepted.status_code == 200, accepted.text
            accepted_data = accepted.json()
            assert accepted_data["email_mismatch_with_master_record"] is False
            assert accepted_data["client_id"]

            accepted_landing = client.get(f"/api/invitations/{token}")
            assert accepted_landing.status_code == 200, accepted_landing.text
            assert accepted_landing.json()["linked_client_id"] == accepted_data["client_id"]
            assert accepted_landing.json()["accepted_at"] is not None

            my_masters = client.get("/api/client/masters")
            assert my_masters.status_code == 200, my_masters.text
            linked = [
                item
                for item in my_masters.json()
                if item["master_id"] == master["id"] and item["client_id"] == accepted_data["client_id"]
            ]
            assert linked
            assert linked[0]["contact_email"] == master_email.lower()
            assert linked[0]["client_alias"] == master_name

            alias_patch = client.patch(
                f"/api/client/masters/{master['id']}",
                json={"client_alias": "My Favorite Studio"},
                headers=_csrf_headers(client),
            )
            assert alias_patch.status_code == 200, alias_patch.text
            assert alias_patch.json()["client_alias"] == "My Favorite Studio"
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_targeted_invitation_accept_links_existing_client_and_flags_email_mismatch():
    suffix = uuid.uuid4().hex[:8]
    master_email = f"master_target_{suffix}@example.com"
    client_email = f"client_target_{suffix}@example.com"
    master_name = f"Target Invite Studio {suffix}"

    try:
        with TestClient(app) as client:
            master = _register_verified_master(client, email=master_email, display_name=master_name)

            created_client = client.post(
                "/api/master/clients",
                json={
                    "display_name": "Stored Client",
                    "phone": "+375291110000",
                    "email": f"profile_target_{suffix}@example.com",
                },
                headers=_csrf_headers(client),
            )
            assert created_client.status_code == 201, created_client.text
            target_client_id = created_client.json()["client"]["id"]

            invite = client.post(
                "/api/invitations",
                json={"target_client_id": target_client_id},
                headers=_csrf_headers(client),
            )
            assert invite.status_code == 201, invite.text
            token = invite.json()["token"]
            assert invite.json()["target_client_id"] == target_client_id

            landing = client.get(f"/api/invitations/{token}")
            assert landing.status_code == 200, landing.text
            assert landing.json()["invite_kind"] == "client"
            assert landing.json()["master_record_has_email"] is True

            assert client.post("/api/auth/logout", headers=_csrf_headers(client)).status_code == 204
            _register_verified_client(client, email=client_email)

            accepted = client.post(
                f"/api/invitations/{token}/accept",
                json={"display_name": "Accepted Client", "phone": "+375292224455"},
                headers=_csrf_headers(client),
            )
            assert accepted.status_code == 200, accepted.text
            assert accepted.json() == {
                "client_id": target_client_id,
                "email_mismatch_with_master_record": True,
            }

            my_masters = client.get("/api/client/masters")
            assert my_masters.status_code == 200, my_masters.text
            assert [
                item
                for item in my_masters.json()
                if item["master_id"] == master["id"]
                and item["client_id"] == target_client_id
                and item["client_display_name"] == "Accepted Client"
            ]

            assert client.post("/api/auth/logout", headers=_csrf_headers(client)).status_code == 204
            _issue_csrf(client)
            login_master = client.post(
                "/api/auth/login",
                json={"email": master_email, "password": MASTER_PASSWORD},
                headers=_csrf_headers(client),
            )
            assert login_master.status_code == 200, login_master.text

            detail = client.get(f"/api/master/clients/{target_client_id}")
            assert detail.status_code == 200, detail.text
            detail_data = detail.json()
            assert detail_data["client"]["display_name"] == "Accepted Client"
            assert detail_data["client"]["phone"] == "+375292224455"
            assert detail_data["client"]["email"] == f"profile_target_{suffix}@example.com"
            assert detail_data["client"]["user_id"] is not None
            assert detail_data["link"]["linked_account_email"] == client_email
            assert detail_data["link"]["invite_email_mismatch"] is True
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise
