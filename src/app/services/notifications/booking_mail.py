from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.service import Service
from app.services.notifications.datetime_format import format_booking_start_local
from app.services.notifications.email_send import send_multipart_email
from app.services.notifications.mail_render import (
    BookingCancelledEmailRenderContext,
    BookingMovedEmailRenderContext,
    render_booking_cancelled,
    render_booking_created,
    render_booking_moved,
)

logger = get_logger("app.mail")


class BookingNotificationSkip(Exception):
    """Non-retryable skip (booking gone or no longer relevant)."""


@dataclass(frozen=True)
class _BookingMailContext:
    booking: Booking
    master: MasterProfile
    service: Service
    cabinet_url: str


async def _load_booking_mail_context(
    *,
    settings: Settings,
    session: AsyncSession,
    booking_id: UUID,
) -> _BookingMailContext:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise BookingNotificationSkip("booking_not_found")

    master = await session.get(MasterProfile, booking.master_id)
    service = await session.get(Service, booking.service_id)
    if master is None or service is None:
        raise BookingNotificationSkip("booking_related_entity_missing")

    cabinet_url = f"{settings.security.frontend_public_origin.rstrip('/')}/client"
    return _BookingMailContext(booking=booking, master=master, service=service, cabinet_url=cabinet_url)


async def deliver_booking_created_email(
    *,
    settings: Settings,
    session: AsyncSession,
    booking_id: UUID,
    to_email: str,
) -> None:
    with log_context(use_case="deliver_booking_created_email", booking_id=str(booking_id)):
        ctx = await _load_booking_mail_context(settings=settings, session=session, booking_id=booking_id)
        if ctx.booking.status is not BookingStatus.SCHEDULED:
            raise BookingNotificationSkip(f"booking_status_{ctx.booking.status.value}")

        start_at_local = format_booking_start_local(ctx.booking.start_at, ctx.master.timezone)
        subject, text_body, html_body = render_booking_created(
            recipient_email=to_email,
            master_name=ctx.master.display_name,
            service_name=ctx.service.name,
            start_at_local=start_at_local,
            duration_min=ctx.booking.duration_min,
            cabinet_url=ctx.cabinet_url,
        )

        await send_multipart_email(
            settings=settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            log_sent_event="email.booking_created.sent",
        )


async def deliver_booking_cancelled_email(
    *,
    settings: Settings,
    session: AsyncSession,
    booking_id: UUID,
    to_email: str,
) -> None:
    with log_context(use_case="deliver_booking_cancelled_email", booking_id=str(booking_id)):
        ctx = await _load_booking_mail_context(settings=settings, session=session, booking_id=booking_id)
        if ctx.booking.status is not BookingStatus.CANCELLED:
            raise BookingNotificationSkip(f"booking_status_{ctx.booking.status.value}")

        start_at_local = format_booking_start_local(ctx.booking.start_at, ctx.master.timezone)
        subject, text_body, html_body = render_booking_cancelled(
            BookingCancelledEmailRenderContext(
                recipient_email=to_email,
                master_name=ctx.master.display_name,
                service_name=ctx.service.name,
                start_at_local=start_at_local,
                duration_min=ctx.booking.duration_min,
                cabinet_url=ctx.cabinet_url,
                master_comment=ctx.booking.cancel_comment,
            ),
        )

        await send_multipart_email(
            settings=settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            log_sent_event="email.booking_cancelled.sent",
        )


async def deliver_booking_moved_email(
    *,
    settings: Settings,
    session: AsyncSession,
    booking_id: UUID,
    to_email: str,
    previous_start_at_iso: str,
) -> None:
    with log_context(use_case="deliver_booking_moved_email", booking_id=str(booking_id)):
        ctx = await _load_booking_mail_context(settings=settings, session=session, booking_id=booking_id)
        if ctx.booking.status is not BookingStatus.SCHEDULED:
            raise BookingNotificationSkip(f"booking_status_{ctx.booking.status.value}")

        if not previous_start_at_iso:
            raise BookingNotificationSkip("missing_previous_start_at")

        start_at_local = format_booking_start_local(ctx.booking.start_at, ctx.master.timezone)
        previous_start_at = datetime.fromisoformat(previous_start_at_iso)
        previous_start_at_local = format_booking_start_local(previous_start_at, ctx.master.timezone)

        subject, text_body, html_body = render_booking_moved(
            BookingMovedEmailRenderContext(
                recipient_email=to_email,
                master_name=ctx.master.display_name,
                service_name=ctx.service.name,
                previous_start_at_local=previous_start_at_local,
                start_at_local=start_at_local,
                duration_min=ctx.booking.duration_min,
                cabinet_url=ctx.cabinet_url,
                master_comment=ctx.booking.reschedule_comment,
            ),
        )

        await send_multipart_email(
            settings=settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            log_sent_event="email.booking_moved.sent",
        )
