"""Booking notification recipients, templates, dispatcher, and create-booking hook."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.models.booking import BookingStatus
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationEventType
from app.schemas.availability import SlotOut
from app.schemas.booking import BookingCreate, BookingOut
from app.services.notifications.booking_mail import BookingNotificationSkip, deliver_booking_created_email
from app.services.notifications.datetime_format import format_booking_start_local
from app.services.notifications.dispatcher import BookingEmailContext, NotificationDispatcher
from app.services.notifications.mail_render import (
    BookingCancelledEmailRenderContext,
    BookingMovedEmailRenderContext,
    append_master_comment_to_body,
    booking_cancelled_in_app_copy,
    booking_created_in_app_copy,
    booking_moved_in_app_copy,
    render_booking_cancelled,
    render_booking_created,
    render_booking_moved,
)
from app.services.notifications.recipients import resolve_booking_client_recipient, resolve_booking_master_recipient
from app.use_cases.booking.create import CreateBookingUseCase
from app.use_cases.booking.update import CancelBookingUseCase, RescheduleBookingUseCase


@pytest.fixture
def mail_settings() -> Settings:
    return Settings.model_validate(
        {
            "celery": {
                "broker_url": "redis://localhost:6379/1",
                "result_backend": "redis://localhost:6379/1",
            },
            "notifications": {"eager_deliveries": True},
            "security": {
                "secret_key": "unit-test-mail-secret",
                "frontend_public_origin": "https://frontend.test",
                "auth_log_verification_link": False,
            },
            "smtp": {"enabled": False},
        },
    )


def test_resolve_booking_client_recipient_requires_linked_verified_user() -> None:
    user_id = uuid.uuid4()
    client = SimpleNamespace(user_id=user_id)
    verified_user = SimpleNamespace(id=user_id, email="client@example.com", email_verified_at=datetime.now(UTC))

    assert resolve_booking_client_recipient(client, verified_user) is not None
    assert resolve_booking_client_recipient(client, None) is None
    assert resolve_booking_client_recipient(SimpleNamespace(user_id=None), verified_user) is None
    assert (
        resolve_booking_client_recipient(
            client,
            SimpleNamespace(id=user_id, email="client@example.com", email_verified_at=None),
        )
        is None
    )
    assert (
        resolve_booking_client_recipient(
            client,
            SimpleNamespace(id=uuid.uuid4(), email="other@example.com", email_verified_at=datetime.now(UTC)),
        )
        is None
    )


def test_format_booking_start_local_uses_master_timezone() -> None:
    start_at = datetime(2026, 5, 20, 7, 30, tzinfo=UTC)
    formatted = format_booking_start_local(start_at, "Europe/Minsk")
    assert "2026" in formatted
    assert "30" in formatted or "10" in formatted


def test_render_booking_created_templates() -> None:
    subject, text_body, html_body = render_booking_created(
        recipient_email="c@example.com",
        master_name="Studio",
        service_name="Стрижка",
        start_at_local="среда, 20 мая 2026 г., 10:00",
        duration_min=45,
        cabinet_url="https://frontend.test/client",
    )
    assert "Стрижка" in subject
    assert "Studio" in text_body
    assert "https://frontend.test/client" in html_body


def test_booking_created_in_app_copy() -> None:
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    title, body, link_url = booking_created_in_app_copy(
        master_display_name="Master",
        service_name="Услуга",
        start_at=start_at,
        master_timezone="UTC",
    )
    assert title == "Новая запись"
    assert "Master" in body
    assert "Услуга" in body
    assert link_url is not None
    assert link_url.endswith("/client")


class _FakeNotificationRepos:
    def __init__(self) -> None:
        self.events: list = []
        self.notes: list = []
        self.deliveries: list = []

    async def create_event(self, data):
        event = SimpleNamespace(id=uuid.uuid4(), **data.__dict__)
        self.events.append(event)
        return event

    async def create_note(self, data):
        extra = {k: v for k, v in data.__dict__.items() if k != "payload"}
        note = SimpleNamespace(id=uuid.uuid4(), payload=data.payload, **extra)
        note.payload = data.payload
        note.recipient_user_id = data.recipient_user_id
        note.event_type = data.event_type
        self.notes.append(note)
        return note

    async def create_delivery(self, data):
        delivery = SimpleNamespace(id=uuid.uuid4(), sent_at=None, **data.__dict__)
        self.deliveries.append(delivery)
        return delivery


async def test_dispatch_booking_created_persists_event_note_and_delivery(mail_settings: Settings) -> None:
    session = AsyncMock()
    dispatcher = NotificationDispatcher(mail_settings, session)
    fake = _FakeNotificationRepos()
    dispatcher._notification_event_repo = SimpleNamespace(create=fake.create_event)
    dispatcher._user_notification_repo = SimpleNamespace(create=fake.create_note)
    dispatcher._notification_delivery_repo = SimpleNamespace(create=fake.create_delivery)

    booking_id = uuid.uuid4()
    recipient = SimpleNamespace(user_id=uuid.uuid4(), email="client@example.com")

    with patch.object(dispatcher, "_deliver_eager", new_callable=AsyncMock) as mock_deliver:
        await dispatcher.dispatch_booking_created(
            booking_id=booking_id,
            master_profile_id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            recipient=recipient,
            email_ctx=BookingEmailContext(
                title="Новая запись",
                body="body",
                link_url="https://frontend.test/client",
                payload={},
            ),
        )

    mock_deliver.assert_awaited_once()
    assert len(fake.events) == 1
    assert fake.events[0].type == NotificationEventType.BOOKING_CREATED
    assert len(fake.notes) == 1
    assert fake.notes[0].event_type == NotificationEventType.BOOKING_CREATED
    assert len(fake.deliveries) == 1
    assert fake.deliveries[0].channel == DeliveryChannel.EMAIL
    assert fake.deliveries[0].status == DeliveryStatus.SENT


async def test_deliver_booking_created_email_skips_non_scheduled() -> None:
    booking_id = uuid.uuid4()
    master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=booking_id,
        master_id=master_id,
        service_id=service_id,
        status=BookingStatus.CANCELLED,
        start_at=datetime.now(UTC),
        duration_min=30,
    )
    master = SimpleNamespace(id=master_id, display_name="Master", timezone="UTC")
    service = SimpleNamespace(id=service_id, name="Стрижка")
    session = AsyncMock()

    async def get_entity(model, entity_id):
        if model.__name__ == "Booking":
            return booking
        if model.__name__ == "MasterProfile":
            return master
        if model.__name__ == "Service":
            return service
        return None

    session.get = get_entity
    settings = Settings.model_validate(
        {
            "celery": {"broker_url": "redis://x", "result_backend": "redis://x"},
            "security": {"frontend_public_origin": "https://app.test"},
            "smtp": {"enabled": False},
        },
    )

    with pytest.raises(BookingNotificationSkip, match="booking_status"):
        await deliver_booking_created_email(
            settings=settings,
            session=session,
            booking_id=booking_id,
            to_email="c@example.com",
        )


async def test_create_booking_notifies_linked_verified_client() -> None:
    master_id = uuid.uuid4()
    client_id = uuid.uuid4()
    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)

    class FakeClientRepository:
        async def link_exists(self, requested_master_id, requested_client_id):
            return True

        async def get_client(self, requested_client_id):
            return SimpleNamespace(id=requested_client_id, user_id=user_id)

    class FakeUserRepository:
        async def get_by_id(self, requested_user_id):
            return SimpleNamespace(
                id=requested_user_id,
                email="client@example.com",
                email_verified_at=datetime.now(UTC),
            )

    class FakeServiceRepository:
        async def get_for_master(self, requested_service_id, requested_master_id):
            return SimpleNamespace(
                id=service_id,
                name="Стрижка",
                duration_min=45,
                price=Decimal("75.00"),
                currency="BYN",
                is_active=True,
            )

    class FakeBookingRepository:
        async def create(self, booking):
            booking.id = uuid.uuid4()
            return booking

        async def has_conflict(self, *args, **kwargs):
            return False

    class FakeAvailableSlotsUseCase:
        async def __call__(self, *, master_id, service_id, calendar_day):
            return [SlotOut(start_at=start_at)]

    dispatcher = SimpleNamespace(dispatch_booking_created=AsyncMock())

    use_case = CreateBookingUseCase(
        user_repo=FakeUserRepository(),
        client_repo=FakeClientRepository(),
        service_repo=FakeServiceRepository(),
        booking_repo=FakeBookingRepository(),
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
    dispatcher.dispatch_booking_created.assert_awaited_once()
    kwargs = dispatcher.dispatch_booking_created.await_args.kwargs
    assert kwargs["client_id"] == client_id
    assert kwargs["recipient"].email == "client@example.com"


async def test_create_booking_skips_notification_without_linked_user() -> None:
    master_id = uuid.uuid4()
    client_id = uuid.uuid4()
    service_id = uuid.uuid4()
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)

    class FakeClientRepository:
        async def link_exists(self, *_args, **_kwargs):
            return True

        async def get_client(self, requested_client_id):
            return SimpleNamespace(id=requested_client_id, user_id=None)

    class FakeUserRepository:
        async def get_by_id(self, *_args, **_kwargs):
            return None

    class FakeServiceRepository:
        async def get_for_master(self, *_args, **_kwargs):
            return SimpleNamespace(
                id=service_id,
                name="Услуга",
                duration_min=45,
                price=Decimal("75.00"),
                currency="BYN",
                is_active=True,
            )

    class FakeBookingRepository:
        async def create(self, booking):
            booking.id = uuid.uuid4()
            return booking

        async def has_conflict(self, *_args, **_kwargs):
            return False

    class FakeAvailableSlotsUseCase:
        async def __call__(self, **_kwargs):
            return [SlotOut(start_at=start_at)]

    dispatcher = SimpleNamespace(dispatch_booking_created=AsyncMock())

    use_case = CreateBookingUseCase(
        user_repo=FakeUserRepository(),
        client_repo=FakeClientRepository(),
        service_repo=FakeServiceRepository(),
        booking_repo=FakeBookingRepository(),
        available_slots_use_case=FakeAvailableSlotsUseCase(),
        dispatcher=dispatcher,
    )

    await use_case(
        BookingCreate(client_id=client_id, service_id=service_id, start_at=start_at),
        master=SimpleNamespace(
            id=master_id,
            display_name="Master",
            public_slug=None,
            timezone="UTC",
        ),
    )

    dispatcher.dispatch_booking_created.assert_not_called()


def test_resolve_booking_master_recipient_requires_verified_email() -> None:
    master = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    user = SimpleNamespace(id=master.user_id, email="m@example.com", email_verified_at=datetime.now(UTC))
    recipient = resolve_booking_master_recipient(master, user)
    assert recipient is not None
    assert recipient.email == "m@example.com"


def test_append_master_comment_to_body() -> None:
    assert append_master_comment_to_body("Основной текст", None) == "Основной текст"
    assert "Комментарий мастера" in append_master_comment_to_body("Основной текст", "Перенёс из‑за болезни")


def test_render_booking_cancelled_templates() -> None:
    subject, text_body, html_body = render_booking_cancelled(
        BookingCancelledEmailRenderContext(
            recipient_email="c@example.com",
            master_name="Studio",
            service_name="Стрижка",
            start_at_local="среда, 20 мая 2026 г., 10:00",
            duration_min=45,
            cabinet_url="https://frontend.test/client",
            master_comment="Свяжитесь для новой даты",
        ),
    )
    assert "отменен" in subject.lower() or "отменена" in subject.lower()
    assert "Studio" in text_body
    assert "Свяжитесь для новой даты" in text_body
    assert "https://frontend.test/client" in html_body


def test_booking_cancelled_in_app_copy() -> None:
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    title, body, link_url = booking_cancelled_in_app_copy(
        master_display_name="Master",
        service_name="Услуга",
        start_at=start_at,
        master_timezone="UTC",
        master_comment="Занят другой клиент",
    )
    assert title == "Запись отменена"
    assert "отменена" in body
    assert "Занят другой клиент" in body
    assert link_url is not None
    assert link_url.endswith("/client/visits")


def test_render_booking_moved_templates() -> None:
    subject, text_body, html_body = render_booking_moved(
        BookingMovedEmailRenderContext(
            recipient_email="c@example.com",
            master_name="Studio",
            service_name="Стрижка",
            previous_start_at_local="вторник, 19 мая 2026 г., 10:00",
            start_at_local="среда, 20 мая 2026 г., 14:00",
            duration_min=45,
            cabinet_url="https://frontend.test/client",
        ),
    )
    assert "перенесен" in subject.lower() or "перенесена" in subject.lower()
    assert "Было" in text_body or "было" in text_body.lower()
    assert "Studio" in text_body


def test_booking_moved_in_app_copy() -> None:
    previous = datetime(2026, 5, 19, 10, 0, tzinfo=UTC)
    start_at = datetime(2026, 5, 20, 14, 0, tzinfo=UTC)
    title, body, link_url = booking_moved_in_app_copy(
        master_display_name="Master",
        service_name="Услуга",
        previous_start_at=previous,
        start_at=start_at,
        master_timezone="UTC",
    )
    assert title == "Запись перенесена"
    assert "→" in body
    assert link_url is not None


async def test_dispatch_booking_cancelled_persists_event(mail_settings: Settings) -> None:
    session = AsyncMock()
    dispatcher = NotificationDispatcher(mail_settings, session)
    fake = _FakeNotificationRepos()
    dispatcher._notification_event_repo = SimpleNamespace(create=fake.create_event)
    dispatcher._user_notification_repo = SimpleNamespace(create=fake.create_note)
    dispatcher._notification_delivery_repo = SimpleNamespace(create=fake.create_delivery)

    recipient = SimpleNamespace(user_id=uuid.uuid4(), email="client@example.com")

    with patch.object(dispatcher, "_deliver_eager", new_callable=AsyncMock):
        await dispatcher.dispatch_booking_cancelled(
            booking_id=uuid.uuid4(),
            master_profile_id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            recipient=recipient,
            email_ctx=BookingEmailContext(
                title="Запись отменена",
                body="body",
                link_url="https://frontend.test/client/visits",
                payload={},
            ),
        )

    assert fake.events[0].type == NotificationEventType.BOOKING_CANCELLED
    assert fake.notes[0].event_type == NotificationEventType.BOOKING_CANCELLED


async def test_cancel_booking_notifies_linked_verified_client() -> None:
    master_id = uuid.uuid4()
    client_id = uuid.uuid4()
    user_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id,
        client_id=client_id,
        service_id=uuid.uuid4(),
        start_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
        end_at=datetime(2026, 5, 20, 11, 0, tzinfo=UTC),
        duration_min=60,
        status=BookingStatus.SCHEDULED,
        blocks_calendar=True,
        cancel_comment=None,
    )
    master = SimpleNamespace(id=master_id, display_name="Master", timezone="UTC")
    service = SimpleNamespace(id=booking.service_id, name="Стрижка")

    class FakeBookingRepo:
        async def get_for_master(self, bid, mid):
            return booking

        flushed = False

        async def flush(self):
            self.flushed = True

    class FakeClientRepo:
        async def get_client(self, cid):
            return SimpleNamespace(id=client_id, user_id=user_id)

    class FakeUserRepo:
        async def get_by_id(self, uid):
            return SimpleNamespace(
                id=uid,
                email="client@example.com",
                email_verified_at=datetime.now(UTC),
            )

    dispatcher = SimpleNamespace(dispatch_booking_cancelled=AsyncMock())
    use_case = CancelBookingUseCase(
        FakeBookingRepo(),
        FakeClientRepo(),
        SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
        FakeUserRepo(),
        dispatcher,
    )

    await use_case(master=master, booking_id=booking.id, comment="  Извините  ")

    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancel_comment == "Извините"
    dispatcher.dispatch_booking_cancelled.assert_awaited_once()


async def test_reschedule_booking_notifies_when_start_changes() -> None:
    master_id = uuid.uuid4()
    client_id = uuid.uuid4()
    user_id = uuid.uuid4()
    old_start = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    new_start = datetime(2026, 5, 21, 14, 0, tzinfo=UTC)
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id,
        client_id=client_id,
        service_id=uuid.uuid4(),
        start_at=old_start,
        end_at=old_start + timedelta(hours=1),
        duration_min=60,
        status=BookingStatus.SCHEDULED,
        blocks_calendar=True,
        price_snapshot=Decimal("50.00"),
        currency_snapshot="BYN",
        reschedule_comment=None,
    )
    master = SimpleNamespace(id=master_id, display_name="Master", timezone="UTC", public_slug=None)
    service = SimpleNamespace(id=booking.service_id, name="Стрижка")

    class FakeBookingRepo:
        async def get_for_master(self, bid, mid):
            return booking

        async def has_conflict(self, *_a, **_k):
            return False

        async def flush(self):
            booking.start_at = new_start
            booking.end_at = new_start + timedelta(hours=1)

    class FakeClientRepo:
        async def get_client(self, cid):
            return SimpleNamespace(id=client_id, user_id=user_id)

    class FakeUserRepo:
        async def get_by_id(self, uid):
            return SimpleNamespace(
                id=uid,
                email="client@example.com",
                email_verified_at=datetime.now(UTC),
            )

    slots_uc = AsyncMock(return_value=[SlotOut(start_at=new_start)])
    dispatcher = SimpleNamespace(dispatch_booking_moved=AsyncMock())
    use_case = RescheduleBookingUseCase(
        FakeBookingRepo(),
        SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
        FakeClientRepo(),
        FakeUserRepo(),
        slots_uc,
        dispatcher,
    )

    await use_case(master=master, booking_id=booking.id, start_at=new_start, comment="Новое время удобно?")

    assert booking.reschedule_comment == "Новое время удобно?"
    dispatcher.dispatch_booking_moved.assert_awaited_once()
