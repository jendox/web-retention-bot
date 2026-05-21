from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.security import hash_password
from app.core.structured_logging import get_logger, log_context
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.auth import RegisterAcceptedOut, RegisterClientPayload, RegisterMasterPayload
from app.schemas.user import UserSchema
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.services.schedule_defaults import default_weekly_schedule_days
from app.use_cases.auth.exceptions import UserAlreadyExistsError

__all__ = [
    "RegisterMasterAccountUseCase",
    "get_register_master_account_use_case",
    "RegisterClientAccountUseCase",
    "get_register_client_account_use_case",
]

logger = get_logger("app.register")


async def _register_user(
    user_repo: UserRepository,
    *,
    email: str,
    password: str,
) -> UserSchema:
    email_norm = email.strip().lower()
    existing = await user_repo.get_by_email(email_norm)
    if existing is not None:
        logger.info("register_user.failed", reason="user_already_exists", user_id=str(existing.id))
        raise UserAlreadyExistsError()
    user = await user_repo.create(
        email=email_norm,
        password_hash=hash_password(password),
    )
    logger.info("register_user.success", user_id=str(user.id))
    return UserSchema.model_validate(user)


class RegisterMasterAccountUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        master_repo: MasterRepository,
        schedule_repo: ScheduleRepository,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._user_repo = user_repo
        self._master_repo = master_repo
        self._schedule_repo = schedule_repo
        self._dispatcher = dispatcher

    async def __call__(self, payload: RegisterMasterPayload) -> RegisterAcceptedOut:
        normalized_email = payload.email.strip().lower()
        with log_context(use_case="register_master_account", email=normalized_email):
            user = await _register_user(self._user_repo, email=normalized_email, password=payload.password)
            master = await self._master_repo.get_by_user_id(user_id=user.id)
            if master is None:
                master = await self._master_repo.create(
                    user_id=user.id,
                    display_name=payload.master_display_name,
                    contact_email=user.email,
                )
                days = default_weekly_schedule_days(master.id)
                await self._schedule_repo.add_weekly_days(days)
                logger.info("created", master_id=str(master.id))
                await self._dispatcher.dispatch_email_verification(user_id=user.id, to_email=user.email)
            else:
                logger.info("exists", master_id=str(master.id))

            return RegisterAcceptedOut(id=user.id, email=user.email)


def get_register_master_account_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RegisterMasterAccountUseCase:
    return RegisterMasterAccountUseCase(user_repo, master_repo, schedule_repo, dispatcher)


class RegisterClientAccountUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._user_repo = user_repo
        self._dispatcher = dispatcher

    async def __call__(self, payload: RegisterClientPayload) -> RegisterAcceptedOut:
        normalized_email = payload.email.strip().lower()
        with log_context(use_case="register_client_account", email=normalized_email):
            user = await _register_user(self._user_repo, email=normalized_email, password=payload.password)
            logger.info("success")
            await self._dispatcher.dispatch_email_verification(user_id=user.id, to_email=user.email)

            return RegisterAcceptedOut(id=user.id, email=user.email)


def get_register_client_account_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RegisterClientAccountUseCase:
    return RegisterClientAccountUseCase(user_repo, dispatcher)
