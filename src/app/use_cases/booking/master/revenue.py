from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.currency import DEFAULT_MASTER_CURRENCY
from app.core.structured_logging import get_logger, log_context
from app.models.master import MasterProfile
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.booking import BookingMonthlyRevenueOut
from app.use_cases.booking.common import current_calendar_month_bounds_utc

__all__ = ["GetMasterMonthlyRevenueUseCase", "get_master_monthly_revenue_use_case"]

logger = get_logger("app.booking")


class GetMasterMonthlyRevenueUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(self, master: MasterProfile) -> BookingMonthlyRevenueOut:
        with log_context(use_case="get_master_monthly_revenue", master_id=str(master.id)):
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
