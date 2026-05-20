from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.service import Service
from app.services.notifications.datetime_format import format_booking_start_local
from app.services.notifications.email_send import send_multipart_email
from app.services.notifications.mail_render import render_booking_created

logger = get_logger("app.mail")


class BookingNotificationSkip(Exception):
    """Non-retryable skip (booking gone or no longer relevant)."""


async def deliver_booking_created_email(
    *,
    settings: Settings,
    session: AsyncSession,
    booking_id: UUID,
    to_email: str,
) -> None:
    with log_context(use_case="deliver_booking_created_email", booking_id=str(booking_id)):
        booking = await session.get(Booking, booking_id)
        if booking is None:
            raise BookingNotificationSkip("booking_not_found")
        if booking.status is not BookingStatus.SCHEDULED:
            raise BookingNotificationSkip(f"booking_status_{booking.status.value}")

        master = await session.get(MasterProfile, booking.master_id)
        service = await session.get(Service, booking.service_id)
        if master is None or service is None:
            raise BookingNotificationSkip("booking_related_entity_missing")

        start_at_local = format_booking_start_local(booking.start_at, master.timezone)
        cabinet_url = f"{settings.security.frontend_public_origin.rstrip('/')}/client"

        subject, text_body, html_body = render_booking_created(
            recipient_email=to_email,
            master_name=master.display_name,
            service_name=service.name,
            start_at_local=start_at_local,
            duration_min=booking.duration_min,
            cabinet_url=cabinet_url,
        )

        await send_multipart_email(
            settings=settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            log_sent_event="email.booking_created.sent",
        )
