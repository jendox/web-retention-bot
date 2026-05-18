import uuid
from types import SimpleNamespace

import pytest

from app.schemas.client import ClientUpdate
from app.use_cases.clients.exceptions import ClientEmailLockedError, ClientNameLockedError
from app.use_cases.clients.list_clients import ListClientsUseCase
from app.use_cases.clients.update_client import UpdateClientUseCase


class FakeSession:
    async def flush(self):
        return None

    async def refresh(self, obj):
        return obj


class FakeClientRepo:
    def __init__(self, row):
        self.row = row
        self.session = FakeSession()

    async def get_link_with_client(self, master_id, client_id):
        return self.row

    async def flush(self):
        await self.session.flush()

    async def refresh(self, obj):
        await self.session.refresh(obj)


class FakeListClientRepo:
    def __init__(self):
        self.count_search = None
        self.page_search = None
        self.link = SimpleNamespace(
            id=uuid.uuid4(),
            alias="VIP",
            notes=None,
            invitation_status="LINKED",
            linked_account_email=None,
            invite_email_mismatch=False,
        )
        self.client = SimpleNamespace(
            id=uuid.uuid4(),
            display_name="Anna Client",
            phone="+375291112233",
            email="anna@example.com",
            user_id=None,
        )

    async def count_clients_for_master(self, master_id, *, search=None):
        self.count_search = search
        return 1

    async def master_clients_with_clients_page(self, master_id, *, limit, offset, search=None):
        self.page_search = search
        return [(self.link, self.client)]


async def test_update_client_rejects_email_change_when_linked_email_is_locked():
    link = SimpleNamespace(
        id=uuid.uuid4(),
        alias=None,
        notes=None,
        invitation_status="LINKED",
        linked_account_email="client@example.com",
        invite_email_mismatch=False,
    )
    client = SimpleNamespace(
        id=uuid.uuid4(),
        display_name="Client",
        phone=None,
        email="client@example.com",
        user_id=uuid.uuid4(),
    )
    use_case = UpdateClientUseCase(FakeClientRepo((link, client)))

    with pytest.raises(ClientEmailLockedError):
        await use_case(
            uuid.uuid4(),
            client.id,
            ClientUpdate(email="other@example.com"),
        )

    assert client.email == "client@example.com"


async def test_update_client_allows_mismatch_email_fix_and_clears_flag():
    link = SimpleNamespace(
        id=uuid.uuid4(),
        alias=None,
        notes=None,
        invitation_status="LINKED",
        linked_account_email="client@example.com",
        invite_email_mismatch=True,
    )
    client = SimpleNamespace(
        id=uuid.uuid4(),
        display_name="Client",
        phone=None,
        email="old@example.com",
        user_id=uuid.uuid4(),
    )
    use_case = UpdateClientUseCase(FakeClientRepo((link, client)))

    out = await use_case(
        uuid.uuid4(),
        client.id,
        ClientUpdate(email="CLIENT@example.com"),
    )

    assert client.email == "client@example.com"
    assert link.invite_email_mismatch is False
    assert out.client.email == "client@example.com"
    assert out.link.invite_email_mismatch is False


async def test_update_client_rejects_name_change_when_client_is_linked():
    link = SimpleNamespace(
        id=uuid.uuid4(),
        alias=None,
        notes=None,
        invitation_status="LINKED",
        linked_account_email="client@example.com",
        invite_email_mismatch=False,
    )
    client = SimpleNamespace(
        id=uuid.uuid4(),
        display_name="Client",
        phone=None,
        email="client@example.com",
        user_id=uuid.uuid4(),
    )
    use_case = UpdateClientUseCase(FakeClientRepo((link, client)))

    with pytest.raises(ClientNameLockedError):
        await use_case(
            uuid.uuid4(),
            client.id,
            ClientUpdate(display_name="Other name"),
        )

    assert client.display_name == "Client"


async def test_list_clients_normalizes_search_and_passes_it_to_repo():
    repo = FakeListClientRepo()
    use_case = ListClientsUseCase(repo)
    pagination = SimpleNamespace(page=1, page_size=10, offset=0)

    out = await use_case(uuid.uuid4(), pagination, search="  Anna  ")

    assert repo.count_search == "Anna"
    assert repo.page_search == "Anna"
    assert out.total == 1
    assert out.items[0].client.display_name == "Anna Client"
