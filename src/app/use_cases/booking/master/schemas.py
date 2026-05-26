from dataclasses import dataclass

from app.repositories.bookings import BookingRepository
from app.repositories.clients import ClientRepository
from app.repositories.notifications import ScheduledNotificationRepository
from app.repositories.services import ServiceRepository
from app.repositories.users import UserRepository


@dataclass(frozen=True)
class MasterBookingUseCaseReposDeps:
    user_repo: UserRepository
    client_repo: ClientRepository
    service_repo: ServiceRepository
    booking_repo: BookingRepository
    scheduled_notifications_repo: ScheduledNotificationRepository
