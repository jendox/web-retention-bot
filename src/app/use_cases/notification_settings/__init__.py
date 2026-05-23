from app.use_cases.notification_settings.common import parse_delivery_channel
from app.use_cases.notification_settings.exceptions import (
    NotificationSettingsChannelContactRequiredError,
    NotificationSettingsChannelNotConnectableError,
    NotificationSettingsChannelNotLinkedError,
    NotificationSettingsChannelUnavailableError,
    NotificationSettingsEmailRequiredError,
    NotificationSettingsError,
    NotificationSettingsUnknownChannelError,
    NotificationSettingsUnknownTopicError,
    NotificationSettingsUnsupportedProviderError,
)
from app.use_cases.notification_settings.get_settings import (
    GetNotificationSettingsUseCase,
    get_get_notification_settings,
)
from app.use_cases.notification_settings.link_channel import (
    LinkNotificationChannelUseCase,
    get_link_notification_channel_settings,
)
from app.use_cases.notification_settings.unlink_channel import (
    UnlinkNotificationChannelUseCase,
    get_unlink_notification_channel_settings,
)
from app.use_cases.notification_settings.update_settings import (
    UpdateNotificationSettingsUseCase,
    get_update_notification_settings,
)

__all__ = [
    "GetNotificationSettingsUseCase",
    "get_get_notification_settings",
    "UpdateNotificationSettingsUseCase",
    "get_update_notification_settings",
    "LinkNotificationChannelUseCase",
    "get_link_notification_channel_settings",
    "UnlinkNotificationChannelUseCase",
    "get_unlink_notification_channel_settings",
    "NotificationSettingsError",
    "NotificationSettingsUnknownTopicError",
    "NotificationSettingsUnknownChannelError",
    "NotificationSettingsChannelUnavailableError",
    "NotificationSettingsChannelNotConnectableError",
    "NotificationSettingsChannelContactRequiredError",
    "NotificationSettingsChannelNotLinkedError",
    "NotificationSettingsEmailRequiredError",
    "NotificationSettingsUnsupportedProviderError",
    "parse_delivery_channel",
]
