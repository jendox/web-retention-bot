import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.currency import Currency
from app.core.pagination import Pagination
from app.models.booking import BookingStatus, booking_needs_attendance_confirmation
from app.schemas.availability import SlotOut
from app.schemas.booking import BookingClientListItem, BookingCreate, BookingListScope, BookingOut
from app.use_cases.booking.available_slots import AvailableSlotsUseCase
from app.use_cases.booking.create import CreateBookingUseCase
from app.use_cases.booking.exceptions import AvailabilitySlotsError, UpdateBookingError
from app.use_cases.booking.list import ListClientBookingsUseCase, ListMasterBookingsUseCase
from app.use_cases.booking.update import (
    CancelBookingUseCase,
    MarkBookingAttendanceUseCase,
    RescheduleBookingUseCase,
)


def _booking(**overrides):
    data = {
        "id": uuid.uuid4(),
        "master_id": uuid.uuid4(),
        "client_id": uuid.uuid4(),
        "service_id": uuid.uuid4(),
        "start_at": datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
        "end_at": datetime(2026, 5, 20, 11, 0, tzinfo=UTC),
        "duration_min": 60,
        "price_snapshot": Decimal("50.00"),
        "currency_snapshot": "BYN",
        "status": BookingStatus.SCHEDULED,
        "attendance_confirmed_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class FakeBookingRepository:
    def __init__(self, booking=None, *, conflicts=False):
        self.booking = booking
        self.conflicts = conflicts
        self.created = None
        self.flushed = False

    async def create(self, booking):
        self.created = booking
        booking.id = uuid.uuid4()
        return booking

    async def has_conflict(self, *args, **kwargs):
        return self.conflicts

    async def get_for_master(self, booking_id, master_id):
        if self.booking and self.booking.id == booking_id and self.booking.master_id == master_id:
            return self.booking
        return None

    async def list_for_master(self, master_id, *, limit=500):
        return [self.booking] if self.booking and self.booking.master_id == master_id else []

    async def count_for_master(self, master_id, scope, client_id=None, service_id=None):
        rows = await self.list_for_master_page(
            master_id,
            scope=scope,
            limit=500,
            offset=0,
            client_id=client_id,
            service_id=service_id,
        )
        return len(rows)

    async def list_for_master_page(self, master_id, scope, limit, offset, client_id=None, service_id=None):
        rows = [self.booking] if self.booking and self.booking.master_id == master_id else []
        if client_id is not None:
            rows = [b for b in rows if b.client_id == client_id]
        if service_id is not None:
            rows = [b for b in rows if b.service_id == service_id]
        return rows[offset : offset + limit]

    async def complete_past_scheduled(self):
        if self.booking and self.booking.status == BookingStatus.SCHEDULED:
            self.booking.status = BookingStatus.COMPLETED
            return 1
        return 0

    async def count_for_client_user(self, user_id, *, scope):
        rows = await self.list_for_client_user_page(user_id, scope=scope, limit=500, offset=0)
        return len(rows)

    async def list_for_client_user_page(self, user_id, *, scope, limit, offset):
        _ = user_id, scope
        rows = [(self.booking, "Master", "Service")] if self.booking else []
        return rows[offset : offset + limit]

    async def flush(self):
        self.flushed = True


async def test_create_booking_creates_snapshot_when_slot_is_available():
    master_id = uuid.uuid4()
    client_id = uuid.uuid4()
    service_id = uuid.uuid4()
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)

    class FakeClientRepository:
        async def link_exists(self, requested_master_id, requested_client_id):
            assert requested_master_id == master_id
            assert requested_client_id == client_id
            return True

        async def get_client(self, requested_client_id):
            return None

    class FakeServiceRepository:
        async def get_for_master(self, requested_service_id, requested_master_id):
            assert requested_service_id == service_id
            assert requested_master_id == master_id
            return SimpleNamespace(
                id=service_id,
                duration_min=45,
                price=Decimal("75.00"),
                currency="BYN",
                is_active=True,
            )

    class FakeAvailableSlotsUseCase:
        async def __call__(self, *, master_id, service_id, calendar_day):
            return [SlotOut(start_at=start_at)]

    class FakeUserRepository:
        async def get_by_id(self, _user_id):
            return None

    booking_repo = FakeBookingRepository()
    dispatcher = SimpleNamespace(dispatch_booking_created=AsyncMock())
    use_case = CreateBookingUseCase(
        user_repo=FakeUserRepository(),
        client_repo=FakeClientRepository(),
        service_repo=FakeServiceRepository(),
        booking_repo=booking_repo,
        available_slots_use_case=FakeAvailableSlotsUseCase(),
        dispatcher=dispatcher,
    )

    result = await use_case(
        BookingCreate(client_id=client_id, service_id=service_id, start_at=start_at),
        master=SimpleNamespace(
            id=master_id,
            display_name="Master",
            public_slug=None,
            timezone="UTC",
        ),
    )

    assert isinstance(result, BookingOut)
    assert result.master_id == master_id
    assert result.client_id == client_id
    assert result.service_id == service_id
    assert result.end_at == start_at + timedelta(minutes=45)
    assert booking_repo.created is not None


async def test_mark_attendance_attended_confirms_completed():
    master_id = uuid.uuid4()
    past = datetime.now(UTC) - timedelta(hours=2)
    booking = _booking(
        master_id=master_id,
        status=BookingStatus.COMPLETED,
        start_at=past,
        end_at=past + timedelta(minutes=60),
    )
    assert booking_needs_attendance_confirmation(booking)
    use_case = MarkBookingAttendanceUseCase(FakeBookingRepository(booking))

    result = await use_case(master_id=master_id, booking_id=booking.id, attended=True)

    assert result.status == BookingStatus.COMPLETED
    assert booking.attendance_confirmed_at is not None
    assert not booking_needs_attendance_confirmation(booking)


async def test_mark_attendance_no_show_updates_status():
    master_id = uuid.uuid4()
    past = datetime.now(UTC) - timedelta(hours=2)
    booking = _booking(
        master_id=master_id,
        status=BookingStatus.COMPLETED,
        start_at=past,
        end_at=past + timedelta(minutes=60),
    )
    use_case = MarkBookingAttendanceUseCase(FakeBookingRepository(booking))

    result = await use_case(master_id=master_id, booking_id=booking.id, attended=False)

    assert result.status == BookingStatus.NO_SHOW
    assert booking.attendance_confirmed_at is not None


async def test_cancel_booking_marks_booking_cancelled_and_flushes():
    master_id = uuid.uuid4()
    booking = _booking(master_id=master_id)
    booking_repo = FakeBookingRepository(booking)
    master = SimpleNamespace(id=master_id, display_name="Master", public_slug=None, timezone="UTC")
    dispatcher = SimpleNamespace()
    use_case = CancelBookingUseCase(
        booking_repo,
        SimpleNamespace(get_client=AsyncMock(return_value=None)),
        SimpleNamespace(get_for_master=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4(), name="Услуга"))),
        SimpleNamespace(),
        dispatcher,
    )

    await use_case(master=master, booking_id=booking.id)

    assert booking.status == BookingStatus.CANCELLED
    assert booking_repo.flushed is True


async def test_reschedule_booking_rejects_unavailable_slot():
    master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking = _booking(master_id=master_id, service_id=service_id)

    class FakeServiceRepository:
        async def get_for_master(self, requested_service_id, requested_master_id):
            assert requested_service_id == service_id
            assert requested_master_id == master_id
            return SimpleNamespace(id=service_id)

    class FakeAvailableSlotsUseCase:
        async def __call__(self, *, master_id, service_id, calendar_day):
            return []

    use_case = RescheduleBookingUseCase(
        FakeBookingRepository(booking),
        FakeServiceRepository(),
        SimpleNamespace(get_client=AsyncMock(return_value=None)),
        SimpleNamespace(),
        FakeAvailableSlotsUseCase(),
        SimpleNamespace(),
    )
    master = SimpleNamespace(id=master_id, display_name="Master", public_slug=None, timezone="UTC")

    with pytest.raises(UpdateBookingError) as exc_info:
        await use_case(master=master, booking_id=booking.id, start_at=datetime(2026, 5, 21, 10, 0, tzinfo=UTC))

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_message == "Requested slot unavailable"


async def test_list_booking_use_cases_return_response_schemas():
    master_id = uuid.uuid4()
    booking = _booking(master_id=master_id)
    booking_repo = FakeBookingRepository(booking)

    master_result = await ListMasterBookingsUseCase(booking_repo)(
        master_id,
        Pagination(page=1, page_size=10),
        scope=BookingListScope.UPCOMING,
    )
    client_result = await ListClientBookingsUseCase(booking_repo)(
        uuid.uuid4(),
        Pagination(page=1, page_size=10),
        scope=BookingListScope.UPCOMING,
    )

    assert master_result.items == [BookingOut.model_validate(booking)]
    assert master_result.total == 1
    assert client_result.items == [
        BookingClientListItem(
            **BookingOut.model_validate(booking).model_dump(),
            master_display_name="Master",
            service_name="Service",
        ),
    ]
    assert client_result.total == 1


async def test_available_slots_use_case_uses_explicit_booking_settings():
    master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    calendar_day = (datetime.now(UTC) + timedelta(days=1)).date()
    slot = datetime.combine(calendar_day, datetime.min.time(), tzinfo=UTC).replace(hour=10)

    class FakeMasterRepository:
        async def get_by_master_id(self, requested_master_id):
            assert requested_master_id == master_id
            return SimpleNamespace(
                id=master_id,
                display_name="Master",
                public_slug=None,
                timezone="UTC",
            )

    class FakeServiceRepository:
        async def get_for_master(self, requested_service_id, requested_master_id):
            assert requested_service_id == service_id
            assert requested_master_id == master_id
            return SimpleNamespace(
                id=service_id,
                master_id=master_id,
                name="Service",
                description=None,
                duration_min=45,
                price=Decimal("75.00"),
                currency=Currency.BYN,
                is_active=True,
                sort_order=0,
            )

    class FakeScheduleRepository:
        async def weekly_days_for_master(self, requested_master_id):
            assert requested_master_id == master_id
            return []

        async def date_overrides_for_master(self, requested_master_id):
            assert requested_master_id == master_id
            return []

    class FakeAvailabilityEngine:
        def __init__(self):
            self.slot_step_minutes = None

        async def slots_between(self, **kwargs):
            self.slot_step_minutes = kwargs["slot_step_minutes"]
            return [slot]

    engine = FakeAvailabilityEngine()
    settings = SimpleNamespace(
        booking=SimpleNamespace(
            max_advance_days=30,
            availability_slot_step_minutes=20,
        ),
    )
    use_case = AvailableSlotsUseCase(
        FakeMasterRepository(),
        FakeServiceRepository(),
        FakeScheduleRepository(),
        engine,
        settings,
    )

    result = await use_case(master_id=master_id, service_id=service_id, calendar_day=calendar_day)

    assert result == [SlotOut(start_at=slot)]
    assert engine.slot_step_minutes == 20


async def test_available_slots_use_case_rejects_past_day():
    settings = SimpleNamespace(
        booking=SimpleNamespace(
            max_advance_days=30,
            availability_slot_step_minutes=15,
        ),
    )

    class FakeMasterRepository:
        async def get_by_master_id(self, master_id):
            return SimpleNamespace(
                id=master_id,
                display_name="Master",
                public_slug=None,
                timezone="UTC",
            )

    use_case = AvailableSlotsUseCase(
        master_repo=FakeMasterRepository(),
        service_repo=SimpleNamespace(),
        schedule_repo=SimpleNamespace(),
        availability_engine=SimpleNamespace(),
        settings=settings,
    )

    with pytest.raises(AvailabilitySlotsError) as exc_info:
        await use_case(
            master_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            calendar_day=(datetime.now(UTC) - timedelta(days=1)).date(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_message == "Date is in the past"
