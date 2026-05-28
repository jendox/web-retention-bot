from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from app.models import Booking, Client, MasterProfile, ScheduledNotification, Service
from app.models.booking import BookingStatus
from app.repositories.bookings import BookingRepository
from app.repositories.clients import ClientRepository
from app.repositories.masters import MasterRepository
from app.repositories.notifications import ScheduledNotificationRepository
from app.repositories.services import ServiceRepository
from app.repositories.users import UserRepository
from app.services.notifications.mail_render import BOOKING_EMAIL_AUDIENCE_CLIENT, booking_reminder_in_app_copy
from app.services.notifications.recipients import resolve_booking_client_recipient

type BookingReminderProcessStatus = Literal["sent", "skipped"]


@dataclass(frozen=True)
class BookingReminderProcessorDeps:
    scheduled_notification_repo: ScheduledNotificationRepository
    booking_repo: BookingRepository
    client_repo: ClientRepository
    user_repo: UserRepository
    master_repo: MasterRepository
    service_repo: ServiceRepository
    dispatcher: Any


@dataclass(frozen=True)
class BookingReminderProcessResult:
    status: BookingReminderProcessStatus
    user_notification_id: UUID | None = None
    reason: str | None = None


@dataclass(frozen=True)
class _ReminderRecipientContext:
    client: Client
    recipient: Any


@dataclass(frozen=True)
class _ReminderEntityContext:
    master: MasterProfile
    service: Service


def _skip(reason: str) -> BookingReminderProcessResult:
    return BookingReminderProcessResult(status="skipped", reason=reason)


async def _resolve_booking(
    scheduled: ScheduledNotification,
    deps: BookingReminderProcessorDeps,
) -> Booking | BookingReminderProcessResult:
    booking = await deps.booking_repo.get(scheduled.booking_id)
    if booking is None:
        return _skip("booking_not_found")
    if booking.status is not BookingStatus.SCHEDULED:
        return _skip(f"booking_status_{booking.status.value}")
    return booking


async def _resolve_recipient_context(
    booking: Booking,
    deps: BookingReminderProcessorDeps,
) -> _ReminderRecipientContext | BookingReminderProcessResult:
    client = await deps.client_repo.get_client(booking.client_id)
    if client is None or client.user_id is None:
        return _skip("client_not_linked")

    user = await deps.user_repo.get_by_id(client.user_id)
    recipient = resolve_booking_client_recipient(client, user)
    if recipient is None:
        return _skip("recipient_not_available")

    return _ReminderRecipientContext(client=client, recipient=recipient)


async def _resolve_entity_context(
    booking: Booking,
    deps: BookingReminderProcessorDeps,
) -> _ReminderEntityContext | BookingReminderProcessResult:
    master = await deps.master_repo.get_by_master_id(booking.master_id)
    if master is None:
        return _skip("master_not_found")

    service = await deps.service_repo.get_for_master(booking.service_id, booking.master_id)
    if service is None:
        return _skip("service_not_found")

    return _ReminderEntityContext(master=master, service=service)


async def process_booking_reminder(
    scheduled: ScheduledNotification,
    deps: BookingReminderProcessorDeps,
) -> BookingReminderProcessResult:
    booking = await _resolve_booking(scheduled, deps)
    if isinstance(booking, BookingReminderProcessResult):
        return booking

    recipient_context = await _resolve_recipient_context(booking, deps)
    if isinstance(recipient_context, BookingReminderProcessResult):
        return recipient_context

    entity_context = await _resolve_entity_context(booking, deps)
    if isinstance(entity_context, BookingReminderProcessResult):
        return entity_context

    from app.services.notifications.dispatcher import (  # noqa: PLC0415
        BookingEmailContext,
        BookingNotificationDispatchContext,
    )

    title, body, link_url = booking_reminder_in_app_copy(
        master_display_name=entity_context.master.display_name,
        service_name=entity_context.service.name,
        start_at=booking.start_at,
        recipient_timezone=recipient_context.client.timezone,
    )

    dispatch_result = await deps.dispatcher.dispatch_booking_reminder(
        ctx=BookingNotificationDispatchContext(
            booking_id=booking.id,
            master_profile_id=entity_context.master.id,
            client_id=recipient_context.client.id,
            recipient=recipient_context.recipient,
            email_ctx=BookingEmailContext(
                title=title,
                body=body,
                link_url=link_url,
                payload={"audience": BOOKING_EMAIL_AUDIENCE_CLIENT},
            ),
        ),
        purpose=scheduled.purpose,
        fire_at=scheduled.fire_at,
    )

    return BookingReminderProcessResult(
        status="sent",
        user_notification_id=dispatch_result.user_notification.id,
    )
