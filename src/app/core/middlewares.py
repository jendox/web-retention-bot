from __future__ import annotations

import secrets
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.structured_logging import bind_request_context, clear_log_context, get_logger

REQUEST_ID_HEADER = "X-Request-Id"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/health",
    }
)
CSRF_ERROR_DETAIL = "CSRF token missing or invalid"

logger = get_logger("app.requestctx_middleware")
csrf_logger = get_logger("app.csrf_middleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if (
            request.method.upper() in SAFE_METHODS
            or request.url.path in CSRF_EXEMPT_PATHS
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
            logger.exception("unhandled_exception")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "request_id": request_id},
                headers={REQUEST_ID_HEADER: request_id},
            )
        finally:
            clear_log_context()
