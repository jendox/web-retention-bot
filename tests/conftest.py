"""Pytest configuration: isolate tests from dev DB/Redis before application import."""

from __future__ import annotations

import errno
import subprocess

import pytest
from tests.support.infra import apply_pytest_env_defaults, prepare_test_infra

apply_pytest_env_defaults()

try:
    prepare_test_infra()
except OSError as exc:
    if getattr(exc, "errno", None) in {errno.ECONNREFUSED, errno.ENOENT}:
        pytest.exit(
            "PostgreSQL/Redis unreachable for tests. Start dev infra: `make infra-up`",
            returncode=1,
        )
    raise
except subprocess.CalledProcessError as exc:
    pytest.exit(f"Test database migration failed: {exc}", returncode=1)
