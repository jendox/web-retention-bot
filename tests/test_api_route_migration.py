"""API route prefix migration: legacy paths removed, new client/master paths wired."""

from __future__ import annotations

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
MASTER_PASSWORD = "masterpass1"
CLIENT_PASSWORD = "clientpass1"

# Flat paths removed in the /client/* and /master/* migration (no redirects).
LEGACY_GET_PATHS = [
    "/api/bookings/me",
    "/api/bookings/stats/monthly-revenue",
    "/api/bookings",
    "/api/masters/me",
    "/api/masters/me/schedule",
    "/api/clients/me/masters",
    "/api/clients",
    "/api/services",
    "/api/availability",
    "/api/notifications/me",
]

# New routes must exist (401 without session, not 404).
NEW_MASTER_PATHS = [
    "/api/master/profile",
    "/api/master/schedule",
    "/api/master/clients?page=1&page_size=10",
    "/api/master/services?page=1&page_size=10",
    "/api/master/bookings?scope=upcoming&page=1&page_size=10",
    "/api/master/bookings/stats/monthly-revenue",
    "/api/master/notifications/me?page=1&page_size=10",
    "/api/master/notification-settings/me",
]

NEW_CLIENT_PATHS = [
    "/api/client/masters",
    "/api/client/bookings?scope=upcoming&page=1&page_size=10",
    "/api/client/notifications/me?page=1&page_size=10",
    "/api/client/notification-settings/me",
]


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
        "X-Forwarded-For": f"10.70.{int(uuid.uuid4().hex[:2], 16)}.{int(uuid.uuid4().hex[2:4], 16)}",
    }


def _issue_csrf(client: TestClient) -> None:
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200, resp.text


def _register_verified_master(client: TestClient, *, email: str) -> None:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": MASTER_PASSWORD,
            "master_display_name": "Route Test Studio",
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


def _register_verified_client(client: TestClient, *, email: str) -> None:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register-client",
        json={"email": email, "password": CLIENT_PASSWORD, "client_display_name": "Route Client"},
        headers=_csrf_headers_with_ip(client),
    )
    assert reg.status_code == 201, reg.text
    verify = client.post(
        "/api/auth/verify-email",
        json={"token": _verification_token(reg.json()["id"], email)},
        headers=_csrf_headers(client),
    )
    assert verify.status_code == 200, verify.text


def _is_unregistered_route(resp) -> bool:
    """FastAPI 404 when no matching route; differs from app-level 404 (e.g. missing master profile)."""
    return resp.status_code == 404 and resp.json().get("detail") == "Not Found"


@pytest.mark.parametrize("path", LEGACY_GET_PATHS)
def test_legacy_api_paths_are_not_registered(path: str) -> None:
    with TestClient(app) as client:
        resp = client.get(path)
        assert _is_unregistered_route(resp), (path, resp.status_code, resp.text)


@pytest.mark.parametrize("path", NEW_MASTER_PATHS)
def test_new_master_api_paths_are_registered(path: str) -> None:
    with TestClient(app) as client:
        resp = client.get(path)
        assert not _is_unregistered_route(resp), (path, resp.status_code, resp.text)


@pytest.mark.parametrize("path", NEW_CLIENT_PATHS)
def test_new_client_api_paths_are_registered(path: str) -> None:
    with TestClient(app) as client:
        resp = client.get(path)
        assert not _is_unregistered_route(resp), (path, resp.status_code, resp.text)


def test_authenticated_master_hits_new_master_routes() -> None:
    email = f"master_routes_{uuid.uuid4().hex[:8]}@example.com"
    try:
        with TestClient(app) as client:
            _register_verified_master(client, email=email)
            for path in NEW_MASTER_PATHS:
                resp = client.get(path)
                assert resp.status_code == 200, (path, resp.status_code, resp.text)
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_authenticated_client_hits_new_client_routes() -> None:
    email = f"client_routes_{uuid.uuid4().hex[:8]}@example.com"
    try:
        with TestClient(app) as client:
            _register_verified_client(client, email=email)
            for path in NEW_CLIENT_PATHS:
                resp = client.get(path)
                assert resp.status_code == 200, (path, resp.status_code, resp.text)
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise
