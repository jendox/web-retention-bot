from uuid import UUID

from structlog import BoundLogger

from app.models import Booking, MasterProfile, Service
from app.use_cases.booking.exceptions import (
    ActiveBookingNotFoundError,
    BookingMasterNotFoundError,
    BookingNotFoundError,
    BookingServiceNotFoundError,
)


class ClientBookingMixin:
    async def _get_master(
        self,
        *,
        master_id: UUID,
        logger: BoundLogger | None = None,
    ) -> MasterProfile:
        master = await self._master_repo.get_by_master_id(master_id)
        if master is None:
            if logger is not None:
                logger.warning("failed", reason="master_not_found")
            raise BookingMasterNotFoundError()
        return master

    async def _get_service(
        self,
        *,
        service_id: UUID,
        master_id: UUID,
        active_only: bool = False,
        logger: BoundLogger | None = None,
    ) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if service is None:
            if logger is not None:
                logger.warning("failed", reason="service_not_found")
            raise BookingServiceNotFoundError()

        if active_only and not service.is_active:
            if logger is not None:
                logger.warning("failed", reason="service_inactive")
            raise BookingServiceNotFoundError()
        return service

    async def _get_active_booking(
        self,
        *,
        booking_id: UUID,
        user_id: UUID,
        logger: BoundLogger | None = None,
    ) -> Booking:
        booking = await self._booking_repo.get_for_user(booking_id, user_id)
        if not booking:
            if logger is not None:
                logger.warning("failed", reason="booking_not_found")
            raise BookingNotFoundError()

        if not booking.status.blocks_calendar:
            if logger is not None:
                logger.warning("failed", reason="active_booking_not_found")
            raise ActiveBookingNotFoundError()
        return booking
