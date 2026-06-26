from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientMyMasterItem
from app.schemas.client_master import client_master_item

__all__ = ["ListClientMastersUseCase", "get_list_client_masters_use_case"]


class ListClientMastersUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, user_id: UUID) -> list[ClientMyMasterItem]:
        rows = await self._client_repo.list_masters_for_user_clients(user_id)
        return [
            client_master_item(
                master,
                link,
                client_id=client.id,
                client_display_name=client.display_name,
            )
            for master, link, client in rows
        ]


def get_list_client_masters_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> ListClientMastersUseCase:
    return ListClientMastersUseCase(client_repo)
