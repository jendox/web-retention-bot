from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.core.security import generate_email_verification_url
from app.core.structured_logging import get_logger, log_context
from app.services.notifications.email_send import send_multipart_email
from app.services.notifications.mail_render import render_email_verification

logger = get_logger("app.mail")


async def deliver_email_verification(*, settings: Settings, user_id: UUID, to_email: str) -> None:
    """Mint verification URL and send (or log) the email — single entry for API and workers."""
    with log_context(use_case="deliver_email_verification", user_id=str(user_id)):
        verification_url = generate_email_verification_url(
            secret_key=settings.security.secret_key,
            user_id=user_id,
            email=to_email,
            base_url=settings.security.frontend_public_origin,
            verification_ttl_seconds=settings.security.email_verification_ttl_seconds,
        )
        await notify_email_verification(
            settings=settings,
            to_email=to_email,
            verification_url=verification_url,
        )


async def notify_email_verification(*, settings: Settings, to_email: str, verification_url: str) -> None:
    subject, text_body, html_body = render_email_verification(
        verification_url=verification_url,
        recipient_email=to_email,
    )

    if settings.security.auth_log_verification_link:
        logger.info(
            "email.verification.log_link",
            to_email=to_email,
            subject=subject,
            verification_url=verification_url,
        )

    await send_multipart_email(
        settings=settings,
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        log_sent_event="email.verification.sent",
    )
