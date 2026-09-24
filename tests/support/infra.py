from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import redis
from psycopg import connect as psycopg_connect, sql

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://retention:retention@localhost:5432/retention_test"
DEFAULT_TEST_REDIS_URL = "redis://localhost:6379/15"


def default_test_database_url() -> str:
    return os.environ.get("INFRA__TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def default_test_redis_url() -> str:
    return os.environ.get("INFRA__TEST_REDIS_URL", DEFAULT_TEST_REDIS_URL)


def apply_pytest_env_defaults() -> None:
    """Force test infra env before `app` is imported (see tests/conftest.py)."""
    test_db_url = default_test_database_url()
    test_redis_url = default_test_redis_url()

    os.environ["APP_ENV"] = "test"
    os.environ["INFRA__DATABASE_URL"] = test_db_url
    os.environ["INFRA__REDIS_URL"] = test_redis_url
    os.environ["CELERY__BROKER_URL"] = test_redis_url
    os.environ["CELERY__RESULT_BACKEND"] = test_redis_url

    os.environ["NOTIFICATIONS__EAGER_DELIVERIES"] = "true"
    os.environ["SMTP__ENABLED"] = "false"

    os.environ["ADMIN__ENABLED"] = "false"
    os.environ["ADMIN__ALLOWED_EMAILS"] = ""
    os.environ["MESSENGER_BOTS__INTERNAL_SECRET"] = "dev-bot-internal-secret-change-me"


def _postgres_maintenance_url(database_url: str) -> tuple[str, str]:
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(normalized)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        msg = f"database name missing in URL: {database_url}"
        raise ValueError(msg)
    maintenance = parsed._replace(path="/postgres").geturl()
    return maintenance, db_name


def ensure_postgres_database(database_url: str) -> None:
    maintenance_url, db_name = _postgres_maintenance_url(database_url)
    with psycopg_connect(maintenance_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))


def flush_redis(redis_url: str) -> None:
    client = redis.from_url(redis_url)
    try:
        client.flushdb()
    finally:
        client.close()


def run_alembic_upgrade(database_url: str) -> None:
    env = os.environ.copy()
    env["INFRA__DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


def prepare_test_infra() -> None:
    database_url = os.environ["INFRA__DATABASE_URL"]
    redis_url = os.environ["INFRA__REDIS_URL"]
    ensure_postgres_database(database_url)
    run_alembic_upgrade(database_url)
    flush_redis(redis_url)
