"""Forgot password, reset password, and change password flows."""

from __future__ import annotations

import errno
import time
import uuid
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.password_reset_token import (
    PasswordResetTokenError,
    mint_password_reset_token,
    parse_password_reset_token,
)
from app.core.verification_token import mint_email_verification_token
from app.main import app

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
MASTER_PASSWORD = "masterpass1"
NEW_PASSWORD = "newpass123"


def _skip_if_unreachable(exc: BaseException) -> None:
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, ConnectionRefusedError):
            pytest.skip(f"infra unreachable: {exc}")
        if isinstance(cur, OSError) and getattr(cur, "errno", None) == errno.ECONNREFUSED:
            pytest.skip(f"infra unreachable: {exc}")
        cur = cur.__cause__


def _random_ip() -> str:
    h = uuid.uuid4().hex
    return f"10.{int(h[:2], 16)}.{int(h[2:4], 16)}.{int(h[4:6], 16)}"


def _verification_token(user_id: str, email: str) -> str:
    settings = get_settings()
    return mint_email_verification_token(
        secret=settings.security.secret_key,
        user_id=uuid.UUID(user_id),
        email=email,
        ttl_seconds=settings.security.email_verification_ttl_seconds,
    )


def _csrf_headers(client: TestClient, *, ip: str | None = None) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    h: dict[str, str] = {CSRF_HEADER: token}
    if ip:
        h["X-Forwarded-For"] = ip
    return h


def _issue_csrf(client: TestClient) -> None:
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200, resp.text


def _register_verified_master(client: TestClient, *, email: str, ip: str) -> str:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": MASTER_PASSWORD, "master_display_name": "Reset Studio"},
        headers=_csrf_headers(client, ip=ip),
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]
    verify = client.post(
        "/api/auth/verify-email",
        json={"token": _verification_token(user_id, email)},
        headers=_csrf_headers(client, ip=ip),
    )
    assert verify.status_code == 200, verify.text
    return user_id


# ── Token unit tests ─────────────────────────────────────────────


def test_mint_and_parse_password_reset_token() -> None:
    uid = uuid.uuid4()
    email = "test@example.com"
    token = mint_password_reset_token(secret="s3cret", user_id=uid, email=email, ttl_seconds=3600)
    parsed_uid, parsed_email = parse_password_reset_token(secret="s3cret", token=token)
    assert parsed_uid == uid
    assert parsed_email == email


def test_password_reset_token_wrong_secret() -> None:
    uid = uuid.uuid4()
    token = mint_password_reset_token(secret="s3cret", user_id=uid, email="a@b.com", ttl_seconds=3600)
    with pytest.raises(PasswordResetTokenError):
        parse_password_reset_token(secret="wrong", token=token)


def test_password_reset_token_expired() -> None:
    uid = uuid.uuid4()
    with patch.object(time, "time", return_value=1_000_000):
        token = mint_password_reset_token(secret="s3cret", user_id=uid, email="a@b.com", ttl_seconds=1)
    with patch.object(time, "time", return_value=1_000_002):
        with pytest.raises(PasswordResetTokenError, match="expired"):
            parse_password_reset_token(secret="s3cret", token=token)


def test_password_reset_token_tampered() -> None:
    uid = uuid.uuid4()
    token = mint_password_reset_token(secret="s3cret", user_id=uid, email="a@b.com", ttl_seconds=3600)
    body, sig = token.rsplit(".", 1)
    tampered = f"{body}.{'0' * len(sig)}"
    with pytest.raises(PasswordResetTokenError):
        parse_password_reset_token(secret="s3cret", token=tampered)


# ── API integration tests ────────────────────────────────────────


def test_forgot_password_always_204() -> None:
    ip = _random_ip()
    email = f"nonexist_{uuid.uuid4().hex[:8]}@example.com"
    try:
        with TestClient(app) as client:
            _issue_csrf(client)
            resp = client.post(
                "/api/auth/forgot-password",
                json={"email": email},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 204
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_forgot_password_sends_for_verified_user() -> None:
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    ip = _random_ip()
    try:
        with TestClient(app) as client:
            _register_verified_master(client, email=email, ip=ip)

            resp = client.post(
                "/api/auth/forgot-password",
                json={"email": email},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 204
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_reset_password_with_valid_token() -> None:
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    ip = _random_ip()
    try:
        with TestClient(app) as client:
            user_id = _register_verified_master(client, email=email, ip=ip)

            settings = get_settings()
            token = mint_password_reset_token(
                secret=settings.security.secret_key,
                user_id=uuid.UUID(user_id),
                email=email,
                ttl_seconds=3600,
            )

            resp = client.post(
                "/api/auth/reset-password",
                json={"token": token, "new_password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 204

            client.post("/api/auth/logout", headers=_csrf_headers(client, ip=ip))
            _issue_csrf(client)

            login = client.post(
                "/api/auth/login",
                json={"email": email, "password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert login.status_code == 200

            old_login = client.post(
                "/api/auth/login",
                json={"email": email, "password": MASTER_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert old_login.status_code == 401
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_reset_password_invalid_token() -> None:
    ip = _random_ip()
    try:
        with TestClient(app) as client:
            _issue_csrf(client)
            resp = client.post(
                "/api/auth/reset-password",
                json={"token": "invalid-token-that-is-long-enough", "new_password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 400
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_change_password_success() -> None:
    email = f"chgpwd_{uuid.uuid4().hex[:8]}@example.com"
    ip = _random_ip()
    try:
        with TestClient(app) as client:
            _register_verified_master(client, email=email, ip=ip)

            resp = client.post(
                "/api/auth/change-password",
                json={"current_password": MASTER_PASSWORD, "new_password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 204

            client.post("/api/auth/logout", headers=_csrf_headers(client, ip=ip))
            _issue_csrf(client)

            login = client.post(
                "/api/auth/login",
                json={"email": email, "password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert login.status_code == 200
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_change_password_wrong_current() -> None:
    email = f"chgpwd_bad_{uuid.uuid4().hex[:8]}@example.com"
    ip = _random_ip()
    try:
        with TestClient(app) as client:
            _register_verified_master(client, email=email, ip=ip)

            resp = client.post(
                "/api/auth/change-password",
                json={"current_password": "wrongpassword1", "new_password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 400
            assert "неверно" in resp.json()["detail"].lower() or "incorrect" in resp.json()["detail"].lower()
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_change_password_requires_auth() -> None:
    ip = _random_ip()
    try:
        with TestClient(app) as client:
            _issue_csrf(client)
            resp = client.post(
                "/api/auth/change-password",
                json={"current_password": "old12345", "new_password": NEW_PASSWORD},
                headers=_csrf_headers(client, ip=ip),
            )
            assert resp.status_code == 401
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise
