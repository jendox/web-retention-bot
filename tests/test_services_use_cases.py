import uuid
from decimal import Decimal
from types import SimpleNamespace

from app.use_cases.services.list_services import ListServicesUseCase


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
