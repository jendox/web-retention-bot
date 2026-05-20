import uuid
from datetime import UTC, datetime, time
from types import SimpleNamespace

from app.schemas.user import UserSchema
from app.services.schedule_defaults import default_weekly_schedule_days
from app.use_cases.auth.register_master import RegisterMasterUseCase


def test_default_weekly_schedule_days_are_weekdays_10_to_18():
    master_id = uuid.uuid4()

    days = default_weekly_schedule_days(master_id)

    assert [
        (day.weekday, day.intervals[0].start_time, day.intervals[0].end_time)
        for day in days
    ] == [
        (0, time(10, 0), time(18, 0)),
        (1, time(10, 0), time(18, 0)),
        (2, time(10, 0), time(18, 0)),
        (3, time(10, 0), time(18, 0)),
        (4, time(10, 0), time(18, 0)),
    ]
    assert {day.master_id for day in days} == {master_id}


def _user_schema() -> UserSchema:
    return UserSchema(
        id=uuid.uuid4(),
        email="master@example.com",
        created_at=datetime.now(UTC),
        is_active=True,
    )


def _master_profile(master_id: uuid.UUID, user_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=master_id,
        user_id=user_id,
        display_name="Master",
        public_slug=None,
        timezone="UTC",
        default_currency=None,
    )


class FakeMasterRepository:
    def __init__(self, existing_master=None) -> None:
        self.existing_master = existing_master
        self.created_with = None

    async def get_by_user_id(self, user_id):
        return self.existing_master

    async def create(self, *, user_id, display_name, contact_email=None):
        self.created_with = {
            "user_id": user_id,
            "display_name": display_name,
            "contact_email": contact_email,
        }
        return _master_profile(uuid.uuid4(), user_id)


class FakeScheduleRepository:
    def __init__(self) -> None:
        self.added_weekly_days = None

    async def add_weekly_days(self, days):
        self.added_weekly_days = days


async def test_register_master_creates_default_weekly_schedule_for_new_master():
    user = _user_schema()
    master_repo = FakeMasterRepository()
    schedule_repo = FakeScheduleRepository()
    use_case = RegisterMasterUseCase(master_repo, schedule_repo)

    master = await use_case(user, display_name="Master")

    assert master.display_name == "Master"
    assert master_repo.created_with == {
        "user_id": user.id,
        "display_name": "Master",
        "contact_email": "master@example.com",
    }
    assert schedule_repo.added_weekly_days is not None
    assert {day.master_id for day in schedule_repo.added_weekly_days} == {master.id}
    assert [day.weekday for day in schedule_repo.added_weekly_days] == [0, 1, 2, 3, 4]


async def test_register_master_does_not_create_default_schedule_for_existing_master():
    user = _user_schema()
    existing_master = _master_profile(uuid.uuid4(), user.id)
    master_repo = FakeMasterRepository(existing_master=existing_master)
    schedule_repo = FakeScheduleRepository()
    use_case = RegisterMasterUseCase(master_repo, schedule_repo)

    master = await use_case(user, display_name="Ignored")

    assert master.id == existing_master.id
    assert master_repo.created_with is None
    assert schedule_repo.added_weekly_days is None
