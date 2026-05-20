"""Client self-service booking use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.booking import BookingStatus
from app.schemas.availability import SlotOut
from app.schemas.booking import ClientBookingCreate
from app.use_cases.booking.client_booking import (
    CancelClientBookingUseCase,
    ClientBookingUseCaseDeps,
    CreateClientBookingUseCase,
    RescheduleClientBookingUseCase,
)
from app.use_cases.booking.exceptions import CreateBookingError, UpdateBookingError


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
        "cancel_comment": None,
        "reschedule_comment": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _booking_deps(
    *,
    master_repo,
    client_repo,
    service_repo,
    booking_repo,
    master_user_id: uuid.UUID,
    slots_uc=None,
):
    return ClientBookingUseCaseDeps(
        master_repo=master_repo,
        client_repo=client_repo,
        service_repo=service_repo,
        booking_repo=booking_repo,
        user_repo=SimpleNamespace(
            get_by_id=AsyncMock(
                return_value=SimpleNamespace(
                    id=master_user_id,
                    email="master@example.com",
                    email_verified_at=datetime.now(UTC),
                ),
            ),
        ),
        dispatcher=SimpleNamespace(
            dispatch_booking_created=AsyncMock(),
            dispatch_booking_cancelled=AsyncMock(),
            dispatch_booking_moved=AsyncMock(),
        ),
        available_slots_use_case=slots_uc,
    )


@pytest.mark.asyncio
async def test_create_client_booking_success() -> None:
    master_id = uuid.uuid4()
    master_user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)

    master = SimpleNamespace(
        id=master_id,
        user_id=master_user_id,
        display_name="Studio",
        timezone="UTC",
        public_slug=None,
    )
    client = SimpleNamespace(id=client_id, user_id=user_id, display_name="Anna")
    link = SimpleNamespace(client_alias="My Studio", alias="Anna K.")
    service = SimpleNamespace(
        id=service_id,
        name="Стрижка",
        duration_min=45,
        price=Decimal("75"),
        currency="BYN",
        is_active=True,
    )

    class FakeMasterRepo:
        async def get_by_master_id(self, mid):
            return master if mid == master_id else None

    class FakeClientRepo:
        async def get_linked_client_for_master_user(self, mid, uid):
            if mid == master_id and uid == user_id:
                return (link, client)
            return None

    class FakeServiceRepo:
        async def get_for_master(self, sid, mid):
            return service if sid == service_id and mid == master_id else None

    class FakeBookingRepo:
        async def has_conflict(self, *_a, **_k):
            return False

        async def create(self, booking):
            booking.id = uuid.uuid4()
            return booking

    slots_uc = AsyncMock(return_value=[SlotOut(start_at=start_at)])
    deps = _booking_deps(
        master_repo=FakeMasterRepo(),
        client_repo=FakeClientRepo(),
        service_repo=FakeServiceRepo(),
        booking_repo=FakeBookingRepo(),
        master_user_id=master_user_id,
        slots_uc=slots_uc,
    )
    uc = CreateClientBookingUseCase(deps)
    result = await uc(
        ClientBookingCreate(master_id=master_id, service_id=service_id, start_at=start_at),
        user=SimpleNamespace(id=user_id),
    )
    assert result.master_display_name == "My Studio"
    assert result.service_name == "Стрижка"
    deps.dispatcher.dispatch_booking_created.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_client_booking_requires_link() -> None:
    uc = CreateClientBookingUseCase(
        _booking_deps(
            master_repo=SimpleNamespace(
                get_by_master_id=AsyncMock(
                    return_value=SimpleNamespace(
                        id=uuid.uuid4(),
                        user_id=uuid.uuid4(),
                        display_name="M",
                        timezone="UTC",
                        public_slug=None,
                    ),
                ),
            ),
            client_repo=SimpleNamespace(get_linked_client_for_master_user=AsyncMock(return_value=None)),
            service_repo=SimpleNamespace(),
            booking_repo=SimpleNamespace(),
            master_user_id=uuid.uuid4(),
            slots_uc=AsyncMock(),
        ),
    )
    with pytest.raises(CreateBookingError, match="Not linked"):
        await uc(
            ClientBookingCreate(master_id=uuid.uuid4(), service_id=uuid.uuid4(), start_at=datetime.now(UTC)),
            user=SimpleNamespace(id=uuid.uuid4()),
        )


@pytest.mark.asyncio
async def test_cancel_client_booking() -> None:
    user_id = uuid.uuid4()
    master_user_id = uuid.uuid4()
    master_id = uuid.uuid4()
    booking = _booking(master_id=master_id)
    master = SimpleNamespace(id=master_id, user_id=master_user_id, display_name="Studio", timezone="UTC")
    service = SimpleNamespace(id=booking.service_id, name="Услуга")
    link = SimpleNamespace(alias="Anna")
    client = SimpleNamespace(id=booking.client_id, display_name="Anna")

    class FakeBookingRepo:
        async def get_for_user(self, bid, uid):
            return booking if bid == booking.id and uid == user_id else None

        flushed = False

        async def flush(self):
            self.flushed = True

    deps = _booking_deps(
        master_repo=SimpleNamespace(get_by_master_id=AsyncMock(return_value=master)),
        client_repo=SimpleNamespace(get_link_with_client=AsyncMock(return_value=(link, client))),
        service_repo=SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
        booking_repo=FakeBookingRepo(),
        master_user_id=master_user_id,
    )
    await CancelClientBookingUseCase(deps)(
        user=SimpleNamespace(id=user_id),
        booking_id=booking.id,
        comment="  Не смогу  ",
    )

    assert booking.status is BookingStatus.CANCELLED
    assert booking.cancel_comment == "Не смогу"
    deps.dispatcher.dispatch_booking_cancelled.assert_awaited_once()


@pytest.mark.asyncio
async def test_reschedule_client_booking() -> None:
    user_id = uuid.uuid4()
    master_user_id = uuid.uuid4()
    master_id = uuid.uuid4()
    new_start = datetime(2026, 5, 21, 14, 0, tzinfo=UTC)
    booking = _booking(master_id=master_id)

    master = SimpleNamespace(
        id=master_id,
        user_id=master_user_id,
        display_name="Studio",
        timezone="UTC",
        public_slug=None,
    )
    service = SimpleNamespace(id=booking.service_id, name="Услуга", is_active=True)
    link = SimpleNamespace(client_alias="Renamed Studio", alias="Anna")
    client = SimpleNamespace(id=booking.client_id, display_name="Anna")

    class FakeBookingRepo:
        async def get_for_user(self, bid, uid):
            return booking if bid == booking.id and uid == user_id else None

        async def has_conflict(self, *_a, **_k):
            return False

        async def flush(self):
            pass

    deps = _booking_deps(
        master_repo=SimpleNamespace(get_by_master_id=AsyncMock(return_value=master)),
        client_repo=SimpleNamespace(get_link_with_client=AsyncMock(return_value=(link, client))),
        service_repo=SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
        booking_repo=FakeBookingRepo(),
        master_user_id=master_user_id,
        slots_uc=AsyncMock(return_value=[SlotOut(start_at=new_start)]),
    )
    uc = RescheduleClientBookingUseCase(deps)
    result = await uc(
        user=SimpleNamespace(id=user_id),
        booking_id=booking.id,
        start_at=new_start,
        comment="Удобно?",
    )
    assert result.start_at == new_start
    assert result.master_display_name == "Renamed Studio"
    assert booking.reschedule_comment == "Удобно?"
    deps.dispatcher.dispatch_booking_moved.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_client_booking_not_found() -> None:
    with pytest.raises(UpdateBookingError):
        await CancelClientBookingUseCase(
            _booking_deps(
                master_repo=SimpleNamespace(),
                client_repo=SimpleNamespace(),
                service_repo=SimpleNamespace(),
                booking_repo=SimpleNamespace(get_for_user=AsyncMock(return_value=None)),
                master_user_id=uuid.uuid4(),
            ),
        )(
            user=SimpleNamespace(id=uuid.uuid4()),
            booking_id=uuid.uuid4(),
        )
