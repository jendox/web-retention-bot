"""User notification list and mark-read use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from app.api.deps import require_user
from app.main import app
from app.use_cases.notifications.exceptions import NotificationNotFoundError
from app.use_cases.notifications.list_notifications import ListClientNotificationsUseCase
from app.use_cases.notifications.mark_read_notifications import (
    MarkNotificationReadUseCase,
    get_mark_notification_read_use_case,
)


class FakeMarkNotificationReadUseCase:
    async def __call__(self, *, user_id, notification_id):
        raise NotificationNotFoundError()


@pytest.mark.asyncio
async def test_list_client_notifications() -> None:
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
        count_for_client_cabinet=AsyncMock(return_value=1),
        list_for_client_cabinet_page=AsyncMock(return_value=[note]),
        count_unread_for_client_cabinet=AsyncMock(return_value=1),
    )
    result = await ListClientNotificationsUseCase(repo)(user_id, Pagination(page=1, page_size=10))
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
    out = await MarkNotificationReadUseCase(repo)(user_id=user_id, notification_id=note.id)
    assert out.read_at is not None
    repo.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_notification_read_not_found_raises_domain_error() -> None:
    repo = SimpleNamespace(
        get_for_user=AsyncMock(return_value=None),
        flush=AsyncMock(),
    )

    with pytest.raises(NotificationNotFoundError) as exc_info:
        await MarkNotificationReadUseCase(repo)(user_id=uuid.uuid4(), notification_id=uuid.uuid4())

    assert exc_info.value.code == "notifications.not_found"
    assert exc_info.value.message == "Notification not found"
    repo.flush.assert_not_awaited()


def test_mark_notification_read_route_returns_app_error_contract() -> None:
    app.dependency_overrides[require_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_mark_notification_read_use_case] = FakeMarkNotificationReadUseCase
    try:
        with TestClient(app) as client:
            client.cookies.set("csrf_token", "token")
            resp = client.post(
                f"/api/client/notifications/{uuid.uuid4()}/read",
                headers={"X-CSRF-Token": "token"},
            )
    finally:
        app.dependency_overrides.pop(require_user, None)
        app.dependency_overrides.pop(get_mark_notification_read_use_case, None)

    assert resp.status_code == 404
    assert resp.json() == {
        "code": "notifications.not_found",
        "detail": "Notification not found",
    }
