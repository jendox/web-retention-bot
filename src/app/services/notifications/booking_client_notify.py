from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.clients import ClientRepository
from app.repositories.users import UserRepository
from app.services.notifications.dispatcher import BookingEmailContext, NotificationDispatcher
from app.services.notifications.mail_render import (
    BOOKING_EMAIL_AUDIENCE_CLIENT,
    booking_cancelled_in_app_copy,
    booking_moved_in_app_copy,
)
from app.services.notifications.recipients import resolve_booking_client_recipient

logger = get_logger("app.notifications.booking_client")


@dataclass(frozen=True)
class BookingClientNotifyContext:
    dispatcher: NotificationDispatcher
    user_repo: UserRepository
    client_repo: ClientRepository
    booking: Booking
    master: MasterProfile
    service: Service


async def _resolve_recipient(ctx: BookingClientNotifyContext):
    client = await ctx.client_repo.get_client(ctx.booking.client_id)
    if client is None or client.user_id is None:
        return None, None

    user = await ctx.user_repo.get_by_id(client.user_id)
    recipient = resolve_booking_client_recipient(client, user)
    if recipient is None:
        return None, None
    return client, recipient


async def notify_client_booking_cancelled(ctx: BookingClientNotifyContext) -> None:
    client, recipient = await _resolve_recipient(ctx)
    if recipient is None or client is None:
        return

    title, body, link_url = booking_cancelled_in_app_copy(
        master_display_name=ctx.master.display_name,
        service_name=ctx.service.name,
        start_at=ctx.booking.start_at,
        recipient_timezone=client.timezone,
        master_comment=ctx.booking.cancel_comment,
    )

    with log_context(booking_id=str(ctx.booking.id), recipient_user_id=str(recipient.user_id)):
        await ctx.dispatcher.dispatch_booking_cancelled(
            booking_id=ctx.booking.id,
            master_profile_id=ctx.master.id,
            client_id=client.id,
            recipient=recipient,
            email_ctx=BookingEmailContext(
                title=title,
                body=body,
                link_url=link_url,
                payload={"audience": BOOKING_EMAIL_AUDIENCE_CLIENT},
            ),
        )
        logger.info("notified")


async def notify_client_booking_moved(ctx: BookingClientNotifyContext, *, previous_start_at: datetime) -> None:
    client, recipient = await _resolve_recipient(ctx)
    if recipient is None or client is None:
        return

    previous_iso = previous_start_at.isoformat()
    title, body, link_url = booking_moved_in_app_copy(
        master_display_name=ctx.master.display_name,
        service_name=ctx.service.name,
        previous_start_at=previous_start_at,
        start_at=ctx.booking.start_at,
        recipient_timezone=client.timezone,
        master_comment=ctx.booking.reschedule_comment,
    )

    with log_context(booking_id=str(ctx.booking.id), recipient_user_id=str(recipient.user_id)):
        await ctx.dispatcher.dispatch_booking_moved(
            booking_id=ctx.booking.id,
            master_profile_id=ctx.master.id,
            client_id=client.id,
            recipient=recipient,
            email_ctx=BookingEmailContext(
                title=title,
                body=body,
                link_url=link_url,
                payload={
                    "audience": BOOKING_EMAIL_AUDIENCE_CLIENT,
                    "previous_start_at": previous_iso,
                    "new_start_at": ctx.booking.start_at.isoformat(),
                },
            ),
            previous_start_at_iso=previous_iso,
        )
        logger.info("notified")
