from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request
from redis.asyncio import Redis

RateLimitKeyBuilder = Callable[[Request], Awaitable[str | None]]


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    method: str
    path: str
    limit: int
    window_seconds: int
    key_builder: RateLimitKeyBuilder
    regex: bool = False


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_after: int


@dataclass(frozen=True)
class MatchedRateLimitPolicy:
    policy: RateLimitPolicy
    path_match: re.Match[str] | None = None


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


async def by_ip(request: Request) -> str:
    return client_ip(request)


async def by_json_field(request: Request, field: str) -> str | None:
    try:
        body = await request.json()
    except Exception:
        return None

    value = body.get(field)
    if value is None:
        return None

    return str(value).strip().lower()


def json_field(field: str) -> RateLimitKeyBuilder:
    async def build(request: Request) -> str | None:
        return await by_json_field(request, field)

    return build


def ip_and_json_field(field: str) -> RateLimitKeyBuilder:
    async def build(request: Request) -> str | None:
        value = await by_json_field(request, field)
        if not value:
            return None
        return f"{client_ip(request)}:{value}"

    return build


def match_rate_limit_policies(
    *,
    policies: list[RateLimitPolicy],
    method: str,
    path: str,
) -> list[MatchedRateLimitPolicy]:
    normalized_method = method.upper()
    matched: list[MatchedRateLimitPolicy] = []

    for policy in policies:
        if policy.method.upper() != normalized_method:
            continue

        if policy.regex:
            path_match = re.match(policy.path, path)
            if path_match is not None:
                matched.append(MatchedRateLimitPolicy(policy=policy, path_match=path_match))
            continue

        if policy.path == path:
            matched.append(MatchedRateLimitPolicy(policy=policy))

    return matched


RATE_LIMIT_POLICIES: list[RateLimitPolicy] = [
    RateLimitPolicy(
        name="auth_csrf_ip",
        method="GET",
        path="/api/auth/csrf",
        limit=120,
        window_seconds=60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_register_master_ip",
        method="POST",
        path="/api/auth/register-master",
        limit=10,
        window_seconds=60 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_register_master_email",
        method="POST",
        path="/api/auth/register-master",
        limit=3,
        window_seconds=60 * 60,
        key_builder=json_field("email"),
    ),
    RateLimitPolicy(
        name="auth_register_client_ip",
        method="POST",
        path="/api/auth/register-client",
        limit=10,
        window_seconds=60 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_register_client_email",
        method="POST",
        path="/api/auth/register-client",
        limit=3,
        window_seconds=60 * 60,
        key_builder=json_field("email"),
    ),
    RateLimitPolicy(
        name="auth_login_ip",
        method="POST",
        path="/api/auth/login",
        limit=30,
        window_seconds=15 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_login_email",
        method="POST",
        path="/api/auth/login",
        limit=10,
        window_seconds=15 * 60,
        key_builder=json_field("email"),
    ),
    RateLimitPolicy(
        name="auth_login_ip_email",
        method="POST",
        path="/api/auth/login",
        limit=5,
        window_seconds=15 * 60,
        key_builder=ip_and_json_field("email"),
    ),
    RateLimitPolicy(
        name="auth_verify_email_ip",
        method="POST",
        path="/api/auth/verify-email",
        limit=30,
        window_seconds=15 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_forgot_password_ip",
        method="POST",
        path="/api/auth/forgot-password",
        limit=5,
        window_seconds=15 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_forgot_password_email",
        method="POST",
        path="/api/auth/forgot-password",
        limit=3,
        window_seconds=60 * 60,
        key_builder=json_field("email"),
    ),
    RateLimitPolicy(
        name="auth_reset_password_ip",
        method="POST",
        path="/api/auth/reset-password",
        limit=10,
        window_seconds=15 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="auth_change_password_ip",
        method="POST",
        path="/api/auth/change-password",
        limit=5,
        window_seconds=15 * 60,
        key_builder=by_ip,
    ),
    RateLimitPolicy(
        name="invite_accept_ip",
        method="POST",
        path=r"^/api/invitations/[^/]+/accept$",
        limit=20,
        window_seconds=15 * 60,
        key_builder=by_ip,
        regex=True,
    ),
]


class RedisRateLimiter:
    def __init__(self, redis: Redis, *, prefix: str = "rate_limit") -> None:
        self._redis = redis
        self._prefix = prefix

    async def check(
        self,
        *,
        policy: RateLimitPolicy,
        identity: str,
    ) -> RateLimitResult:
        now = int(time.time())
        window_start = now - (now % policy.window_seconds)
        reset_at = window_start + policy.window_seconds
        retry_after = max(reset_at - now, 1)

        key = f"{self._prefix}:{policy.name}:{identity}:{window_start}"
        current = await self._redis.incr(key)
        if current == 1:
            await self._redis.expire(key, policy.window_seconds)

        remaining = max(policy.limit - current, 0)

        return RateLimitResult(
            allowed=current <= policy.limit,
            limit=policy.limit,
            remaining=remaining,
            retry_after=retry_after,
            reset_after=retry_after,
        )
