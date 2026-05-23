from __future__ import annotations

from app.core.exceptions import DomainError, ValidationError

__all__ = [
    "NotificationSettingsError",
    "NotificationSettingsUnknownTopicError",
    "NotificationSettingsUnknownChannelError",
    "NotificationSettingsChannelUnavailableError",
    "NotificationSettingsChannelNotConnectableError",
    "NotificationSettingsChannelContactRequiredError",
    "NotificationSettingsChannelNotLinkedError",
    "NotificationSettingsEmailRequiredError",
    "NotificationSettingsUnsupportedProviderError",
]


class NotificationSettingsError(DomainError):
    """Base notification settings use case error."""


class NotificationSettingsUnknownTopicError(NotificationSettingsError, ValidationError):
    code = "notification_settings.unknown_topic"
    message = "Unknown notification topic"


class NotificationSettingsUnknownChannelError(NotificationSettingsError, ValidationError):
    code = "notification_settings.unknown_channel"
    message = "Unknown notification channel"


class NotificationSettingsChannelUnavailableError(NotificationSettingsError, ValidationError):
    code = "notification_settings.channel_unavailable"
    message = "Notification channel is unavailable"


class NotificationSettingsChannelNotConnectableError(NotificationSettingsError, ValidationError):
    code = "notification_settings.channel_not_connectable"
    message = "Notification channel is not connectable"


class NotificationSettingsChannelContactRequiredError(NotificationSettingsError, ValidationError):
    code = "notification_settings.channel_contact_required"
    message = "Notification channel contact is required"


class NotificationSettingsChannelNotLinkedError(NotificationSettingsError, ValidationError):
    code = "notification_settings.channel_not_linked"
    message = "Notification channel must be linked before enabling notifications"


class NotificationSettingsEmailRequiredError(NotificationSettingsError, ValidationError):
    code = "notification_settings.email_required"
    message = "Email channel cannot be disconnected"


class NotificationSettingsUnsupportedProviderError(NotificationSettingsError, ValidationError):
    code = "notification_settings.unsupported_provider"
    message = "Unsupported messenger provider"
