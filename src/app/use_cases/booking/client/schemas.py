from __future__ import annotations

from dataclasses import dataclass

from app.repositories.bookings import BookingRepository
from app.repositories.clients import ClientRepository
from app.repositories.masters import MasterRepository
from app.repositories.services import ServiceRepository
from app.repositories.users import UserRepository
from app.services.notifications.dispatcher import NotificationDispatcher
from app.use_cases.booking.available_slots import AvailableSlotsUseCase


@dataclass(frozen=True)
class ClientBookingUseCaseDeps:
    master_repo: MasterRepository
    client_repo: ClientRepository
    service_repo: ServiceRepository
    booking_repo: BookingRepository
    user_repo: UserRepository
    dispatcher: NotificationDispatcher
    available_slots_use_case: AvailableSlotsUseCase | None = None
