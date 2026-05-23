from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.core.config import Settings
from app.models import NotificationChannel, UserNotificationPreference
from app.models.notifications import DeliveryChannel
from app.models.user import User
from app.repositories.notification_preferences import (
    NotificationPreferenceRepository,
    get_notification_preference_repo,
)
from app.schemas.notification_settings import (
    ExternalChannelOut,
    InAppChannelOut,
    NotificationSettingsOut,
    NotificationTopicOut,
    TopicChannelPrefsOut,
)
from app.services.messenger.link_tokens import MessengerLinkTokenStore, get_messenger_link_token_store_dep
from app.services.notifications.settings_catalog import (
    CHANNEL_DEFS,
    CabinetKind,
    NotificationTopicDef,
    topics_for_cabinet,
)
from app.use_cases.notification_settings.common import build_connect_url, messenger_provider_for_channel

__all__ = ["GetNotificationSettingsUseCase", "get_get_notification_settings"]


def _channel_enabled(
    preferences: list[UserNotificationPreference],
    topic: NotificationTopicDef,
    kind: DeliveryChannel,
    channel_by_kind: dict[DeliveryChannel, NotificationChannel],
) -> bool:
    if kind != DeliveryChannel.EMAIL:
        linked = channel_by_kind.get(kind)
        if linked is None or not linked.is_verified:
            return False
    for pref in preferences:
        if pref.channel != kind:
            continue
        if topic.event_type is not None and pref.event_type == topic.event_type:
            return pref.enabled
        if (
            topic.event_type is None
            and topic.category is not None
            and pref.event_type is None
            and pref.category == topic.category
        ):
            return pref.enabled
    return kind == DeliveryChannel.EMAIL


def _topic_prefs(
    preferences: list[UserNotificationPreference],
    topic: NotificationTopicDef,
    channel_by_kind: dict[DeliveryChannel, NotificationChannel],
) -> TopicChannelPrefsOut:
    return TopicChannelPrefsOut(
        email=_channel_enabled(preferences, topic, DeliveryChannel.EMAIL, channel_by_kind),
        telegram=_channel_enabled(preferences, topic, DeliveryChannel.TELEGRAM, channel_by_kind),
        sms=_channel_enabled(preferences, topic, DeliveryChannel.SMS, channel_by_kind),
    )


class GetNotificationSettingsUseCase:
    def __init__(
        self,
        settings: Settings,
        pref_repo: NotificationPreferenceRepository,
        link_tokens: MessengerLinkTokenStore,
    ) -> None:
        self._settings = settings
        self._pref_repo = pref_repo
        self._link_tokens = link_tokens

    async def _pending_connect_url(
        self,
        user_id: UUID,
        kind: DeliveryChannel,
        *,
        connected: bool,
    ) -> str | None:
        if connected:
            return None

        provider = messenger_provider_for_channel(kind)
        if provider is None:
            return None

        token = await self._link_tokens.get_pending_token(user_id, provider)
        if not token:
            return None

        return build_connect_url(provider, token, self._settings.messenger_bots)

    async def __call__(self, user: User, *, cabinet: CabinetKind) -> NotificationSettingsOut:
        await self._pref_repo.ensure_defaults(user.id, cabinet=cabinet)
        preferences = await self._pref_repo.list_preferences(user.id)
        channels = await self._pref_repo.list_channels(user.id)
        channel_by_kind: dict[DeliveryChannel, NotificationChannel] = {c.kind: c for c in channels}

        topic_rows: list[NotificationTopicOut] = []
        for topic in topics_for_cabinet(cabinet):
            topic_rows.append(
                NotificationTopicOut(
                    id=topic.id,
                    label=topic.label,
                    description=topic.description,
                    channels=_topic_prefs(preferences, topic, channel_by_kind),
                ),
            )

        external: list[ExternalChannelOut] = []
        for channel_def in CHANNEL_DEFS:
            linked = channel_by_kind.get(channel_def.kind)
            connected = linked is not None and linked.is_verified
            if linked:
                address = linked.address
            elif channel_def.kind == DeliveryChannel.EMAIL:
                address = user.email
            else:
                address = None
            external.append(
                ExternalChannelOut(
                    kind=channel_def.kind.value,
                    label=channel_def.label,
                    description=channel_def.description,
                    available=channel_def.available,
                    connectable=channel_def.connectable,
                    connected=connected,
                    address=address,
                    connect_url=await self._pending_connect_url(user.id, channel_def.kind, connected=connected),
                    coming_soon_label=channel_def.coming_soon_label,
                ),
            )

        return NotificationSettingsOut(
            in_app=InAppChannelOut(),
            channels=external,
            topics=topic_rows,
        )


def get_get_notification_settings(
    request: Request,
    pref_repo: Annotated[NotificationPreferenceRepository, Depends(get_notification_preference_repo)],
    link_tokens: Annotated[MessengerLinkTokenStore, Depends(get_messenger_link_token_store_dep)],
) -> GetNotificationSettingsUseCase:
    settings = request.app.state.settings
    return GetNotificationSettingsUseCase(settings, pref_repo, link_tokens)
