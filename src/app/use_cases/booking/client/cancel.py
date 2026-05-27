from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Booking, Client, MasterClient, User
from app.models.booking import BookingStatus
from app.schemas.booking import normalize_booking_comment
from app.schemas.client_master import client_label_for_master
from app.services.notifications.booking_master_notify import BookingMasterNotifyContext, notify_master_booking_cancelled
from app.services.notifications.booking_reminders import cancel_booking_reminders
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.client.deps import get_client_booking_use_case_repos_deps
from app.use_cases.booking.client.mixins import ClientBookingMixin
from app.use_cases.booking.client.schemas import ClientBookingUseCaseReposDeps
from app.use_cases.booking.exceptions import BookingClientLinkNotFoundError

__all__ = ["CancelClientBookingUseCase", "get_cancel_client_booking_use_case"]

logger = get_logger("app.booking")


class CancelClientBookingUseCase(ClientBookingMixin):
    def __init__(
        self,
        repos_deps: ClientBookingUseCaseReposDeps,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._master_repo = repos_deps.master_repo
        self._user_repo = repos_deps.user_repo
        self._client_repo = repos_deps.client_repo
        self._service_repo = repos_deps.service_repo
        self._booking_repo = repos_deps.booking_repo
        self._scheduled_notifications_repo = repos_deps.scheduled_notifications_repo
        self._dispatcher = dispatcher

    async def _get_link_with_client(
        self,
        *,
        master_id: UUID,
        client_id: UUID,
    ) -> tuple[MasterClient, Client]:
        row = await self._client_repo.get_link_with_client(master_id, client_id)
        if row is None:
            logger.warning("failed", reason="client_link_not_found")
            raise BookingClientLinkNotFoundError()

        link, client = row
        return link, client

    async def _update_booking_status(
        self,
        booking: Booking,
        status: BookingStatus,
        comment: str | None,
    ) -> None:
        booking.status = status
        booking.cancel_comment = normalize_booking_comment(comment)
        await self._booking_repo.flush()

    async def __call__(self, *, user: User, booking_id: UUID, comment: str | None = None) -> None:
        with log_context(use_case="cancel_client_booking", user_id=str(user.id), booking_id=str(booking_id)):
            booking = await self._get_active_booking(booking_id=booking_id, user_id=user.id, logger=logger)
            master = await self._get_master(master_id=booking.master_id, logger=logger)
            service = await self._get_service(service_id=booking.service_id, master_id=master.id, logger=logger)

            link, client = await self._get_link_with_client(master_id=master.id, client_id=booking.client_id)

            await self._update_booking_status(booking=booking, comment=comment, status=BookingStatus.CANCELLED)
            logger.info("cancelled")

            await cancel_booking_reminders(
                repo=self._scheduled_notifications_repo,
                booking_id=booking.id,
            )

            await notify_master_booking_cancelled(
                BookingMasterNotifyContext(
                    dispatcher=self._dispatcher,
                    user_repo=self._user_repo,
                    booking=booking,
                    master=master,
                    service=service,
                    client_display_name=client_label_for_master(link, client),
                ),
            )


def get_cancel_client_booking_use_case(
    repos_deps: Annotated[ClientBookingUseCaseReposDeps, Depends(get_client_booking_use_case_repos_deps)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CancelClientBookingUseCase:
    return CancelClientBookingUseCase(repos_deps, dispatcher)
