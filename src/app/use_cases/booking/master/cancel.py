from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import MasterProfile
from app.models.booking import BookingStatus
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.booking import normalize_booking_comment
from app.services.notifications.booking_client_notify import BookingClientNotifyContext, notify_client_booking_cancelled
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.master.mixins import MasterBookingMixin

__all__ = ["CancelMasterBookingUseCase", "get_cancel_master_booking_use_case"]

logger = get_logger("app.booking")


class CancelMasterBookingUseCase(MasterBookingMixin):
    def __init__(
        self,
        booking_repo: BookingRepository,
        client_repo: ClientRepository,
        service_repo: ServiceRepository,
        user_repo: UserRepository,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._booking_repo = booking_repo
        self._client_repo = client_repo
        self._service_repo = service_repo
        self._user_repo = user_repo
        self._dispatcher = dispatcher

    async def __call__(self, *, master: MasterProfile, booking_id: UUID, comment: str | None = None) -> None:
        with log_context(
            use_case="cancel_master_booking",
            master_id=str(master.id),
            booking_id=str(booking_id),
        ):
            booking = await self._get_active_booking(booking_id=booking_id, master_id=master.id, logger=logger)
            service = await self._get_service(service_id=booking.service_id, master_id=master.id, logger=logger)

            booking.status = BookingStatus.CANCELLED
            booking.cancel_comment = normalize_booking_comment(comment)
            await self._booking_repo.flush()
            logger.info("cancelled")

            await notify_client_booking_cancelled(
                BookingClientNotifyContext(
                    dispatcher=self._dispatcher,
                    user_repo=self._user_repo,
                    client_repo=self._client_repo,
                    booking=booking,
                    master=master,
                    service=service,
                ),
            )


def get_cancel_master_booking_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CancelMasterBookingUseCase:
    return CancelMasterBookingUseCase(booking_repo, client_repo, service_repo, user_repo, dispatcher)
