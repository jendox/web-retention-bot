from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core import datetime_utils
from app.models import Booking, ScheduledNotification
from app.models.notifications import ScheduledNotificationPurpose
from app.repositories.clients import ClientRepository
from app.repositories.notifications import ScheduledNotificationCreate, ScheduledNotificationRepository

REMINDER_OFFSETS: tuple[tuple[ScheduledNotificationPurpose, timedelta], ...] = (
    (ScheduledNotificationPurpose.REMINDER_24H, timedelta(hours=24)),
    (ScheduledNotificationPurpose.REMINDER_1H, timedelta(hours=1)),
)


@dataclass(frozen=True)
class BookingReminderRecipient:
    user_id: UUID
    client_id: UUID


async def _resolve_reminder_recipient(
    *,
    client_repo: ClientRepository,
    booking: Booking,
) -> BookingReminderRecipient | None:
    if booking.client_id is None:
        return None
    client = await client_repo.get_client(booking.client_id)
    if client is None or booking.client_id != client.id or client.user_id is None:
        return None
    return BookingReminderRecipient(user_id=client.user_id, client_id=client.id)


def build_booking_reminders(
    *,
    booking: Booking,
    recipient: BookingReminderRecipient,
    now: datetime | None = None,
) -> list[ScheduledNotificationCreate]:
    now_utc = datetime_utils.local_to_utc(now or datetime.now(UTC))
    start_at_utc = datetime_utils.local_to_utc(booking.start_at)

    reminders: list[ScheduledNotificationCreate] = []
    for purpose, offset in REMINDER_OFFSETS:
        fire_at = start_at_utc - offset
        if fire_at <= now_utc:
            continue

        reminders.append(
            ScheduledNotificationCreate(
                booking_id=booking.id,
                purpose=purpose,
                fire_at=fire_at,
                recipient_user_id=recipient.user_id,
                recipient_client_id=recipient.client_id,
            ),
        )

    return reminders


async def schedule_booking_reminders(
    *,
    repo: ScheduledNotificationRepository,
    booking: Booking,
    recipient: BookingReminderRecipient,
    now: datetime | None = None,
) -> list[ScheduledNotification]:
    reminders = build_booking_reminders(booking=booking, recipient=recipient, now=now)
    return [await repo.upsert(reminder) for reminder in reminders]


async def cancel_booking_reminders(
    *,
    repo: ScheduledNotificationRepository,
    booking_id: UUID,
) -> int:
    return await repo.cancel_pending_for_booking(booking_id)


async def reschedule_booking_reminders(
    *,
    client_repo: ClientRepository,
    scheduled_notification_repo: ScheduledNotificationRepository,
    booking: Booking,
) -> str | None:
    await cancel_booking_reminders(
        repo=scheduled_notification_repo,
        booking_id=booking.id,
    )

    recipient = await _resolve_reminder_recipient(client_repo=client_repo, booking=booking)
    if recipient is None:
        return "cannot_resolve_booking_recipient"

    await schedule_booking_reminders(
        repo=scheduled_notification_repo,
        booking=booking,
        recipient=recipient,
    )
    return None
