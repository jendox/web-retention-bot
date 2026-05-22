from uuid import UUID

from structlog import BoundLogger

from app.models import Booking, Service
from app.use_cases.booking.exceptions import (
    ActiveBookingNotFoundError,
    BookingNotFoundError,
    BookingServiceNotFoundError,
)


class MasterBookingMixin:
    async def _get_active_booking(
        self,
        *,
        booking_id: UUID,
        master_id: UUID,
        logger: BoundLogger,
    ) -> Booking:
        booking = await self._booking_repo.get_for_master(booking_id, master_id)
        if not booking:
            logger.warning("failed", reason="booking_not_found")
            raise BookingNotFoundError()

        if not booking.status.blocks_calendar:
            logger.warning("failed", reason="booking_not_active")
            raise ActiveBookingNotFoundError()

        return booking

    async def _get_service(
        self,
        *,
        service_id: UUID,
        master_id: UUID,
        logger: BoundLogger,
    ) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if not service:
            logger.error("failed", reason="service_missing", service_id=str(service_id))
            raise BookingServiceNotFoundError()
        return service
