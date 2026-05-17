from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


@dataclass
class BaseRepository:
    session: AsyncSession

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, obj: Base) -> None:
        await self.session.refresh(obj)
