from __future__ import annotations

from starlette.testclient import TestClient

from app.admin.database import sync_database_url
from app.admin.setup import ADMIN_BASE_URL
from app.core.config import AdminSettings
from app.main import app


def test_sync_database_url_rewrites_asyncpg() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert sync_database_url(url) == "postgresql+psycopg://user:pass@localhost:5432/db"


def test_admin_settings_allowed_emails() -> None:
    settings = AdminSettings(allowed_emails=" Ops@Example.com ,other@test.io ")
    assert settings.allowed_email_set == frozenset({"ops@example.com", "other@test.io"})


def test_admin_not_mounted_when_disabled() -> None:
    with TestClient(app) as client:
        resp = client.get(f"{ADMIN_BASE_URL}/login")
        assert resp.status_code == 404
