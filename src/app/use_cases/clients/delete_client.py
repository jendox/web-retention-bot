from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.clients import ClientRepository, get_client_repo

from .exceptions import ClientHasBlockingRelationsError, ClientNotFoundError


class DeleteClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, master_id: UUID, client_id: UUID) -> None:
        row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
        if row is None:
            raise ClientNotFoundError from None
        _link, client = row

        if await self._client_repo.count_bookings_for_client(client_id):
            raise ClientHasBlockingRelationsError(reason="has_bookings") from None
        if await self._client_repo.has_invitation_linked_to_client(client_id):
            raise ClientHasBlockingRelationsError(reason="has_invitation") from None

        await self._client_repo.delete_client(client)


def get_delete_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> DeleteClientUseCase:
    return DeleteClientUseCase(client_repo)
