from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.core.security import generate_password_reset_url
from app.core.structured_logging import get_logger, log_context
from app.services.notifications.email_send import send_multipart_email
from app.services.notifications.mail_render import render_password_reset

logger = get_logger("app.mail")


async def deliver_password_reset(*, settings: Settings, user_id: UUID, to_email: str) -> None:
    """Mint password reset URL and send (or log) the email — single entry for API and workers."""
    with log_context(use_case="deliver_password_reset", user_id=str(user_id)):
        reset_url = generate_password_reset_url(
            secret_key=settings.security.secret_key,
            user_id=user_id,
            email=to_email,
            base_url=settings.security.frontend_public_origin,
            password_reset_ttl_seconds=settings.security.password_reset_ttl_seconds,
        )
        await notify_password_reset(
            settings=settings,
            to_email=to_email,
            reset_url=reset_url,
        )


async def notify_password_reset(*, settings: Settings, to_email: str, reset_url: str) -> None:
    subject, text_body, html_body = render_password_reset(
        reset_url=reset_url,
        recipient_email=to_email,
    )

    if settings.security.auth_log_verification_link:
        logger.info(
            "email.password_reset.log_link",
            to_email=to_email,
            subject=subject,
            reset_url=reset_url,
        )

    await send_multipart_email(
        settings=settings,
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        log_sent_event="email.password_reset.sent",
    )
