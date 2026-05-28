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
from app.models.notifications.enums import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationEventType,
    ScheduledNotificationPurpose,
)
from app.schemas.availability import SlotOut
from app.schemas.booking import BookingCreate, BookingOut
from app.services.notifications import tasks as notification_tasks
from app.services.notifications.booking_mail import (
    BookingEmailDeliveryOptions,
    BookingNotificationSkip,
    deliver_booking_created_email,
    deliver_booking_reminder_email,
)
from app.services.notifications.datetime_format import format_booking_start_local
from app.services.notifications.dispatcher import (
    BookingEmailContext,
    BookingNotificationDispatchContext,
    NotificationDispatcher,
)
from app.services.notifications.mail_render import (
    BookingCancelledEmailRenderContext,
    BookingMovedEmailRenderContext,
    BookingReminderEmailRenderContext,
    append_master_comment_to_body,
    booking_cancelled_in_app_copy,
    booking_created_in_app_copy,
    booking_moved_in_app_copy,
    booking_reminder_in_app_copy,
    render_booking_cancelled,
    render_booking_created,
    render_booking_moved,
    render_booking_reminder,
)
from app.services.notifications.recipients import resolve_booking_client_recipient, resolve_booking_master_recipient
from app.use_cases.booking import CancelMasterBookingUseCase, CreateMasterBookingUseCase, RescheduleMasterBookingUseCase
from app.use_cases.booking.master.schemas import MasterBookingUseCaseReposDeps


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
        recipient_timezone="Europe/Warsaw",
    )
    assert title == "Новая запись"
    assert "Master" in body
    assert "Услуга" in body
    assert "12:00" in body
    assert link_url is not None
    assert link_url.endswith("/client")


def test_render_booking_reminder_templates() -> None:
    subject, text_body, html_body = render_booking_reminder(
        BookingReminderEmailRenderContext(
            recipient_email="c@example.com",
            master_name="Studio",
            service_name="Стрижка",
            start_at_local="среда, 20 мая 2026 г., 10:00",
            duration_min=45,
            cabinet_url="https://frontend.test/client/visits",
        ),
    )

    assert "Напоминание" in subject
    assert "Studio" in text_body
    assert "Стрижка" in html_body
    assert "https://frontend.test/client/visits" in html_body


def test_booking_reminder_in_app_copy() -> None:
    start_at = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    title, body, link_url = booking_reminder_in_app_copy(
        master_display_name="Master",
        service_name="Услуга",
        start_at=start_at,
        recipient_timezone="Europe/Warsaw",
    )

    assert title == "Напоминание о записи"
    assert "Master" in body
    assert "Услуга" in body
    assert "12:00" in body
    assert link_url is not None
    assert link_url.endswith("/client/visits")


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


class _FakeScheduledNotificationRepository:
    def __init__(self) -> None:
        self.scheduled: list = []
        self.cancelled_booking_ids: list = []

    async def upsert(self, payload):
        self.scheduled.append(payload)
        return payload

    async def cancel_pending_for_booking(self, booking_id):
        self.cancelled_booking_ids.append(booking_id)
        return 1


async def test_dispatch_booking_created_persists_event_note_and_delivery(mail_settings: Settings) -> None:
    session = AsyncMock()
    dispatcher = NotificationDispatcher(mail_settings, session)
    fake = _FakeNotificationRepos()
    dispatcher._notification_event_repo = SimpleNamespace(create=fake.create_event)
    dispatcher._user_notification_repo = SimpleNamespace(create=fake.create_note)
    dispatcher._notification_delivery_repo = SimpleNamespace(create=fake.create_delivery)

    booking_id = uuid.uuid4()
    recipient = SimpleNamespace(user_id=uuid.uuid4(), email="client@example.com")

    with (
        patch(
            "app.services.notifications.dispatcher.delivery_channels_for_user",
            AsyncMock(return_value=[DeliveryChannel.EMAIL]),
        ),
        patch.object(dispatcher, "_deliver_delivery", new_callable=AsyncMock) as mock_deliver,
    ):
        result = await dispatcher.dispatch_booking_created(
            ctx=BookingNotificationDispatchContext(
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
            ),
        )

    mock_deliver.assert_awaited_once()
    assert result.event == fake.events[0]
    assert result.user_notification == fake.notes[0]
    assert result.deliveries == fake.deliveries
    assert len(fake.events) == 1
    assert fake.events[0].type == NotificationEventType.BOOKING_CREATED
    assert len(fake.notes) == 1
    assert fake.notes[0].event_type == NotificationEventType.BOOKING_CREATED
    assert len(fake.deliveries) == 1
    assert fake.deliveries[0].channel == DeliveryChannel.EMAIL
    assert fake.deliveries[0].status == DeliveryStatus.SENT


async def test_dispatch_booking_reminder_persists_event_note_and_delivery(mail_settings: Settings) -> None:
    session = AsyncMock()
    dispatcher = NotificationDispatcher(mail_settings, session)
    fake = _FakeNotificationRepos()
    dispatcher._notification_event_repo = SimpleNamespace(create=fake.create_event)
    dispatcher._user_notification_repo = SimpleNamespace(create=fake.create_note)
    dispatcher._notification_delivery_repo = SimpleNamespace(create=fake.create_delivery)

    booking_id = uuid.uuid4()
    fire_at = datetime(2026, 5, 20, 9, 0, tzinfo=UTC)
    recipient = SimpleNamespace(user_id=uuid.uuid4(), email="client@example.com")

    with (
        patch(
            "app.services.notifications.dispatcher.delivery_channels_for_user",
            AsyncMock(return_value=[DeliveryChannel.EMAIL, DeliveryChannel.TELEGRAM]),
        ) as mock_channels,
        patch.object(dispatcher, "_deliver_delivery", new_callable=AsyncMock) as mock_deliver,
    ):
        result = await dispatcher.dispatch_booking_reminder(
            ctx=BookingNotificationDispatchContext(
                booking_id=booking_id,
                master_profile_id=uuid.uuid4(),
                client_id=uuid.uuid4(),
                recipient=recipient,
                email_ctx=BookingEmailContext(
                    title="Напоминание о записи",
                    body="body",
                    link_url="https://frontend.test/client/visits",
                    payload={"audience": "client"},
                ),
            ),
            purpose=ScheduledNotificationPurpose.REMINDER_1H,
            fire_at=fire_at,
        )

    mock_channels.assert_awaited_once_with(
        dispatcher._preference_repo,
        user_id=recipient.user_id,
        event_type=NotificationEventType.REMINDER_BEFORE_VISIT,
    )
    assert mock_deliver.await_count == 2
    assert result.user_notification == fake.notes[0]
    assert result.deliveries == fake.deliveries
    assert fake.events[0].type == NotificationEventType.REMINDER_BEFORE_VISIT
    assert fake.notes[0].event_type == NotificationEventType.REMINDER_BEFORE_VISIT
    assert fake.notes[0].dedup_key == (
        f"booking_reminder:booking:{booking_id}:user:{recipient.user_id}:"
        f"purpose:{ScheduledNotificationPurpose.REMINDER_1H.value}:{fire_at.isoformat()}"
    )
    assert fake.notes[0].payload["reminder_purpose"] == ScheduledNotificationPurpose.REMINDER_1H.value
    assert [delivery.channel for delivery in fake.deliveries] == [DeliveryChannel.EMAIL, DeliveryChannel.TELEGRAM]


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


async def test_deliver_booking_reminder_email_skips_non_scheduled() -> None:
    booking_id = uuid.uuid4()
    master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=booking_id,
        master_id=master_id,
        service_id=service_id,
        client_id=uuid.uuid4(),
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
        await deliver_booking_reminder_email(
            settings=settings,
            session=session,
            booking_id=booking_id,
            to_email="c@example.com",
            options=BookingEmailDeliveryOptions(),
        )


async def test_process_booking_reminder_email_marks_delivery_sent(mail_settings: Settings) -> None:
    booking_id = uuid.uuid4()
    delivery = SimpleNamespace(
        status=DeliveryStatus.PENDING,
        error_message=None,
        sent_at=None,
        user_notification=SimpleNamespace(
            payload={
                "booking_id": str(booking_id),
                "to_email": "client@example.com",
                "audience": "client",
            },
        ),
    )
    session = object()

    class WorkerSession:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with (
        patch.object(notification_tasks, "worker_db_session", return_value=WorkerSession()),
        patch.object(notification_tasks, "deliver_booking_reminder_email", new_callable=AsyncMock) as mock_deliver,
    ):
        await notification_tasks._process_booking_reminder_email(mail_settings, delivery)

    mock_deliver.assert_awaited_once()
    assert mock_deliver.await_args.kwargs["session"] is session
    assert mock_deliver.await_args.kwargs["booking_id"] == booking_id
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.sent_at is not None


async def test_process_booking_reminder_email_fails_without_email(mail_settings: Settings) -> None:
    delivery = SimpleNamespace(
        status=DeliveryStatus.PENDING,
        error_message=None,
        user_notification=SimpleNamespace(payload={"booking_id": str(uuid.uuid4())}),
    )

    await notification_tasks._process_booking_reminder_email(mail_settings, delivery)

    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.error_message == "missing to_email"


async def test_deliver_booking_created_email_uses_client_timezone(mail_settings: Settings) -> None:
    booking_id = uuid.uuid4()
    master_id = uuid.uuid4()
    service_id = uuid.uuid4()
    client_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=booking_id,
        master_id=master_id,
        client_id=client_id,
        service_id=service_id,
        status=BookingStatus.SCHEDULED,
        start_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
        duration_min=30,
    )
    master = SimpleNamespace(id=master_id, display_name="Master", timezone="UTC")
    service = SimpleNamespace(id=service_id, name="Стрижка")
    client = SimpleNamespace(id=client_id, timezone="Europe/Warsaw")
    session = AsyncMock()

    async def get_entity(model, entity_id):
        if model.__name__ == "Booking":
            return booking
        if model.__name__ == "MasterProfile":
            return master
        if model.__name__ == "Service":
            return service
        if model.__name__ == "Client":
            return client
        return None

    session.get = get_entity

    with patch("app.services.notifications.booking_mail.send_multipart_email", AsyncMock()) as send:
        await deliver_booking_created_email(
            settings=mail_settings,
            session=session,
            booking_id=booking_id,
            to_email="c@example.com",
        )

    send.assert_awaited_once()
    kwargs = send.await_args.kwargs
    assert "12:00" in kwargs["text_body"]


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
            return SimpleNamespace(id=requested_client_id, user_id=user_id, timezone="Europe/Warsaw")

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

    use_case = CreateMasterBookingUseCase(
        MasterBookingUseCaseReposDeps(
            user_repo=FakeUserRepository(),
            client_repo=FakeClientRepository(),
            service_repo=FakeServiceRepository(),
            booking_repo=FakeBookingRepository(),
            scheduled_notifications_repo=_FakeScheduledNotificationRepository(),
        ),
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
    dispatch_ctx = kwargs["ctx"]
    assert dispatch_ctx.client_id == client_id
    assert dispatch_ctx.recipient.email == "client@example.com"
    assert "12:00" in dispatch_ctx.email_ctx.body


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

    use_case = CreateMasterBookingUseCase(
        MasterBookingUseCaseReposDeps(
            user_repo=FakeUserRepository(),
            client_repo=FakeClientRepository(),
            service_repo=FakeServiceRepository(),
            booking_repo=FakeBookingRepository(),
            scheduled_notifications_repo=_FakeScheduledNotificationRepository(),
        ),
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
        recipient_timezone="Europe/Warsaw",
        master_comment="Занят другой клиент",
    )
    assert title == "Запись отменена"
    assert "отменена" in body
    assert "12:00" in body
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
        recipient_timezone="Europe/Warsaw",
    )
    assert title == "Запись перенесена"
    assert "→" in body
    assert "12:00" in body
    assert "16:00" in body
    assert link_url is not None


async def test_dispatch_booking_cancelled_persists_event(mail_settings: Settings) -> None:
    session = AsyncMock()
    dispatcher = NotificationDispatcher(mail_settings, session)
    fake = _FakeNotificationRepos()
    dispatcher._notification_event_repo = SimpleNamespace(create=fake.create_event)
    dispatcher._user_notification_repo = SimpleNamespace(create=fake.create_note)
    dispatcher._notification_delivery_repo = SimpleNamespace(create=fake.create_delivery)

    recipient = SimpleNamespace(user_id=uuid.uuid4(), email="client@example.com")

    with (
        patch(
            "app.services.notifications.dispatcher.delivery_channels_for_user",
            AsyncMock(return_value=[DeliveryChannel.EMAIL]),
        ),
        patch.object(dispatcher, "_deliver_delivery", new_callable=AsyncMock),
    ):
        await dispatcher.dispatch_booking_cancelled(
            ctx=BookingNotificationDispatchContext(
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
            return SimpleNamespace(id=client_id, user_id=user_id, timezone="Europe/Warsaw")

    class FakeUserRepo:
        async def get_by_id(self, uid):
            return SimpleNamespace(
                id=uid,
                email="client@example.com",
                email_verified_at=datetime.now(UTC),
            )

    dispatcher = SimpleNamespace(dispatch_booking_cancelled=AsyncMock())
    use_case = CancelMasterBookingUseCase(
        MasterBookingUseCaseReposDeps(
            user_repo=FakeUserRepo(),
            client_repo=FakeClientRepo(),
            service_repo=SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
            booking_repo=FakeBookingRepo(),
            scheduled_notifications_repo=_FakeScheduledNotificationRepository(),
        ),
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
            return SimpleNamespace(id=client_id, user_id=user_id, timezone="Europe/Warsaw")

    class FakeUserRepo:
        async def get_by_id(self, uid):
            return SimpleNamespace(
                id=uid,
                email="client@example.com",
                email_verified_at=datetime.now(UTC),
            )

    slots_uc = AsyncMock(return_value=[SlotOut(start_at=new_start)])
    dispatcher = SimpleNamespace(dispatch_booking_moved=AsyncMock())
    use_case = RescheduleMasterBookingUseCase(
        MasterBookingUseCaseReposDeps(
            user_repo=FakeUserRepo(),
            client_repo=FakeClientRepo(),
            service_repo=SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
            booking_repo=FakeBookingRepo(),
            scheduled_notifications_repo=_FakeScheduledNotificationRepository(),
        ),
        slots_uc,
        dispatcher,
    )

    await use_case(master=master, booking_id=booking.id, start_at=new_start, comment="Новое время удобно?")

    assert booking.reschedule_comment == "Новое время удобно?"
    dispatcher.dispatch_booking_moved.assert_awaited_once()
