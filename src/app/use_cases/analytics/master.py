from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.core.currency import DEFAULT_MASTER_CURRENCY
from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.schedule import ScheduleDateOverride, WeeklyScheduleDay
from app.repositories.bookings import AnalyticsBookingRow, BookingRepository, get_booking_repo
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.schemas.analytics import (
    AnalyticsDailyMoneyOut,
    AnalyticsMoneyOut,
    AnalyticsOccupancyOut,
    AnalyticsPeriodOut,
    AnalyticsPeriodPreset,
    AnalyticsReturnClientMoneyOut,
    AnalyticsReturnClientOut,
    AnalyticsRevenuePointOut,
    AnalyticsServiceMoneyOut,
    AnalyticsServiceOut,
    AnalyticsSummaryOut,
    MasterAnalyticsOut,
)
from app.services.availability import windows_for_date

__all__ = ["GetMasterAnalyticsUseCase", "get_master_analytics_use_case"]

_RETURN_CLIENT_DAYS = 45
_RETURN_CLIENT_MIN_COMPLETED = 2
_RETURN_CLIENT_LIMIT = 5
_DECEMBER = 12
_REPEAT_CLIENT_MIN_PERIOD_COMPLETED = 2

logger = get_logger("app.analytics")


@dataclass(frozen=True)
class AnalyticsPeriod:
    preset: AnalyticsPeriodPreset | None
    from_date: date
    to_date: date
    range_start: datetime
    range_end: datetime
    label: str


@dataclass(frozen=True)
class AnalyticsRows:
    period_rows: list[AnalyticsBookingRow]
    completed_until_period_end: list[AnalyticsBookingRow]
    completed_until_now: list[AnalyticsBookingRow]
    occupancy_bookings: list[Booking]


@dataclass(frozen=True)
class ScheduleRows:
    weekly_days: list[WeeklyScheduleDay]
    date_overrides: list[ScheduleDateOverride]


@dataclass(frozen=True)
class OccupancyRange:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class OccupancyMinutes:
    available: int
    booked: int


@dataclass
class ServiceStats:
    service_id: UUID
    name: str
    completed_count: int = 0
    cancelled_count: int = 0
    no_show_count: int = 0
    revenue_by_currency: dict[str, Decimal] | None = None
    completed_count_by_currency: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.revenue_by_currency is None:
            self.revenue_by_currency = defaultdict(Decimal)
        if self.completed_count_by_currency is None:
            self.completed_count_by_currency = defaultdict(int)


@dataclass
class ClientStats:
    client_id: UUID
    display_name: str
    completed_count: int = 0
    last_visit_at: datetime | None = None
    revenue_by_currency: dict[str, Decimal] | None = None

    def __post_init__(self) -> None:
        if self.revenue_by_currency is None:
            self.revenue_by_currency = defaultdict(Decimal)


def _money_dict() -> defaultdict[str, Decimal]:
    return defaultdict(Decimal)


def _display_name(row: AnalyticsBookingRow) -> str:
    alias = row.client_alias.strip() if row.client_alias else ""
    return alias or row.client_display_name


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _local_midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz)


def _period_label(from_date: date, to_date: date) -> str:
    if from_date == to_date:
        return from_date.strftime("%d.%m.%Y")
    if from_date.year == to_date.year:
        return f"{from_date.strftime('%d.%m')} - {to_date.strftime('%d.%m.%Y')}"
    return f"{from_date.strftime('%d.%m.%Y')} - {to_date.strftime('%d.%m.%Y')}"


def _month_bounds(ref: datetime, tz: ZoneInfo) -> tuple[date, date]:
    local = ref.astimezone(tz)
    first = date(local.year, local.month, 1)
    if local.month == _DECEMBER:
        next_first = date(local.year + 1, 1, 1)
    else:
        next_first = date(local.year, local.month + 1, 1)
    return first, next_first - timedelta(days=1)


def _previous_month_bounds(ref: datetime, tz: ZoneInfo) -> tuple[date, date]:
    current_first, _ = _month_bounds(ref, tz)
    previous_last = current_first - timedelta(days=1)
    previous_first = date(previous_last.year, previous_last.month, 1)
    return previous_first, previous_last


def _resolve_period(
    *,
    timezone_name: str,
    preset: AnalyticsPeriodPreset | None,
    from_date: date | None,
    to_date: date | None,
    now: datetime | None,
) -> AnalyticsPeriod:
    tz = ZoneInfo(timezone_name)
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)

    if from_date is not None or to_date is not None:
        if from_date is None or to_date is None:
            raise ValueError("Both from_date and to_date are required for custom analytics period.")
        if to_date < from_date:
            raise ValueError("Analytics period to_date must be greater than or equal to from_date.")
        resolved_preset = None
        start_day = from_date
        end_day = to_date
    else:
        resolved_preset = preset or AnalyticsPeriodPreset.CURRENT_MONTH
        if resolved_preset == AnalyticsPeriodPreset.CURRENT_MONTH:
            start_day, end_day = _month_bounds(ref, tz)
        elif resolved_preset == AnalyticsPeriodPreset.PREVIOUS_MONTH:
            start_day, end_day = _previous_month_bounds(ref, tz)
        else:
            local_today = ref.astimezone(tz).date()
            start_day = local_today - timedelta(days=29)
            end_day = local_today

    range_start = _local_midnight(start_day, tz).astimezone(UTC)
    range_end = _local_midnight(end_day + timedelta(days=1), tz).astimezone(UTC)
    return AnalyticsPeriod(
        preset=resolved_preset,
        from_date=start_day,
        to_date=end_day,
        range_start=range_start,
        range_end=range_end,
        label=_period_label(start_day, end_day),
    )


def _average(amount: Decimal, count: int) -> Decimal:
    if count <= 0:
        return Decimal("0.00")
    return (amount / Decimal(count)).quantize(Decimal("0.01"))


def _sorted_money(values: dict[str, Decimal]) -> list[tuple[str, Decimal]]:
    return sorted(values.items(), key=lambda item: item[0])


def _clip_interval(
    start_at: datetime,
    end_at: datetime,
    range_start: datetime,
    range_end: datetime,
) -> tuple[datetime, datetime] | None:
    clipped_start = max(_as_utc(start_at), _as_utc(range_start))
    clipped_end = min(_as_utc(end_at), _as_utc(range_end))
    if clipped_end <= clipped_start:
        return None
    return clipped_start, clipped_end


def _minutes_between(start_at: datetime, end_at: datetime) -> int:
    return int((end_at - start_at).total_seconds() // 60)


def _minutes_to_hours(minutes: int) -> Decimal:
    return (Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"))


class GetMasterAnalyticsUseCase:
    def __init__(self, booking_repo: BookingRepository, schedule_repo: ScheduleRepository) -> None:
        self._booking_repo = booking_repo
        self._schedule_repo = schedule_repo

    async def __call__(
        self,
        master: MasterProfile,
        *,
        preset: AnalyticsPeriodPreset | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        now: datetime | None = None,
    ) -> MasterAnalyticsOut:
        with log_context(use_case="get_master_analytics", master_id=str(master.id)):
            period = _resolve_period(
                timezone_name=master.timezone,
                preset=preset,
                from_date=from_date,
                to_date=to_date,
                now=now,
            )
            rows = await self._booking_repo.analytics_rows_between(
                master_id=master.id,
                range_start=period.range_start,
                range_end=period.range_end,
            )
            completed_rows_until_period_end = await self._booking_repo.completed_analytics_rows_until(
                master_id=master.id,
                range_end=period.range_end,
            )
            ref = now or datetime.now(UTC)
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=UTC)
            completed_rows_until_now = await self._booking_repo.completed_analytics_rows_until(
                master_id=master.id,
                range_end=ref.astimezone(UTC),
            )
            occupancy_range = self._occupancy_range(period, ref)
            occupancy_bookings = await self._booking_repo.occupancy_bookings_between(
                master_id=master.id,
                range_start=occupancy_range.start_at,
                range_end=occupancy_range.end_at,
            )
            weekly_days = await self._schedule_repo.weekly_days_for_master(master.id)
            date_overrides = await self._schedule_repo.date_overrides_for_master(master.id)

            display_currency = (
                master.default_currency.value
                if master.default_currency is not None
                else DEFAULT_MASTER_CURRENCY.value
            )
            return await self._build_response(
                master=master,
                period=period,
                rows=AnalyticsRows(
                    period_rows=rows,
                    completed_until_period_end=completed_rows_until_period_end,
                    completed_until_now=completed_rows_until_now,
                    occupancy_bookings=occupancy_bookings,
                ),
                schedules=ScheduleRows(weekly_days=weekly_days, date_overrides=date_overrides),
                occupancy_range=occupancy_range,
                display_currency=display_currency,
                now=ref,
            )

    async def _build_response(  # noqa: PLR0913, PLR0914
        self,
        *,
        master: MasterProfile,
        period: AnalyticsPeriod,
        rows: AnalyticsRows,
        schedules: ScheduleRows,
        occupancy_range: OccupancyRange,
        display_currency: str,
        now: datetime | None,
    ) -> MasterAnalyticsOut:
        tz = ZoneInfo(master.timezone)
        completed_rows = [row for row in rows.period_rows if row.booking.status == BookingStatus.COMPLETED]
        cancelled_count = sum(1 for row in rows.period_rows if row.booking.status == BookingStatus.CANCELLED)
        no_show_count = sum(1 for row in rows.period_rows if row.booking.status == BookingStatus.NO_SHOW)
        completed_count = len(completed_rows)

        revenue_by_currency = _money_dict()
        lost_by_currency = _money_dict()
        completed_count_by_currency: dict[str, int] = defaultdict(int)
        for row in rows.period_rows:
            currency = row.booking.currency_snapshot
            if row.booking.status == BookingStatus.COMPLETED:
                revenue_by_currency[currency] += row.booking.price_snapshot
                completed_count_by_currency[currency] += 1
            elif row.booking.status in {BookingStatus.CANCELLED, BookingStatus.NO_SHOW}:
                lost_by_currency[currency] += row.booking.price_snapshot

        first_visit_by_client: dict[UUID, datetime] = {}
        period_completed_count_by_client: dict[UUID, int] = defaultdict(int)
        for row in rows.completed_until_period_end:
            client_id = row.booking.client_id
            start_at = _as_utc(row.booking.start_at)
            if client_id not in first_visit_by_client or start_at < first_visit_by_client[client_id]:
                first_visit_by_client[client_id] = start_at
            if period.range_start <= start_at < period.range_end:
                period_completed_count_by_client[client_id] += 1

        period_clients = set(period_completed_count_by_client)
        new_clients = sum(
            1
            for client_id in period_clients
            if period.range_start <= first_visit_by_client[client_id] < period.range_end
        )
        repeat_clients = sum(
            1
            for client_id in period_clients
            if first_visit_by_client[client_id] < period.range_start
            or period_completed_count_by_client[client_id] >= _REPEAT_CLIENT_MIN_PERIOD_COMPLETED
        )
        money_currencies = revenue_by_currency.keys() | lost_by_currency.keys()

        return MasterAnalyticsOut(
            period=AnalyticsPeriodOut(
                preset=period.preset,
                from_date=period.from_date,
                to_date=period.to_date,
                timezone=master.timezone,
                range_start=period.range_start,
                range_end=period.range_end,
                label=period.label,
            ),
            display_currency=display_currency,
            summary=AnalyticsSummaryOut(
                completed_count=completed_count,
                cancelled_count=cancelled_count,
                no_show_count=no_show_count,
                unique_clients=len(period_clients),
                new_clients=new_clients,
                repeat_clients=repeat_clients,
            ),
            occupancy=self._occupancy(master, schedules, occupancy_range, rows.occupancy_bookings),
            money=[
                AnalyticsMoneyOut(
                    currency=currency,
                    revenue=revenue,
                    average_check=_average(revenue, completed_count_by_currency[currency]),
                    lost_revenue=lost_by_currency[currency],
                )
                for currency, revenue in _sorted_money(
                    {currency: revenue_by_currency[currency] for currency in money_currencies},
                )
            ],
            revenue_by_day=self._revenue_by_day(period, completed_rows, tz),
            services=self._services(rows.period_rows, display_currency, revenue_by_currency[display_currency]),
            clients_to_return=await self._clients_to_return(
                master_id=master.id,
                completed_rows_until_now=rows.completed_until_now,
                display_currency=display_currency,
                timezone=tz,
                now=now,
            ),
        )

    @staticmethod
    def _occupancy_range(period: AnalyticsPeriod, now: datetime) -> OccupancyRange:
        ref = _as_utc(now)
        range_end = min(period.range_end, ref)
        range_end = max(period.range_start, range_end)
        return OccupancyRange(start_at=period.range_start, end_at=range_end)

    def _occupancy(
        self,
        master: MasterProfile,
        schedules: ScheduleRows,
        occupancy_range: OccupancyRange,
        bookings: list[Booking],
    ) -> AnalyticsOccupancyOut:
        minutes = self._occupancy_minutes(master, schedules, occupancy_range, bookings)
        percent = 0
        if minutes.available > 0:
            percent = round(minutes.booked / minutes.available * 100)
        return AnalyticsOccupancyOut(
            percent=percent,
            available_minutes=minutes.available,
            booked_minutes=minutes.booked,
            available_hours=_minutes_to_hours(minutes.available),
            booked_hours=_minutes_to_hours(minutes.booked),
        )

    @staticmethod
    def _occupancy_minutes(
        master: MasterProfile,
        schedules: ScheduleRows,
        occupancy_range: OccupancyRange,
        bookings: list[Booking],
    ) -> OccupancyMinutes:
        tz = ZoneInfo(master.timezone)
        range_start_local = occupancy_range.start_at.astimezone(tz)
        range_end_local = occupancy_range.end_at.astimezone(tz)
        if range_end_local <= range_start_local:
            return OccupancyMinutes(available=0, booked=0)

        available = 0
        booked = 0
        current_day = range_start_local.date()
        while current_day <= range_end_local.date():
            windows = windows_for_date(
                current_day,
                schedules.weekly_days,
                schedules.date_overrides,
                tz,
            )
            for window_start, window_end in windows:
                clipped_window = _clip_interval(
                    window_start.astimezone(UTC),
                    window_end.astimezone(UTC),
                    occupancy_range.start_at,
                    occupancy_range.end_at,
                )
                if clipped_window is None:
                    continue
                window_start_utc, window_end_utc = clipped_window
                available += _minutes_between(window_start_utc, window_end_utc)
                for booking in bookings:
                    clipped_booking = _clip_interval(
                        _as_utc(booking.start_at),
                        _as_utc(booking.end_at),
                        window_start_utc,
                        window_end_utc,
                    )
                    if clipped_booking is None:
                        continue
                    booked += _minutes_between(*clipped_booking)
            current_day += timedelta(days=1)
        return OccupancyMinutes(available=available, booked=min(booked, available))

    def _revenue_by_day(
        self,
        period: AnalyticsPeriod,
        completed_rows: list[AnalyticsBookingRow],
        tz: ZoneInfo,
    ) -> list[AnalyticsRevenuePointOut]:
        by_day: dict[date, dict[str, Decimal]] = {}
        counts_by_day: dict[date, int] = defaultdict(int)
        current_day = period.from_date
        while current_day <= period.to_date:
            by_day[current_day] = _money_dict()
            current_day += timedelta(days=1)

        for row in completed_rows:
            day = row.booking.start_at.astimezone(tz).date()
            if day not in by_day:
                continue
            by_day[day][row.booking.currency_snapshot] += row.booking.price_snapshot
            counts_by_day[day] += 1

        return [
            AnalyticsRevenuePointOut(
                date=day,
                label=str(day.day),
                completed_count=counts_by_day[day],
                money=[
                    AnalyticsDailyMoneyOut(currency=currency, revenue=revenue)
                    for currency, revenue in _sorted_money(values)
                ],
            )
            for day, values in sorted(by_day.items())
        ]

    def _services(
        self,
        rows: list[AnalyticsBookingRow],
        display_currency: str,
        display_total_revenue: Decimal,
    ) -> list[AnalyticsServiceOut]:
        stats_by_service: dict[UUID, ServiceStats] = {}
        for row in rows:
            service_id = row.booking.service_id
            stats = stats_by_service.setdefault(
                service_id,
                ServiceStats(service_id=service_id, name=row.service_name),
            )
            if row.booking.status == BookingStatus.COMPLETED:
                stats.completed_count += 1
                stats.revenue_by_currency[row.booking.currency_snapshot] += row.booking.price_snapshot
                stats.completed_count_by_currency[row.booking.currency_snapshot] += 1
            elif row.booking.status == BookingStatus.CANCELLED:
                stats.cancelled_count += 1
            elif row.booking.status == BookingStatus.NO_SHOW:
                stats.no_show_count += 1

        services = []
        for stats in stats_by_service.values():
            display_revenue = stats.revenue_by_currency[display_currency]
            share = 0
            if display_total_revenue > 0:
                share = int((display_revenue / display_total_revenue * Decimal(100)).quantize(Decimal("1")))
            services.append(
                AnalyticsServiceOut(
                    service_id=stats.service_id,
                    name=stats.name,
                    completed_count=stats.completed_count,
                    cancelled_count=stats.cancelled_count,
                    no_show_count=stats.no_show_count,
                    revenue_share_percent=share,
                    money=[
                        AnalyticsServiceMoneyOut(
                            currency=currency,
                            revenue=revenue,
                            average_check=_average(revenue, stats.completed_count_by_currency[currency]),
                        )
                        for currency, revenue in _sorted_money(stats.revenue_by_currency)
                    ],
                ),
            )

        return sorted(
            services,
            key=lambda service: (
                self._service_display_revenue(service, display_currency),
                service.completed_count,
                service.name.lower(),
            ),
            reverse=True,
        )

    @staticmethod
    def _service_display_revenue(service: AnalyticsServiceOut, display_currency: str) -> Decimal:
        for money in service.money:
            if money.currency == display_currency:
                return money.revenue
        return Decimal("0.00")

    async def _clients_to_return(
        self,
        *,
        master_id: UUID,
        completed_rows_until_now: list[AnalyticsBookingRow],
        display_currency: str,
        timezone: ZoneInfo,
        now: datetime | None,
    ) -> list[AnalyticsReturnClientOut]:
        ref = now or datetime.now(UTC)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        local_today = ref.astimezone(timezone).date()
        cutoff_day = local_today - timedelta(days=_RETURN_CLIENT_DAYS)

        stats_by_client: dict[UUID, ClientStats] = {}
        for row in completed_rows_until_now:
            client_id = row.booking.client_id
            stats = stats_by_client.setdefault(
                client_id,
                ClientStats(client_id=client_id, display_name=_display_name(row)),
            )
            start_at = _as_utc(row.booking.start_at)
            stats.completed_count += 1
            stats.revenue_by_currency[row.booking.currency_snapshot] += row.booking.price_snapshot
            if stats.last_visit_at is None or start_at > stats.last_visit_at:
                stats.last_visit_at = start_at

        candidate_ids = [
            client_id
            for client_id, stats in stats_by_client.items()
            if stats.completed_count >= _RETURN_CLIENT_MIN_COMPLETED
            and stats.last_visit_at is not None
            and stats.last_visit_at.astimezone(timezone).date() < cutoff_day
        ]
        future_scheduled_client_ids = await self._booking_repo.future_scheduled_client_ids(
            master_id=master_id,
            client_ids=candidate_ids,
            now=ref.astimezone(UTC),
        )

        candidates = []
        for client_id in candidate_ids:
            if client_id in future_scheduled_client_ids:
                continue
            stats = stats_by_client[client_id]
            assert stats.last_visit_at is not None
            days_since_last_visit = (local_today - stats.last_visit_at.astimezone(timezone).date()).days
            candidates.append(
                AnalyticsReturnClientOut(
                    client_id=client_id,
                    display_name=stats.display_name,
                    last_visit_at=stats.last_visit_at,
                    days_since_last_visit=days_since_last_visit,
                    completed_count=stats.completed_count,
                    note=f"{stats.completed_count} завершенных визита, нет записи {days_since_last_visit} дней",
                    money=[
                        AnalyticsReturnClientMoneyOut(currency=currency, revenue=revenue)
                        for currency, revenue in _sorted_money(stats.revenue_by_currency)
                    ],
                ),
            )

        return sorted(
            candidates,
            key=lambda client: (
                self._return_client_display_revenue(client, display_currency),
                client.days_since_last_visit,
                client.completed_count,
            ),
            reverse=True,
        )[:_RETURN_CLIENT_LIMIT]

    @staticmethod
    def _return_client_display_revenue(client: AnalyticsReturnClientOut, display_currency: str) -> Decimal:
        for money in client.money:
            if money.currency == display_currency:
                return money.revenue
        return Decimal("0.00")


def get_master_analytics_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
) -> GetMasterAnalyticsUseCase:
    return GetMasterAnalyticsUseCase(booking_repo, schedule_repo)
