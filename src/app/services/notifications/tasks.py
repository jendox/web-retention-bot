from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from celery import shared_task

from app.core.config import Settings, get_settings
from app.core.worker_db import worker_db_session
from app.models.notifications import NotificationEventType
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus
from app.models.notifications.models import NotificationDelivery
from app.repositories.notifications import NotificationDeliveryRepository
from app.services.notifications.registration_mail import deliver_email_verification

logger = logging.getLogger("app.notifications.tasks")


@shared_task(name="notifications.ping")
def ping() -> str:
    """Health check for the worker process."""
    return "pong"


async def _process_email_verification_notification(
    settings: Settings,
    delivery: NotificationDelivery,
) -> None:
    user_note = delivery.user_notification
    payload = user_note.payload if user_note.payload is not None else {}
    to_email: str | None = payload.get("to_email")
    if not to_email or not user_note.recipient_user_id:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = "missing to_email or user_id"
        return

    delivery.status = DeliveryStatus.SENDING

    try:
        await deliver_email_verification(
            settings=settings,
            user_id=user_note.recipient_user_id,
            to_email=to_email,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("notification delivery failed id=%s", delivery.id)
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = str(exc)[:2048]
        return

    delivery.status = DeliveryStatus.SENT
    delivery.sent_at = datetime.now(UTC)


NOTIFICATION_HANDLERS: dict[NotificationEventType, Callable] = {
    NotificationEventType.EMAIL_VERIFICATION: _process_email_verification_notification,
}


async def _process_notification_delivery_async(delivery_id: UUID) -> None:
    settings = get_settings()
    async with worker_db_session() as session:
        notification_delivery_repo = NotificationDeliveryRepository(session)
        delivery = await notification_delivery_repo.get(delivery_id)
        if delivery is None:
            logger.warning("notification delivery missing id=%s", delivery_id)
            return
        if delivery.status != DeliveryStatus.PENDING:
            return

        if delivery.channel != DeliveryChannel.EMAIL:
            delivery.status = DeliveryStatus.SKIPPED
            delivery.error_message = "channel not implemented in worker"
            return

        event_type = delivery.user_notification.event_type
        handler = NOTIFICATION_HANDLERS.get(event_type)
        if handler is None:
            raise RuntimeError(f"Unsupported notification event type: {event_type.value}")

        await handler(settings, delivery)


@shared_task(name="notifications.process_notification_delivery", bind=True, max_retries=5)
def process_notification_delivery(self, delivery_id: str) -> None:
    """Consume a pending NotificationDelivery row (email channel supported)."""
    try:
        asyncio.run(_process_notification_delivery_async(UUID(delivery_id)))
    except Exception as exc:  # noqa: BLE001
        logger.exception("worker error for delivery_id=%s", delivery_id)
        raise self.retry(exc=exc, countdown=2) from exc
