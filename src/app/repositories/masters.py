from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import Base, get_db_session
from app.models.master import MasterProfile
from app.repositories.base import BaseRepository


class MasterRepository(BaseRepository):
    async def get_by_user_id(self, user_id: UUID) -> MasterProfile | None:
        stmt = select(MasterProfile).where(MasterProfile.user_id == user_id)
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()

    async def get_by_master_id(self, master_id: UUID) -> MasterProfile | None:
        stmt = (
            select(MasterProfile)
            .where(MasterProfile.id == master_id)
            .options(selectinload(MasterProfile.user))
        )
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        display_name: str,
        public_slug: str | None = None,
        contact_email: str | None = None,
    ) -> MasterProfile:
        profile = MasterProfile(
            user_id=user_id,
            display_name=display_name,
            public_slug=public_slug,
            contact_email=contact_email,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, obj: Base) -> None:
        await self.session.refresh(obj)


def get_master_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MasterRepository:
    return MasterRepository(session)
