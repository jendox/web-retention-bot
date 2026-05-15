import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.repositories.clients import ClientRepository
from app.repositories.invitations import InvitationRepository


async def create_invitation_use_case(
    session: AsyncSession,
    *,
    master_id: UUID,
    expires_hours: int,
    target_email: str | None,
    target_client_id: UUID | None,
    replace: bool,
) -> Invitation:
    invites = InvitationRepository(session)
    clients = ClientRepository(session)
    if target_client_id is not None:
        row = await clients.get_link_with_client(master_id=master_id, client_id=target_client_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found.") from None
        _link, client = row
        if client.user_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Client already has a login linked.",
            ) from None
        if replace:
            await invites.revoke_pending_target_invites(master_id, target_client_id)
        elif await invites.find_active_pending_target_invite(master_id, target_client_id) is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="An active invitation already exists for this client.",
            ) from None

    token = secrets.token_urlsafe(48)[:64]
    invite = Invitation(
        master_id=master_id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        target_email=target_email.lower() if target_email else None,
        target_client_id=target_client_id,
    )
    return await invites.create_invite(invite)
