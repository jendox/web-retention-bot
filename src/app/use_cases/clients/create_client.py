from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.client import InvitationStatus
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientCreate, ClientSchema, ClientWithLinkResponse, MasterClientOut

logger = get_logger("app.client")


class CreateClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, payload: ClientCreate, master_id: UUID) -> ClientWithLinkResponse:
        with log_context(use_case="create_client", master_id=str(master_id)):
            client = await self._client_repo.create(
                display_name=payload.display_name,
                phone=payload.phone,
                email=str(payload.email).lower() if payload.email else None,
            )
            link = await self._client_repo.create_link(
                master_id=master_id,
                client_id=client.id,
                invitation_status=InvitationStatus.LINKED,
            )
            logger.info("created", client_id=str(client.id), link_id=str(link.id))
            return ClientWithLinkResponse(
                client=ClientSchema.model_validate(client),
                link=MasterClientOut.model_validate(link),
            )


def get_create_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> CreateClientUseCase:
    return CreateClientUseCase(client_repo)
