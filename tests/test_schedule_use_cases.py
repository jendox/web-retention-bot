import uuid
from datetime import UTC, datetime, time
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.booking import BookingStatus
from app.models.schedule import WeeklyScheduleRule, WorkdayOverride, WorkdayOverrideInterval
from app.schemas.master import MasterScheduleUpsert
from app.services.availability import windows_for_date
from app.use_cases import replace_schedule as replace_schedule_module
from app.use_cases.replace_schedule import booking_fits_schedule


def test_schedule_payload_rejects_overlapping_weekly_intervals():
    with pytest.raises(ValidationError):
        MasterScheduleUpsert(
            weekly_rules=[
                {
                    "weekday": 0,
                    "intervals": [
                        {"start_time": "10:00", "end_time": "13:00"},
                        {"start_time": "12:30", "end_time": "18:00"},
                    ],
                },
            ],
            overrides=[],
        )


def test_schedule_payload_rejects_closed_override_with_intervals():
    with pytest.raises(ValidationError):
        MasterScheduleUpsert(
            weekly_rules=[],
            overrides=[
                {
                    "override_date": "2026-05-23",
                    "is_closed": True,
                    "intervals": [{"start_time": "10:00", "end_time": "12:00"}],
                },
            ],
        )


def test_windows_for_date_uses_multiple_override_intervals_instead_of_weekly_template():
    target = datetime(2026, 5, 23, tzinfo=UTC).date()
    weekly = [
        WeeklyScheduleRule(
            master_id=uuid.uuid4(),
            weekday=target.weekday(),
            start_time=time(9, 0),
            end_time=time(18, 0),
        ),
    ]
    override = WorkdayOverride(
        master_id=uuid.uuid4(),
        override_date=target,
        is_closed=False,
    )
    override.intervals = [
        WorkdayOverrideInterval(start_time=time(11, 0), end_time=time(14, 0), sort_order=0),
        WorkdayOverrideInterval(start_time=time(15, 0), end_time=time(18, 0), sort_order=1),
    ]

    windows = windows_for_date(target, weekly, [override], UTC)

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
        status=BookingStatus.scheduled,
    )
    weekly = [
        WeeklyScheduleRule(
            master_id=master_id,
            weekday=5,
            start_time=time(10, 0),
            end_time=time(14, 30),
        ),
    ]

    assert booking_fits_schedule(booking, weekly, [], "UTC") is False


async def test_replace_schedule_rejects_changes_that_cut_existing_future_booking(monkeypatch):
    master_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id,
        start_at=datetime(2026, 6, 1, 13, 0, tzinfo=UTC),
        end_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        status=BookingStatus.scheduled,
    )

    class FakeBookingRepository:
        def __init__(self, session):
            self.session = session

        async def list_for_master(self, requested_master_id):
            assert requested_master_id == master_id
            return [booking]

    monkeypatch.setattr(replace_schedule_module, "BookingRepository", FakeBookingRepository)

    payload = MasterScheduleUpsert(
        weekly_rules=[
            {
                "weekday": 0,
                "intervals": [{"start_time": "10:00", "end_time": "12:00"}],
            },
        ],
        overrides=[],
    )

    with pytest.raises(replace_schedule_module.ScheduleBookingConflictError) as exc_info:
        await replace_schedule_module.replace_master_schedule(
            SimpleNamespace(),
            master_id,
            "UTC",
            weekly=payload.weekly_rules,
            overrides=payload.overrides,
        )

    assert exc_info.value.conflicts == [booking]
