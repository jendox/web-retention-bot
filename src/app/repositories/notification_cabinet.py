from __future__ import annotations

from sqlalchemy import and_, or_

from app.models.notifications import NotificationEventType
from app.models.notifications.models import UserNotification
from app.services.notifications.mail_render import (
    BOOKING_EMAIL_AUDIENCE_CLIENT,
    BOOKING_EMAIL_AUDIENCE_MASTER,
)

_INVITE_MISMATCH_TITLE = "Клиент принял приглашение с другим email"


def notification_belongs_to_client_cabinet():
    audience = UserNotification.payload["audience"].astext
    link = UserNotification.link_url

    client_booking = or_(
        audience == BOOKING_EMAIL_AUDIENCE_CLIENT,
        link.ilike("%/client%"),
    )
    account_wide = UserNotification.event_type == NotificationEventType.EMAIL_VERIFICATION
    return or_(client_booking, account_wide)


def notification_belongs_to_master_cabinet():
    audience = UserNotification.payload["audience"].astext
    link = UserNotification.link_url

    master_booking = or_(
        audience == BOOKING_EMAIL_AUDIENCE_MASTER,
        link.ilike("%/master%"),
        and_(
            UserNotification.event_type == NotificationEventType.DEFAULT,
            UserNotification.title == _INVITE_MISMATCH_TITLE,
        ),
    )
    account_wide = UserNotification.event_type == NotificationEventType.EMAIL_VERIFICATION
    return or_(master_booking, account_wide)
