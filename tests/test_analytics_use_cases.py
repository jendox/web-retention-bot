import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from app.api.deps import require_master_profile
from app.core.currency import Currency
from app.main import app
from app.models.booking import BookingStatus
from app.repositories.bookings import AnalyticsBookingRow
from app.schemas.analytics import (
    AnalyticsPeriodOut,
    AnalyticsPeriodPreset,
    AnalyticsSummaryOut,
    MasterAnalyticsOut,
)
from app.use_cases.analytics import GetMasterAnalyticsUseCase, get_master_analytics_use_case


def _analytics_row(
    *,
    master_id,
    client_id,
    service_id,
    start_at,
    status=BookingStatus.COMPLETED,
    price=Decimal("50.00"),
    currency="BYN",
    client_name="Client",
    client_alias=None,
    service_name="Service",
):
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id,
        client_id=client_id,
        service_id=service_id,
        start_at=start_at,
        end_at=start_at,
        duration_min=60,
        price_snapshot=price,
        currency_snapshot=currency,
        status=status,
    )
    return AnalyticsBookingRow(
        booking=booking,
        client_display_name=client_name,
        client_alias=client_alias,
        service_name=service_name,
    )


@pytest.mark.asyncio
async def test_master_analytics_aggregates_real_booking_metrics():
    expected_master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    returning_service_id = uuid.uuid4()
    client_existing = uuid.uuid4()
    client_new_repeat = uuid.uuid4()
    client_return = uuid.uuid4()
    client_with_future_booking = uuid.uuid4()
    client_returned_now = uuid.uuid4()
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

    period_rows = [
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_existing,
            service_id=service_id,
            start_at=datetime(2026, 6, 10, 10, 0, tzinfo=UTC),
            price=Decimal("50.00"),
            client_name="Existing",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_new_repeat,
            service_id=service_id,
            start_at=datetime(2026, 6, 11, 10, 0, tzinfo=UTC),
            price=Decimal("70.00"),
            client_name="New Repeat",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_new_repeat,
            service_id=service_id,
            start_at=datetime(2026, 6, 12, 10, 0, tzinfo=UTC),
            price=Decimal("80.00"),
            client_name="New Repeat",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=uuid.uuid4(),
            service_id=service_id,
            start_at=datetime(2026, 6, 13, 10, 0, tzinfo=UTC),
            status=BookingStatus.CANCELLED,
            price=Decimal("30.00"),
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=uuid.uuid4(),
            service_id=service_id,
            start_at=datetime(2026, 6, 14, 10, 0, tzinfo=UTC),
            status=BookingStatus.NO_SHOW,
            price=Decimal("20.00"),
        ),
    ]
    completed_until_period_end = [
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_existing,
            service_id=service_id,
            start_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
            price=Decimal("90.00"),
            client_name="Existing",
        ),
        *[row for row in period_rows if row.booking.status == BookingStatus.COMPLETED],
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_return,
            service_id=returning_service_id,
            start_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            price=Decimal("100.00"),
            client_name="Return",
            client_alias="Alias Return",
            service_name="Return Service",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_return,
            service_id=returning_service_id,
            start_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            price=Decimal("150.00"),
            client_name="Return",
            client_alias="Alias Return",
            service_name="Return Service",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_returned_now,
            service_id=returning_service_id,
            start_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            price=Decimal("200.00"),
            client_name="Returned Now",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_returned_now,
            service_id=returning_service_id,
            start_at=datetime(2026, 4, 2, 10, 0, tzinfo=UTC),
            price=Decimal("200.00"),
            client_name="Returned Now",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_with_future_booking,
            service_id=returning_service_id,
            start_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            price=Decimal("300.00"),
            client_name="Scheduled Later",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_with_future_booking,
            service_id=returning_service_id,
            start_at=datetime(2026, 4, 2, 10, 0, tzinfo=UTC),
            price=Decimal("300.00"),
            client_name="Scheduled Later",
        ),
    ]
    completed_until_now = [
        *completed_until_period_end,
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_returned_now,
            service_id=returning_service_id,
            start_at=datetime(2026, 6, 10, 10, 0, tzinfo=UTC),
            price=Decimal("200.00"),
            client_name="Returned Now",
        ),
    ]

    class FakeBookingRepo:
        def __init__(self):
            self.completed_until_calls = 0

        async def analytics_rows_between(self, *, master_id: uuid.UUID, range_start, range_end):
            assert master_id == expected_master_id
            assert range_start == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
            assert range_end == datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
            return period_rows

        async def completed_analytics_rows_until(self, *, master_id: uuid.UUID, range_end):
            assert master_id == expected_master_id
            self.completed_until_calls += 1
            if self.completed_until_calls == 1:
                assert range_end == datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
                return completed_until_period_end
            assert range_end == now
            return completed_until_now

        async def future_scheduled_client_ids(self, *, master_id: uuid.UUID, client_ids, now):
            assert master_id == expected_master_id
            assert client_with_future_booking in client_ids
            assert now == datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
            return {client_with_future_booking}

    result = await GetMasterAnalyticsUseCase(FakeBookingRepo())(
        SimpleNamespace(
            id=expected_master_id,
            timezone="UTC",
            default_currency=Currency.BYN,
        ),
        preset=AnalyticsPeriodPreset.CURRENT_MONTH,
        now=now,
    )

    assert result.summary.completed_count == 3
    assert result.summary.cancelled_count == 1
    assert result.summary.no_show_count == 1
    assert result.summary.unique_clients == 2
    assert result.summary.new_clients == 1
    assert result.summary.repeat_clients == 2
    assert result.money[0].currency == "BYN"
    assert result.money[0].revenue == Decimal("200.00")
    assert result.money[0].average_check == Decimal("66.67")
    assert result.money[0].lost_revenue == Decimal("50.00")
    assert result.services[0].completed_count == 3
    assert result.services[0].revenue_share_percent == 100
    assert [client.client_id for client in result.clients_to_return] == [client_return]
    assert result.clients_to_return[0].display_name == "Alias Return"
    assert result.clients_to_return[0].days_since_last_visit == 75


@pytest.mark.asyncio
async def test_clients_to_return_are_calculated_as_of_now_not_selected_period():
    expected_master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    client_returned_now = uuid.uuid4()
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    completed_until_period_end = [
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_returned_now,
            service_id=service_id,
            start_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            price=Decimal("100.00"),
            client_name="Returned Now",
        ),
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_returned_now,
            service_id=service_id,
            start_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            price=Decimal("100.00"),
            client_name="Returned Now",
        ),
    ]
    completed_until_now = [
        *completed_until_period_end,
        _analytics_row(
            master_id=expected_master_id,
            client_id=client_returned_now,
            service_id=service_id,
            start_at=datetime(2026, 6, 10, 10, 0, tzinfo=UTC),
            price=Decimal("100.00"),
            client_name="Returned Now",
        ),
    ]

    class FakeBookingRepo:
        def __init__(self):
            self.completed_until_calls = 0

        async def analytics_rows_between(self, *, master_id: uuid.UUID, range_start, range_end):
            assert master_id == expected_master_id
            assert range_start == datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
            assert range_end == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
            return []

        async def completed_analytics_rows_until(self, *, master_id: uuid.UUID, range_end):
            assert master_id == expected_master_id
            self.completed_until_calls += 1
            if self.completed_until_calls == 1:
                assert range_end == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
                return completed_until_period_end
            assert range_end == now
            return completed_until_now

        async def future_scheduled_client_ids(self, *, master_id: uuid.UUID, client_ids, now):
            assert master_id == expected_master_id
            assert client_returned_now not in client_ids
            return set()

    result = await GetMasterAnalyticsUseCase(FakeBookingRepo())(
        SimpleNamespace(
            id=expected_master_id,
            timezone="UTC",
            default_currency=Currency.BYN,
        ),
        preset=AnalyticsPeriodPreset.PREVIOUS_MONTH,
        now=now,
    )

    assert result.clients_to_return == []


def test_master_analytics_route_is_registered():
    expected_master_id = uuid.uuid4()

    class FakeAnalyticsUseCase:
        async def __call__(self, master, *, preset=None, from_date=None, to_date=None):
            assert master.id == expected_master_id
            assert preset == AnalyticsPeriodPreset.CURRENT_MONTH
            assert from_date is None
            assert to_date is None
            return MasterAnalyticsOut(
                period=AnalyticsPeriodOut(
                    preset=AnalyticsPeriodPreset.CURRENT_MONTH,
                    from_date=date(2026, 6, 1),
                    to_date=date(2026, 6, 30),
                    timezone="UTC",
                    range_start=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
                    range_end=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
                    label="01.06 - 30.06.2026",
                ),
                display_currency="BYN",
                summary=AnalyticsSummaryOut(
                    completed_count=0,
                    cancelled_count=0,
                    no_show_count=0,
                    unique_clients=0,
                    new_clients=0,
                    repeat_clients=0,
                ),
                money=[],
                revenue_by_day=[],
                services=[],
                clients_to_return=[],
            )

    app.dependency_overrides[require_master_profile] = lambda: SimpleNamespace(id=expected_master_id)
    app.dependency_overrides[get_master_analytics_use_case] = FakeAnalyticsUseCase
    try:
        with TestClient(app) as client:
            response = client.get("/api/master/analytics?period=current_month")
    finally:
        app.dependency_overrides.pop(require_master_profile, None)
        app.dependency_overrides.pop(get_master_analytics_use_case, None)

    assert response.status_code == 200
    assert response.json()["display_currency"] == "BYN"
