"""User notification list and mark-read use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.use_cases.notifications.list import ListMyNotificationsUseCase, MarkNotificationReadUseCase


@pytest.mark.asyncio
async def test_list_my_notifications() -> None:
    user_id = uuid.uuid4()
    note = SimpleNamespace(
        id=uuid.uuid4(),
        event_type="BOOKING_CREATED",
        title="Новая запись",
        body="Master: Услуга",
        link_url="/client",
        read_at=None,
        created_at=datetime.now(UTC),
    )

    from app.core.pagination import Pagination

    repo = SimpleNamespace(
        count_for_user=AsyncMock(return_value=1),
        list_for_user_page=AsyncMock(return_value=[note]),
        count_unread_for_user=AsyncMock(return_value=1),
    )
    result = await ListMyNotificationsUseCase(repo)(SimpleNamespace(id=user_id), Pagination(page=1, page_size=10))
    assert result.unread_count == 1
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].title == "Новая запись"


@pytest.mark.asyncio
async def test_mark_notification_read() -> None:
    user_id = uuid.uuid4()
    note = SimpleNamespace(
        id=uuid.uuid4(),
        event_type="BOOKING_CREATED",
        title="T",
        body="B",
        link_url=None,
        read_at=None,
        created_at=datetime.now(UTC),
    )

    repo = SimpleNamespace(
        get_for_user=AsyncMock(return_value=note),
        flush=AsyncMock(),
    )
    out = await MarkNotificationReadUseCase(repo)(SimpleNamespace(id=user_id), note.id)
    assert out.read_at is not None
    repo.flush.assert_awaited_once()
