from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import require_user
from app.models.user import User
from app.schemas.errors import ErrorDetail
from app.schemas.notification_settings import (
    LinkNotificationChannelIn,
    NotificationSettingsOut,
    NotificationSettingsPatch,
)
from app.use_cases.notification_settings import (
    GetNotificationSettingsUseCase,
    LinkNotificationChannelUseCase,
    UnlinkNotificationChannelUseCase,
    UpdateNotificationSettingsUseCase,
    get_get_notification_settings,
    get_link_notification_channel_settings,
    get_unlink_notification_channel_settings,
    get_update_notification_settings,
    parse_delivery_channel,
)

router = APIRouter(prefix="/notification-settings", tags=["client-notification-settings"])


@router.get(
    "/me",
    response_model=NotificationSettingsOut,
    status_code=status.HTTP_200_OK,
    summary="Notification channel and topic preferences (client cabinet)",
    description=(
        "Returns delivery channels available to the authenticated user and the current topic preferences for the "
        "client cabinet. In-app notifications are always enabled. External channels include connection state and, "
        "for pending bot links, a temporary `connect_url` deep link."
    ),
    response_description="Current client notification channels and topic preferences.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
    },
)
async def get_my_notification_settings(
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[GetNotificationSettingsUseCase, Depends(get_get_notification_settings)],
) -> NotificationSettingsOut:
    return await use_case(user, cabinet="client")


@router.patch(
    "/me",
    response_model=NotificationSettingsOut,
    status_code=status.HTTP_200_OK,
    summary="Update notification preferences (client cabinet)",
    description=(
        "Partially updates topic-level delivery preferences for the client cabinet. Send only topics and channels "
        "that should change. Enabling Telegram requires a verified linked Telegram channel first."
    ),
    response_description="Updated client notification settings.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Unknown topic/channel, unavailable channel, or channel is not linked.",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
    },
)
async def patch_my_notification_settings(
    payload: NotificationSettingsPatch,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[UpdateNotificationSettingsUseCase, Depends(get_update_notification_settings)],
) -> NotificationSettingsOut:
    return await use_case(user, cabinet="client", payload=payload)


@router.post(
    "/channels/{channel_kind}/link",
    response_model=NotificationSettingsOut,
    status_code=status.HTTP_200_OK,
    summary="Create a messenger link URL (client cabinet)",
    description=(
        "Creates a short-lived link token for a bot-backed notification channel, stores it in Redis, and returns "
        "fresh notification settings containing `connect_url`. The browser should open that URL so the user can "
        "complete linking in the messenger bot."
    ),
    response_description="Notification settings with a pending messenger `connect_url` when applicable.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Unknown channel, unavailable channel, or unsupported manual linking request.",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorDetail,
            "description": "Messenger bot is not configured for this environment.",
        },
    },
)
async def link_notification_channel(
    channel_kind: Annotated[str, Path(description="Delivery channel key, currently `telegram` for bot linking.")],
    payload: LinkNotificationChannelIn,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[LinkNotificationChannelUseCase, Depends(get_link_notification_channel_settings)],
) -> NotificationSettingsOut:
    kind = parse_delivery_channel(channel_kind)
    return await use_case(user, cabinet="client", kind=kind, payload=payload)


@router.delete(
    "/channels/{channel_kind}",
    response_model=NotificationSettingsOut,
    status_code=status.HTTP_200_OK,
    summary="Disconnect an external notification channel",
    description=(
        "Disconnects a linked external channel for the current user and clears any pending bot link token for the "
        "same channel. Email and in-app delivery cannot be disconnected through this endpoint."
    ),
    response_description="Notification settings after the channel was disconnected.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Unknown channel or channel cannot be disconnected.",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
    },
)
async def unlink_notification_channel(
    channel_kind: Annotated[str, Path(description="Delivery channel key, for example `telegram`.")],
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[UnlinkNotificationChannelUseCase, Depends(get_unlink_notification_channel_settings)],
) -> NotificationSettingsOut:
    kind = parse_delivery_channel(channel_kind)
    return await use_case(user, cabinet="client", kind=kind)
