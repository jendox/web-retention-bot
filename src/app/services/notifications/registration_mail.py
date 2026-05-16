from __future__ import annotations

from email.message import EmailMessage
from uuid import UUID

import aiosmtplib

from app.core.config import Settings
from app.core.security import generate_email_verification_url
from app.core.structured_logging import get_logger, log_context
from app.services.notifications.mail_render import render_email_verification

logger = get_logger("app.mail")


def _smtp_credentials(settings: Settings) -> tuple[str | None, str | None]:
    user = (settings.smtp.username or "").strip() or None
    password = settings.smtp.password
    if user is None:
        return None, None
    return user, password if password is not None else ""


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

    if not settings.smtp.enabled:
        logger.info(
            "email.verification.send_failed",
            reason="smtp.disabled",
            to_email=to_email,
            subject=subject,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp.from_email
    msg["To"] = to_email
    msg.set_content(text_body, subtype="plain", charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")

    user, password = _smtp_credentials(settings)
    async with aiosmtplib.SMTP(
        hostname=settings.smtp.host,
        port=settings.smtp.port,
        username=user,
        password=password,
        use_tls=settings.smtp.tls,
        start_tls=settings.smtp.start_tls,
    ) as smtp:
        await smtp.send_message(msg)
    logger.info("email.verification.sent", to_email=to_email, subject=subject)
