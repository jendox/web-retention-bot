import enum


class NotificationEventType(enum.StrEnum):
    DEFAULT = "default"
    BOOKING_CREATED = "booking_created"
    BOOKING_MOVED = "booking_moved"
    BOOKING_CANCELLED = "booking_cancelled"
    REMINDER_BEFORE_VISIT = "reminder_before_visit"
    REENGAGEMENT_IDLE = "reengagement_idle"
    EMAIL_VERIFICATION = "email_verification"
    EMAIL_PASSWORD_RESET = "email_password_reset"


class DeliveryChannel(enum.StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"


class DeliveryStatus(enum.StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ScheduledNotificationPurpose(enum.StrEnum):
    REMINDER_24H = "reminder_24h"
    REMINDER_1H = "reminder_1h"


class ScheduledNotificationStatus(enum.StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    DONE = "done"
    CANCELLED = "cancelled"


class PreferenceCategory(enum.StrEnum):
    """Группировка для грубого вкл/выкл."""
    BOOKING = "booking"
    MARKETING = "marketing"
    RETENTION = "retention"
    SYSTEM = "system"
