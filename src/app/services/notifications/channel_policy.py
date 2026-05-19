from __future__ import annotations

from uuid import UUID

from app.models.notifications import NotificationEventType, DeliveryChannel


# later: UserNotificationPreferenceRepository + NotificationChannelRepository

def delivery_channels_for_user(
    *,
    user_id: UUID,
    event_type: NotificationEventType,
) -> list[DeliveryChannel]:
    _ = user_id, event_type
    return [DeliveryChannel.EMAIL]

# prefs = repo.list_enabled(user_id, event_type=event_type, category=PreferenceCategory.BOOKING)
# if DeliveryChannel.TELEGRAM in prefs and has_verified_telegram_channel(user_id):
#     channels.append(DeliveryChannel.TELEGRAM)
