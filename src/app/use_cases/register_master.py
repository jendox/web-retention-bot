from __future__ import annotations

from datetime import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.schedule import WeeklyScheduleRule
from app.repositories.masters import MasterRepository, get_master_repo
from app.schemas.master import MasterProfileSchema
from app.schemas.user import UserSchema

__all__ = [
    "RegisterMasterUseCase",
    "get_register_master_use_case",
]

logger = get_logger("app.register_master")

DEFAULT_WORKING_WEEKDAYS = range(5)
DEFAULT_WORKDAY_START = time(10, 0)
DEFAULT_WORKDAY_END = time(18, 0)


def default_weekly_schedule_rules(master_id: UUID) -> list[WeeklyScheduleRule]:
    return [
        WeeklyScheduleRule(
            master_id=master_id,
            weekday=weekday,
            start_time=DEFAULT_WORKDAY_START,
            end_time=DEFAULT_WORKDAY_END,
        )
        for weekday in DEFAULT_WORKING_WEEKDAYS
    ]


class RegisterMasterUseCase:
    def __init__(self, master_repo: MasterRepository) -> None:
        self.master_repo = master_repo

    async def __call__(self, user: UserSchema, display_name: str) -> MasterProfileSchema:
        with log_context(use_case="register_master_profile", user_id=str(user.id)):
            master = await self.master_repo.get_by_user_id(user_id=user.id)
            if master is None:
                master = await self.master_repo.create(
                    user_id=user.id,
                    display_name=display_name,
                )
                self.master_repo.session.add_all(default_weekly_schedule_rules(master.id))
                await self.master_repo.session.flush()
                logger.info("created", master_id=str(master.id))
            else:
                logger.info("exists", master_id=str(master.id))

            return MasterProfileSchema.model_validate(master)


def get_register_master_use_case(
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
) -> RegisterMasterUseCase:
    return RegisterMasterUseCase(master_repo)
