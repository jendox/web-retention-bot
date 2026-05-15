"""Invitation persistence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.invitation import Invitation
from app.models.master import MasterProfile
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository):
    async def create_invite(self, invite: Invitation) -> Invitation:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = (
            select(Invitation)
            .options(
                selectinload(Invitation.master).selectinload(MasterProfile.user),
                selectinload(Invitation.target_client),
            )
            .where(Invitation.token == token)
            .limit(1)
        )
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()

    async def find_active_pending_target_invite(self, master_id: UUID, client_id: UUID) -> Invitation | None:
        now = datetime.now(UTC)
        stmt = (
            select(Invitation)
            .where(
                Invitation.master_id == master_id,
                Invitation.target_client_id == client_id,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
                Invitation.expires_at > now,
            )
            .limit(1)
        )
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()

    async def revoke_pending_target_invites(self, master_id: UUID, client_id: UUID) -> None:
        now = datetime.now(UTC)
        stmt = select(Invitation).where(
            Invitation.master_id == master_id,
            Invitation.target_client_id == client_id,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
            Invitation.expires_at > now,
        )
        for inv in (await self.session.scalars(stmt)).all():
            inv.revoked_at = now
        await self.session.flush()
