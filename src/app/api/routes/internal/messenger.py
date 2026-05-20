from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps_bots import verify_bot_internal_secret
from app.models.notifications import DeliveryChannel
from app.repositories.notification_preferences import (
    NotificationPreferenceRepository,
    get_notification_preference_repo,
)
from app.schemas.messenger_internal import MessengerCompleteLinkIn, MessengerCompleteLinkOut
from app.services.messenger.link_tokens import MessengerLinkTokenStore, get_messenger_link_token_store_dep
from app.services.messenger.providers import MessengerProvider

router = APIRouter(
    prefix="/messenger",
    tags=["internal-messenger"],
    dependencies=[Depends(verify_bot_internal_secret)],
)


def _provider_from_path(kind: str) -> MessengerProvider:
    try:
        return MessengerProvider(kind)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown messenger provider.") from exc


@router.post(
    "/{provider}/complete-link",
    response_model=MessengerCompleteLinkOut,
    summary="Bot sidecar: confirm user linked messenger (chat_id)",
)
async def complete_messenger_link(
    provider: str,
    payload: MessengerCompleteLinkIn,
    token_store: Annotated[MessengerLinkTokenStore, Depends(get_messenger_link_token_store_dep)],
    preference_repo: Annotated[NotificationPreferenceRepository, Depends(get_notification_preference_repo)],
) -> MessengerCompleteLinkOut:
    messenger = _provider_from_path(provider)
    user_id = await token_store.consume(messenger, payload.token.strip())
    if user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Ссылка устарела или уже использована.")

    channel_kind = DeliveryChannel(messenger.delivery_channel_value)
    await preference_repo.upsert_channel(
        user_id=user_id,
        kind=channel_kind,
        address=payload.external_id.strip(),
        is_verified=True,
    )

    return MessengerCompleteLinkOut(
        user_id=str(user_id),
        provider=messenger.value,
        external_id=payload.external_id.strip(),
    )
