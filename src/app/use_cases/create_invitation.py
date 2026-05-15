import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.repositories.invitations import InvitationRepository


async def create_invitation_use_case(
    session: AsyncSession,
    *,
    master_id: UUID,
    expires_hours: int,
    target_email: str | None,
) -> Invitation:
    invites = InvitationRepository(session)
    token = secrets.token_urlsafe(48)[:64]
    invite = Invitation(
        master_id=master_id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        target_email=target_email,
    )
    return await invites.create_invite(invite)
