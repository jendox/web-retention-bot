from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.schemas.client import ClientMasterLinkUpdate
from app.schemas.client_master import client_master_item, master_label_for_client
from app.use_cases.clients.exceptions import ClientMasterLinkNotFoundError, ClientNothingToUpdateError
from app.use_cases.clients.update_client_master_link import UpdateClientMasterLinkUseCase


def test_master_label_for_client_prefers_client_alias():
    master = SimpleNamespace(display_name="Official Studio")
    link = SimpleNamespace(client_alias="  My Studio  ", alias=None)
    assert master_label_for_client(link, master) == "My Studio"


def test_master_label_for_client_falls_back_to_display_name():
    master = SimpleNamespace(display_name="Official Studio")
    link = SimpleNamespace(client_alias=None, alias=None)
    assert master_label_for_client(link, master) == "Official Studio"


def test_client_master_link_update_empty_alias_becomes_none():
    payload = ClientMasterLinkUpdate(client_alias="   ")
    assert payload.client_alias is None


def test_client_master_item_maps_contact_fields():
    master_id = uuid.uuid4()
    master = SimpleNamespace(
        id=master_id,
        display_name="Studio",
        public_slug="studio",
        contact_email="a@b.c",
        contact_phone="+1",
        telegram="@s",
    )
    link = SimpleNamespace(
        id=uuid.uuid4(),
        alias="Client A",
        client_alias="My Studio",
        invitation_status=SimpleNamespace(value="LINKED"),
    )
    client_id = uuid.uuid4()
    item = client_master_item(master, link, client_id=client_id, client_display_name="Elena")
    assert item.master_id == master_id
    assert item.client_alias == "My Studio"
    assert item.contact_email == "a@b.c"
    assert item.contact_phone == "+1"
    assert item.telegram == "@s"


@pytest.mark.asyncio
async def test_update_client_master_link_sets_alias():
    user_id = uuid.uuid4()
    master_id = uuid.uuid4()
    client_id = uuid.uuid4()

    master = SimpleNamespace(
        id=master_id,
        display_name="Studio",
        public_slug=None,
        contact_email="studio@example.com",
        contact_phone=None,
        telegram=None,
    )
    link = SimpleNamespace(
        id=uuid.uuid4(),
        alias=None,
        client_alias=None,
        invitation_status=SimpleNamespace(value="LINKED"),
    )
    client = SimpleNamespace(id=client_id, display_name="Client")

    class FakeClientRepo:
        def __init__(self) -> None:
            self.flushed = False

        async def get_linked_client_for_master_user(self, mid, uid):
            if mid == master_id and uid == user_id:
                return link, client
            return None

        async def flush(self) -> None:
            self.flushed = True

        async def list_masters_for_user_clients(self, uid):
            if uid == user_id:
                return [(master, link, client)]
            return []

    repo = FakeClientRepo()
    use_case = UpdateClientMasterLinkUseCase(repo)
    user = SimpleNamespace(id=user_id)

    result = await use_case(user, master_id, ClientMasterLinkUpdate(client_alias="My label"))

    assert link.client_alias == "My label"
    assert result.client_alias == "My label"
    assert repo.flushed is True


@pytest.mark.asyncio
async def test_update_client_master_link_requires_link():
    class FakeClientRepo:
        async def get_linked_client_for_master_user(self, *_a, **_k):
            return None

    use_case = UpdateClientMasterLinkUseCase(FakeClientRepo())
    with pytest.raises(ClientMasterLinkNotFoundError) as exc_info:
        await use_case(
            SimpleNamespace(id=uuid.uuid4()),
            uuid.uuid4(),
            ClientMasterLinkUpdate(client_alias="x"),
        )

    assert exc_info.value.code == "clients.master_link_not_found"
    assert exc_info.value.message == "Not linked to this master"


@pytest.mark.asyncio
async def test_update_client_master_link_rejects_empty_patch():
    class FakeClientRepo:
        async def get_linked_client_for_master_user(self, *_a, **_k):
            return SimpleNamespace(), SimpleNamespace()

    use_case = UpdateClientMasterLinkUseCase(FakeClientRepo())
    with pytest.raises(ClientNothingToUpdateError) as exc_info:
        await use_case(SimpleNamespace(id=uuid.uuid4()), uuid.uuid4(), ClientMasterLinkUpdate())

    assert exc_info.value.code == "clients.empty_patch"
    assert exc_info.value.message == "No fields to update."
