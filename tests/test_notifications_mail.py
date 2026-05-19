"""Unit tests for email verification templates and delivery glue (no SMTP server)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.core.security import generate_email_verification_url
from app.services.notifications.mail_render import (
    email_verification_user_notification_copy,
    render_email_verification,
)
from app.services.notifications.registration_mail import (
    deliver_email_verification,
    notify_email_verification,
)


@pytest.fixture
def mail_settings() -> Settings:
    return Settings.model_validate(
        {
            "celery": {
                "broker_url": "redis://localhost:6379/1",
                "result_backend": "redis://localhost:6379/1",
            },
            "security": {
                "secret_key": "unit-test-mail-secret",
                "frontend_public_origin": "https://frontend.test",
                "email_verification_ttl_seconds": 7200,
                "auth_log_verification_link": False,
            },
            "smtp": {"enabled": False},
        },
    )


def test_render_email_verification_embeds_url_and_recipient() -> None:
    url = "https://frontend.test/verify-email?token=abc"
    email = "master@studio.example"
    subject, text_body, html_body = render_email_verification(
        verification_url=url,
        recipient_email=email,
    )

    assert subject == "Подтвердите адрес электронной почты"
    assert url in text_body
    assert email in text_body
    assert url in html_body
    assert email in html_body


def test_email_verification_user_notification_copy_matches_templates() -> None:
    to_email = "user@example.com"
    title, body = email_verification_user_notification_copy(to_email=to_email)

    assert title == "Подтвердите адрес электронной почты"
    assert to_email in body
    assert "http" not in body.lower()


async def test_deliver_email_verification_passes_url_from_security_to_notify(mail_settings: Settings) -> None:
    uid = uuid.uuid4()
    to_mail = "user@example.com"
    expected_url = generate_email_verification_url(
        secret_key=mail_settings.security.secret_key,
        user_id=uid,
        email=to_mail,
        base_url=mail_settings.security.frontend_public_origin,
        verification_ttl_seconds=mail_settings.security.email_verification_ttl_seconds,
    )
    mock_notify = AsyncMock()
    with patch("app.services.notifications.registration_mail.notify_email_verification", mock_notify):
        await deliver_email_verification(settings=mail_settings, user_id=uid, to_email=to_mail)

    mock_notify.assert_awaited_once_with(
        settings=mail_settings,
        to_email=to_mail,
        verification_url=expected_url,
    )


async def test_notify_email_verification_does_not_connect_smtp_when_disabled(mail_settings: Settings) -> None:
    url = "https://frontend.test/verify-email?token=t"
    with patch("app.services.notifications.email_send.aiosmtplib.SMTP") as smtp_ctor:
        await notify_email_verification(
            settings=mail_settings,
            to_email="a@b.c",
            verification_url=url,
        )
    smtp_ctor.assert_not_called()
