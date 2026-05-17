"""Schedule recurring + overrides persistence."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.models.schedule import WeeklyScheduleRule, WorkdayOverride
from app.repositories.base import BaseRepository


class ScheduleRepository(BaseRepository):
    async def weekly_for_master(self, master_id: UUID) -> list[WeeklyScheduleRule]:
        stmt = select(WeeklyScheduleRule).where(WeeklyScheduleRule.master_id == master_id)
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def replace_weekly_rules(self, master_id: UUID, rules: list[WeeklyScheduleRule]) -> None:
        await self.session.execute(delete(WeeklyScheduleRule).where(WeeklyScheduleRule.master_id == master_id))
        self.session.add_all(rules)

    async def overrides_for_master(self, master_id: UUID) -> list[WorkdayOverride]:
        stmt = (
            select(WorkdayOverride)
            .where(WorkdayOverride.master_id == master_id)
            .options(selectinload(WorkdayOverride.intervals))
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def replace_overrides(self, master_id: UUID, items: list[WorkdayOverride]) -> None:
        await self.session.execute(delete(WorkdayOverride).where(WorkdayOverride.master_id == master_id))
        self.session.add_all(items)
