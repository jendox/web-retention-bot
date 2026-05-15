from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientWithLinkResponse, MasterClientOut

from .exceptions import ClientNotFoundError


class GetClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, master_id: UUID, client_id: UUID) -> ClientWithLinkResponse:
        row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
        if row is None:
            raise ClientNotFoundError from None
        link, client = row
        return ClientWithLinkResponse(
            client=ClientSchema.model_validate(client),
            link=MasterClientOut.model_validate(link),
        )


def get_get_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> GetClientUseCase:
    return GetClientUseCase(client_repo)
