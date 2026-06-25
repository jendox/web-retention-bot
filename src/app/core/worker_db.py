from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import Database

__all__ = ["worker_db_session"]


async def _ensure_database() -> None:
    if Database.engine is None:
        settings = get_settings()
        await Database._init(url=settings.infra.database_url, echo=False)


@asynccontextmanager
async def worker_db_session() -> AsyncGenerator[AsyncSession]:
    await _ensure_database()
    session_maker = Database.require_session_maker()

    async with session_maker() as session:
        async with session.begin():
            yield session
