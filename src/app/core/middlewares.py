from __future__ import annotations

import secrets
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rate_limit import RATE_LIMIT_POLICIES, RedisRateLimiter, match_rate_limit_policies
from app.core.structured_logging import bind_request_context, clear_log_context, get_logger

REQUEST_ID_HEADER = "X-Request-Id"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/health",
    },
)


def _csrf_exempt(path: str) -> bool:
    return path in CSRF_EXEMPT_PATHS or path.startswith("/api/internal/")


CSRF_ERROR_DETAIL = "CSRF token missing or invalid"
RATE_LIMIT_ERROR_DETAIL = "Too many requests"

request_ctx_logger = get_logger("app.request_ctx_middleware")
csrf_logger = get_logger("app.csrf_middleware")
rate_limit_logger = get_logger("app.rate_limit_middleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if (
            request.method.upper() in SAFE_METHODS
            or _csrf_exempt(request.url.path)
            or not request.url.path.startswith("/api/")
        ):
            return await call_next(request)

        settings = request.app.state.settings
        cookie_token = request.cookies.get(settings.session.csrf_cookie_name)
        header_token = request.headers.get(settings.session.csrf_header_name)
        if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
            csrf_logger.warning("csrf_rejected")
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": CSRF_ERROR_DETAIL})

        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        bind_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            request_ctx_logger.exception("unhandled_exception")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "request_id": request_id},
                headers={REQUEST_ID_HEADER: request_id},
            )
        finally:
            clear_log_context()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        policies = match_rate_limit_policies(
            policies=RATE_LIMIT_POLICIES,
            method=request.method,
            path=request.url.path,
        )
        if not policies:
            return await call_next(request)

        redis = request.app.state.redis
        limiter = RedisRateLimiter(redis)

        for matched_policy in policies:
            policy = matched_policy.policy
            identity = await policy.key_builder(request)
            if not identity:
                continue

            result = await limiter.check(policy=policy, identity=identity)
            if not result.allowed:
                rate_limit_logger.warning(
                    "rate_limited",
                    rate_limit_policy=policy.name,
                    rate_limit_identity=identity,
                    rate_limit_limit=result.limit,
                    rate_limit_remaining=result.remaining,
                    rate_limit_retry_after=result.retry_after,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": RATE_LIMIT_ERROR_DETAIL},
                    headers={
                        "Retry-After": str(result.retry_after),
                        "X-RateLimit-Limit": str(result.limit),
                        "X-RateLimit-Remaining": str(result.remaining),
                        "X-RateLimit-Reset": str(result.reset_after),
                    },
                )

        return await call_next(request)
