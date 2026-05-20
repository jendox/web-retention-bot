"""Telegram notification delivery and channel preference routing."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationEventType
from app.services.notifications.channel_policy import delivery_channels_for_user
from app.services.notifications.dispatcher import BookingEmailContext, NotificationDispatcher
from app.services.notifications.messenger_delivery import (
    deliver_user_notification_telegram,
    format_notification_text,
)


def _mail_settings(*, eager: bool = True, telegram_url: str = "http://telegram-bot:8091") -> Settings:
    return Settings.model_validate(
        {
            "celery": {"broker_url": "redis://localhost:6379/1", "result_backend": "redis://localhost:6379/1"},
            "notifications": {"eager_deliveries": eager},
            "security": {"frontend_public_origin": "https://frontend.test"},
            "smtp": {"enabled": False},
            "messenger_bots": {
                "internal_secret": "test-secret",
                "telegram_service_url": telegram_url,
            },
        },
    )


def test_format_notification_text_includes_link() -> None:
    text = format_notification_text(
        title="Новая запись",
        body="Мастер: Услуга",
        link_url="https://frontend.test/client",
    )
    assert "Новая запись" in text
    assert "https://frontend.test/client" in text


@pytest.mark.asyncio
async def test_deliver_telegram_sends_via_bot_client() -> None:
    user_id = uuid.uuid4()
    delivery = SimpleNamespace(
        id=uuid.uuid4(),
        status=DeliveryStatus.PENDING,
        error_message=None,
        sent_at=None,
        channel=DeliveryChannel.TELEGRAM,
        user_notification=SimpleNamespace(
            recipient_user_id=user_id,
            title="Заголовок",
            body="Текст",
            link_url="/client",
        ),
    )
    linked = SimpleNamespace(is_verified=True, address="123456789")
    preference_repo = SimpleNamespace(get_channel=AsyncMock(return_value=linked))

    with patch(
        "app.services.notifications.messenger_delivery.MessengerBotClients.send_text",
        new_callable=AsyncMock,
    ) as send_text:
        await deliver_user_notification_telegram(
            settings=_mail_settings(),
            preference_repo=preference_repo,
            delivery=delivery,
        )

    send_text.assert_awaited_once()
    assert send_text.await_args.kwargs["external_id"] == "123456789"
    assert "Заголовок" in send_text.await_args.kwargs["text"]
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.sent_at is not None


@pytest.mark.asyncio
async def test_deliver_telegram_skipped_when_not_linked() -> None:
    delivery = SimpleNamespace(
        id=uuid.uuid4(),
        status=DeliveryStatus.PENDING,
        error_message=None,
        sent_at=None,
        channel=DeliveryChannel.TELEGRAM,
        user_notification=SimpleNamespace(
            recipient_user_id=uuid.uuid4(),
            title="T",
            body="B",
            link_url=None,
        ),
    )
    preference_repo = SimpleNamespace(get_channel=AsyncMock(return_value=None))

    await deliver_user_notification_telegram(
        settings=_mail_settings(),
        preference_repo=preference_repo,
        delivery=delivery,
    )

    assert delivery.status == DeliveryStatus.SKIPPED


@pytest.mark.asyncio
async def test_dispatch_booking_creates_email_and_telegram_deliveries() -> None:
    session = AsyncMock()
    dispatcher = NotificationDispatcher(_mail_settings(), session)
    fake_deliveries: list = []

    async def capture_delivery(data):
        fields = data.__dict__
        delivery = SimpleNamespace(
            id=uuid.uuid4(),
            sent_at=None,
            status=fields.get("status", DeliveryStatus.PENDING),
            **{k: v for k, v in fields.items() if k != "status"},
        )
        fake_deliveries.append(delivery)
        return delivery

    dispatcher._notification_event_repo = SimpleNamespace(
        create=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
    )
    dispatcher._user_notification_repo = SimpleNamespace(
        create=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid.uuid4(),
                event_type=NotificationEventType.BOOKING_CREATED,
                title="T",
                body="B",
                link_url=None,
                payload={"booking_id": str(uuid.uuid4()), "to_email": "c@example.com"},
                recipient_user_id=uuid.uuid4(),
            ),
        ),
    )
    dispatcher._notification_delivery_repo = SimpleNamespace(create=capture_delivery)

    channels = [DeliveryChannel.EMAIL, DeliveryChannel.TELEGRAM]
    with (
        patch(
            "app.services.notifications.dispatcher.delivery_channels_for_user",
            AsyncMock(return_value=channels),
        ),
        patch.object(dispatcher, "_deliver_delivery", new_callable=AsyncMock),
    ):
        await dispatcher.dispatch_booking_created(
            booking_id=uuid.uuid4(),
            master_profile_id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            recipient=SimpleNamespace(user_id=uuid.uuid4(), email="c@example.com"),
            email_ctx=BookingEmailContext(title="T", body="B", link_url=None, payload={}),
        )

    assert len(fake_deliveries) == 2
    assert {d.channel for d in fake_deliveries} == {DeliveryChannel.EMAIL, DeliveryChannel.TELEGRAM}


@pytest.mark.asyncio
async def test_delivery_channels_excludes_telegram_when_pref_disabled() -> None:
    user_id = uuid.uuid4()

    async def enabled(_uid, channel, _event_type, *, category):
        return channel == DeliveryChannel.EMAIL

    repo = AsyncMock()
    repo.is_channel_enabled_for_event = AsyncMock(side_effect=enabled)
    repo.get_channel = AsyncMock(return_value=SimpleNamespace(is_verified=True, address="1"))

    channels = await delivery_channels_for_user(
        repo,
        user_id=user_id,
        event_type=NotificationEventType.BOOKING_CREATED,
    )
    assert channels == [DeliveryChannel.EMAIL]
