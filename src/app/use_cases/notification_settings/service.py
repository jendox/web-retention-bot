from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings
from app.models.notifications import DeliveryChannel
from app.models.user import User
from app.repositories.notification_preferences import (
    NotificationPreferenceRepository,
    get_notification_preference_repo,
)
from app.schemas.notification_settings import (
    ExternalChannelOut,
    InAppChannelOut,
    LinkNotificationChannelIn,
    NotificationSettingsOut,
    NotificationSettingsPatch,
    NotificationTopicOut,
    TopicChannelPrefsOut,
)
from app.services.messenger.link_tokens import MessengerLinkTokenStore, get_messenger_link_token_store_dep
from app.services.messenger.providers import MessengerProvider
from app.services.notifications.settings_catalog import (
    BOT_LINKABLE_CHANNELS,
    CHANNEL_DEFS,
    CabinetKind,
    topics_for_cabinet,
)

_CHANNEL_TO_PROVIDER = {
    DeliveryChannel.TELEGRAM: MessengerProvider.TELEGRAM,
    DeliveryChannel.VIBER: MessengerProvider.VIBER,
}


class NotificationSettingsService:
    def __init__(
        self,
        preference_repo: NotificationPreferenceRepository,
        link_tokens: MessengerLinkTokenStore,
        settings: Settings,
    ) -> None:
        self._repo = preference_repo
        self._link_tokens = link_tokens
        self._settings = settings

    async def get_settings(self, user: User, *, cabinet: CabinetKind) -> NotificationSettingsOut:
        await self._repo.ensure_defaults(user.id, cabinet=cabinet)
        prefs = await self._repo.list_preferences(user.id)
        channels = await self._repo.list_channels(user.id)
        channel_by_kind = {c.kind: c for c in channels}

        topic_rows: list[NotificationTopicOut] = []
        for topic in topics_for_cabinet(cabinet):
            topic_rows.append(
                NotificationTopicOut(
                    id=topic.id,
                    label=topic.label,
                    description=topic.description,
                    channels=self._topic_prefs(prefs, topic, channel_by_kind),
                ),
            )

        external: list[ExternalChannelOut] = []
        for channel_def in CHANNEL_DEFS:
            linked = channel_by_kind.get(channel_def.kind)
            connected = linked is not None and linked.is_verified
            external.append(
                ExternalChannelOut(
                    kind=channel_def.kind.value,
                    label=channel_def.label,
                    description=channel_def.description,
                    available=channel_def.available,
                    connectable=channel_def.connectable,
                    connected=connected,
                    address=linked.address if linked else (user.email if channel_def.kind == DeliveryChannel.EMAIL else None),
                    connect_url=await self._pending_connect_url(user.id, channel_def.kind, connected=connected),
                    coming_soon_label=channel_def.coming_soon_label,
                ),
            )

        return NotificationSettingsOut(
            in_app=InAppChannelOut(),
            channels=external,
            topics=topic_rows,
        )

    async def update_settings(
        self,
        user: User,
        *,
        cabinet: CabinetKind,
        payload: NotificationSettingsPatch,
    ) -> NotificationSettingsOut:
        await self._repo.ensure_defaults(user.id, cabinet=cabinet)
        topic_by_id = {t.id: t for t in topics_for_cabinet(cabinet)}

        for topic_patch in payload.topics:
            topic = topic_by_id.get(topic_patch.id)
            if topic is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown topic: {topic_patch.id}")

            ch = topic_patch.channels
            if ch.email is not None:
                await self._repo.set_topic_channel(
                    user_id=user.id,
                    topic=topic,
                    channel=DeliveryChannel.EMAIL,
                    enabled=ch.email,
                )
            for kind, enabled in (
                (DeliveryChannel.TELEGRAM, ch.telegram),
                (DeliveryChannel.VIBER, ch.viber),
                (DeliveryChannel.SMS, ch.sms),
            ):
                if enabled is None:
                    continue
                if enabled and not await self._can_enable_external(user.id, kind):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        detail=f"Подключите канал {kind.value} перед включением уведомлений.",
                    )
                await self._repo.set_topic_channel(
                    user_id=user.id,
                    topic=topic,
                    channel=kind,
                    enabled=enabled,
                )

        return await self.get_settings(user, cabinet=cabinet)

    async def link_channel(
        self,
        user: User,
        *,
        cabinet: CabinetKind,
        kind: DeliveryChannel,
        payload: LinkNotificationChannelIn,
    ) -> NotificationSettingsOut:
        channel_def = next((c for c in CHANNEL_DEFS if c.kind == kind), None)
        if channel_def is None or not channel_def.available:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Канал недоступен.")
        if kind not in BOT_LINKABLE_CHANNELS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Подключение этого канала пока недоступно.")

        provider = _CHANNEL_TO_PROVIDER.get(kind)
        if provider is not None:
            token = await self._link_tokens.create(user.id, provider)
            await self._link_tokens.remember_pending(user.id, provider, token)
            return await self.get_settings(user, cabinet=cabinet)

        address = (payload.address or "").strip()
        if not address:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Укажите контакт для канала.")
        await self._repo.upsert_channel(user_id=user.id, kind=kind, address=address, is_verified=True)
        return await self.get_settings(user, cabinet=cabinet)

    async def unlink_channel(
        self,
        user: User,
        *,
        kind: DeliveryChannel,
        cabinet: CabinetKind,
    ) -> NotificationSettingsOut:
        if kind == DeliveryChannel.EMAIL:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Email нельзя отключить.")
        provider = _CHANNEL_TO_PROVIDER.get(kind)
        if provider is not None:
            await self._link_tokens.clear_pending(user.id, provider)
        await self._repo.delete_channel(user.id, kind)
        return await self.get_settings(user, cabinet=cabinet)

    async def _pending_connect_url(
        self,
        user_id: UUID,
        kind: DeliveryChannel,
        *,
        connected: bool,
    ) -> str | None:
        if connected:
            return None
        provider = _CHANNEL_TO_PROVIDER.get(kind)
        if provider is None:
            return None
        token = await self._link_tokens.get_pending_token(user_id, provider)
        if not token:
            return None
        return self._build_connect_url(provider, token)

    def _build_connect_url(self, provider: MessengerProvider, token: str) -> str:
        bots = self._settings.messenger_bots
        if provider == MessengerProvider.TELEGRAM:
            username = bots.telegram_bot_username.lstrip("@")
            return f"https://t.me/{username}?start={token}"
        if provider == MessengerProvider.VIBER:
            # Viber public account deep link; URI scheme may vary by PA setup.
            return f"viber://pa?chatURI={bots.viber_pa_uri}&context={token}"
        raise ValueError(f"Unsupported provider: {provider}")

    async def _can_enable_external(self, user_id: UUID, kind: DeliveryChannel) -> bool:
        if kind == DeliveryChannel.EMAIL:
            return True
        linked = await self._repo.get_channel(user_id, kind)
        return linked is not None and linked.is_verified

    def _topic_prefs(self, prefs, topic, channel_by_kind) -> TopicChannelPrefsOut:
        def enabled_for(kind: DeliveryChannel) -> bool:
            if kind != DeliveryChannel.EMAIL:
                linked = channel_by_kind.get(kind)
                if linked is None or not linked.is_verified:
                    return False
            for pref in prefs:
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

        return TopicChannelPrefsOut(
            email=enabled_for(DeliveryChannel.EMAIL),
            telegram=enabled_for(DeliveryChannel.TELEGRAM),
            viber=enabled_for(DeliveryChannel.VIBER),
            sms=enabled_for(DeliveryChannel.SMS),
        )


def get_notification_settings_service(
    request: Request,
    preference_repo: Annotated[NotificationPreferenceRepository, Depends(get_notification_preference_repo)],
    link_tokens: Annotated[MessengerLinkTokenStore, Depends(get_messenger_link_token_store_dep)],
) -> NotificationSettingsService:
    return NotificationSettingsService(
        preference_repo,
        link_tokens,
        request.app.state.settings,
    )
