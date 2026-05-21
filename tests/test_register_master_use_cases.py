import uuid
from datetime import UTC, datetime, time
from types import SimpleNamespace

import pytest

from app.schemas.auth import RegisterMasterPayload
from app.services.schedule_defaults import default_weekly_schedule_days
from app.use_cases.auth.exceptions import UserAlreadyExistsError
from app.use_cases.auth.register import RegisterMasterAccountUseCase


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


def _user_model(user_id: uuid.UUID, email: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email=email,
        created_at=datetime.now(UTC),
        email_verified_at=None,
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
        self.created_master = None

    async def get_by_user_id(self, user_id):
        return self.existing_master

    async def create(self, *, user_id, display_name, contact_email=None):
        self.created_with = {
            "user_id": user_id,
            "display_name": display_name,
            "contact_email": contact_email,
        }
        self.created_master = _master_profile(uuid.uuid4(), user_id)
        return self.created_master


class FakeScheduleRepository:
    def __init__(self) -> None:
        self.added_weekly_days = None

    async def add_weekly_days(self, days):
        self.added_weekly_days = days


class FakeUserRepository:
    def __init__(self, existing_user=None) -> None:
        self.existing_user = existing_user
        self.created_with = None
        self.created_user = None

    async def get_by_email(self, email):
        return self.existing_user

    async def create(self, *, email, password_hash):
        self.created_with = {
            "email": email,
            "password_hash": password_hash,
        }
        self.created_user = _user_model(uuid.uuid4(), email)
        return self.created_user


class FakeNotificationDispatcher:
    def __init__(self) -> None:
        self.email_verification_sent_to = None

    async def dispatch_email_verification(self, *, user_id, to_email):
        self.email_verification_sent_to = {
            "user_id": user_id,
            "to_email": to_email,
        }


def _payload(email: str = "MASTER@Example.COM") -> RegisterMasterPayload:
    return RegisterMasterPayload(
        email=email,
        password="longpassword1",
        master_display_name="Master",
    )


async def test_register_master_creates_default_weekly_schedule_for_new_master():
    user_repo = FakeUserRepository()
    master_repo = FakeMasterRepository()
    schedule_repo = FakeScheduleRepository()
    dispatcher = FakeNotificationDispatcher()
    use_case = RegisterMasterAccountUseCase(user_repo, master_repo, schedule_repo, dispatcher)

    result = await use_case(_payload())

    assert result.id == user_repo.created_user.id
    assert result.email == "master@example.com"
    assert result.email_verified is False
    assert user_repo.created_with is not None
    assert user_repo.created_with["email"] == "master@example.com"
    assert master_repo.created_with == {
        "user_id": user_repo.created_user.id,
        "display_name": "Master",
        "contact_email": "master@example.com",
    }
    assert schedule_repo.added_weekly_days is not None
    assert {day.master_id for day in schedule_repo.added_weekly_days} == {master_repo.created_master.id}
    assert [day.weekday for day in schedule_repo.added_weekly_days] == [0, 1, 2, 3, 4]
    assert dispatcher.email_verification_sent_to == {
        "user_id": user_repo.created_user.id,
        "to_email": "master@example.com",
    }


async def test_register_master_rejects_existing_user_email():
    existing_user = _user_model(uuid.uuid4(), "master@example.com")
    user_repo = FakeUserRepository(existing_user=existing_user)
    master_repo = FakeMasterRepository()
    schedule_repo = FakeScheduleRepository()
    dispatcher = FakeNotificationDispatcher()
    use_case = RegisterMasterAccountUseCase(user_repo, master_repo, schedule_repo, dispatcher)

    with pytest.raises(UserAlreadyExistsError):
        await use_case(_payload("master@example.com"))

    assert master_repo.created_with is None
    assert schedule_repo.added_weekly_days is None
    assert dispatcher.email_verification_sent_to is None
