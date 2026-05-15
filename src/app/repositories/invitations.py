"""Invitation persistence."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.invitation import Invitation
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository):
    async def create_invite(self, invite: Invitation) -> Invitation:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = (
            select(Invitation)
            .options(selectinload(Invitation.master))
            .where(Invitation.token == token)
            .limit(1)
        )
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()
