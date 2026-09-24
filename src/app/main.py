from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.worker.celery_app as _celery_app  # noqa: F401  # side effect: configure Celery before task imports
from app.admin import mount_admin
from app.api.errors import app_error_handler
from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Database
from app.core.exceptions import AppError
from app.core.middlewares import REQUEST_ID_HEADER, CSRFMiddleware, RateLimitMiddleware, RequestContextMiddleware
from app.core.structured_logging import configure_structlog


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        _app.state.redis = redis.from_url(_app.state.settings.infra.redis_url, decode_responses=True)
        async with Database.lifespan(url=_app.state.settings.infra.database_url):
            yield
    finally:
        if _app.state.redis:
            await _app.state.redis.aclose()


def create_application() -> FastAPI:
    settings = get_settings()
    configure_structlog(
        debug=settings.app_env.lower() in {"dev", "development", "local", "test"},
        json_logs=settings.app_env.lower() not in {"dev", "development", "local", "test"},
    )
    _app = FastAPI(
        title="Retention Scheduling API",
        lifespan=lifespan,
    )
    _app.state.settings = settings

    _app.add_exception_handler(AppError, app_error_handler)

    _app.add_middleware(CSRFMiddleware)
    _app.add_middleware(RateLimitMiddleware)
    _app.add_middleware(RequestContextMiddleware)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    _app.include_router(api_router, prefix="/api")
    mount_admin(_app, settings)

    @_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return _app


app = create_application()
