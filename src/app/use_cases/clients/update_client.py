from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientUpdate, ClientWithLinkResponse, MasterClientOut

from .exceptions import ClientNotFoundError, ClientNothingToUpdateError

_CLIENT_FIELDS = frozenset({"display_name", "phone", "email"})
_LINK_FIELDS = frozenset({"notes", "alias"})


class UpdateClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(
        self,
        master_id: UUID,
        client_id: UUID,
        payload: ClientUpdate,
    ) -> ClientWithLinkResponse:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            raise ClientNothingToUpdateError from None

        row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
        if row is None:
            raise ClientNotFoundError from None
        link, client = row

        for key, value in patch.items():
            if key in _CLIENT_FIELDS:
                if key == "email" and value is not None:
                    value = str(value).lower()
                setattr(client, key, value)
            elif key in _LINK_FIELDS:
                setattr(link, key, value)

        await self._client_repo.session.flush()
        await self._client_repo.session.refresh(client)
        await self._client_repo.session.refresh(link)

        return ClientWithLinkResponse(
            client=ClientSchema.model_validate(client),
            link=MasterClientOut.model_validate(link),
        )


def get_update_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> UpdateClientUseCase:
    return UpdateClientUseCase(client_repo)
