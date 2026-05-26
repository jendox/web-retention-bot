from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models.notifications import ScheduledNotificationPurpose
from app.services.notifications.booking_reminders import BookingReminderRecipient, build_booking_reminders


def _booking(*, start_at: datetime):
    return SimpleNamespace(id=uuid.uuid4(), start_at=start_at)


def _recipient() -> BookingReminderRecipient:
    return BookingReminderRecipient(user_id=uuid.uuid4(), client_id=uuid.uuid4())


def test_build_booking_reminders_creates_24h_and_1h_reminders() -> None:
    now = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    booking = _booking(start_at=now + timedelta(hours=30))
    recipient = _recipient()

    reminders = build_booking_reminders(booking=booking, recipient=recipient, now=now)

    assert [reminder.purpose for reminder in reminders] == [
        ScheduledNotificationPurpose.REMINDER_24H,
        ScheduledNotificationPurpose.REMINDER_1H,
    ]
    assert [reminder.fire_at for reminder in reminders] == [
        datetime(2026, 5, 20, 16, 0, tzinfo=UTC),
        datetime(2026, 5, 21, 15, 0, tzinfo=UTC),
    ]
    assert all(reminder.booking_id == booking.id for reminder in reminders)
    assert all(reminder.recipient_user_id == recipient.user_id for reminder in reminders)
    assert all(reminder.recipient_client_id == recipient.client_id for reminder in reminders)


def test_build_booking_reminders_skips_past_24h_reminder() -> None:
    now = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    booking = _booking(start_at=now + timedelta(hours=2))

    reminders = build_booking_reminders(booking=booking, recipient=_recipient(), now=now)

    assert [reminder.purpose for reminder in reminders] == [ScheduledNotificationPurpose.REMINDER_1H]
    assert reminders[0].fire_at == datetime(2026, 5, 20, 11, 0, tzinfo=UTC)


def test_build_booking_reminders_skips_all_past_reminders() -> None:
    now = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    booking = _booking(start_at=now + timedelta(minutes=30))

    reminders = build_booking_reminders(booking=booking, recipient=_recipient(), now=now)

    assert reminders == []


def test_build_booking_reminders_treats_naive_booking_start_as_utc() -> None:
    now = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    booking = _booking(start_at=datetime(2026, 5, 21, 16, 0))

    reminders = build_booking_reminders(booking=booking, recipient=_recipient(), now=now)

    assert [reminder.fire_at for reminder in reminders] == [
        datetime(2026, 5, 20, 16, 0, tzinfo=UTC),
        datetime(2026, 5, 21, 15, 0, tzinfo=UTC),
    ]
