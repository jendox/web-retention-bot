from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.clients import ClientNotFound, ClientRepository, get_client_repo
from app.repositories.invitations import InvitationRepository, get_invitation_repo
from app.schemas.invitation import InvitationOut

__all__ = [
    "CreateInvitationUseCase",
    "CreateInvitationError",
    "get_create_invitation_use_case",
]


class CreateInvitationError(Exception): ...


class CreateInvitationUseCase:
    def __init__(
        self,
        client_repo: ClientRepository,
        invite_repo: InvitationRepository,
    ) -> None:
        self._client_repo = client_repo
        self._invite_repo = invite_repo

    async def __call__(
        self,
        *,
        master_id: UUID,
        expires_hours: int,
        target_email: str | None,
        target_client_id: UUID | None,
        replace: bool,
    ) -> InvitationOut:
        if target_client_id is not None:
            row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=target_client_id)
            if row is None:
                raise ClientNotFound("Client not found.") from None
            _link, client = row
            if client.user_id is not None:
                raise CreateInvitationError("Client already has a login linked.") from None
            if replace:
                await self._invite_repo.revoke_pending_target_invites(master_id, target_client_id)
            elif await self._invite_repo.find_active_pending_target_invite(master_id, target_client_id) is not None:
                raise CreateInvitationError("An active invitation already exists for this client.") from None

        token = secrets.token_urlsafe(48)[:64]
        invite = await self._invite_repo.create_invite(
            master_id=master_id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
            target_email=target_email.lower() if target_email else None,
            target_client_id=target_client_id,
        )

        return InvitationOut.model_validate(invite)


def get_create_invitation_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    invite_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
) -> CreateInvitationUseCase:
    return CreateInvitationUseCase(client_repo, invite_repo)
