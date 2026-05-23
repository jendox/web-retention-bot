from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import require_user
from app.models.user import User
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

router = APIRouter(prefix="/notification-settings", tags=["master-notification-settings"])


@router.get(
    "/me",
    response_model=NotificationSettingsOut,
    summary="Notification channel and topic preferences (master cabinet)",
)
async def get_my_notification_settings(
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[GetNotificationSettingsUseCase, Depends(get_get_notification_settings)],
) -> NotificationSettingsOut:
    return await use_case(user, cabinet="master")


@router.patch(
    "/me",
    response_model=NotificationSettingsOut,
    summary="Update notification preferences (master cabinet)",
)
async def patch_my_notification_settings(
    payload: NotificationSettingsPatch,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[UpdateNotificationSettingsUseCase, Depends(get_update_notification_settings)],
) -> NotificationSettingsOut:
    return await use_case(user, cabinet="master", payload=payload)


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
    use_case: Annotated[LinkNotificationChannelUseCase, Depends(get_link_notification_channel_settings)],
) -> NotificationSettingsOut:
    kind = parse_delivery_channel(channel_kind)
    return await use_case(user, cabinet="master", kind=kind, payload=payload)


@router.delete(
    "/channels/{channel_kind}",
    response_model=NotificationSettingsOut,
    summary="Disconnect an external notification channel",
)
async def unlink_notification_channel(
    channel_kind: str,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[UnlinkNotificationChannelUseCase, Depends(get_unlink_notification_channel_settings)],
) -> NotificationSettingsOut:
    kind = parse_delivery_channel(channel_kind)
    return await use_case(user, cabinet="master", kind=kind)
