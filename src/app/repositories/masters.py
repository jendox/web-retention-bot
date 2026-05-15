from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
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
    ) -> MasterProfile:
        profile = MasterProfile(
            user_id=user_id,
            display_name=display_name,
            public_slug=public_slug,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile


def get_master_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MasterRepository:
    return MasterRepository(session)
