import uuid
from datetime import UTC, date, datetime, time
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.api.deps import require_master_profile
from app.main import app
from app.models.booking import BookingStatus
from app.models.schedule import (
    ScheduleDateOverride,
    ScheduleDateOverrideInterval,
    WeeklyScheduleDay,
    WeeklyScheduleInterval,
)
from app.schemas.master import MasterProfileSchema, MasterScheduleUpsert
from app.services.availability import windows_for_date
from app.use_cases.booking import available_slots as available_slots_module
from app.use_cases.schedule import replace_schedule as replace_schedule_module
from app.use_cases.schedule.exceptions import ScheduleBookingConflictError
from app.use_cases.schedule.replace_schedule import booking_fits_schedule, get_replace_master_schedule_use_case


def test_schedule_payload_rejects_overlapping_weekly_intervals():
    with pytest.raises(ValidationError):
        MasterScheduleUpsert(
            weekly_days=[
                {
                    "weekday": 0,
                    "intervals": [
                        {"start_time": "10:00", "end_time": "13:00"},
                        {"start_time": "12:30", "end_time": "18:00"},
                    ],
                },
            ],
            date_overrides=[],
        )


def test_schedule_payload_rejects_closed_override_with_intervals():
    with pytest.raises(ValidationError):
        MasterScheduleUpsert(
            weekly_days=[],
            date_overrides=[
                {
                    "schedule_date": "2026-05-23",
                    "is_closed": True,
                    "intervals": [{"start_time": "10:00", "end_time": "12:00"}],
                },
            ],
        )


def test_windows_for_date_uses_multiple_override_intervals_instead_of_weekly_template():
    target = datetime(2026, 5, 23, tzinfo=UTC).date()
    weekly_day = WeeklyScheduleDay(
        master_id=uuid.uuid4(),
        weekday=target.weekday(),
        is_closed=False,
    )
    weekly_day.intervals = [
        WeeklyScheduleInterval(start_time=time(9, 0), end_time=time(18, 0), sort_order=0),
    ]
    override = ScheduleDateOverride(
        master_id=uuid.uuid4(),
        schedule_date=target,
        is_closed=False,
    )
    override.intervals = [
        ScheduleDateOverrideInterval(start_time=time(11, 0), end_time=time(14, 0), sort_order=0),
        ScheduleDateOverrideInterval(start_time=time(15, 0), end_time=time(18, 0), sort_order=1),
    ]

    windows = windows_for_date(target, [weekly_day], [override], UTC)

    assert [(window[0].time(), window[1].time()) for window in windows] == [
        (time(11, 0), time(14, 0)),
        (time(15, 0), time(18, 0)),
    ]


def test_booking_fits_schedule_detects_booking_cut_by_new_hours():
    master_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id,
        start_at=datetime(2026, 5, 23, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 5, 23, 15, 0, tzinfo=UTC),
        status=BookingStatus.SCHEDULED,
    )
    weekly_day = WeeklyScheduleDay(
        master_id=master_id,
        weekday=5,
        is_closed=False,
    )
    weekly_day.intervals = [
        WeeklyScheduleInterval(start_time=time(10, 0), end_time=time(14, 30), sort_order=0),
    ]

    assert booking_fits_schedule(booking, [weekly_day], [], "UTC") is False


def test_filter_future_slots_for_today_removes_past_and_current_slots():
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    slots = [
        datetime(2026, 5, 18, 11, 45, tzinfo=UTC),
        datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        datetime(2026, 5, 18, 12, 15, tzinfo=UTC),
    ]

    filtered = available_slots_module.filter_future_slots_for_day(
        slots,
        master_profile=MasterProfileSchema(
            id=uuid.uuid4(),
            display_name="Master",
            public_slug=None,
            timezone="UTC",
        ),
        calendar_day=now.date(),
        now=now,
    )

    assert filtered == [datetime(2026, 5, 18, 12, 15, tzinfo=UTC)]


def test_filter_future_slots_keeps_all_future_day_slots():
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    slots = [
        datetime(2026, 5, 19, 9, 0, tzinfo=UTC),
        datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
    ]

    filtered = available_slots_module.filter_future_slots_for_day(
        slots,
        master_profile=MasterProfileSchema(
            id=uuid.uuid4(),
            display_name="Master",
            public_slug=None,
            timezone="UTC",
        ),
        calendar_day=datetime(2026, 5, 19, tzinfo=UTC).date(),
        now=now,
    )

    assert filtered == slots


async def test_replace_schedule_rejects_changes_that_cut_existing_future_booking():
    master_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id,
        start_at=datetime(2026, 6, 1, 13, 0, tzinfo=UTC),
        end_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        status=BookingStatus.SCHEDULED,
    )
    expected_master_id = master_id

    class FakeBookingRepository:
        async def list_for_master(self, *, master_id, limit=500):
            assert master_id == expected_master_id
            return [booking]

    class FakeScheduleRepository:
        async def replace_weekly_days(self, requested_master_id, days):
            raise AssertionError("schedule must not be replaced when future bookings conflict")

        async def replace_date_overrides(self, requested_master_id, items):
            raise AssertionError("schedule must not be replaced when future bookings conflict")

        async def flush(self):
            raise AssertionError("schedule must not be flushed when future bookings conflict")

    class FakeGetScheduleUseCase:
        async def __call__(self, requested_master_id):
            raise AssertionError("updated schedule must not be returned when future bookings conflict")

    payload = MasterScheduleUpsert(
        weekly_days=[
            {
                "weekday": 0,
                "intervals": [{"start_time": "10:00", "end_time": "12:00"}],
            },
        ],
        date_overrides=[],
    )

    use_case = replace_schedule_module.ReplaceMasterScheduleUseCase(
        FakeScheduleRepository(),
        FakeBookingRepository(),
        FakeGetScheduleUseCase(),
    )
    master = SimpleNamespace(id=master_id, timezone="UTC")

    with pytest.raises(replace_schedule_module.ScheduleBookingConflictError) as exc_info:
        await use_case(master, payload)

    assert exc_info.value.code == "schedule.booking_conflict"
    assert exc_info.value.context == {
        "conflicts": [
            {
                "id": str(booking.id),
                "start_at": "2026-06-01T13:00:00+00:00",
                "end_at": "2026-06-01T14:00:00+00:00",
            },
        ],
    }


def test_replace_schedule_route_returns_conflict_context():
    conflict_context = {
        "conflicts": [
            {
                "id": str(uuid.uuid4()),
                "start_at": "2026-06-01T13:00:00+00:00",
                "end_at": "2026-06-01T14:00:00+00:00",
            },
        ],
    }

    class FakeReplaceScheduleUseCase:
        async def __call__(self, master, payload):
            raise ScheduleBookingConflictError(context=conflict_context)

    app.dependency_overrides[require_master_profile] = lambda: SimpleNamespace(id=uuid.uuid4(), timezone="UTC")
    app.dependency_overrides[get_replace_master_schedule_use_case] = FakeReplaceScheduleUseCase
    try:
        with TestClient(app) as client:
            client.cookies.set("csrf_token", "token")
            response = client.put(
                "/api/master/schedule",
                json={
                    "weekly_days": [
                        {
                            "weekday": 0,
                            "is_closed": False,
                            "intervals": [{"start_time": "10:00", "end_time": "18:00"}],
                            "note": None,
                        },
                    ],
                    "date_overrides": [],
                },
                headers={"X-CSRF-Token": "token"},
            )
    finally:
        app.dependency_overrides.pop(require_master_profile, None)
        app.dependency_overrides.pop(get_replace_master_schedule_use_case, None)

    assert response.status_code == 409
    assert response.json() == {
        "code": "schedule.booking_conflict",
        "detail": "Schedule changes affect existing bookings.",
        "context": conflict_context,
    }


async def test_replace_schedule_replaces_models_flushes_and_returns_snapshot():
    master_id = uuid.uuid4()
    expected_master_id = master_id

    class FakeBookingRepository:
        async def list_for_master(self, *, master_id, limit=500):
            assert master_id == expected_master_id
            return []

    class FakeScheduleRepository:
        def __init__(self):
            self.weekly_days = None
            self.date_overrides = None
            self.flushed = False

        async def replace_weekly_days(self, requested_master_id, days):
            assert requested_master_id == master_id
            self.weekly_days = days

        async def replace_date_overrides(self, requested_master_id, items):
            assert requested_master_id == master_id
            self.date_overrides = items

        async def flush(self):
            self.flushed = True

    class FakeGetScheduleUseCase:
        def __init__(self):
            self.requested_master_id = None

        async def __call__(self, requested_master_id):
            self.requested_master_id = requested_master_id
            return "snapshot"

    payload = MasterScheduleUpsert(
        weekly_days=[
            {
                "weekday": 0,
                "intervals": [{"start_time": "10:00", "end_time": "18:00"}],
            },
        ],
        date_overrides=[
            {
                "schedule_date": "2026-05-19",
                "is_closed": False,
                "intervals": [{"start_time": "12:00", "end_time": "16:00"}],
                "note": "Special day",
            },
        ],
    )
    schedule_repo = FakeScheduleRepository()
    get_schedule = FakeGetScheduleUseCase()
    use_case = replace_schedule_module.ReplaceMasterScheduleUseCase(
        schedule_repo,
        FakeBookingRepository(),
        get_schedule,
    )
    master = SimpleNamespace(id=master_id, timezone="UTC")

    result = await use_case(master, payload)

    assert result == "snapshot"
    assert schedule_repo.flushed is True
    assert get_schedule.requested_master_id == master_id
    assert len(schedule_repo.weekly_days) == 1
    assert schedule_repo.weekly_days[0].master_id == master_id
    assert schedule_repo.weekly_days[0].weekday == 0
    assert schedule_repo.weekly_days[0].intervals[0].start_time == time(10, 0)
    assert schedule_repo.weekly_days[0].intervals[0].end_time == time(18, 0)
    assert len(schedule_repo.date_overrides) == 1
    assert schedule_repo.date_overrides[0].schedule_date == date(2026, 5, 19)
    assert schedule_repo.date_overrides[0].note == "Special day"
    assert schedule_repo.date_overrides[0].intervals[0].start_time == time(12, 0)
    assert schedule_repo.date_overrides[0].intervals[0].end_time == time(16, 0)
