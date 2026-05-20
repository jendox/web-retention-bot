from __future__ import annotations

from fastapi import status


class NotificationNotFoundError(Exception):
    status_code = status.HTTP_404_NOT_FOUND
    error_message = "Notification not found"
