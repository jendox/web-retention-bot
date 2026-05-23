from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import User
from app.models.notifications import DeliveryChannel
from app.repositories.notification_preferences import (
    NotificationPreferenceRepository,
    get_notification_preference_repo,
)
from app.schemas.notification_settings import NotificationSettingsOut
from app.services.messenger import MessengerLinkTokenStore
from app.services.messenger.link_tokens import get_messenger_link_token_store_dep
from app.services.notifications.settings_catalog import CabinetKind
from app.use_cases.notification_settings.common import messenger_provider_for_channel
from app.use_cases.notification_settings.exceptions import NotificationSettingsEmailRequiredError
from app.use_cases.notification_settings.get_settings import (
    GetNotificationSettingsUseCase,
    get_get_notification_settings,
)

__all__ = ["UnlinkNotificationChannelUseCase", "get_unlink_notification_channel_settings"]

logger = get_logger("app.notification_settings")


class UnlinkNotificationChannelUseCase:
    def __init__(
        self,
        pref_repo: NotificationPreferenceRepository,
        link_tokens: MessengerLinkTokenStore,
        use_case: GetNotificationSettingsUseCase,
    ) -> None:
        self._link_tokens = link_tokens
        self._pref_repo = pref_repo
        self._get_note_settings_use_case = use_case

    async def __call__(
        self,
        user: User,
        *,
        cabinet: CabinetKind,
        kind: DeliveryChannel,
    ) -> NotificationSettingsOut:
        with log_context(
            use_case="unlink_notification_channel",
            user_id=user.id,
            cabinet=cabinet,
            channel=kind.value,
        ):
            if kind == DeliveryChannel.EMAIL:
                logger.warning("failed", reason="email_channel_cannot_be_disconnected")
                raise NotificationSettingsEmailRequiredError()

            provider = messenger_provider_for_channel(kind)
            if provider is not None:
                await self._link_tokens.clear_pending(user.id, provider)
            await self._pref_repo.delete_channel(user.id, kind)
            return await self._get_note_settings_use_case(user, cabinet=cabinet)


def get_unlink_notification_channel_settings(
    pref_repo: Annotated[NotificationPreferenceRepository, Depends(get_notification_preference_repo)],
    link_tokens: Annotated[MessengerLinkTokenStore, Depends(get_messenger_link_token_store_dep)],
    use_case: Annotated[GetNotificationSettingsUseCase, Depends(get_get_notification_settings)],
) -> UnlinkNotificationChannelUseCase:
    return UnlinkNotificationChannelUseCase(pref_repo, link_tokens, use_case)
