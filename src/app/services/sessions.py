from __future__ import annotations

import secrets
from uuid import UUID

import redis.asyncio as redis_async

__all__ = ["SessionStore"]

SESSION_PREFIX = "sess:"


class SessionStore:
    def __init__(self, client: redis_async.Redis) -> None:
        self.client = client

    async def create(self, user_id: UUID, ttl_seconds: int) -> str:
        token = secrets.token_urlsafe(32)
        key = f"{SESSION_PREFIX}{token}"
        await self.client.set(key, str(user_id), ex=ttl_seconds)
        return token

    async def destroy(self, session_token: str | None) -> None:
        if not session_token:
            return
        await self.client.delete(f"{SESSION_PREFIX}{session_token}")

    async def lookup_user(self, session_token: str | None) -> UUID | None:
        if not session_token:
            return None
        raw_user_id = await self.client.get(f"{SESSION_PREFIX}{session_token}")
        if not raw_user_id:
            return None
        try:
            return UUID(str(raw_user_id))
        except (TypeError, ValueError):
            return None
