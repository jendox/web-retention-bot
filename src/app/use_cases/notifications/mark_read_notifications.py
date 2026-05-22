from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import UserNotification
from app.repositories.notifications import UserNotificationRepository, get_user_notification_repo
from app.schemas.notification import UserNotificationOut
from app.use_cases.notifications.exceptions import NotificationNotFoundError

__all__ = ["MarkNotificationReadUseCase", "get_mark_notification_read_use_case"]

logger = get_logger("app.notifications")


class MarkNotificationReadUseCase:
    def __init__(self, notification_repo: UserNotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def _mark_as_read(self, notification: UserNotification) -> None:
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await self._notification_repo.flush()

    async def __call__(self, *, user_id: UUID, notification_id: UUID) -> UserNotificationOut:
        with log_context(
            use_case="mark_notification_read", user_id=str(user_id), notification_id=str(notification_id),
        ):
            notification = await self._notification_repo.get_for_user(notification_id, user_id)
            if notification is None:
                logger.warning("failed", reason="notification_not_found")
                raise NotificationNotFoundError()

            await self._mark_as_read(notification)

            return UserNotificationOut.model_validate(notification)


def get_mark_notification_read_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> MarkNotificationReadUseCase:
    return MarkNotificationReadUseCase(notification_repo)
