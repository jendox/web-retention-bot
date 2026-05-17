"""Import-order registration for SQLAlchemy mappers."""

from app.models.booking import Booking  # noqa: F401
from app.models.client import Client, MasterClient  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401
from app.models.master import MasterProfile  # noqa: F401
from app.models.notifications import (  # noqa: F401
    NotificationDelivery,
    NotificationEvent,
    RetentionPolicy,
    ScheduledNotification,
    UserNotification,
    UserNotificationPreference,
)
from app.models.notifications.models import NotificationChannel
from app.models.schedule import WeeklyScheduleRule, WorkdayOverride, WorkdayOverrideInterval  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "Booking",
    "Client",
    "Invitation",
    "MasterClient",
    "MasterProfile",
    "NotificationChannel",
    "NotificationDelivery",
    "NotificationEvent",
    "RetentionPolicy",
    "ScheduledNotification",
    "UserNotification",
    "UserNotificationPreference",
    "Service",
    "User",
    "WeeklyScheduleRule",
    "WorkdayOverride",
    "WorkdayOverrideInterval",
]
