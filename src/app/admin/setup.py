from __future__ import annotations

from fastapi import FastAPI
from sqladmin import Admin

from app.admin.auth import AllowlistAdminAuthBackend
from app.admin.database import create_admin_engine
from app.admin.views import (
    BookingAdmin,
    ClientAdmin,
    InvitationAdmin,
    MasterClientAdmin,
    MasterProfileAdmin,
    NotificationChannelAdmin,
    NotificationDeliveryAdmin,
    NotificationEventAdmin,
    RetentionPolicyAdmin,
    ScheduleDateOverrideAdmin,
    ScheduleDateOverrideIntervalAdmin,
    ScheduledNotificationAdmin,
    ServiceAdmin,
    UserAdmin,
    UserNotificationAdmin,
    UserNotificationPreferenceAdmin,
    WeeklyScheduleDayAdmin,
    WeeklyScheduleIntervalAdmin,
)
from app.core.config import Settings
from app.core.structured_logging import get_logger

__all__ = ["mount_admin", "ADMIN_BASE_URL"]

ADMIN_BASE_URL = "/admin"

logger = get_logger("app.admin.setup")

_ADMIN_VIEWS = (
    UserAdmin,
    MasterProfileAdmin,
    ClientAdmin,
    MasterClientAdmin,
    ServiceAdmin,
    BookingAdmin,
    InvitationAdmin,
    WeeklyScheduleDayAdmin,
    WeeklyScheduleIntervalAdmin,
    ScheduleDateOverrideAdmin,
    ScheduleDateOverrideIntervalAdmin,
    NotificationEventAdmin,
    UserNotificationAdmin,
    NotificationDeliveryAdmin,
    UserNotificationPreferenceAdmin,
    ScheduledNotificationAdmin,
    NotificationChannelAdmin,
    RetentionPolicyAdmin,
)


def mount_admin(app: FastAPI, settings: Settings) -> Admin | None:
    if not settings.admin.enabled:
        return None

    if not settings.admin.allowed_email_set:
        logger.warning("admin_disabled_missing_allowlist")
        return None

    engine = create_admin_engine(settings.infra.database_url)
    auth_backend = AllowlistAdminAuthBackend(settings=settings, engine=engine)

    admin = Admin(
        app,
        engine,
        base_url=ADMIN_BASE_URL,
        title="Retention Ops",
        authentication_backend=auth_backend,
    )

    for view in _ADMIN_VIEWS:
        admin.add_view(view)

    logger.info(
        "admin_mounted",
        base_url=ADMIN_BASE_URL,
        allowed_emails=sorted(settings.admin.allowed_email_set),
    )
    return admin
