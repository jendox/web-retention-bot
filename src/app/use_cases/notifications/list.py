from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.pagination import Pagination
from app.models.user import User
from app.repositories.notifications import UserNotificationRepository, get_user_notification_repo
from app.schemas.notification import UserNotificationOut, UserNotificationsListOut
from app.use_cases.notifications.exceptions import NotificationNotFoundError


class ListMyNotificationsUseCase:
    def __init__(self, notification_repo: UserNotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def __call__(self, user: User, pagination: Pagination) -> UserNotificationsListOut:
        total = await self._notification_repo.count_for_user(user.id)
        items = await self._notification_repo.list_for_user_page(
            user.id,
            limit=pagination.page_size,
            offset=pagination.offset,
        )
        unread_count = await self._notification_repo.count_unread_for_user(user.id)
        return UserNotificationsListOut(
            items=[UserNotificationOut.model_validate(item) for item in items],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            unread_count=unread_count,
        )


class MarkNotificationReadUseCase:
    def __init__(self, notification_repo: UserNotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def __call__(self, user: User, notification_id: UUID) -> UserNotificationOut:
        note = await self._notification_repo.get_for_user(notification_id, user.id)
        if note is None:
            raise NotificationNotFoundError()
        if note.read_at is None:
            note.read_at = datetime.now(UTC)
            await self._notification_repo.flush()
        return UserNotificationOut.model_validate(note)


def get_list_my_notifications_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> ListMyNotificationsUseCase:
    return ListMyNotificationsUseCase(notification_repo)


def get_mark_notification_read_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> MarkNotificationReadUseCase:
    return MarkNotificationReadUseCase(notification_repo)
