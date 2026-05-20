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


async def _list_cabinet_notifications(
    repo: UserNotificationRepository,
    user: User,
    pagination: Pagination,
    *,
    count_total,
    list_page,
    count_unread,
) -> UserNotificationsListOut:
    total = await count_total(user.id)
    items = await list_page(
        user.id,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    unread_count = await count_unread(user.id)
    return UserNotificationsListOut(
        items=[UserNotificationOut.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        unread_count=unread_count,
    )


class ListClientNotificationsUseCase:
    def __init__(self, notification_repo: UserNotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def __call__(self, user: User, pagination: Pagination) -> UserNotificationsListOut:
        repo = self._notification_repo
        return await _list_cabinet_notifications(
            repo,
            user,
            pagination,
            count_total=repo.count_for_client_cabinet,
            list_page=repo.list_for_client_cabinet_page,
            count_unread=repo.count_unread_for_client_cabinet,
        )


class ListMasterNotificationsUseCase:
    def __init__(self, notification_repo: UserNotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def __call__(self, user: User, pagination: Pagination) -> UserNotificationsListOut:
        repo = self._notification_repo
        return await _list_cabinet_notifications(
            repo,
            user,
            pagination,
            count_total=repo.count_for_master_cabinet,
            list_page=repo.list_for_master_cabinet_page,
            count_unread=repo.count_unread_for_master_cabinet,
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


def get_list_client_notifications_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> ListClientNotificationsUseCase:
    return ListClientNotificationsUseCase(notification_repo)


def get_list_master_notifications_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> ListMasterNotificationsUseCase:
    return ListMasterNotificationsUseCase(notification_repo)


def get_mark_notification_read_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> MarkNotificationReadUseCase:
    return MarkNotificationReadUseCase(notification_repo)
