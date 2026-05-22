from app.core.exceptions import DomainError, NotFoundError

__all__ = [
    "NotificationError",
    "NotificationNotFoundError",
]


class NotificationError(DomainError):
    """Base notifications use case error."""


class NotificationNotFoundError(NotificationError, NotFoundError):
    code = "notifications.not_found"
    message = "Notification not found"
