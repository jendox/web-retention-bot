from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.booking import BookingStatus
from app.models.notifications import ScheduledNotificationPurpose
from app.services.notifications import tasks as notification_tasks
from app.services.notifications.booking_reminder_processor import (
    BookingReminderProcessorDeps,
    process_booking_reminder,
)


def _scheduled(**overrides):
    data = {
        "id": uuid.uuid4(),
        "booking_id": uuid.uuid4(),
        "purpose": ScheduledNotificationPurpose.REMINDER_1H,
        "fire_at": datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _booking(**overrides):
    data = {
        "id": uuid.uuid4(),
        "master_id": uuid.uuid4(),
        "client_id": uuid.uuid4(),
        "service_id": uuid.uuid4(),
        "status": BookingStatus.SCHEDULED,
        "start_at": datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _deps(
    *,
    booking=None,
    client=None,
    user=None,
    master=None,
    service=None,
    dispatcher=None,
):
    return BookingReminderProcessorDeps(
        scheduled_notification_repo=SimpleNamespace(),
        booking_repo=SimpleNamespace(get=AsyncMock(return_value=booking)),
        client_repo=SimpleNamespace(get_client=AsyncMock(return_value=client)),
        user_repo=SimpleNamespace(get_by_id=AsyncMock(return_value=user)),
        master_repo=SimpleNamespace(get_by_master_id=AsyncMock(return_value=master)),
        service_repo=SimpleNamespace(get_for_master=AsyncMock(return_value=service)),
        dispatcher=dispatcher or SimpleNamespace(dispatch_booking_reminder=AsyncMock()),
    )


async def test_process_booking_reminder_dispatches_notification() -> None:
    user_id = uuid.uuid4()
    user_notification_id = uuid.uuid4()
    booking = _booking()
    client = SimpleNamespace(
        id=booking.client_id,
        user_id=user_id,
        timezone="Europe/Warsaw",
    )
    user = SimpleNamespace(
        id=user_id,
        email="client@example.com",
        email_verified_at=datetime.now(UTC),
    )
    master = SimpleNamespace(id=booking.master_id, display_name="Master")
    service = SimpleNamespace(id=booking.service_id, name="Стрижка")
    dispatcher = SimpleNamespace(
        dispatch_booking_reminder=AsyncMock(
            return_value=SimpleNamespace(user_notification=SimpleNamespace(id=user_notification_id)),
        ),
    )
    scheduled = _scheduled(booking_id=booking.id)

    result = await process_booking_reminder(
        scheduled,
        _deps(
            booking=booking,
            client=client,
            user=user,
            master=master,
            service=service,
            dispatcher=dispatcher,
        ),
    )

    assert result.status == "sent"
    assert result.user_notification_id == user_notification_id
    dispatcher.dispatch_booking_reminder.assert_awaited_once()
    kwargs = dispatcher.dispatch_booking_reminder.await_args.kwargs
    assert kwargs["purpose"] == scheduled.purpose
    assert kwargs["fire_at"] == scheduled.fire_at
    assert kwargs["ctx"].booking_id == booking.id
    assert kwargs["ctx"].recipient.email == "client@example.com"
    assert "12:00" in kwargs["ctx"].email_ctx.body


async def test_process_booking_reminder_skips_cancelled_booking() -> None:
    booking = _booking(status=BookingStatus.CANCELLED)
    dispatcher = SimpleNamespace(dispatch_booking_reminder=AsyncMock())

    result = await process_booking_reminder(
        _scheduled(booking_id=booking.id),
        _deps(booking=booking, dispatcher=dispatcher),
    )

    assert result.status == "skipped"
    assert result.reason == "booking_status_CANCELLED"
    dispatcher.dispatch_booking_reminder.assert_not_called()


async def test_process_booking_reminder_skips_unlinked_client() -> None:
    booking = _booking()
    client = SimpleNamespace(id=booking.client_id, user_id=None, timezone="Europe/Warsaw")
    dispatcher = SimpleNamespace(dispatch_booking_reminder=AsyncMock())

    result = await process_booking_reminder(
        _scheduled(booking_id=booking.id),
        _deps(booking=booking, client=client, dispatcher=dispatcher),
    )

    assert result.status == "skipped"
    assert result.reason == "client_not_linked"
    dispatcher.dispatch_booking_reminder.assert_not_called()


class _WorkerSession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def test_process_due_booking_reminders_marks_processed_reminders_done() -> None:
    reminder = _scheduled()
    fake_repo = SimpleNamespace(
        claim_due=AsyncMock(return_value=[reminder]),
        mark_done=AsyncMock(),
        release_claimed=AsyncMock(),
    )
    user_notification_id = uuid.uuid4()

    with (
        patch.object(
            notification_tasks,
            "get_settings",
            return_value=SimpleNamespace(notifications=SimpleNamespace(reminder_batch_size=10)),
        ),
        patch.object(notification_tasks, "worker_db_session", return_value=_WorkerSession()),
        patch.object(notification_tasks, "ScheduledNotificationRepository", return_value=fake_repo),
        patch.object(notification_tasks, "process_booking_reminder", new_callable=AsyncMock) as mock_process,
        patch.object(notification_tasks, "BookingRepository"),
        patch.object(notification_tasks, "ClientRepository"),
        patch.object(notification_tasks, "UserRepository"),
        patch.object(notification_tasks, "MasterRepository"),
        patch.object(notification_tasks, "ServiceRepository"),
    ):
        mock_process.return_value = SimpleNamespace(user_notification_id=user_notification_id)

        processed = await notification_tasks._process_due_booking_reminders_async()

    assert processed == 1
    fake_repo.claim_due.assert_awaited_once()
    fake_repo.mark_done.assert_awaited_once_with(reminder.id, user_notification_id=user_notification_id)
    fake_repo.release_claimed.assert_not_awaited()


async def test_process_due_booking_reminders_releases_claimed_on_processing_error() -> None:
    reminder = _scheduled()
    fake_repo = SimpleNamespace(
        claim_due=AsyncMock(return_value=[reminder]),
        mark_done=AsyncMock(),
        release_claimed=AsyncMock(),
    )

    with (
        patch.object(
            notification_tasks,
            "get_settings",
            return_value=SimpleNamespace(notifications=SimpleNamespace(reminder_batch_size=10)),
        ),
        patch.object(notification_tasks, "worker_db_session", return_value=_WorkerSession()),
        patch.object(notification_tasks, "ScheduledNotificationRepository", return_value=fake_repo),
        patch.object(
            notification_tasks,
            "process_booking_reminder",
            new_callable=AsyncMock,
            side_effect=RuntimeError("temporary failure"),
        ),
        patch.object(notification_tasks, "BookingRepository"),
        patch.object(notification_tasks, "ClientRepository"),
        patch.object(notification_tasks, "UserRepository"),
        patch.object(notification_tasks, "MasterRepository"),
        patch.object(notification_tasks, "ServiceRepository"),
    ):
        processed = await notification_tasks._process_due_booking_reminders_async()

    assert processed == 0
    fake_repo.release_claimed.assert_awaited_once_with(reminder.id)
    fake_repo.mark_done.assert_not_awaited()
