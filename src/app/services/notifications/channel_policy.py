from __future__ import annotations

from uuid import UUID

from app.models.notifications import DeliveryChannel, NotificationEventType
from app.repositories.notification_preferences import NotificationPreferenceRepository
from app.services.notifications.settings_catalog import category_for_event_type

EXTERNAL_CHANNELS = (
    DeliveryChannel.EMAIL,
    DeliveryChannel.TELEGRAM,
    DeliveryChannel.SMS,
)


async def delivery_channels_for_user(
    preference_repo: NotificationPreferenceRepository,
    *,
    user_id: UUID,
    event_type: NotificationEventType,
) -> list[DeliveryChannel]:
    """External delivery channels for a notification event (in-app is always UserNotification)."""
    category = category_for_event_type(event_type)
    channels: list[DeliveryChannel] = []

    for channel in EXTERNAL_CHANNELS:
        if not await preference_repo.is_channel_enabled_for_event(
            user_id,
            channel,
            event_type,
            category=category,
        ):
            continue
        if channel != DeliveryChannel.EMAIL:
            linked = await preference_repo.get_channel(user_id, channel)
            if linked is None or not linked.is_verified:
                continue
        channels.append(channel)

    return channels
