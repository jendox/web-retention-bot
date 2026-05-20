from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger
from app.models.user import User
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientMasterLinkUpdate, ClientMyMasterItem
from app.schemas.client_master import client_master_item

from .exceptions import ClientMasterLinkError, ClientNothingToUpdateError

logger = get_logger("app.client")


class UpdateClientMasterLinkUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(
        self,
        user: User,
        master_id: UUID,
        payload: ClientMasterLinkUpdate,
    ) -> ClientMyMasterItem:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            logger.warning("failed", reason="empty_patch")
            raise ClientNothingToUpdateError from None

        link_row = await self._client_repo.get_linked_client_for_master_user(master_id, user.id)
        if link_row is None:
            raise ClientMasterLinkError()

        link, client = link_row
        if "client_alias" in patch:
            link.client_alias = patch["client_alias"]
            await self._client_repo.flush()

        rows = await self._client_repo.list_masters_for_user_clients(user.id)
        for master, updated_link, row_client in rows:
            if master.id == master_id and row_client.id == client.id:
                return client_master_item(
                    master,
                    updated_link,
                    client_id=row_client.id,
                    client_display_name=row_client.display_name,
                )

        raise ClientMasterLinkError()


def get_update_client_master_link_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> UpdateClientMasterLinkUseCase:
    return UpdateClientMasterLinkUseCase(client_repo)
