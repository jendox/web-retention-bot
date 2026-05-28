from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.users import UserRepository
from app.services.notifications.dispatcher import (
    BookingEmailContext,
    BookingNotificationDispatchContext,
    NotificationDispatcher,
)
from app.services.notifications.mail_render import (
    BOOKING_EMAIL_AUDIENCE_MASTER,
    booking_cancelled_master_in_app_copy,
    booking_created_master_in_app_copy,
    booking_moved_master_in_app_copy,
)
from app.services.notifications.recipients import resolve_booking_master_recipient

logger = get_logger("app.notifications.booking_master")


@dataclass(frozen=True)
class BookingMasterNotifyContext:
    dispatcher: NotificationDispatcher
    user_repo: UserRepository
    booking: Booking
    master: MasterProfile
    service: Service
    client_display_name: str


async def _resolve_recipient(ctx: BookingMasterNotifyContext):
    user = await ctx.user_repo.get_by_id(ctx.master.user_id)
    recipient = resolve_booking_master_recipient(ctx.master, user)
    if recipient is None:
        return None
    return recipient


async def notify_master_booking_created(ctx: BookingMasterNotifyContext) -> None:
    recipient = await _resolve_recipient(ctx)
    if recipient is None:
        return

    title, body, link_url = booking_created_master_in_app_copy(
        client_display_name=ctx.client_display_name,
        service_name=ctx.service.name,
        start_at=ctx.booking.start_at,
        master_timezone=ctx.master.timezone,
    )

    with log_context(booking_id=str(ctx.booking.id), recipient_user_id=str(recipient.user_id)):
        await ctx.dispatcher.dispatch_booking_created(
            ctx=BookingNotificationDispatchContext(
                booking_id=ctx.booking.id,
                master_profile_id=ctx.master.id,
                client_id=ctx.booking.client_id,
                recipient=recipient,
                email_ctx=BookingEmailContext(
                    title=title,
                    body=body,
                    link_url=link_url,
                    payload={
                        "audience": BOOKING_EMAIL_AUDIENCE_MASTER,
                        "client_display_name": ctx.client_display_name,
                    },
                ),
            ),
        )
        logger.info("notified")


async def notify_master_booking_cancelled(ctx: BookingMasterNotifyContext) -> None:
    recipient = await _resolve_recipient(ctx)
    if recipient is None:
        return

    title, body, link_url = booking_cancelled_master_in_app_copy(
        client_display_name=ctx.client_display_name,
        service_name=ctx.service.name,
        start_at=ctx.booking.start_at,
        master_timezone=ctx.master.timezone,
        client_comment=ctx.booking.cancel_comment,
    )

    with log_context(booking_id=str(ctx.booking.id), recipient_user_id=str(recipient.user_id)):
        await ctx.dispatcher.dispatch_booking_cancelled(
            ctx=BookingNotificationDispatchContext(
                booking_id=ctx.booking.id,
                master_profile_id=ctx.master.id,
                client_id=ctx.booking.client_id,
                recipient=recipient,
                email_ctx=BookingEmailContext(
                    title=title,
                    body=body,
                    link_url=link_url,
                    payload={
                        "audience": BOOKING_EMAIL_AUDIENCE_MASTER,
                        "client_display_name": ctx.client_display_name,
                    },
                ),
            ),
        )
        logger.info("notified")


async def notify_master_booking_moved(ctx: BookingMasterNotifyContext, *, previous_start_at: datetime) -> None:
    recipient = await _resolve_recipient(ctx)
    if recipient is None:
        return

    previous_iso = previous_start_at.isoformat()
    title, body, link_url = booking_moved_master_in_app_copy(
        client_display_name=ctx.client_display_name,
        service_name=ctx.service.name,
        previous_start_at=previous_start_at,
        start_at=ctx.booking.start_at,
        master_timezone=ctx.master.timezone,
        client_comment=ctx.booking.reschedule_comment,
    )

    with log_context(booking_id=str(ctx.booking.id), recipient_user_id=str(recipient.user_id)):
        await ctx.dispatcher.dispatch_booking_moved(
            ctx=BookingNotificationDispatchContext(
                booking_id=ctx.booking.id,
                master_profile_id=ctx.master.id,
                client_id=ctx.booking.client_id,
                recipient=recipient,
                email_ctx=BookingEmailContext(
                    title=title,
                    body=body,
                    link_url=link_url,
                    payload={
                        "audience": BOOKING_EMAIL_AUDIENCE_MASTER,
                        "client_display_name": ctx.client_display_name,
                        "previous_start_at": previous_iso,
                        "new_start_at": ctx.booking.start_at.isoformat(),
                    },
                ),
            ),
            previous_start_at_iso=previous_iso,
        )
        logger.info("notified")
