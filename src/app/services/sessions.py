from __future__ import annotations

import secrets
from typing import Annotated
from uuid import UUID

import redis.asyncio as redis_async
from fastapi import Depends, Request, Response

from app.core.config import Settings

__all__ = [
    "SessionStore",
    "get_session_store",
    "SessionManager",
    "get_session_manager",
]

SESSION_PREFIX = "sess:"


class SessionStore:
    def __init__(self, client: redis_async.Redis) -> None:
        self._client = client

    async def create(self, user_id: UUID, ttl_seconds: int) -> str:
        token = secrets.token_urlsafe(32)
        key = f"{SESSION_PREFIX}{token}"
        await self._client.set(key, str(user_id), ex=ttl_seconds)
        return token

    async def destroy(self, session_token: str | None) -> None:
        if not session_token:
            return
        await self._client.delete(f"{SESSION_PREFIX}{session_token}")

    async def lookup_user(self, session_token: str | None) -> UUID | None:
        if not session_token:
            return None
        raw_user_id = await self._client.get(f"{SESSION_PREFIX}{session_token}")
        if not raw_user_id:
            return None
        if isinstance(raw_user_id, bytes):
            raw_user_id = raw_user_id.decode()
        try:
            return UUID(raw_user_id)
        except (TypeError, ValueError):
            return None


class SessionManager:
    def __init__(
        self,
        session_store: SessionStore,
        settings: Settings,
    ) -> None:
        self._session_store = session_store
        self._session_cookie_name = settings.session.cookie_name
        self._csrf_cookie_name = settings.session.csrf_cookie_name
        self._cookie_secure = settings.session.cookie_secure
        self._ttl_seconds = settings.session.ttl_seconds

    def set_csrf_cookie(self, response: Response) -> str:
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            key=self._csrf_cookie_name,
            value=token,
            httponly=False,
            samesite="lax",
            secure=self._cookie_secure,
            max_age=self._ttl_seconds,
            path="/",
        )
        return token

    async def attach_session(self, response: Response, user_id: UUID) -> None:
        token = await self._session_store.create(user_id, self._ttl_seconds)
        response.set_cookie(
            key=self._session_cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            secure=self._cookie_secure,
            max_age=self._ttl_seconds,
            path="/",
        )
        self.set_csrf_cookie(response)

    async def clear_session(self, request: Request, response: Response) -> None:
        token = request.cookies.get(self._session_cookie_name)
        await self._session_store.destroy(token)
        response.delete_cookie(self._session_cookie_name, path="/")
        response.delete_cookie(self._csrf_cookie_name, path="/")


def get_session_store(
    request: Request,
) -> SessionStore:
    return SessionStore(request.app.state.redis)


def get_session_manager(
    request: Request,
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> SessionManager:
    return SessionManager(session_store, request.app.state.settings)
