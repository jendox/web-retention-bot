"""Pytest configuration: set safe defaults before application packages load."""

from __future__ import annotations

import os

# Avoid requiring a Celery broker during API tests; dispatcher sends verification inline.
os.environ["NOTIFICATIONS__EAGER_DELIVERIES"] = "true"
# Avoid requiring a listening SMTP server during API tests.
os.environ["SMTP__ENABLED"] = "false"
