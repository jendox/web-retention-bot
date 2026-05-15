from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.worker.celery_app  # noqa: F401  # side effect: configure Celery before task imports
from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Database


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
    _app = FastAPI(
        title="Retention Scheduling API",
        lifespan=lifespan,
    )
    _app.state.settings = settings
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _app.include_router(api_router, prefix="/api")

    @_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return _app

app = create_application()
