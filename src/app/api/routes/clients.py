from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_master_profile
from app.core.database import get_db_session
from app.models.client import Client, InvitationStatus, MasterClient
from app.models.master import MasterProfile
from app.repositories.clients import ClientRepository
from app.schemas.client import ClientCreate, ClientOut, MasterClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[dict])
async def list_clients(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> list[dict]:
    repo = ClientRepository(session)
    rows = await repo.master_clients_with_clients(master.id)
    return [
        {"link": MasterClientOut.model_validate(link), "client": ClientOut.model_validate(client)}
        for link, client in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
async def post_client(
    payload: ClientCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> dict:
    repo = ClientRepository(session)
    client = Client(
        display_name=payload.display_name,
        phone=payload.phone,
        email=str(payload.email).lower() if payload.email else None,
    )
    await repo.create(client)
    link = MasterClient(
        master_id=master.id,
        client_id=client.id,
        invitation_status=InvitationStatus.linked,
    )
    await repo.create_link(link)
    await session.refresh(client)
    return {"client": ClientOut.model_validate(client), "link": MasterClientOut.model_validate(link)}
