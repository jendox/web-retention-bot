from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.models import ScheduleDateOverride, WeeklyScheduleDay
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.schemas.master import MasterScheduleOut, ScheduleDateOverrideOut, WeeklyScheduleDayOut

__all__ = [
    "GetMasterScheduleUseCase",
    "get_get_master_schedule_use_case",
]


class GetMasterScheduleUseCase:
    def __init__(
        self,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self._schedule_repo = schedule_repo

    async def __call__(self, master_id: UUID) -> MasterScheduleOut:
        weekly_days_models: list[WeeklyScheduleDay] = await self._schedule_repo.weekly_days_for_master(master_id)
        date_overrides_models: list[ScheduleDateOverride] = (
            await self._schedule_repo.date_overrides_for_master(master_id)
        )

        days = [
            WeeklyScheduleDayOut.model_validate(weekly_day)
            for weekly_day in weekly_days_models
        ]

        overrides = [
            ScheduleDateOverrideOut.model_validate(override)
            for override in date_overrides_models
        ]
        return MasterScheduleOut(
            weekly_days=days,
            date_overrides=overrides,
        )


def get_get_master_schedule_use_case(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
) -> GetMasterScheduleUseCase:
    return GetMasterScheduleUseCase(schedule_repo)
