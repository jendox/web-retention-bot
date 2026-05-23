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
from app.schemas.notification_settings import LinkNotificationChannelIn, NotificationSettingsOut
from app.services.messenger import MessengerLinkTokenStore
from app.services.messenger.link_tokens import get_messenger_link_token_store_dep
from app.services.notifications.settings_catalog import BOT_LINKABLE_CHANNELS, CHANNEL_DEFS, CabinetKind
from app.use_cases.notification_settings.common import messenger_provider_for_channel
from app.use_cases.notification_settings.exceptions import (
    NotificationSettingsChannelContactRequiredError,
    NotificationSettingsChannelNotConnectableError,
    NotificationSettingsChannelUnavailableError,
)
from app.use_cases.notification_settings.get_settings import (
    GetNotificationSettingsUseCase,
    get_get_notification_settings,
)

__all__ = ["LinkNotificationChannelUseCase", "get_link_notification_channel_settings"]

logger = get_logger("app.notification_settings")


class LinkNotificationChannelUseCase:
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
        payload: LinkNotificationChannelIn,
    ) -> NotificationSettingsOut:
        with log_context(
            use_case="link_notification_channel",
            user_id=user.id,
            cabinet=cabinet,
            channel=kind.value,
        ):
            channel_def = next((c for c in CHANNEL_DEFS if c.kind == kind), None)
            if channel_def is None or not channel_def.available:
                logger.warning("failed", reason="channel_unavailable")
                raise NotificationSettingsChannelUnavailableError()

            if kind not in BOT_LINKABLE_CHANNELS:
                logger.warning("failed", reason="channel_not_connectable")
                raise NotificationSettingsChannelNotConnectableError()

            provider = messenger_provider_for_channel(kind)
            if provider is not None:
                token = await self._link_tokens.create(user.id, provider)
                await self._link_tokens.remember_pending(user.id, provider, token)
                return await self._get_note_settings_use_case(user, cabinet=cabinet)

            address = (payload.address or "").strip()
            if not address:
                logger.warning("failed", reason="channel_contact_required")
                raise NotificationSettingsChannelContactRequiredError()

            await self._pref_repo.upsert_channel(user_id=user.id, kind=kind, address=address, is_verified=True)

            return await self._get_note_settings_use_case(user, cabinet=cabinet)


def get_link_notification_channel_settings(
    pref_repo: Annotated[NotificationPreferenceRepository, Depends(get_notification_preference_repo)],
    link_tokens: Annotated[MessengerLinkTokenStore, Depends(get_messenger_link_token_store_dep)],
    use_case: Annotated[GetNotificationSettingsUseCase, Depends(get_get_notification_settings)],
) -> LinkNotificationChannelUseCase:
    return LinkNotificationChannelUseCase(pref_repo, link_tokens, use_case)
