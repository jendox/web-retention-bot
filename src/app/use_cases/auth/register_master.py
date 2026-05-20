from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.schemas.master import MasterProfileSchema
from app.schemas.user import UserSchema
from app.services.schedule_defaults import default_weekly_schedule_days

__all__ = [
    "RegisterMasterUseCase",
    "get_register_master_use_case",
]

logger = get_logger("app.register_master")


class RegisterMasterUseCase:
    def __init__(
        self,
        master_repo: MasterRepository,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self._master_repo = master_repo
        self._schedule_repo = schedule_repo

    async def __call__(self, user: UserSchema, display_name: str) -> MasterProfileSchema:
        with log_context(use_case="register_master_profile", user_id=str(user.id)):
            master = await self._master_repo.get_by_user_id(user_id=user.id)
            if master is None:
                master = await self._master_repo.create(
                    user_id=user.id,
                    display_name=display_name,
                    contact_email=str(user.email).lower(),
                )
                days = default_weekly_schedule_days(master.id)
                await self._schedule_repo.add_weekly_days(days)
                logger.info("created", master_id=str(master.id))
            else:
                logger.info("exists", master_id=str(master.id))

            return MasterProfileSchema.model_validate(master)


def get_register_master_use_case(
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
) -> RegisterMasterUseCase:
    return RegisterMasterUseCase(master_repo, schedule_repo)
