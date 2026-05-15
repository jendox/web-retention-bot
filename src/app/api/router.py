from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, availability, bookings, clients, invitations, masters, services

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(masters.router)
api_router.include_router(services.router)
api_router.include_router(clients.router)
api_router.include_router(invitations.router)
api_router.include_router(availability.router)
api_router.include_router(bookings.router)
