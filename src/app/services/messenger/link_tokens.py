from __future__ import annotations

import secrets
from typing import Annotated
from uuid import UUID

import redis.asyncio as redis_async
from fastapi import Depends, Request

from app.services.messenger.providers import MessengerProvider

LINK_PREFIX = "messenger:link:"
PENDING_PREFIX = "messenger:pending:"
DEFAULT_TTL_SECONDS = 900


class MessengerLinkTokenStore:
    def __init__(self, client: redis_async.Redis, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    def _key(self, provider: MessengerProvider, token: str) -> str:
        return f"{LINK_PREFIX}{provider.value}:{token}"

    async def create(self, user_id: UUID, provider: MessengerProvider) -> str:
        token = secrets.token_urlsafe(24)
        await self._client.set(
            self._key(provider, token),
            str(user_id),
            ex=self._ttl_seconds,
        )
        return token

    def _pending_key(self, user_id: UUID, provider: MessengerProvider) -> str:
        return f"{PENDING_PREFIX}{provider.value}:{user_id}"

    async def remember_pending(self, user_id: UUID, provider: MessengerProvider, token: str) -> None:
        await self._client.set(self._pending_key(user_id, provider), token, ex=self._ttl_seconds)

    async def get_pending_token(self, user_id: UUID, provider: MessengerProvider) -> str | None:
        raw = await self._client.get(self._pending_key(user_id, provider))
        if not raw:
            return None
        if isinstance(raw, bytes):
            return raw.decode()
        return str(raw)

    async def clear_pending(self, user_id: UUID, provider: MessengerProvider) -> None:
        await self._client.delete(self._pending_key(user_id, provider))

    async def consume(self, provider: MessengerProvider, token: str) -> UUID | None:
        key = self._key(provider, token)
        raw = await self._client.getdel(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            user_id = UUID(raw)
        except (TypeError, ValueError):
            return None
        await self.clear_pending(user_id, provider)
        return user_id


def get_messenger_link_token_store(request: Request) -> MessengerLinkTokenStore:
    settings = request.app.state.settings
    ttl = settings.messenger_bots.link_token_ttl_seconds
    return MessengerLinkTokenStore(request.app.state.redis, ttl_seconds=ttl)


def get_messenger_link_token_store_dep(
    store: Annotated[MessengerLinkTokenStore, Depends(get_messenger_link_token_store)],
) -> MessengerLinkTokenStore:
    return store
