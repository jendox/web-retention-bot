from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.schemas.master import MasterScheduleOut, ScheduleDateOverrideOut, WeeklyScheduleDayOut

__all__ = [
    "GetMasterScheduleUseCase",
    "get_get_master_schedule_use_case",
]

logger = get_logger("app.schedule")


class GetMasterScheduleUseCase:
    def __init__(self, schedule_repo: ScheduleRepository) -> None:
        self._schedule_repo = schedule_repo

    async def _get_weekly_days_for_master(self, master_id: UUID) -> list[WeeklyScheduleDayOut]:
        weekly_days_models = await self._schedule_repo.weekly_days_for_master(master_id)
        return [
            WeeklyScheduleDayOut.model_validate(weekly_day)
            for weekly_day in weekly_days_models
        ]

    async def _get_overrides_for_master(self, master_id: UUID) -> list[ScheduleDateOverrideOut]:
        date_overrides_models = await self._schedule_repo.date_overrides_for_master(master_id)
        return [
            ScheduleDateOverrideOut.model_validate(override)
            for override in date_overrides_models
        ]

    async def __call__(self, master_id: UUID) -> MasterScheduleOut:
        with log_context(use_case="get_master_schedule", master_id=str(master_id)):
            days = await self._get_weekly_days_for_master(master_id)
            overrides = await self._get_overrides_for_master(master_id)

            return MasterScheduleOut(
                weekly_days=days,
                date_overrides=overrides,
            )


def get_get_master_schedule_use_case(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
) -> GetMasterScheduleUseCase:
    return GetMasterScheduleUseCase(schedule_repo)
