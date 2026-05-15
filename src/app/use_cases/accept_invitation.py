from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, InvitationStatus, MasterClient
from app.repositories.clients import ClientRepository
from app.repositories.invitations import InvitationRepository
from app.schemas.invitation import InvitationAccept


async def accept_invitation_use_case(session: AsyncSession, token: str, payload: InvitationAccept) -> UUID:
    invites = InvitationRepository(session)
    clients = ClientRepository(session)
    invite = await invites.get_by_token(token)
    if not invite:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invite.accepted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Invitation already accepted")
    if invite.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_410_GONE, detail="Invitation expired")

    client = Client(
        display_name=payload.display_name,
        phone=payload.phone,
        email=str(payload.email).lower() if payload.email else None,
    )
    await clients.create(client)

    master_link = MasterClient(
        master_id=invite.master_id,
        client_id=client.id,
        invitation_status=InvitationStatus.linked,
    )
    await clients.create_link(master_link)

    invite.linked_client_id = client.id
    invite.accepted_at = datetime.now(UTC)
    await session.flush()
    return client.id
