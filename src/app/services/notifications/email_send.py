from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from app.core.config import Settings
from app.core.structured_logging import get_logger

logger = get_logger("app.mail")


def smtp_credentials(settings: Settings) -> tuple[str | None, str | None]:
    user = (settings.smtp.username or "").strip() or None
    password = settings.smtp.password
    if user is None:
        return None, None
    return user, password if password is not None else ""


async def send_multipart_email(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    log_sent_event: str,
) -> None:
    if not settings.smtp.enabled:
        logger.info(
            "email.send_skipped",
            reason="smtp.disabled",
            mail_event=log_sent_event,
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

    user, password = smtp_credentials(settings)
    async with aiosmtplib.SMTP(
        hostname=settings.smtp.host,
        port=settings.smtp.port,
        username=user,
        password=password,
        use_tls=settings.smtp.tls,
        start_tls=settings.smtp.start_tls,
    ) as smtp:
        await smtp.send_message(msg)
    logger.info(log_sent_event, to_email=to_email, subject=subject)
