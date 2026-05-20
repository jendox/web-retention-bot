"""Messenger bot link tokens and internal complete-link API."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.messenger.link_tokens import MessengerLinkTokenStore
from app.services.messenger.providers import MessengerProvider


@pytest.mark.asyncio
async def test_messenger_link_token_create_and_consume() -> None:
    user_id = uuid.uuid4()
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.getdel = AsyncMock(return_value=str(user_id))
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock()

    store = MessengerLinkTokenStore(redis, ttl_seconds=60)
    token = await store.create(user_id, MessengerProvider.TELEGRAM)
    assert token

    consumed = await store.consume(MessengerProvider.TELEGRAM, token)
    assert consumed == user_id
    redis.getdel.assert_awaited()


@pytest.mark.asyncio
async def test_messenger_pending_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value="pending-token")
    redis.delete = AsyncMock()

    store = MessengerLinkTokenStore(redis, ttl_seconds=60)
    await store.remember_pending(user_id, MessengerProvider.TELEGRAM, "pending-token")
    assert await store.get_pending_token(user_id, MessengerProvider.TELEGRAM) == "pending-token"
    await store.clear_pending(user_id, MessengerProvider.TELEGRAM)
    redis.delete.assert_awaited()


def test_internal_complete_link_requires_secret() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/internal/messenger/telegram/complete-link",
            json={"token": "abc", "external_id": "12345"},
        )
        assert resp.status_code == 401


def test_internal_complete_link_invalid_token() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/internal/messenger/telegram/complete-link",
            json={"token": "not-a-real-token-value", "external_id": "12345"},
            headers={"X-Bot-Secret": "dev-bot-internal-secret-change-me"},
        )
        assert resp.status_code == 400
