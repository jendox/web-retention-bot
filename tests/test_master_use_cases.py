import uuid
from datetime import date, time
from types import SimpleNamespace

from app.core.currency import Currency
from app.schemas.master import MasterProfileUpdate
from app.use_cases.master.update_profile import UpdateMasterProfileUseCase
from app.use_cases.schedule.get_schedule import GetMasterScheduleUseCase


def _master_profile() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        display_name="Old name",
        public_slug="old-slug",
        timezone="UTC",
        default_currency=Currency.BYN,
        contact_email="old@example.com",
        contact_phone=None,
        telegram=None,
    )


class FakeMasterRepository:
    def __init__(self) -> None:
        self.flush_called = False

    async def flush(self) -> None:
        self.flush_called = True


async def test_update_master_profile_applies_patch_and_flushes():
    master = _master_profile()
    repo = FakeMasterRepository()
    use_case = UpdateMasterProfileUseCase(master, repo)

    result = await use_case(
        MasterProfileUpdate(
            display_name="New name",
            public_slug=None,
            timezone="Europe/Minsk",
            default_currency=Currency.EUR,
        ),
    )

    assert result.display_name == "New name"
    assert result.public_slug is None
    assert result.timezone == "Europe/Minsk"
    assert result.default_currency == Currency.EUR
    assert repo.flush_called is True


async def test_update_master_profile_ignores_null_for_required_fields():
    master = _master_profile()
    repo = FakeMasterRepository()
    use_case = UpdateMasterProfileUseCase(master, repo)

    result = await use_case(
        MasterProfileUpdate(
            display_name=None,
            timezone=None,
            default_currency=None,
            public_slug=None,
        ),
    )

    assert result.display_name == "Old name"
    assert result.timezone == "UTC"
    assert result.default_currency == Currency.BYN
    assert result.public_slug is None
    assert repo.flush_called is True


async def test_update_master_profile_updates_contact_fields():
    master = _master_profile()
    repo = FakeMasterRepository()
    use_case = UpdateMasterProfileUseCase(master, repo)

    result = await use_case(
        MasterProfileUpdate(
            contact_email="new@example.com",
            contact_phone="+375291112233",
            telegram="@studio",
        ),
    )

    assert result.contact_email == "new@example.com"
    assert result.contact_phone == "+375291112233"
    assert result.telegram == "@studio"
    assert master.contact_email == "new@example.com"
    assert repo.flush_called is True


class FakeScheduleRepository:
    async def weekly_days_for_master(self, master_id):
        return [
            SimpleNamespace(
                weekday=0,
                is_closed=False,
                intervals=[
                    SimpleNamespace(start_time=time(10, 0), end_time=time(13, 0)),
                    SimpleNamespace(start_time=time(14, 0), end_time=time(18, 0)),
                ],
                note=None,
            ),
        ]

    async def date_overrides_for_master(self, master_id):
        return [
            SimpleNamespace(
                schedule_date=date(2026, 5, 19),
                is_closed=True,
                intervals=[],
                note="Holiday",
            ),
        ]


async def test_get_master_schedule_returns_weekly_days_and_date_overrides():
    use_case = GetMasterScheduleUseCase(FakeScheduleRepository())

    result = await use_case(uuid.uuid4())

    assert result.model_dump(mode="json") == {
        "weekly_days": [
            {
                "weekday": 0,
                "is_closed": False,
                "intervals": [
                    {"start_time": "10:00", "end_time": "13:00"},
                    {"start_time": "14:00", "end_time": "18:00"},
                ],
                "note": None,
            },
        ],
        "date_overrides": [
            {
                "schedule_date": "2026-05-19",
                "is_closed": True,
                "intervals": [],
                "note": "Holiday",
            },
        ],
    }
