"""Notification settings API and channel policy."""

from __future__ import annotations

import errno
import uuid
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.verification_token import mint_email_verification_token
from app.main import app
from app.models.notifications import DeliveryChannel, NotificationEventType, PreferenceCategory
from app.services.notifications.channel_policy import delivery_channels_for_user

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
MASTER_PASSWORD = "masterpass1"
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
        "X-Forwarded-For": f"10.71.{int(uuid.uuid4().hex[:2], 16)}.{int(uuid.uuid4().hex[2:4], 16)}",
    }


def _issue_csrf(client: TestClient) -> None:
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200, resp.text


def _register_verified_client(client: TestClient, *, email: str) -> None:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register-client",
        json={"email": email, "password": CLIENT_PASSWORD, "client_display_name": "Notify Client"},
        headers=_csrf_headers_with_ip(client),
    )
    assert reg.status_code == 201, reg.text
    verify = client.post(
        "/api/auth/verify-email",
        json={"token": _verification_token(reg.json()["id"], email)},
        headers=_csrf_headers(client),
    )
    assert verify.status_code == 200, verify.text


def _register_verified_master(client: TestClient, *, email: str) -> None:
    _issue_csrf(client)
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": MASTER_PASSWORD,
            "master_display_name": "Notify Studio",
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


def test_client_notification_settings_get_and_patch() -> None:
    email = f"notify_client_{uuid.uuid4().hex[:8]}@example.com"
    try:
        with TestClient(app) as client:
            _register_verified_client(client, email=email)

            get_resp = client.get("/api/client/notification-settings/me")
            assert get_resp.status_code == 200, get_resp.text
            body = get_resp.json()
            assert body["in_app"]["connected"] is True
            assert any(c["kind"] == "telegram" for c in body["channels"])
            booking = next(t for t in body["topics"] if t["id"] == "booking_events")
            assert booking["channels"]["email"] is True

            patch_resp = client.patch(
                "/api/client/notification-settings/me",
                json={"topics": [{"id": "booking_events", "channels": {"email": False}}]},
                headers=_csrf_headers(client),
            )
            assert patch_resp.status_code == 200, patch_resp.text
            updated = patch_resp.json()
            booking = next(t for t in updated["topics"] if t["id"] == "booking_events")
            assert booking["channels"]["email"] is False
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


def test_master_notification_settings_telegram_bot_link_request() -> None:
    email = f"notify_master_{uuid.uuid4().hex[:8]}@example.com"
    try:
        with TestClient(app) as client:
            _register_verified_master(client, email=email)

            link_resp = client.post(
                "/api/master/notification-settings/channels/telegram/link",
                json={},
                headers=_csrf_headers(client),
            )
            assert link_resp.status_code == 200, link_resp.text
            tg = next(c for c in link_resp.json()["channels"] if c["kind"] == "telegram")
            assert tg["connected"] is False
            assert tg["connect_url"] is not None
            assert "retention_studio_bot" in tg["connect_url"]
            assert "start=" in tg["connect_url"]

            unlink_resp = client.delete(
                "/api/master/notification-settings/channels/telegram",
                headers=_csrf_headers(client),
            )
            assert unlink_resp.status_code == 200, unlink_resp.text
            tg = next(c for c in unlink_resp.json()["channels"] if c["kind"] == "telegram")
            assert tg["connected"] is False
    except Exception as exc:
        _skip_if_unreachable(exc)
        raise


@pytest.mark.asyncio
async def test_delivery_channels_respects_disabled_email_pref() -> None:
    user_id = uuid.uuid4()
    repo = AsyncMock()
    repo.is_channel_enabled_for_event = AsyncMock(return_value=False)
    repo.get_channel = AsyncMock(return_value=None)

    channels = await delivery_channels_for_user(
        repo,
        user_id=user_id,
        event_type=NotificationEventType.BOOKING_CREATED,
    )
    assert channels == []
    assert repo.is_channel_enabled_for_event.await_count == len(
        (DeliveryChannel.EMAIL, DeliveryChannel.TELEGRAM, DeliveryChannel.SMS),
    )
    email_calls = [
        c
        for c in repo.is_channel_enabled_for_event.await_args_list
        if c.args[1] == DeliveryChannel.EMAIL
    ]
    assert len(email_calls) == 1
    assert email_calls[0].kwargs["category"] == PreferenceCategory.BOOKING


@pytest.mark.asyncio
async def test_delivery_channels_includes_telegram_when_linked_and_enabled() -> None:
    user_id = uuid.uuid4()
    repo = AsyncMock()

    async def enabled(user_id_arg, channel, event_type, *, category):
        return channel in {DeliveryChannel.EMAIL, DeliveryChannel.TELEGRAM}

    repo.is_channel_enabled_for_event = AsyncMock(side_effect=enabled)
    repo.get_channel = AsyncMock(
        return_value=type("Ch", (), {"is_verified": True, "address": "@u"})(),
    )

    channels = await delivery_channels_for_user(
        repo,
        user_id=user_id,
        event_type=NotificationEventType.BOOKING_CREATED,
    )
    assert DeliveryChannel.EMAIL in channels
    assert DeliveryChannel.TELEGRAM in channels
