from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.invitation import Invitation
from app.models.master import MasterProfile
from app.repositories.base import BaseRepository

__all__ = ["InvitationRepository", "InvitationNotFound", "get_invitation_repo"]


class InvitationNotFound(Exception): ...


class InvitationRepository(BaseRepository):
    async def create_invite(
        self,
        *,
        master_id: UUID,
        token: str,
        expires_at: datetime,
        target_email: str | None = None,
        target_client_id: UUID | None = None,
    ) -> Invitation:
        invite = Invitation(
            master_id=master_id,
            token=token,
            expires_at=expires_at,
            target_email=target_email,
            target_client_id=target_client_id,
        )
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


def get_invitation_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvitationRepository:
    return InvitationRepository(session)
