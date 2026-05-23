from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.users import UserRepository, get_user_repo
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher

__all__ = ["ForgotPasswordUseCase", "get_forgot_password_use_case"]

logger = get_logger("app.forgot_password")


class ForgotPasswordUseCase:
    def __init__(self, user_repo: UserRepository, dispatcher: NotificationDispatcher) -> None:
        self._user_repo = user_repo
        self._dispatcher = dispatcher

    async def __call__(self, *, email: str) -> None:
        email_norm = email.strip().lower()
        with log_context(use_case="forgot_password", email=email_norm):
            user = await self._user_repo.get_by_email(email_norm)
            if user is None:
                logger.info("skipped", reason="user_not_found")
                return

            if not user.is_active:
                logger.info("skipped", reason="user_inactive")
                return

            if user.email_verified_at is None:
                logger.info("skipped", reason="user_unverified")
                return

            await self._dispatcher.dispatch_password_reset(user_id=user.id, to_email=user.email)
            logger.info("email_enqueued")


def get_forgot_password_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> ForgotPasswordUseCase:
    return ForgotPasswordUseCase(user_repo, dispatcher)
