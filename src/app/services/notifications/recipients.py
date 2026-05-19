from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models import Client, User


@dataclass(frozen=True)
class BookingClientRecipient:
    user_id: UUID
    email: str


def resolve_booking_client_recipient(
    client: Client,
    user: User | None,
) -> BookingClientRecipient | None:
    if client.user_id is None or user is None:
        return None
    if user.id != client.user_id:
        return None
    if user.email_verified_at is None:
        return None
    return BookingClientRecipient(user_id=user.id, email=user.email)
