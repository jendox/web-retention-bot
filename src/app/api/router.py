from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.client import (
    availability as client_availability,
    bookings as client_bookings,
    masters as client_masters,
    notification_settings as client_notification_settings,
    notifications as client_notifications,
    profile as client_profile,
)
from app.api.routes.common import auth, invitations
from app.api.routes.internal import messenger as internal_messenger
from app.api.routes.master import (
    analytics as master_analytics,
    bookings as master_bookings,
    clients as master_clients,
    notification_settings as master_notification_settings,
    notifications as master_notifications,
    profile as master_profile,
    services as master_services,
)

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(invitations.router)

api_router.include_router(client_profile.router, prefix="/client")
api_router.include_router(client_bookings.router, prefix="/client")
api_router.include_router(client_masters.router, prefix="/client")
api_router.include_router(client_availability.router, prefix="/client")
api_router.include_router(client_notifications.router, prefix="/client")
api_router.include_router(client_notification_settings.router, prefix="/client")

api_router.include_router(master_profile.router, prefix="/master")
api_router.include_router(master_analytics.router, prefix="/master")
api_router.include_router(master_clients.router, prefix="/master")
api_router.include_router(master_services.router, prefix="/master")
api_router.include_router(master_bookings.router, prefix="/master")
api_router.include_router(master_notifications.router, prefix="/master")
api_router.include_router(master_notification_settings.router, prefix="/master")

api_router.include_router(internal_messenger.router, prefix="/internal")
