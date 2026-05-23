from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import User
from app.models.notifications import DeliveryChannel
from app.repositories.notification_preferences import (
    NotificationPreferenceRepository,
    get_notification_preference_repo,
)
from app.schemas.notification_settings import NotificationSettingsOut, NotificationSettingsPatch
from app.services.notifications.settings_catalog import CabinetKind, NotificationTopicDef, topics_for_cabinet
from app.use_cases.notification_settings.exceptions import (
    NotificationSettingsChannelNotLinkedError,
    NotificationSettingsUnknownTopicError,
)
from app.use_cases.notification_settings.get_settings import (
    GetNotificationSettingsUseCase,
    get_get_notification_settings,
)

__all__ = ["UpdateNotificationSettingsUseCase", "get_update_notification_settings"]

logger = get_logger("app.notification_settings")


class UpdateNotificationSettingsUseCase:
    def __init__(
        self,
        pref_repo: NotificationPreferenceRepository,
        use_case: GetNotificationSettingsUseCase,
    ) -> None:
        self._pref_repo = pref_repo
        self._get_notifications_use_case = use_case

    async def _can_enable_external(self, user_id: UUID, kind: DeliveryChannel) -> bool:
        if kind == DeliveryChannel.EMAIL:
            return True
        linked = await self._pref_repo.get_channel(user_id, kind)
        return linked is not None and linked.is_verified

    async def __call__(
        self,
        user: User,
        *,
        cabinet: CabinetKind,
        payload: NotificationSettingsPatch,
    ) -> NotificationSettingsOut:
        with log_context(
            use_case="update_notification_settings",
            cabinet=cabinet,
            user_id=user.id,
        ):
            await self._pref_repo.ensure_defaults(user.id, cabinet=cabinet)
            topic_by_id: dict[str, NotificationTopicDef] = {t.id: t for t in topics_for_cabinet(cabinet)}

            for topic_patch in payload.topics:
                topic = topic_by_id.get(topic_patch.id)
                if topic is None:
                    logger.warning("failed", reason="unknown_topic", topic_id=topic_patch.id)
                    raise NotificationSettingsUnknownTopicError()

                channel = topic_patch.channels
                if channel.email is not None:
                    await self._pref_repo.set_topic_channel(
                        user_id=user.id,
                        topic=topic,
                        channel=DeliveryChannel.EMAIL,
                        enabled=channel.email,
                    )
                for kind, enabled in (
                    (DeliveryChannel.TELEGRAM, channel.telegram),
                    (DeliveryChannel.SMS, channel.sms),
                ):
                    if enabled is None:
                        continue

                    if enabled and not await self._can_enable_external(user.id, kind):
                        logger.warning("failed", reason="channel_not_linked", channel=kind.value)
                        raise NotificationSettingsChannelNotLinkedError()

                    await self._pref_repo.set_topic_channel(
                        user_id=user.id,
                        topic=topic,
                        channel=kind,
                        enabled=enabled,
                    )

            return await self._get_notifications_use_case(user, cabinet=cabinet)


def get_update_notification_settings(
    pref_repo: Annotated[NotificationPreferenceRepository, Depends(get_notification_preference_repo)],
    use_case: Annotated[GetNotificationSettingsUseCase, Depends(get_get_notification_settings)],
) -> UpdateNotificationSettingsUseCase:
    return UpdateNotificationSettingsUseCase(pref_repo, use_case)
