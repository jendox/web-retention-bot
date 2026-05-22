import uuid
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from app.api.deps import require_master_profile, require_user
from app.main import app
from app.schemas.client import ClientProfileUpdate, ClientUpdate
from app.use_cases.clients.delete_client import DeleteClientUseCase, get_delete_client_use_case
from app.use_cases.clients.exceptions import (
    ClientEmailLockedError,
    ClientHasBookingsError,
    ClientNameLockedError,
    ClientNotFoundError,
    ClientNothingToUpdateError,
    ClientProfileNotFoundError,
)
from app.use_cases.clients.get_client import get_get_client_use_case
from app.use_cases.clients.get_client_profile import GetClientProfileUseCase, get_get_client_profile_use_case
from app.use_cases.clients.list_clients import ListClientsUseCase
from app.use_cases.clients.update_client import UpdateClientUseCase
from app.use_cases.clients.update_client_profile import UpdateClientProfileUseCase


class FakeSession:
    async def flush(self):
        return None

    async def refresh(self, obj):
        return obj


class FakePatchable(SimpleNamespace):
    def apply_patch(self, patch):
        for key, value in patch.items():
            setattr(self, key, value)
        return True


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
    link = FakePatchable(
        id=uuid.uuid4(),
        alias=None,
        notes=None,
        invitation_status="LINKED",
        linked_account_email="client@example.com",
        invite_email_mismatch=False,
    )
    client = FakePatchable(
        id=uuid.uuid4(),
        display_name="Client",
        phone=None,
        email="client@example.com",
        user_id=uuid.uuid4(),
    )
    use_case = UpdateClientUseCase(FakeClientRepo((link, client)), FakeBookingRepo())

    with pytest.raises(ClientEmailLockedError):
        await use_case(
            master_id=uuid.uuid4(),
            client_id=client.id,
            payload=ClientUpdate(email="other@example.com"),
        )

    assert client.email == "client@example.com"


async def test_update_client_allows_mismatch_email_fix_and_clears_flag():
    link = FakePatchable(
        id=uuid.uuid4(),
        alias=None,
        notes=None,
        invitation_status="LINKED",
        linked_account_email="client@example.com",
        invite_email_mismatch=True,
    )
    client = FakePatchable(
        id=uuid.uuid4(),
        display_name="Client",
        phone=None,
        email="old@example.com",
        user_id=uuid.uuid4(),
    )
    use_case = UpdateClientUseCase(FakeClientRepo((link, client)), FakeBookingRepo())

    out = await use_case(
        master_id=uuid.uuid4(),
        client_id=client.id,
        payload=ClientUpdate(email="CLIENT@example.com"),
    )

    assert client.email == "client@example.com"
    assert link.invite_email_mismatch is False
    assert out.client.email == "client@example.com"
    assert out.link.invite_email_mismatch is False


async def test_update_client_rejects_name_change_when_client_is_linked():
    link = FakePatchable(
        id=uuid.uuid4(),
        alias=None,
        notes=None,
        invitation_status="LINKED",
        linked_account_email="client@example.com",
        invite_email_mismatch=False,
    )
    client = FakePatchable(
        id=uuid.uuid4(),
        display_name="Client",
        phone=None,
        email="client@example.com",
        user_id=uuid.uuid4(),
    )
    use_case = UpdateClientUseCase(FakeClientRepo((link, client)), FakeBookingRepo())

    with pytest.raises(ClientNameLockedError):
        await use_case(
            master_id=uuid.uuid4(),
            client_id=client.id,
            payload=ClientUpdate(display_name="Other name"),
        )

    assert client.display_name == "Client"


class FakeBookingRepo:
    async def no_show_counts_by_client_ids(self, *, master_id, client_ids):
        return {}

    async def completed_counts_by_client_ids(self, *, master_id, client_ids):
        return {}


async def test_list_clients_normalizes_search_and_passes_it_to_repo():
    repo = FakeListClientRepo()
    use_case = ListClientsUseCase(repo, FakeBookingRepo())
    pagination = SimpleNamespace(page=1, page_size=10, offset=0)

    out = await use_case(uuid.uuid4(), pagination, search="  Anna  ")

    assert repo.count_search == "Anna"
    assert repo.page_search == "Anna"
    assert out.total == 1
    assert out.items[0].client.display_name == "Anna Client"
    assert out.items[0].booking_stats.no_show_count == 0


class FakeBookingRepoWithNoShows(FakeBookingRepo):
    async def no_show_counts_by_client_ids(self, *, master_id, client_ids):
        return {client_ids[0]: 3}


class FakeGetClientUseCase:
    async def __call__(self, master_id, client_id):
        raise ClientNotFoundError()


class FakeDeleteClientUseCase:
    async def __call__(self, *, master_id, client_id):
        raise ClientHasBookingsError()


class FakeGetClientProfileUseCase:
    async def __call__(self, user_id):
        raise ClientProfileNotFoundError()


async def test_list_clients_attaches_no_show_stats():
    repo = FakeListClientRepo()
    use_case = ListClientsUseCase(repo, FakeBookingRepoWithNoShows())
    pagination = SimpleNamespace(page=1, page_size=10, offset=0)

    out = await use_case(uuid.uuid4(), pagination)

    assert out.items[0].booking_stats.no_show_count == 3


async def test_update_client_empty_patch_raises_domain_error():
    use_case = UpdateClientUseCase(FakeClientRepo(None), FakeBookingRepo())

    with pytest.raises(ClientNothingToUpdateError) as exc_info:
        await use_case(master_id=uuid.uuid4(), client_id=uuid.uuid4(), payload=ClientUpdate())

    assert exc_info.value.code == "clients.empty_patch"
    assert exc_info.value.message == "No fields to update."


async def test_delete_client_with_bookings_raises_domain_error():
    client = SimpleNamespace(id=uuid.uuid4())

    class Repo:
        async def get_link_with_client(self, master_id, client_id):
            return SimpleNamespace(), client

        async def count_bookings_for_client(self, client_id):
            return 1

    use_case = DeleteClientUseCase(Repo())

    with pytest.raises(ClientHasBookingsError) as exc_info:
        await use_case(master_id=uuid.uuid4(), client_id=client.id)

    assert exc_info.value.code == "clients.has_bookings"
    assert exc_info.value.message == "Client has bookings and cannot be deleted."


def test_get_client_route_returns_app_error_contract():
    app.dependency_overrides[require_master_profile] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_get_client_use_case] = FakeGetClientUseCase
    try:
        with TestClient(app) as client:
            resp = client.get(f"/api/master/clients/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(require_master_profile, None)
        app.dependency_overrides.pop(get_get_client_use_case, None)

    assert resp.status_code == 404
    assert resp.json() == {
        "code": "clients.not_found",
        "detail": "Client not found.",
    }


def test_delete_client_route_returns_conflict_app_error_contract():
    app.dependency_overrides[require_master_profile] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_delete_client_use_case] = FakeDeleteClientUseCase
    try:
        with TestClient(app) as client:
            client.cookies.set("csrf_token", "token")
            resp = client.delete(
                f"/api/master/clients/{uuid.uuid4()}",
                headers={"X-CSRF-Token": "token"},
            )
    finally:
        app.dependency_overrides.pop(require_master_profile, None)
        app.dependency_overrides.pop(get_delete_client_use_case, None)

    assert resp.status_code == 409
    assert resp.json() == {
        "code": "clients.has_bookings",
        "detail": "Client has bookings and cannot be deleted.",
    }


async def test_update_client_profile_without_profile_raises_domain_error():
    class Repo:
        async def list_client_profiles_for_user(self, user_id):
            return []

    use_case = UpdateClientProfileUseCase(Repo())

    with pytest.raises(ClientProfileNotFoundError) as exc_info:
        await use_case(user_id=uuid.uuid4(), payload=ClientProfileUpdate(display_name="Client"))

    assert exc_info.value.code == "clients.profile_not_found"
    assert exc_info.value.message == "Client profile not found"


async def test_get_client_profile_without_profile_raises_domain_error():
    class Repo:
        async def primary_client_profile_for_user(self, user_id):
            return None

    use_case = GetClientProfileUseCase(Repo())

    with pytest.raises(ClientProfileNotFoundError) as exc_info:
        await use_case(uuid.uuid4())

    assert exc_info.value.code == "clients.profile_not_found"
    assert exc_info.value.message == "Client profile not found"


def test_get_client_profile_route_returns_app_error_contract():
    app.dependency_overrides[require_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_get_client_profile_use_case] = FakeGetClientProfileUseCase
    try:
        with TestClient(app) as client:
            resp = client.get("/api/client/profile")
    finally:
        app.dependency_overrides.pop(require_user, None)
        app.dependency_overrides.pop(get_get_client_profile_use_case, None)

    assert resp.status_code == 404
    assert resp.json() == {
        "code": "clients.profile_not_found",
        "detail": "Client profile not found",
    }
