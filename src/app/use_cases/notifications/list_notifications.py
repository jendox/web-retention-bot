from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.pagination import Pagination
from app.models import UserNotification
from app.repositories.notifications import UserNotificationRepository, get_user_notification_repo
from app.schemas.notification import UserNotificationOut, UserNotificationsListOut

__all__ = [
    "ListMasterNotificationsUseCase",
    "get_list_master_notifications_use_case",
    "ListClientNotificationsUseCase",
    "get_list_client_notifications_use_case",
]


async def _list_cabinet_notifications(
    *,
    user_id: UUID,
    pagination: Pagination,
    count_total: Callable[[UUID], Awaitable[int]],
    list_page: Callable[..., Awaitable[list[UserNotification]]],
    count_unread: Callable[[UUID], Awaitable[int]],
) -> UserNotificationsListOut:
    total = await count_total(user_id)
    items = await list_page(
        user_id,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    unread_count = await count_unread(user_id)
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

    async def __call__(self, user_id: UUID, pagination: Pagination) -> UserNotificationsListOut:
        repo = self._notification_repo
        return await _list_cabinet_notifications(
            user_id=user_id,
            pagination=pagination,
            count_total=repo.count_for_client_cabinet,
            list_page=repo.list_for_client_cabinet_page,
            count_unread=repo.count_unread_for_client_cabinet,
        )


class ListMasterNotificationsUseCase:
    def __init__(self, notification_repo: UserNotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def __call__(self, user_id: UUID, pagination: Pagination) -> UserNotificationsListOut:
        repo = self._notification_repo
        return await _list_cabinet_notifications(
            user_id=user_id,
            pagination=pagination,
            count_total=repo.count_for_master_cabinet,
            list_page=repo.list_for_master_cabinet_page,
            count_unread=repo.count_unread_for_master_cabinet,
        )


def get_list_client_notifications_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> ListClientNotificationsUseCase:
    return ListClientNotificationsUseCase(notification_repo)


def get_list_master_notifications_use_case(
    notification_repo: Annotated[UserNotificationRepository, Depends(get_user_notification_repo)],
) -> ListMasterNotificationsUseCase:
    return ListMasterNotificationsUseCase(notification_repo)
