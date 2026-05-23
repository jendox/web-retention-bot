from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import Settings
from app.core.structured_logging import get_logger
from app.models.notifications import NotificationDelivery
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus
from app.repositories.notification_preferences import NotificationPreferenceRepository
from app.services.messenger.bot_clients import MessengerBotClients, MessengerBotSendError
from app.services.messenger.providers import MessengerProvider

logger = get_logger("app.notifications.messenger")


def format_notification_text(
    *,
    title: str,
    body: str,
    link_url: str | None = None,
) -> str:
    lines = [title.strip(), "", body.strip()]
    if link_url and link_url.strip():
        lines.extend(["", link_url.strip()])
    return "\n".join(lines)


async def deliver_user_notification_telegram(
    *,
    settings: Settings,
    preference_repo: NotificationPreferenceRepository,
    delivery: NotificationDelivery,
) -> None:
    user_note = delivery.user_notification
    if user_note is None:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = "missing user_notification"
        logger.warning("telegram_failed", reason="missing_user_notification")
        return

    user_id = user_note.recipient_user_id
    if user_id is None:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = "missing recipient_user_id"
        logger.warning("telegram_failed", reason="missing_recipient_user_id")
        return

    linked = await preference_repo.get_channel(user_id, DeliveryChannel.TELEGRAM)
    if linked is None or not linked.is_verified or not linked.address.strip():
        delivery.status = DeliveryStatus.SKIPPED
        delivery.error_message = "telegram not linked"
        logger.info("telegram_skipped", reason="not_linked", user_id=str(user_id))
        return

    if not settings.messenger_bots.telegram_service_url:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = "telegram bot service URL is not configured"
        logger.warning("telegram_failed", reason="service_url_missing")
        return

    text = format_notification_text(
        title=user_note.title,
        body=user_note.body,
        link_url=user_note.link_url,
    )
    delivery.status = DeliveryStatus.SENDING

    try:
        await MessengerBotClients(settings.messenger_bots).send_text(
            MessengerProvider.TELEGRAM,
            external_id=linked.address.strip(),
            text=text,
        )
    except MessengerBotSendError as exc:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = exc.detail[:2048]
        logger.warning(
            "telegram_failed",
            reason="send_error",
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return
    except Exception as exc:  # noqa: BLE001
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = str(exc)[:2048]
        logger.exception("telegram_failed", reason="unexpected")
        return

    delivery.status = DeliveryStatus.SENT
    delivery.sent_at = datetime.now(UTC)
    logger.info("telegram_sent", user_id=str(user_id), delivery_id=str(delivery.id))
