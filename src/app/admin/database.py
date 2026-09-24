from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

__all__ = ["create_admin_engine", "sync_database_url"]


def sync_database_url(database_url: str) -> str:
    if "+asyncpg" in database_url:
        return database_url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    if database_url.startswith("sqlite+aiosqlite"):
        return database_url.replace("sqlite+aiosqlite", "sqlite", 1)
    return database_url


def create_admin_engine(database_url: str) -> Engine:
    return create_engine(
        sync_database_url(database_url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
