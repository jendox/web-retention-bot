from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from datetime import datetime

from app.core.config import get_settings
from app.services.notifications.datetime_format import format_booking_start_local

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "email"


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "htm"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_email_verification(*, verification_url: str, recipient_email: str) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {"verification_url": verification_url, "recipient_email": recipient_email}
    subject = env.get_template("email_verification.subject.txt").render(**ctx).strip()
    text_body = env.get_template("email_verification.txt").render(**ctx)
    html_body = env.get_template("email_verification.html").render(**ctx)
    return subject, text_body, html_body


def email_verification_user_notification_copy(*, to_email: str) -> tuple[str, str]:
    """Title and body stored on `UserNotification` (in-app history); no secrets or links."""
    env = _jinja_env()
    ctx = {"recipient_email": to_email}
    title = env.get_template("email_verification.subject.txt").render(**ctx).strip()
    body = env.get_template("email_verification.in_app_body.txt").render(**ctx).strip()
    return title, body


def render_booking_created(
    *,
    recipient_email: str,
    master_name: str,
    service_name: str,
    start_at_local: str,
    duration_min: int,
    cabinet_url: str,
) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": recipient_email,
        "master_name": master_name,
        "service_name": service_name,
        "start_at_local": start_at_local,
        "duration_min": duration_min,
        "cabinet_url": cabinet_url,
    }
    subject = env.get_template("booking_created.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_created.txt").render(**ctx)
    html_body = env.get_template("booking_created.html").render(**ctx)
    return subject, text_body, html_body


def booking_created_in_app_copy(
    *,
    master_display_name: str,
    service_name: str,
    start_at: datetime,
    master_timezone: str,
) -> tuple[str, str, str | None]:
    start_at_local = format_booking_start_local(start_at, master_timezone)
    title = "Новая запись"
    body = f"{master_display_name}: {service_name}, {start_at_local}"
    link_url = f"{get_settings().security.frontend_public_origin.rstrip('/')}/client"
    return title, body, link_url
