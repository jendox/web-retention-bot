from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import MasterProfile
from app.models.booking import BookingStatus
from app.schemas.booking import normalize_booking_comment
from app.services.notifications.booking_client_notify import BookingClientNotifyContext, notify_client_booking_cancelled
from app.services.notifications.booking_reminders import cancel_booking_reminders
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.master.deps import get_master_booking_use_case_repos_deps
from app.use_cases.booking.master.mixins import MasterBookingMixin
from app.use_cases.booking.master.schemas import MasterBookingUseCaseReposDeps

__all__ = ["CancelMasterBookingUseCase", "get_cancel_master_booking_use_case"]

logger = get_logger("app.booking")


class CancelMasterBookingUseCase(MasterBookingMixin):
    def __init__(
        self,
        repos_deps: MasterBookingUseCaseReposDeps,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._booking_repo = repos_deps.booking_repo
        self._client_repo = repos_deps.client_repo
        self._service_repo = repos_deps.service_repo
        self._user_repo = repos_deps.user_repo
        self._scheduled_notifications_repo = repos_deps.scheduled_notifications_repo
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

            await cancel_booking_reminders(
                repo=self._scheduled_notifications_repo,
                booking_id=booking.id,
            )

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
    repos_deps: Annotated[MasterBookingUseCaseReposDeps, Depends(get_master_booking_use_case_repos_deps)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CancelMasterBookingUseCase:
    return CancelMasterBookingUseCase(repos_deps, dispatcher)
