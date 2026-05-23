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
    ListMasterNotificationsUseCase,
    MarkNotificationReadUseCase,
    get_list_master_notifications_use_case,
    get_mark_notification_read_use_case,
)

router = APIRouter(prefix="/notifications", tags=["master-notifications"])


@router.get(
    path="/me",
    summary="Current user's in-app notifications (master cabinet)",
    description=(
        "Returns a paginated in-app notification feed for the current user in the master cabinet, including the "
        "total unread count used by the header badge."
    ),
    response_model=UserNotificationsListOut,
    status_code=status.HTTP_200_OK,
    response_description="Paginated notification feed and unread count.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
    },
)
async def list_my_notifications(
    user: Annotated[User, Depends(require_user)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    use_case: Annotated[ListMasterNotificationsUseCase, Depends(get_list_master_notifications_use_case)],
) -> UserNotificationsListOut:
    return await use_case(user_id=user.id, pagination=pagination)


@router.post(
    path="/{notification_id}/read",
    summary="Mark a notification as read",
    description="Marks one in-app notification owned by the current user as read and returns the updated row.",
    response_model=UserNotificationOut,
    status_code=status.HTTP_200_OK,
    response_description="Notification with `read_at` set.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Notification not found for this user."},
    },
)
async def mark_notification_read(
    notification_id: UUID,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[MarkNotificationReadUseCase, Depends(get_mark_notification_read_use_case)],
) -> UserNotificationOut:
    return await use_case(user_id=user.id, notification_id=notification_id)
