from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.core.currency import DEFAULT_MASTER_CURRENCY
from app.models.master import MasterProfile
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.booking import BookingMonthlyRevenueOut

_DECEMBER = 12


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


class GetMasterMonthlyRevenueUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(self, master: MasterProfile) -> BookingMonthlyRevenueOut:
        range_start, range_end, month = current_calendar_month_bounds_utc(master.timezone)
        amount, completed_count = await self._booking_repo.sum_completed_revenue_between(
            master_id=master.id,
            range_start=range_start,
            range_end=range_end,
        )
        currency = (
            master.default_currency.value
            if master.default_currency is not None
            else DEFAULT_MASTER_CURRENCY.value
        )
        return BookingMonthlyRevenueOut(
            amount=amount,
            currency=currency,
            month=month,
            completed_count=completed_count,
        )


def get_master_monthly_revenue_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> GetMasterMonthlyRevenueUseCase:
    return GetMasterMonthlyRevenueUseCase(booking_repo)
