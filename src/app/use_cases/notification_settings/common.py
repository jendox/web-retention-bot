from __future__ import annotations

from app.core.config import MessengerBotsSettings
from app.models.notifications import DeliveryChannel
from app.services.messenger.providers import MessengerProvider
from app.use_cases.notification_settings.exceptions import (
    NotificationSettingsUnknownChannelError,
    NotificationSettingsUnsupportedProviderError,
)

__all__ = [
    "build_connect_url",
    "messenger_provider_for_channel",
    "parse_delivery_channel",
]


def parse_delivery_channel(channel_kind: str) -> DeliveryChannel:
    try:
        return DeliveryChannel(channel_kind)
    except ValueError as exc:
        raise NotificationSettingsUnknownChannelError() from exc


def messenger_provider_for_channel(kind: DeliveryChannel) -> MessengerProvider | None:
    try:
        return MessengerProvider(kind.value.lower())
    except ValueError:
        return None


def build_connect_url(
    provider: MessengerProvider,
    token: str,
    bots_settings: MessengerBotsSettings,
) -> str:
    if provider == MessengerProvider.TELEGRAM:
        username = bots_settings.telegram_bot_username.lstrip("@")
        return f"https://t.me/{username}?start={token}"
    raise NotificationSettingsUnsupportedProviderError()
