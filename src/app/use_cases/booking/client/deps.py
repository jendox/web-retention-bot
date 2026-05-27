from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.notifications import ScheduledNotificationRepository, get_scheduled_notification_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.use_cases.booking.client.schemas import ClientBookingUseCaseReposDeps


def get_client_booking_use_case_repos_deps(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    scheduled_notifications_repo: Annotated[
        ScheduledNotificationRepository, Depends(get_scheduled_notification_repo),
    ],
) -> ClientBookingUseCaseReposDeps:
    return ClientBookingUseCaseReposDeps(
        user_repo=user_repo,
        master_repo=master_repo,
        client_repo=client_repo,
        service_repo=service_repo,
        booking_repo=booking_repo,
        scheduled_notifications_repo=scheduled_notifications_repo,
    )
