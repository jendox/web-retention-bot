from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import InvitationStatus
from app.models.user import User
from app.repositories.clients import ClientRepository
from app.repositories.invitations import InvitationRepository
from app.schemas.invitation import InvitationAccept
from app.services.notifications.dispatcher import NotificationDispatcher


async def accept_invitation_use_case(
    session: AsyncSession,
    dispatcher: NotificationDispatcher,
    token: str,
    payload: InvitationAccept,
    user: User,
) -> tuple[UUID, bool]:
    invites = InvitationRepository(session)
    clients = ClientRepository(session)
    invite = await invites.get_by_token(token)
    if not invite:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found") from None
    if invite.revoked_at is not None:
        raise HTTPException(status.HTTP_410_GONE, detail="Invitation revoked") from None
    if invite.accepted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Invitation already accepted") from None
    if invite.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_410_GONE, detail="Invitation expired") from None

    master_profile = invite.master
    if master_profile.user_id == user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot accept your own invitation.",
        ) from None

    account_email = user.email.strip().lower()
    mismatch = False

    if invite.target_client_id is not None:
        row = await clients.get_link_with_client(master_id=invite.master_id, client_id=invite.target_client_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found.") from None
        link, client = row
        if invite.target_client_id != client.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invitation client mismatch.") from None
        if client.user_id is not None and client.user_id != user.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="This client card is already linked to another account.",
            ) from None

        stored_profile_email = client.email.strip().lower() if client.email else None

        client.display_name = payload.display_name.strip()
        client.phone = payload.phone.strip() if payload.phone and payload.phone.strip() else None
        client.user_id = user.id

        link.linked_account_email = account_email
        if stored_profile_email and stored_profile_email != account_email:
            mismatch = True
            link.invite_email_mismatch = True
            await dispatcher.dispatch_invite_email_mismatch_for_master(
                master_user_id=master_profile.user_id,
                master_profile_id=master_profile.id,
                client_id=client.id,
                profile_email=stored_profile_email,
                account_email=account_email,
                client_display_name=client.display_name,
            )
        else:
            link.invite_email_mismatch = False
            client.email = account_email
    else:
        existing = await clients.client_ids_for_master_user(invite.master_id, user.id)
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="You are already linked to this master.",
            ) from None

        client = await clients.create(
            display_name=payload.display_name.strip(),
            phone=payload.phone.strip() if payload.phone and payload.phone.strip() else None,
            email=account_email,
        )
        client.user_id = user.id
        await session.flush()

        link = await clients.create_link(
            master_id=invite.master_id,
            client_id=client.id,
            invitation_status=InvitationStatus.LINKED,
        )
        link.linked_account_email = account_email
        link.invite_email_mismatch = False

    invite.linked_client_id = client.id
    invite.accepted_at = datetime.now(UTC)
    await session.flush()
    return client.id, mismatch
