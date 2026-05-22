import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from app.api.deps import require_master_profile
from app.main import app
from app.schemas.service import ServiceUpdate
from app.use_cases.services.delete_service import DeleteServiceUseCase, get_delete_service_use_case
from app.use_cases.services.exceptions import (
    ServiceEmptyPatchError,
    ServiceHasBookingsError,
    ServiceNoFieldsToUpdateError,
    ServiceNotFoundError,
)
from app.use_cases.services.get_service import get_get_service_use_case
from app.use_cases.services.list_services import ListServicesUseCase
from app.use_cases.services.update_service import UpdateServiceUseCase


class FakeGetServiceUseCase:
    async def __call__(self, master, service_id):
        raise ServiceNotFoundError()


class FakeDeleteServiceUseCase:
    async def execute(self, master, service_id):
        raise ServiceHasBookingsError()


class FakeListServiceRepo:
    def __init__(self):
        self.count_search = None
        self.page_search = None
        self.service = SimpleNamespace(
            id=uuid.uuid4(),
            master_id=uuid.uuid4(),
            name="Manicure",
            description=None,
            duration_min=90,
            price=Decimal("75.00"),
            currency="BYN",
            is_active=True,
            sort_order=0,
        )

    async def count_for_master(self, master_id, *, is_active, search=None):
        self.count_search = search
        return 1

    async def list_page_for_master(self, master_id, *, limit, offset, is_active, search=None):
        self.page_search = search
        return [self.service]


async def test_list_services_normalizes_search_and_passes_it_to_repo():
    repo = FakeListServiceRepo()
    use_case = ListServicesUseCase(repo)
    master = SimpleNamespace(id=uuid.uuid4())
    pagination = SimpleNamespace(page=1, page_size=10, offset=0)

    out = await use_case(master, pagination, is_active=True, search="  Mani  ")

    assert repo.count_search == "Mani"
    assert repo.page_search == "Mani"
    assert out.total == 1
    assert out.items[0].name == "Manicure"


async def test_update_service_empty_patch_raises_domain_error():
    use_case = UpdateServiceUseCase(SimpleNamespace())
    master = SimpleNamespace(id=uuid.uuid4())

    with pytest.raises(ServiceEmptyPatchError) as exc_info:
        await use_case(master, uuid.uuid4(), ServiceUpdate())

    assert exc_info.value.code == "services.empty_patch"
    assert exc_info.value.message == "No fields to update."


async def test_update_service_without_applicable_fields_raises_domain_error():
    class Repo:
        async def get_for_master(self, service_id, master_id):
            return SimpleNamespace(apply_patch=lambda patch: False)

    use_case = UpdateServiceUseCase(Repo())
    master = SimpleNamespace(id=uuid.uuid4())

    with pytest.raises(ServiceNoFieldsToUpdateError) as exc_info:
        await use_case(master, uuid.uuid4(), ServiceUpdate(name=None))

    assert exc_info.value.code == "services.no_fields_to_update"
    assert exc_info.value.message == "No fields to update."


async def test_delete_service_with_bookings_raises_domain_error():
    class Repo:
        async def get_for_master(self, service_id, master_id):
            return SimpleNamespace()

        async def count_bookings_for_service(self, service_id):
            return 1

    use_case = DeleteServiceUseCase(Repo())
    master = SimpleNamespace(id=uuid.uuid4())

    with pytest.raises(ServiceHasBookingsError) as exc_info:
        await use_case.execute(master, uuid.uuid4())

    assert exc_info.value.code == "services.has_bookings"
    assert exc_info.value.message == "Service has bookings and cannot be deleted."


def test_get_service_route_returns_app_error_contract():
    app.dependency_overrides[require_master_profile] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_get_service_use_case] = FakeGetServiceUseCase
    try:
        with TestClient(app) as client:
            resp = client.get(f"/api/master/services/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(require_master_profile, None)
        app.dependency_overrides.pop(get_get_service_use_case, None)

    assert resp.status_code == 404
    assert resp.json() == {
        "code": "services.not_found",
        "detail": "Service not found.",
    }


def test_delete_service_route_returns_conflict_app_error_contract():
    app.dependency_overrides[require_master_profile] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_delete_service_use_case] = FakeDeleteServiceUseCase
    try:
        with TestClient(app) as client:
            client.cookies.set("csrf_token", "token")
            resp = client.delete(
                f"/api/master/services/{uuid.uuid4()}",
                headers={"X-CSRF-Token": "token"},
            )
    finally:
        app.dependency_overrides.pop(require_master_profile, None)
        app.dependency_overrides.pop(get_delete_service_use_case, None)

    assert resp.status_code == 409
    assert resp.json() == {
        "code": "services.has_bookings",
        "detail": "Service has bookings and cannot be deleted.",
    }
