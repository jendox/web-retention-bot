from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.clients import ClientNotFound, ClientRepository, get_client_repo
from app.repositories.invitations import InvitationRepository, get_invitation_repo
from app.schemas.invitation import InvitationOut

__all__ = [
    "CreateInvitationUseCase",
    "CreateInvitationError",
    "get_create_invitation_use_case",
]


class CreateInvitationError(Exception): ...


logger = get_logger("app.invitation")


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
        with log_context(
            use_case="create_invitation",
            master_id=str(master_id),
            target_client_id=str(target_client_id) if target_client_id else None,
        ):
            if target_client_id is not None:
                row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=target_client_id)
                if row is None:
                    logger.warning("failed", reason="client_not_found")
                    raise ClientNotFound("Client not found.") from None
                _link, client = row
                if client.user_id is not None:
                    logger.warning("failed", reason="client_already_linked", client_user_id=str(client.user_id))
                    raise CreateInvitationError("Client already has a login linked.") from None
                if replace:
                    await self._invite_repo.revoke_pending_target_invites(master_id, target_client_id)
                    logger.info("revoked_pending_target_invites")
                elif await self._invite_repo.find_active_pending_target_invite(master_id, target_client_id) is not None:
                    logger.warning("failed", reason="active_invitation_exists")
                    raise CreateInvitationError("An active invitation already exists for this client.") from None

            token = secrets.token_urlsafe(48)[:64]
            invite = await self._invite_repo.create_invite(
                master_id=master_id,
                token=token,
                expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
                target_email=target_email.lower() if target_email else None,
                target_client_id=target_client_id,
            )
            logger.info(
                "created",
                invitation_id=str(invite.id) if getattr(invite, "id", None) else None,
                invite_kind="client" if target_client_id else "open",
                expires_at=invite.expires_at.isoformat(),
            )

            return InvitationOut.model_validate(invite)


def get_create_invitation_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    invite_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
) -> CreateInvitationUseCase:
    return CreateInvitationUseCase(client_repo, invite_repo)
