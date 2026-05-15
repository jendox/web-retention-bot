import errno
import uuid
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.verification_token import mint_email_verification_token
from app.main import app


def _skip_if_unreachable(exc: BaseException) -> None:
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, ConnectionRefusedError):
            pytest.skip(f"infra unreachable: {exc}")
        if isinstance(cur, OSError) and getattr(cur, "errno", None) == errno.ECONNREFUSED:
            pytest.skip(f"infra unreachable: {exc}")
        cur = cur.__cause__


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_auth_register_verify_login_flow():
    suffix = uuid.uuid4().hex[:8]
    email = f"user_{suffix}@example.com"
    password = "longpassword1"
    register_body = {
        "email": email,
        "password": password,
        "master_display_name": "Test Studio",
    }
    settings = get_settings()

    try:
        with TestClient(app) as client:
            reg = client.post("/api/auth/register", json=register_body)
            assert reg.status_code == 201
            data = reg.json()
            assert data["email"] == email
            assert data["email_verified"] is False
            assert client.get("/api/auth/me").status_code == 401

            deny = client.post("/api/auth/login", json={"email": email, "password": password})
            assert deny.status_code == 403

            tok = mint_email_verification_token(
                secret=settings.security.secret_key,
                user_id=UUID(data["id"]),
                email=email,
                ttl_seconds=settings.security.email_verification_ttl_seconds,
            )

            verify = client.post("/api/auth/verify-email", json={"token": tok})
            assert verify.status_code == 200
            assert verify.json()["email_verified"] is True
            assert client.get("/api/auth/me").status_code == 200

            client.post("/api/auth/logout")
            assert client.get("/api/auth/me").status_code == 401

            login_ok = client.post("/api/auth/login", json={"email": email, "password": password})
            assert login_ok.status_code == 200
            assert client.get("/api/auth/me").status_code == 200

    except Exception as exc:
        _skip_if_unreachable(exc)
        raise
