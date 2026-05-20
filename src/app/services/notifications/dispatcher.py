from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.structured_logging import get_logger, get_request_id, log_context
from app.models import NotificationDelivery, NotificationEvent, UserNotification
from app.models.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationEventType
from app.repositories.notification_preferences import NotificationPreferenceRepository
from app.repositories.notifications import (
    NotificationDeliveryCreate,
    NotificationDeliveryRepository,
    NotificationEventCreate,
    NotificationEventRepository,
    UserNotificationCreate,
    UserNotificationRepository,
)
from app.services.notifications.booking_mail import (
    BookingEmailDeliveryOptions,
    deliver_booking_cancelled_email,
    deliver_booking_created_email,
    deliver_booking_moved_email,
)
from app.services.notifications.channel_policy import delivery_channels_for_user
from app.services.notifications.mail_render import (
    BOOKING_EMAIL_AUDIENCE_MASTER,
    email_verification_user_notification_copy,
)
from app.services.notifications.messenger_delivery import deliver_user_notification_telegram
from app.services.notifications.recipients import BookingClientRecipient
from app.services.notifications.registration_mail import deliver_email_verification
from app.services.notifications.tasks import process_notification_delivery

EMAIL_VERIFY_DEDUP = "email_verify:user:{user_id}"
BOOKING_CREATED_DEDUP = "booking_created:booking:{booking_id}:user:{user_id}"
BOOKING_CANCELLED_DEDUP = "booking_cancelled:booking:{booking_id}:user:{user_id}"
BOOKING_MOVED_DEDUP = "booking_moved:booking:{booking_id}:user:{user_id}:{start_at_iso}"

logger = get_logger("app.notifications.dispatcher")


@dataclass(frozen=True)
class EmailVerificationDispatchResult:
    event: NotificationEvent
    user_notification: UserNotification
    delivery: NotificationDelivery


@dataclass(frozen=True)
class BookingEmailContext:
    title: str
    body: str
    link_url: str | None
    payload: dict[str, str]


class NotificationDispatcher:
    """Single entry: persist notification graph and optionally enqueue external delivery."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings = settings
        self._session = session
        self._notification_event_repo = NotificationEventRepository(session)
        self._user_notification_repo = UserNotificationRepository(session)
        self._notification_delivery_repo = NotificationDeliveryRepository(session)
        self._preference_repo = NotificationPreferenceRepository(session)

    async def _deliver_booking_email(self, user_note: UserNotification, *, to_email: str) -> None:
        payload = user_note.payload or {}
        booking_id = UUID(payload["booking_id"])
        email_options = BookingEmailDeliveryOptions(
            audience=payload.get("audience", "client"),
            client_display_name=payload.get("client_display_name"),
        )
        if user_note.event_type is NotificationEventType.BOOKING_CREATED:
            await deliver_booking_created_email(
                settings=self._settings,
                session=self._session,
                booking_id=booking_id,
                to_email=to_email,
                options=email_options,
            )
            return
        if user_note.event_type is NotificationEventType.BOOKING_CANCELLED:
            await deliver_booking_cancelled_email(
                settings=self._settings,
                session=self._session,
                booking_id=booking_id,
                to_email=to_email,
                options=email_options,
            )
            return
        if user_note.event_type is NotificationEventType.BOOKING_MOVED:
            previous_start_at_iso = payload.get("previous_start_at")
            if not previous_start_at_iso:
                raise ValueError("missing previous_start_at for booking_moved")
            await deliver_booking_moved_email(
                settings=self._settings,
                session=self._session,
                booking_id=booking_id,
                to_email=to_email,
                previous_start_at_iso=previous_start_at_iso,
                options=email_options,
            )
            return
        raise ValueError(f"unsupported booking email event: {user_note.event_type.value}")

    async def _deliver_email_eager(self, user_note: UserNotification) -> None:
        payload = user_note.payload or {}
        to_email = payload.get("to_email")
        if not to_email:
            raise ValueError("missing to_email in notification payload")

        if user_note.event_type is NotificationEventType.EMAIL_VERIFICATION:
            if not user_note.recipient_user_id:
                raise ValueError("missing recipient_user_id for email verification")
            await deliver_email_verification(
                settings=self._settings,
                user_id=user_note.recipient_user_id,
                to_email=to_email,
            )
            return

        if user_note.event_type in {
            NotificationEventType.BOOKING_CREATED,
            NotificationEventType.BOOKING_CANCELLED,
            NotificationEventType.BOOKING_MOVED,
        }:
            await self._deliver_booking_email(user_note, to_email=to_email)
            return

        raise ValueError(f"unsupported eager event type: {user_note.event_type.value}")

    async def _deliver_delivery(
        self,
        delivery: NotificationDelivery,
        user_note: UserNotification,
    ) -> None:
        if delivery.channel == DeliveryChannel.EMAIL:
            await self._deliver_email_eager(user_note)
            return
        if delivery.channel == DeliveryChannel.TELEGRAM:
            await deliver_user_notification_telegram(
                settings=self._settings,
                preference_repo=self._preference_repo,
                delivery=delivery,
            )
            return
        delivery.status = DeliveryStatus.SKIPPED
        delivery.error_message = f"channel not supported: {delivery.channel.value}"

    async def _enqueue_delivery(
        self,
        *,
        event: NotificationEvent,
        delivery: NotificationDelivery,
        user_note: UserNotification,
    ) -> None:
        if self._settings.notifications.eager_deliveries:
            await self._deliver_delivery(delivery, user_note)
            if delivery.channel == DeliveryChannel.EMAIL and delivery.status == DeliveryStatus.PENDING:
                delivery.sent_at = datetime.now(UTC)
                delivery.status = DeliveryStatus.SENT
            if delivery.status in {DeliveryStatus.SENT, DeliveryStatus.SKIPPED}:
                logger.info(
                    "sent_eagerly",
                    event_id=str(event.id),
                    delivery_id=str(delivery.id),
                    channel=delivery.channel.value,
                    status=delivery.status.value,
                )
            elif delivery.status == DeliveryStatus.FAILED:
                logger.warning(
                    "eager_delivery_failed",
                    event_id=str(event.id),
                    delivery_id=str(delivery.id),
                    channel=delivery.channel.value,
                    error=delivery.error_message,
                )
                raise RuntimeError(delivery.error_message or "eager delivery failed")
        else:
            process_notification_delivery.apply_async(
                args=[str(delivery.id)],
                countdown=2,
                headers={"parent_request_id": get_request_id()},
            )
            logger.info("queued", event_id=str(event.id), delivery_id=str(delivery.id))

    async def dispatch_email_verification(
        self,
        *,
        user_id: UUID,
        to_email: str,
    ) -> EmailVerificationDispatchResult:
        with log_context(notification="dispatch_email_verification", user_id=str(user_id), channel="email"):
            payload: dict[str, str] = {"to_email": to_email}

            event = await self._notification_event_repo.create(
                NotificationEventCreate(
                    type=NotificationEventType.EMAIL_VERIFICATION,
                    target_user_id=user_id,
                    payload=payload,
                ),
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
                    dedup_key=EMAIL_VERIFY_DEDUP.format(user_id=user_id),
                ),
            )

            delivery = await self._notification_delivery_repo.create(
                NotificationDeliveryCreate(
                    user_notification_id=user_note.id,
                    channel=DeliveryChannel.EMAIL,
                    status=DeliveryStatus.PENDING,
                    scheduled_at=datetime.now(UTC),
                ),
            )

            await self._enqueue_delivery(event=event, delivery=delivery, user_note=user_note)

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
            notification="dispatch_invite_email_mismatch",
            master_user_id=str(master_user_id),
            master_id=str(master_profile_id),
            client_id=str(client_id),
        ):
            payload = {
                "audience": BOOKING_EMAIL_AUDIENCE_MASTER,
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
                ),
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

    async def dispatch_booking_created(
        self,
        *,
        booking_id: UUID,
        master_profile_id: UUID,
        client_id: UUID,
        recipient: BookingClientRecipient,
        email_ctx: BookingEmailContext,
    ) -> None:
        with log_context(notification="dispatch_booking_created"):
            payload = {
                **email_ctx.payload,
                "booking_id": str(booking_id),
                "to_email": recipient.email,
            }
            event = await self._notification_event_repo.create(
                NotificationEventCreate(
                    type=NotificationEventType.BOOKING_CREATED,
                    target_user_id=recipient.user_id,
                    master_profile_id=master_profile_id,
                    client_id=client_id,
                    booking_id=booking_id,
                    payload=payload,
                ),
            )

            user_note = await self._user_notification_repo.create(
                UserNotificationCreate(
                    event_id=event.id,
                    recipient_user_id=recipient.user_id,
                    recipient_client_id=client_id,
                    event_type=NotificationEventType.BOOKING_CREATED,
                    title=email_ctx.title,
                    body=email_ctx.body,
                    link_url=email_ctx.link_url,
                    payload=payload,
                    dedup_key=BOOKING_CREATED_DEDUP.format(
                        booking_id=booking_id,
                        user_id=recipient.user_id,
                    ),
                ),
            )

            for channel in await delivery_channels_for_user(
                self._preference_repo,
                user_id=recipient.user_id,
                event_type=NotificationEventType.BOOKING_CREATED,
            ):
                delivery = await self._notification_delivery_repo.create(
                    NotificationDeliveryCreate(
                        user_notification_id=user_note.id,
                        channel=channel,
                        status=DeliveryStatus.PENDING,
                        scheduled_at=datetime.now(UTC),
                    ),
                )
                await self._enqueue_delivery(event=event, delivery=delivery, user_note=user_note)

    async def dispatch_booking_cancelled(
        self,
        *,
        booking_id: UUID,
        master_profile_id: UUID,
        client_id: UUID,
        recipient: BookingClientRecipient,
        email_ctx: BookingEmailContext,
    ) -> None:
        with log_context(notification="dispatch_booking_cancelled"):
            payload = {
                **email_ctx.payload,
                "booking_id": str(booking_id),
                "to_email": recipient.email,
            }
            event = await self._notification_event_repo.create(
                NotificationEventCreate(
                    type=NotificationEventType.BOOKING_CANCELLED,
                    target_user_id=recipient.user_id,
                    master_profile_id=master_profile_id,
                    client_id=client_id,
                    booking_id=booking_id,
                    payload=payload,
                ),
            )

            user_note = await self._user_notification_repo.create(
                UserNotificationCreate(
                    event_id=event.id,
                    recipient_user_id=recipient.user_id,
                    recipient_client_id=client_id,
                    event_type=NotificationEventType.BOOKING_CANCELLED,
                    title=email_ctx.title,
                    body=email_ctx.body,
                    link_url=email_ctx.link_url,
                    payload=payload,
                    dedup_key=BOOKING_CANCELLED_DEDUP.format(
                        booking_id=booking_id,
                        user_id=recipient.user_id,
                    ),
                ),
            )

            for channel in await delivery_channels_for_user(
                self._preference_repo,
                user_id=recipient.user_id,
                event_type=NotificationEventType.BOOKING_CANCELLED,
            ):
                delivery = await self._notification_delivery_repo.create(
                    NotificationDeliveryCreate(
                        user_notification_id=user_note.id,
                        channel=channel,
                        status=DeliveryStatus.PENDING,
                        scheduled_at=datetime.now(UTC),
                    ),
                )
                await self._enqueue_delivery(event=event, delivery=delivery, user_note=user_note)

    async def dispatch_booking_moved(
        self,
        *,
        booking_id: UUID,
        master_profile_id: UUID,
        client_id: UUID,
        recipient: BookingClientRecipient,
        email_ctx: BookingEmailContext,
        previous_start_at_iso: str,
    ) -> None:
        with log_context(notification="dispatch_booking_moved"):
            payload = {
                **email_ctx.payload,
                "booking_id": str(booking_id),
                "to_email": recipient.email,
                "previous_start_at": previous_start_at_iso,
                "new_start_at": email_ctx.payload["new_start_at"],
            }
            event = await self._notification_event_repo.create(
                NotificationEventCreate(
                    type=NotificationEventType.BOOKING_MOVED,
                    target_user_id=recipient.user_id,
                    master_profile_id=master_profile_id,
                    client_id=client_id,
                    booking_id=booking_id,
                    payload=payload,
                ),
            )

            user_note = await self._user_notification_repo.create(
                UserNotificationCreate(
                    event_id=event.id,
                    recipient_user_id=recipient.user_id,
                    recipient_client_id=client_id,
                    event_type=NotificationEventType.BOOKING_MOVED,
                    title=email_ctx.title,
                    body=email_ctx.body,
                    link_url=email_ctx.link_url,
                    payload=payload,
                    dedup_key=BOOKING_MOVED_DEDUP.format(
                        booking_id=booking_id,
                        user_id=recipient.user_id,
                        start_at_iso=payload["new_start_at"],
                    ),
                ),
            )

            for channel in await delivery_channels_for_user(
                self._preference_repo,
                user_id=recipient.user_id,
                event_type=NotificationEventType.BOOKING_MOVED,
            ):
                delivery = await self._notification_delivery_repo.create(
                    NotificationDeliveryCreate(
                        user_notification_id=user_note.id,
                        channel=channel,
                        status=DeliveryStatus.PENDING,
                        scheduled_at=datetime.now(UTC),
                    ),
                )
                await self._enqueue_delivery(event=event, delivery=delivery, user_note=user_note)


def get_notification_dispatcher(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationDispatcher:
    settings = request.app.state.settings or get_settings()
    return NotificationDispatcher(settings, session)
