from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from celery import shared_task

from app.core.config import Settings, get_settings
from app.core.structured_logging import get_logger, log_context
from app.core.worker_db import worker_db_session
from app.models.notifications import NotificationEventType
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus
from app.models.notifications.models import NotificationDelivery
from app.repositories.notifications import NotificationDeliveryRepository
from app.services.notifications.booking_mail import BookingNotificationSkip, deliver_booking_created_email
from app.services.notifications.registration_mail import deliver_email_verification

logger = get_logger("app.notifications.tasks")


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
        logger.warning("failed", reason="missing_to_email_or_user_id")
        return

    delivery.status = DeliveryStatus.SENDING

    try:
        await deliver_email_verification(
            settings=settings,
            user_id=user_note.recipient_user_id,
            to_email=to_email,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("failed", reason="email_verification_delivery_error")
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = str(exc)[:2048]
        return

    delivery.status = DeliveryStatus.SENT
    delivery.sent_at = datetime.now(UTC)
    logger.info("sent")


async def _process_booking_created_email(
    settings: Settings,
    deliver: NotificationDelivery,
) -> None:
    user_note = deliver.user_notification
    payload = user_note.payload or {}
    booking_id = UUID(payload["booking_id"])
    to_email = payload.get("to_email")
    if not to_email:
        deliver.status = DeliveryStatus.FAILED
        deliver.error_message = "missing to_email"
        return

    deliver.status = DeliveryStatus.SENDING
    try:
        async with worker_db_session() as session:
            await deliver_booking_created_email(
                settings=settings,
                session=session,
                booking_id=booking_id,
                to_email=to_email,
            )
    except BookingNotificationSkip as exc:
        deliver.status = DeliveryStatus.SKIPPED
        deliver.error_message = str(exc)
        return
    except Exception as exc:
        deliver.status = DeliveryStatus.FAILED
        deliver.error_message = str(exc)[:2048]
        return

    deliver.status = DeliveryStatus.SENT
    deliver.sent_at = datetime.now(UTC)


NOTIFICATION_HANDLERS: dict[NotificationEventType, Callable] = {
    NotificationEventType.EMAIL_VERIFICATION: _process_email_verification_notification,
    NotificationEventType.BOOKING_CREATED: _process_booking_created_email,
}


async def _process_notification_delivery_async(delivery_id: UUID) -> None:
    settings = get_settings()
    async with worker_db_session() as session:
        notification_delivery_repo = NotificationDeliveryRepository(session)
        delivery = await notification_delivery_repo.get(delivery_id)
        if delivery is None:
            logger.warning("missing")
            return
        if delivery.status != DeliveryStatus.PENDING:
            logger.info("skipped", reason="status_not_pending", status=delivery.status.value)
            return

        if delivery.channel != DeliveryChannel.EMAIL:
            delivery.status = DeliveryStatus.SKIPPED
            delivery.error_message = "channel not implemented in worker"
            logger.warning("skipped", reason="channel_not_implemented", channel=delivery.channel.value)
            return

        event_type = delivery.user_notification.event_type
        handler = NOTIFICATION_HANDLERS.get(event_type)
        if handler is None:
            logger.error("failed", reason="unsupported_event_type", event_type=event_type.value)
            raise RuntimeError(f"Unsupported notification event type: {event_type.value}")

        logger.info("processing", event_type=event_type.value, channel=delivery.channel.value)
        await handler(settings, delivery)


@shared_task(name="notifications.process_notification_delivery", bind=True, max_retries=5)
def process_notification_delivery(self, delivery_id: str) -> None:
    """Consume a pending NotificationDelivery row (email channel supported)."""
    headers = self.request.headers or {}
    with log_context(
        task="process_notification_delivery",
        task_id=self.request.id,
        parent_request_id=headers.get("parent_request_id"),
        delivery_id=str(delivery_id),
    ):
        try:
            asyncio.run(_process_notification_delivery_async(UUID(delivery_id)))
        except Exception as exc:  # noqa: BLE001
            logger.exception("worker_error", delivery_id=delivery_id)
            raise self.retry(exc=exc, countdown=2) from exc
