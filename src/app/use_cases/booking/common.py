from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from structlog import BoundLogger

from app.core import datetime_utils
from app.models import MasterProfile, Service
from app.repositories.bookings import BookingRepository
from app.schemas.master import MasterProfileSchema
from app.use_cases.booking.available_slots import AvailableSlotsUseCase, slots_contain
from app.use_cases.booking.exceptions import BookingOverlapsExistingError, BookingRequestedSlotUnavailableError

_DECEMBER = 12


@dataclass(frozen=True)
class DateTimeRange:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class ScheduleBookingContext:
    master: MasterProfile
    service: Service
    start_at: datetime
    duration_min: int
    booking_id: UUID | None = None


def get_master_booking_day(master: MasterProfile, start_utc: datetime) -> date:
    master_schema = MasterProfileSchema.model_validate(master)
    return master_schema.calendar_day_for_master(start_utc)


async def ensure_slot_available(
    use_case: AvailableSlotsUseCase,
    *,
    master: MasterProfile,
    service_id: UUID,
    start_utc: datetime,
    logger: BoundLogger | None = None,
) -> None:
    slots = await use_case(
        master_id=master.id,
        service_id=service_id,
        calendar_day=get_master_booking_day(master, start_utc),
    )
    if not slots_contain([slot.start_at for slot in slots], start_utc):
        if logger is not None:
            logger.warning(
                "failed",
                reason="requested_slot_unavailable",
                start_at=start_utc.isoformat(),
            )
        raise BookingRequestedSlotUnavailableError()


async def check_booking_conflicts(
    booking_repo: BookingRepository,
    *,
    master_id: UUID,
    dt_range: DateTimeRange,
    booking_id: UUID | None = None,
    logger: BoundLogger | None = None,
) -> None:
    if await booking_repo.has_conflict(
        master_id=master_id,
        start_at=dt_range.start_at,
        end_at=dt_range.end_at,
        exclude_booking_id=booking_id,
    ):
        if logger is not None:
            logger.warning(
                "failed",
                reason="overlapping_booking",
                start_at=dt_range.start_at.isoformat(),
                end_at=dt_range.end_at.isoformat(),
            )
        raise BookingOverlapsExistingError()


async def schedule_booking(
    available_slots_use_case: AvailableSlotsUseCase,
    booking_repo: BookingRepository,
    *,
    schedule_context: ScheduleBookingContext,
    logger: BoundLogger | None = None,
) -> tuple[datetime, datetime]:
    start_utc = datetime_utils.local_to_utc(schedule_context.start_at)
    end_utc = start_utc + timedelta(minutes=schedule_context.duration_min)

    await ensure_slot_available(
        available_slots_use_case,
        master=schedule_context.master,
        service_id=schedule_context.service.id,
        start_utc=start_utc,
        logger=logger,
    )
    await check_booking_conflicts(
        booking_repo,
        master_id=schedule_context.master.id,
        dt_range=DateTimeRange(start_at=start_utc, end_at=end_utc),
        booking_id=schedule_context.booking_id,
        logger=logger,
    )

    return start_utc, end_utc


def current_calendar_month_bounds_utc(
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(timezone_name)
    ref = (now or datetime.now(UTC)).astimezone(tz)
    month_label = f"{ref.year:04d}-{ref.month:02d}"
    start_local = datetime(ref.year, ref.month, 1, tzinfo=tz)
    if ref.month == _DECEMBER:
        end_local = datetime(ref.year + 1, 1, 1, tzinfo=tz)
    else:
        end_local = datetime(ref.year, ref.month + 1, 1, tzinfo=tz)
    return (
        start_local.astimezone(UTC).replace(tzinfo=UTC),
        end_local.astimezone(UTC).replace(tzinfo=UTC),
        month_label,
    )
