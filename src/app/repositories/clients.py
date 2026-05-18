from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.booking import Booking
from app.models.client import Client, InvitationStatus, MasterClient
from app.models.invitation import Invitation
from app.models.master import MasterProfile
from app.repositories.base import BaseRepository

__all__ = [
    "ClientRepository",
    "ClientNotFound",
    "get_client_repo",
]


class ClientNotFound(Exception): ...


class ClientRepository(BaseRepository):
    async def create(
        self,
        *,
        display_name: str,
        phone: str | None = None,
        email: str | None = None,
    ) -> Client:
        client = Client(
            display_name=display_name,
            phone=phone,
            email=email,
        )
        self.session.add(client)
        await self.session.flush()
        return client

    @staticmethod
    def _search_filter(search: str):
        pattern = f"%{search.lower()}%"
        return or_(
            func.lower(Client.display_name).like(pattern),
            func.lower(Client.phone).like(pattern),
            func.lower(Client.email).like(pattern),
            func.lower(MasterClient.alias).like(pattern),
            func.lower(MasterClient.linked_account_email).like(pattern),
        )

    async def count_clients_for_master(self, master_id: UUID, *, search: str | None = None) -> int:
        stmt = select(func.count()).select_from(MasterClient).where(MasterClient.master_id == master_id)
        if search:
            stmt = stmt.join(Client, MasterClient.client_id == Client.id).where(self._search_filter(search))
        n = (await self.session.execute(stmt)).scalar_one()
        return int(n)

    async def master_clients_with_clients_page(
        self,
        master_id: UUID,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
    ) -> list[tuple[MasterClient, Client]]:
        stmt = (
            select(MasterClient, Client)
            .join(Client, MasterClient.client_id == Client.id)
            .where(MasterClient.master_id == master_id)
            .order_by(func.lower(Client.display_name).asc(), Client.id.asc())
            .limit(limit)
            .offset(offset)
        )
        if search:
            stmt = stmt.where(self._search_filter(search))
        rows = await self.session.execute(stmt)
        return list(rows.all())

    async def create_link(
        self,
        *,
        master_id: UUID,
        client_id: UUID,
        invitation_status: InvitationStatus = InvitationStatus.LINKED,
        alias: str | None = None,
        notes: str | None = None,
    ) -> MasterClient:
        link = MasterClient(
            master_id=master_id,
            client_id=client_id,
            invitation_status=invitation_status,
            alias=alias,
            notes=notes,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def get_client(self, client_id: UUID) -> Client | None:
        return await self.session.get(Client, client_id)

    async def link_exists(self, master_id: UUID, client_id: UUID) -> bool:
        stmt = (
            select(MasterClient.id)
            .where(
                MasterClient.master_id == master_id,
                MasterClient.client_id == client_id,
            )
            .limit(1)
        )
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none() is not None

    async def get_link_with_client(self, master_id: UUID, client_id: UUID) -> tuple[MasterClient, Client] | None:
        stmt = (
            select(MasterClient, Client)
            .join(Client, MasterClient.client_id == Client.id)
            .where(MasterClient.master_id == master_id, MasterClient.client_id == client_id)
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def unlinked_clients_by_master_email(
        self,
        *,
        master_id: UUID,
        email: str,
        limit: int = 2,
    ) -> list[tuple[MasterClient, Client]]:
        stmt = (
            select(MasterClient, Client)
            .join(Client, MasterClient.client_id == Client.id)
            .where(
                MasterClient.master_id == master_id,
                Client.user_id.is_(None),
                func.lower(Client.email) == email.lower(),
            )
            .order_by(Client.id.asc())
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in rows.all()]

    async def list_masters_for_user_clients(self, user_id: UUID) -> list[tuple[MasterProfile, MasterClient, Client]]:
        stmt = (
            select(MasterProfile, MasterClient, Client)
            .join(MasterClient, MasterClient.master_id == MasterProfile.id)
            .join(Client, MasterClient.client_id == Client.id)
            .where(
                Client.user_id == user_id,
                MasterClient.invitation_status != InvitationStatus.REVOKED,
            )
            .order_by(func.lower(MasterProfile.display_name).asc(), Client.id.asc())
        )
        rows = await self.session.execute(stmt)
        return [(row[0], row[1], row[2]) for row in rows.all()]

    async def client_ids_for_master_user(self, master_id: UUID, user_id: UUID) -> list[UUID]:
        stmt = select(Client.id).join(MasterClient).where(
            MasterClient.master_id == master_id,
            Client.user_id == user_id,
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_bookings_for_client(self, client_id: UUID) -> int:
        stmt = select(func.count()).select_from(Booking).where(Booking.client_id == client_id)
        count = (await self.session.execute(stmt)).scalar_one()
        return int(count)

    async def has_invitation_blocking_client(self, client_id: UUID) -> bool:
        now = datetime.now(UTC)
        stmt = (
            select(Invitation.id)
            .where(
                or_(
                    Invitation.linked_client_id == client_id,
                    and_(
                        Invitation.target_client_id == client_id,
                        Invitation.accepted_at.is_(None),
                        Invitation.revoked_at.is_(None),
                        Invitation.expires_at > now,
                    ),
                ),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def delete_client(self, client: Client) -> None:
        await self.session.delete(client)
        await self.session.flush()


def get_client_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientRepository:
    return ClientRepository(session)
