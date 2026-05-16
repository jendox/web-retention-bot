from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.structured_logging import get_logger, log_context
from app.models import NotificationDelivery, NotificationEvent, UserNotification
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationEventType
from app.repositories.notifications import (
    NotificationDeliveryCreate,
    NotificationDeliveryRepository,
    NotificationEventCreate,
    NotificationEventRepository,
    UserNotificationCreate,
    UserNotificationRepository,
)
from app.services.notifications.mail_render import email_verification_user_notification_copy
from app.services.notifications.registration_mail import deliver_email_verification
from app.services.notifications.tasks import process_notification_delivery

EMAIL_VERIFY_DEDUP_PREFIX = "email_verify:user:"

logger = get_logger("app.notifications.dispatcher")


@dataclass(frozen=True)
class EmailVerificationDispatchResult:
    event: NotificationEvent
    user_notification: UserNotification
    delivery: NotificationDelivery


class NotificationDispatcher:
    """Single entry: persist notification graph and optionally enqueue external delivery."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings = settings
        self._notification_event_repo = NotificationEventRepository(session)
        self._user_notification_repo = UserNotificationRepository(session)
        self._notification_delivery_repo = NotificationDeliveryRepository(session)

    async def dispatch_email_verification(
        self,
        *,
        user_id: UUID,
        to_email: str,
    ) -> EmailVerificationDispatchResult:
        with log_context(use_case="dispatch_email_verification", user_id=str(user_id), channel="email"):
            payload: dict[str, str] = {"to_email": to_email}

            event = await self._notification_event_repo.create(
                NotificationEventCreate(
                    type=NotificationEventType.EMAIL_VERIFICATION,
                    target_user_id=user_id,
                    payload=payload,
                )
            )

            note_title, note_body = email_verification_user_notification_copy(to_email=to_email)
            user_note = await self._user_notification_repo.create(
                UserNotificationCreate(
                    event_id=event.id,
                    recipient_user_id=user_id,
                    event_type=NotificationEventType.EMAIL_VERIFICATION,
                    title=note_title,
                    body=note_body,
                    payload=payload,
                    dedup_key=f"{EMAIL_VERIFY_DEDUP_PREFIX}{user_id}",
                )
            )

            delivery = await self._notification_delivery_repo.create(
                NotificationDeliveryCreate(
                    user_notification_id=user_note.id,
                    channel=DeliveryChannel.EMAIL,
                    status=DeliveryStatus.PENDING,
                    scheduled_at=datetime.now(UTC),
                )
            )

            if self._settings.notifications.eager_deliveries:
                await deliver_email_verification(
                    settings=self._settings,
                    user_id=user_id,
                    to_email=to_email,
                )
                delivery.sent_at = datetime.now(UTC)
                delivery.status = DeliveryStatus.SENT
                logger.info("sent_eagerly", event_id=str(event.id), delivery_id=str(delivery.id))
            else:
                process_notification_delivery.apply_async(args=[str(delivery.id)], countdown=2)
                logger.info("queued", event_id=str(event.id), delivery_id=str(delivery.id))

            return EmailVerificationDispatchResult(event=event, user_notification=user_note, delivery=delivery)

    async def dispatch_invite_email_mismatch_for_master(
        self,
        *,
        master_user_id: UUID,
        master_profile_id: UUID,
        client_id: UUID,
        profile_email: str,
        account_email: str,
        client_display_name: str,
    ) -> None:
        with log_context(
            use_case="dispatch_invite_email_mismatch",
            master_user_id=str(master_user_id),
            master_id=str(master_profile_id),
            client_id=str(client_id),
        ):
            payload = {
                "profile_email": profile_email,
                "account_email": account_email,
                "client_display_name": client_display_name,
                "client_id": str(client_id),
            }
            event = await self._notification_event_repo.create(
                NotificationEventCreate(
                    type=NotificationEventType.DEFAULT,
                    target_user_id=master_user_id,
                    master_profile_id=master_profile_id,
                    client_id=client_id,
                    payload=payload,
                )
            )
            title = "Клиент принял приглашение с другим email"
            body = (
                f"«{client_display_name}»: в карточке был указан {profile_email}, "
                f"а вошёл как {account_email}. Обновите email в карточке, "
                "если хотите слать уведомления на актуальный адрес."
            )
            dedup = f"invite_email_mismatch:{client_id}:{account_email}"
            await self._user_notification_repo.create(
                UserNotificationCreate(
                    event_id=event.id,
                    recipient_user_id=master_user_id,
                    event_type=NotificationEventType.DEFAULT,
                    title=title,
                    body=body,
                    payload=payload,
                    dedup_key=dedup,
                ),
            )
            logger.info("created", event_id=str(event.id))


def get_notification_dispatcher(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationDispatcher:
    settings = request.app.state.settings or get_settings()
    return NotificationDispatcher(settings, session)
