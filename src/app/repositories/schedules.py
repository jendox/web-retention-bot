from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models import ScheduleDateOverride, WeeklyScheduleDay
from app.repositories.base import BaseRepository

__all__ = ["ScheduleRepository", "get_schedule_repo"]


class ScheduleRepository(BaseRepository):
    async def weekly_days_for_master(self, master_id: UUID) -> list[WeeklyScheduleDay]:
        stmt = (
            select(WeeklyScheduleDay)
            .where(WeeklyScheduleDay.master_id == master_id)
            .options(selectinload(WeeklyScheduleDay.intervals))
            .order_by(WeeklyScheduleDay.weekday)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def add_weekly_days(self, days: list[WeeklyScheduleDay]) -> None:
        self.session.add_all(days)
        await self.session.flush()

    async def replace_weekly_days(self, master_id: UUID, days: list[WeeklyScheduleDay]) -> None:
        await self.session.execute(
            delete(WeeklyScheduleDay).where(WeeklyScheduleDay.master_id == master_id),
        )
        self.session.add_all(days)

    async def date_overrides_for_master(self, master_id: UUID) -> list[ScheduleDateOverride]:
        stmt = (
            select(ScheduleDateOverride)
            .where(ScheduleDateOverride.master_id == master_id)
            .options(selectinload(ScheduleDateOverride.intervals))
            .order_by(ScheduleDateOverride.schedule_date)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def replace_date_overrides(self, master_id: UUID, items: list[ScheduleDateOverride]) -> None:
        await self.session.execute(
            delete(ScheduleDateOverride).where(ScheduleDateOverride.master_id == master_id),
        )
        self.session.add_all(items)


def get_schedule_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScheduleRepository:
    return ScheduleRepository(session)
