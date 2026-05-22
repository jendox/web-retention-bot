from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import require_user
from app.core.pagination import Pagination, get_pagination
from app.models.user import User
from app.schemas.errors import ErrorDetail
from app.schemas.notification import UserNotificationOut, UserNotificationsListOut
from app.use_cases.notifications import (
    ListClientNotificationsUseCase,
    MarkNotificationReadUseCase,
    get_list_client_notifications_use_case,
    get_mark_notification_read_use_case,
)

router = APIRouter(prefix="/notifications", tags=["client-notifications"])


@router.get(
    path="/me",
    summary="Current user's in-app notifications (client cabinet)",
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
    use_case: Annotated[ListClientNotificationsUseCase, Depends(get_list_client_notifications_use_case)],
) -> UserNotificationsListOut:
    return await use_case(user_id=user.id, pagination=pagination)


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
    return await use_case(user_id=user.id, notification_id=notification_id)
