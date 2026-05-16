from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientUpdate, ClientWithLinkResponse, MasterClientOut

from .exceptions import ClientNotFoundError, ClientNothingToUpdateError

_CLIENT_FIELDS = frozenset({"display_name", "phone", "email"})
_LINK_FIELDS = frozenset({"notes", "alias"})

logger = get_logger("app.client")


class UpdateClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(
        self,
        master_id: UUID,
        client_id: UUID,
        payload: ClientUpdate,
    ) -> ClientWithLinkResponse:
        with log_context(use_case="update_client", master_id=str(master_id), client_id=str(client_id)):
            patch = payload.model_dump(exclude_unset=True)
            if not patch:
                logger.warning("failed", reason="empty_patch")
                raise ClientNothingToUpdateError from None

            row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
            if row is None:
                logger.warning("failed", reason="client_not_found")
                raise ClientNotFoundError from None
            link, client = row

            for key, value in patch.items():
                if key in _CLIENT_FIELDS:
                    if key == "email" and value is not None:
                        value = str(value).lower()
                    setattr(client, key, value)
                elif key in _LINK_FIELDS:
                    setattr(link, key, value)

            mismatch_cleared = False
            if link.linked_account_email and client.email:
                if str(client.email).lower() == link.linked_account_email.lower():
                    mismatch_cleared = link.invite_email_mismatch
                    link.invite_email_mismatch = False

            await self._client_repo.session.flush()
            await self._client_repo.session.refresh(client)
            await self._client_repo.session.refresh(link)
            logger.info("updated", fields=sorted(patch.keys()), invite_email_mismatch_cleared=mismatch_cleared)

            return ClientWithLinkResponse(
                client=ClientSchema.model_validate(client),
                link=MasterClientOut.model_validate(link),
            )


def get_update_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> UpdateClientUseCase:
    return UpdateClientUseCase(client_repo)
