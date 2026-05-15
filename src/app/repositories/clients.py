"""Client + linkage persistence."""

from uuid import UUID

from sqlalchemy import select

from app.models.client import Client, MasterClient
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository):
    async def create(self, client: Client) -> Client:
        self.session.add(client)
        await self.session.flush()
        return client

    async def master_clients_with_clients(self, master_id: UUID) -> list[tuple[MasterClient, Client]]:
        stmt = (
            select(MasterClient, Client)
            .join(Client, MasterClient.client_id == Client.id)
            .where(MasterClient.master_id == master_id)
        )
        rows = await self.session.execute(stmt)
        return list(rows.all())

    async def create_link(self, link: MasterClient) -> MasterClient:
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
