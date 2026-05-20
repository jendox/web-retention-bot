from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_user
from app.core.pagination import Pagination, get_pagination
from app.models.user import User
from app.schemas.errors import ErrorDetail
from app.schemas.notification import UserNotificationOut, UserNotificationsListOut
from app.use_cases.notifications.exceptions import NotificationNotFoundError
from app.use_cases.notifications.list import (
    ListMasterNotificationsUseCase,
    MarkNotificationReadUseCase,
    get_list_master_notifications_use_case,
    get_mark_notification_read_use_case,
)

router = APIRouter(prefix="/notifications", tags=["master-notifications"])


def _raise_not_found(_exc: NotificationNotFoundError) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found") from None


@router.get(
    path="/me",
    summary="Current user's in-app notifications (master cabinet)",
    response_model=UserNotificationsListOut,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
    },
)
async def list_my_notifications(
    user: Annotated[User, Depends(require_user)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    use_case: Annotated[ListMasterNotificationsUseCase, Depends(get_list_master_notifications_use_case)],
) -> UserNotificationsListOut:
    return await use_case(user, pagination)


@router.post(
    path="/{notification_id}/read",
    summary="Mark a notification as read",
    response_model=UserNotificationOut,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail},
    },
)
async def mark_notification_read(
    notification_id: UUID,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[MarkNotificationReadUseCase, Depends(get_mark_notification_read_use_case)],
) -> UserNotificationOut:
    try:
        return await use_case(user, notification_id)
    except NotificationNotFoundError as exc:
        _raise_not_found(exc)
