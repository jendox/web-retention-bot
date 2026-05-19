from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.client import Client, MasterClient
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientUpdate, ClientWithLinkResponse, MasterClientOut

from .enrich_booking_stats import enrich_clients_with_booking_stats
from .exceptions import ClientEmailLockedError, ClientNameLockedError, ClientNotFoundError, ClientNothingToUpdateError

_CLIENT_FIELDS = frozenset({"display_name", "phone", "email"})
_LINK_FIELDS = frozenset({"notes", "alias"})

logger = get_logger("app.client")


class UpdateClientUseCase:
    def __init__(self, client_repo: ClientRepository, booking_repo: BookingRepository) -> None:
        self._client_repo = client_repo
        self._booking_repo = booking_repo

    @staticmethod
    def _get_patch(payload: ClientUpdate) -> dict[str, Any]:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            logger.warning("failed", reason="empty_patch")
            raise ClientNothingToUpdateError from None
        return patch

    async def _get_link_with_client(self, master_id: UUID, client_id: UUID) -> tuple[MasterClient, Client]:
        row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
        if row is None:
            logger.warning("failed", reason="client_not_found")
            raise ClientNotFoundError from None
        link, client = row
        return link, client

    @staticmethod
    def _ensure_email_modification_allowed(
        patch: dict[str, Any],
        client: Client,
        link: MasterClient,
    ) -> None:
        if "email" in patch and client.user_id is not None and not link.invite_email_mismatch:
            incoming_email = str(patch["email"]).lower() if patch["email"] is not None else None
            current_email = str(client.email).lower() if client.email is not None else None
            if incoming_email != current_email:
                logger.warning("failed", reason="client_email_locked")
                raise ClientEmailLockedError from None

    @staticmethod
    def _ensure_display_name_modification_allowed(
        patch: dict[str, Any],
        client: Client,
    ) -> None:
        if "display_name" in patch and client.user_id is not None:
            incoming_name = str(patch["display_name"])
            current_name = str(client.display_name)
            if incoming_name != current_name:
                logger.warning("failed", reason="client_name_locked")
                raise ClientNameLockedError from None

    @staticmethod
    def _apply_patch_updates(patch: dict[str, Any], client: Client, link: MasterClient) -> None:
        for key, value in patch.items():
            if key in _CLIENT_FIELDS:
                update_value = str(value).lower() if key == "email" and value is not None else value
                setattr(client, key, update_value)
            elif key in _LINK_FIELDS:
                setattr(link, key, value)

    @staticmethod
    def _resolve_email_mismatch(client: Client, link: MasterClient) -> bool:
        mismatch_cleared = False
        if link.linked_account_email and client.email:
            if str(client.email).lower() == link.linked_account_email.lower():
                mismatch_cleared = link.invite_email_mismatch
                link.invite_email_mismatch = False
        return mismatch_cleared

    async def __call__(
        self,
        master_id: UUID,
        client_id: UUID,
        payload: ClientUpdate,
    ) -> ClientWithLinkResponse:
        with log_context(use_case="update_client", master_id=str(master_id), client_id=str(client_id)):
            patch = self._get_patch(payload)
            link, client = await self._get_link_with_client(master_id=master_id, client_id=client_id)

            self._ensure_email_modification_allowed(patch, client, link)
            self._ensure_display_name_modification_allowed(patch, client)

            self._apply_patch_updates(patch, client, link)

            mismatch_cleared = self._resolve_email_mismatch(client, link)

            await self._client_repo.flush()
            await self._client_repo.refresh(client)
            await self._client_repo.refresh(link)
            logger.info("updated", fields=sorted(patch.keys()), invite_email_mismatch_cleared=mismatch_cleared)

            response = ClientWithLinkResponse(
                client=ClientSchema.model_validate(client),
                link=MasterClientOut.model_validate(link),
            )
            await enrich_clients_with_booking_stats(
                self._booking_repo,
                master_id=master_id,
                items=[response],
            )
            return response


def get_update_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> UpdateClientUseCase:
    return UpdateClientUseCase(client_repo, booking_repo)
