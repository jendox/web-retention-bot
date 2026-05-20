from __future__ import annotations

from app.models.client import MasterClient
from app.models.master import MasterProfile
from app.schemas.client import ClientMyMasterItem


def client_master_item(
    master: MasterProfile,
    link: MasterClient,
    *,
    client_id,
    client_display_name: str,
) -> ClientMyMasterItem:
    return ClientMyMasterItem(
        master_id=master.id,
        display_name=master.display_name,
        public_slug=master.public_slug,
        link_id=link.id,
        invitation_status=link.invitation_status.value,
        client_id=client_id,
        client_display_name=client_display_name,
        alias=link.alias,
        client_alias=link.client_alias,
        contact_email=master.contact_email,
        contact_phone=master.contact_phone,
        telegram=master.telegram,
        viber=master.viber,
    )


def master_label_for_client(link: MasterClient, master: MasterProfile) -> str:
    if link.client_alias and link.client_alias.strip():
        return link.client_alias.strip()
    return master.display_name
