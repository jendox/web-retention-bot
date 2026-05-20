from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_user
from app.models.notifications import DeliveryChannel
from app.models.user import User
from app.schemas.notification_settings import (
    LinkNotificationChannelIn,
    NotificationSettingsOut,
    NotificationSettingsPatch,
)
from app.use_cases.notification_settings.service import (
    NotificationSettingsService,
    get_notification_settings_service,
)

router = APIRouter(prefix="/notification-settings", tags=["master-notification-settings"])


@router.get(
    "/me",
    response_model=NotificationSettingsOut,
    summary="Notification channel and topic preferences (master cabinet)",
)
async def get_my_notification_settings(
    user: Annotated[User, Depends(require_user)],
    service: Annotated[NotificationSettingsService, Depends(get_notification_settings_service)],
) -> NotificationSettingsOut:
    return await service.get_settings(user, cabinet="master")


@router.patch(
    "/me",
    response_model=NotificationSettingsOut,
    summary="Update notification preferences (master cabinet)",
)
async def patch_my_notification_settings(
    payload: NotificationSettingsPatch,
    user: Annotated[User, Depends(require_user)],
    service: Annotated[NotificationSettingsService, Depends(get_notification_settings_service)],
) -> NotificationSettingsOut:
    return await service.update_settings(user, cabinet="master", payload=payload)


@router.post(
    "/channels/{channel_kind}/link",
    response_model=NotificationSettingsOut,
    status_code=status.HTTP_200_OK,
    summary="Connect a notification channel (mock: Telegram)",
)
async def link_notification_channel(
    channel_kind: str,
    payload: LinkNotificationChannelIn,
    user: Annotated[User, Depends(require_user)],
    service: Annotated[NotificationSettingsService, Depends(get_notification_settings_service)],
) -> NotificationSettingsOut:
    try:
        kind = DeliveryChannel(channel_kind)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown channel.") from exc
    return await service.link_channel(user, cabinet="master", kind=kind, payload=payload)


@router.delete(
    "/channels/{channel_kind}",
    response_model=NotificationSettingsOut,
    summary="Disconnect an external notification channel",
)
async def unlink_notification_channel(
    channel_kind: str,
    user: Annotated[User, Depends(require_user)],
    service: Annotated[NotificationSettingsService, Depends(get_notification_settings_service)],
) -> NotificationSettingsOut:
    try:
        kind = DeliveryChannel(channel_kind)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown channel.") from exc
    return await service.unlink_channel(user, cabinet="master", kind=kind)
