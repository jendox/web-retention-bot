from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings
from app.services.notifications.datetime_format import format_booking_start_local

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "email"

BOOKING_EMAIL_AUDIENCE_CLIENT = "client"
BOOKING_EMAIL_AUDIENCE_MASTER = "master"


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


def render_password_reset(*, reset_url: str, recipient_email: str) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {"reset_url": reset_url, "recipient_email": recipient_email}
    subject = env.get_template("password_reset.subject.txt").render(**ctx).strip()
    text_body = env.get_template("password_reset.txt").render(**ctx)
    html_body = env.get_template("password_reset.html").render(**ctx)
    return subject, text_body, html_body


def email_password_reset_user_notification_copy(*, to_email: str) -> tuple[str, str]:
    env = _jinja_env()
    ctx = {"recipient_email": to_email}
    title = env.get_template("password_reset.subject.txt").render(**ctx).strip()
    body = env.get_template("password_reset.in_app_body.txt").render(**ctx).strip()
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
    recipient_timezone: str,
) -> tuple[str, str, str | None]:
    start_at_local = format_booking_start_local(start_at, recipient_timezone)
    title = "Новая запись"
    body = f"{master_display_name}: {service_name}, {start_at_local}"
    link_url = f"{get_settings().security.frontend_public_origin.rstrip('/')}/client"
    return title, body, link_url


def append_master_comment_to_body(body: str, comment: str | None) -> str:
    if not comment:
        return body
    return f"{body}\n\nКомментарий мастера: {comment}"


def append_client_comment_to_body(body: str, comment: str | None) -> str:
    if not comment:
        return body
    return f"{body}\n\nКомментарий клиента: {comment}"


def _master_bookings_url() -> str:
    return f"{get_settings().security.frontend_public_origin.rstrip('/')}/master/bookings"


@dataclass(frozen=True)
class BookingCancelledEmailRenderContext:
    recipient_email: str
    master_name: str
    service_name: str
    start_at_local: str
    duration_min: int
    cabinet_url: str
    master_comment: str | None = None


def render_booking_cancelled(render_ctx: BookingCancelledEmailRenderContext) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": render_ctx.recipient_email,
        "master_name": render_ctx.master_name,
        "service_name": render_ctx.service_name,
        "start_at_local": render_ctx.start_at_local,
        "duration_min": render_ctx.duration_min,
        "cabinet_url": render_ctx.cabinet_url,
        "master_comment": render_ctx.master_comment,
    }
    subject = env.get_template("booking_cancelled.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_cancelled.txt").render(**ctx)
    html_body = env.get_template("booking_cancelled.html").render(**ctx)
    return subject, text_body, html_body


def booking_cancelled_in_app_copy(
    *,
    master_display_name: str,
    service_name: str,
    start_at: datetime,
    recipient_timezone: str,
    master_comment: str | None = None,
) -> tuple[str, str, str | None]:
    start_at_local = format_booking_start_local(start_at, recipient_timezone)
    title = "Запись отменена"
    body = append_master_comment_to_body(
        f"{master_display_name}: {service_name}, {start_at_local} — отменена",
        master_comment,
    )
    link_url = f"{get_settings().security.frontend_public_origin.rstrip('/')}/client/visits"
    return title, body, link_url


@dataclass(frozen=True)
class BookingMovedEmailRenderContext:
    recipient_email: str
    master_name: str
    service_name: str
    start_at_local: str
    duration_min: int
    cabinet_url: str
    previous_start_at_local: str
    master_comment: str | None = None


def render_booking_moved(render_ctx: BookingMovedEmailRenderContext) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": render_ctx.recipient_email,
        "master_name": render_ctx.master_name,
        "service_name": render_ctx.service_name,
        "previous_start_at_local": render_ctx.previous_start_at_local,
        "start_at_local": render_ctx.start_at_local,
        "duration_min": render_ctx.duration_min,
        "cabinet_url": render_ctx.cabinet_url,
        "master_comment": render_ctx.master_comment,
    }
    subject = env.get_template("booking_moved.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_moved.txt").render(**ctx)
    html_body = env.get_template("booking_moved.html").render(**ctx)
    return subject, text_body, html_body


def booking_moved_in_app_copy(
    *,
    master_display_name: str,
    service_name: str,
    previous_start_at: datetime,
    start_at: datetime,
    recipient_timezone: str,
    master_comment: str | None = None,
) -> tuple[str, str, str | None]:
    previous_local = format_booking_start_local(previous_start_at, recipient_timezone)
    start_at_local = format_booking_start_local(start_at, recipient_timezone)
    title = "Запись перенесена"
    body = append_master_comment_to_body(
        f"{master_display_name}: {service_name}, {previous_local} → {start_at_local}",
        master_comment,
    )
    link_url = f"{get_settings().security.frontend_public_origin.rstrip('/')}/client/visits"
    return title, body, link_url


@dataclass(frozen=True)
class BookingCreatedMasterEmailRenderContext:
    recipient_email: str
    client_name: str
    service_name: str
    start_at_local: str
    duration_min: int
    bookings_url: str


def render_booking_created_master(render_ctx: BookingCreatedMasterEmailRenderContext) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": render_ctx.recipient_email,
        "client_name": render_ctx.client_name,
        "service_name": render_ctx.service_name,
        "start_at_local": render_ctx.start_at_local,
        "duration_min": render_ctx.duration_min,
        "bookings_url": render_ctx.bookings_url,
    }
    subject = env.get_template("booking_created_master.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_created_master.txt").render(**ctx)
    html_body = env.get_template("booking_created_master.html").render(**ctx)
    return subject, text_body, html_body


def booking_created_master_in_app_copy(
    *,
    client_display_name: str,
    service_name: str,
    start_at: datetime,
    master_timezone: str,
) -> tuple[str, str, str | None]:
    start_at_local = format_booking_start_local(start_at, master_timezone)
    title = "Новая запись от клиента"
    body = f"{client_display_name}: {service_name}, {start_at_local}"
    return title, body, _master_bookings_url()


@dataclass(frozen=True)
class BookingCancelledMasterEmailRenderContext:
    recipient_email: str
    client_name: str
    service_name: str
    start_at_local: str
    duration_min: int
    bookings_url: str
    client_comment: str | None = None


def render_booking_cancelled_master(render_ctx: BookingCancelledMasterEmailRenderContext) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": render_ctx.recipient_email,
        "client_name": render_ctx.client_name,
        "service_name": render_ctx.service_name,
        "start_at_local": render_ctx.start_at_local,
        "duration_min": render_ctx.duration_min,
        "bookings_url": render_ctx.bookings_url,
        "client_comment": render_ctx.client_comment,
    }
    subject = env.get_template("booking_cancelled_master.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_cancelled_master.txt").render(**ctx)
    html_body = env.get_template("booking_cancelled_master.html").render(**ctx)
    return subject, text_body, html_body


def booking_cancelled_master_in_app_copy(
    *,
    client_display_name: str,
    service_name: str,
    start_at: datetime,
    master_timezone: str,
    client_comment: str | None = None,
) -> tuple[str, str, str | None]:
    start_at_local = format_booking_start_local(start_at, master_timezone)
    title = "Запись отменена клиентом"
    body = append_client_comment_to_body(
        f"{client_display_name}: {service_name}, {start_at_local} — отменена",
        client_comment,
    )
    return title, body, _master_bookings_url()


@dataclass(frozen=True)
class BookingMovedMasterEmailRenderContext:
    recipient_email: str
    client_name: str
    service_name: str
    start_at_local: str
    duration_min: int
    bookings_url: str
    previous_start_at_local: str
    client_comment: str | None = None


def render_booking_moved_master(render_ctx: BookingMovedMasterEmailRenderContext) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": render_ctx.recipient_email,
        "client_name": render_ctx.client_name,
        "service_name": render_ctx.service_name,
        "previous_start_at_local": render_ctx.previous_start_at_local,
        "start_at_local": render_ctx.start_at_local,
        "duration_min": render_ctx.duration_min,
        "bookings_url": render_ctx.bookings_url,
        "client_comment": render_ctx.client_comment,
    }
    subject = env.get_template("booking_moved_master.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_moved_master.txt").render(**ctx)
    html_body = env.get_template("booking_moved_master.html").render(**ctx)
    return subject, text_body, html_body


def booking_moved_master_in_app_copy(
    *,
    client_display_name: str,
    service_name: str,
    previous_start_at: datetime,
    start_at: datetime,
    master_timezone: str,
    client_comment: str | None = None,
) -> tuple[str, str, str | None]:
    previous_local = format_booking_start_local(previous_start_at, master_timezone)
    start_at_local = format_booking_start_local(start_at, master_timezone)
    title = "Запись перенесена клиентом"
    body = append_client_comment_to_body(
        f"{client_display_name}: {service_name}, {previous_local} → {start_at_local}",
        client_comment,
    )
    return title, body, _master_bookings_url()


@dataclass(frozen=True)
class BookingReminderEmailRenderContext:
    recipient_email: str
    master_name: str
    service_name: str
    start_at_local: str
    duration_min: int
    cabinet_url: str


def render_booking_reminder(render_ctx: BookingReminderEmailRenderContext) -> tuple[str, str, str]:
    env = _jinja_env()
    ctx = {
        "recipient_email": render_ctx.recipient_email,
        "master_name": render_ctx.master_name,
        "service_name": render_ctx.service_name,
        "start_at_local": render_ctx.start_at_local,
        "duration_min": render_ctx.duration_min,
        "cabinet_url": render_ctx.cabinet_url,
    }
    subject = env.get_template("booking_reminder.subject.txt").render(**ctx).strip()
    text_body = env.get_template("booking_reminder.txt").render(**ctx)
    html_body = env.get_template("booking_reminder.html").render(**ctx)
    return subject, text_body, html_body


def booking_reminder_in_app_copy(
    *,
    master_display_name: str,
    service_name: str,
    start_at: datetime,
    recipient_timezone: str,
) -> tuple[str, str, str | None]:
    start_at_local = format_booking_start_local(start_at, recipient_timezone)
    title = "Напоминание о записи"
    body = f"{master_display_name}: {service_name}, {start_at_local}"
    link_url = f"{get_settings().security.frontend_public_origin.rstrip('/')}/client/visits"
    return title, body, link_url
