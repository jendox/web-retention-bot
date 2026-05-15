import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

__all__ = [
    "Base",
    "Database",
    "get_db_session",
]

logger = logging.getLogger("db.sa")


class Base(DeclarativeBase):
    pass


class Database:
    engine: AsyncEngine | None = None
    session_maker: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    async def _init(cls, *, url: str, echo: bool) -> None:
        cls.engine = create_async_engine(
            url=url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=10,
        )
        cls.session_maker = async_sessionmaker(cls.engine, expire_on_commit=False, class_=AsyncSession)
        logger.info("db.engine.initialized")

    @classmethod
    async def _close(cls) -> None:
        if cls.engine is not None:
            await cls.engine.dispose()
            logger.info("db.engine.disposed")
        cls.engine = None
        cls.session_maker = None

    @classmethod
    def require_session_maker(cls) -> async_sessionmaker[AsyncSession]:
        if cls.session_maker is None:
            raise RuntimeError("DB session_maker is not initialized.")
        return cls.session_maker

    @classmethod
    @asynccontextmanager
    async def lifespan(cls, url: str, echo: bool = False) -> AsyncIterator[None]:
        await cls._init(url=url, echo=echo)
        try:
            yield
        finally:
            await cls._close()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_maker = Database.require_session_maker()
    async with session_maker() as session:
        async with session.begin():
            yield session
