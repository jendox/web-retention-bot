from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.user import User
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceSchema
from app.use_cases.clients.exceptions import ClientMasterLinkNotFoundError

__all__ = ["ListMasterServicesForClientUseCase", "get_list_master_services_for_client_use_case"]

logger = get_logger("app.client")


class ListMasterServicesForClientUseCase:
    def __init__(self, client_repo: ClientRepository, service_repo: ServiceRepository) -> None:
        self._client_repo = client_repo
        self._service_repo = service_repo

    async def __call__(self, *, user: User, master_id: UUID) -> list[ServiceSchema]:
        with log_context(use_case="list_master_services_for_client", master_id=str(master_id)):
            link_row = await self._client_repo.get_linked_client_for_master_user(master_id, user.id)
            if link_row is None:
                raise ClientMasterLinkNotFoundError()

            services = await self._service_repo.list_for_master(master_id)
            return [ServiceSchema.model_validate(service) for service in services if service.is_active]


def get_list_master_services_for_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> ListMasterServicesForClientUseCase:
    return ListMasterServicesForClientUseCase(client_repo, service_repo)
