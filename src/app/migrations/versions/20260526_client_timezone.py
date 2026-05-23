"""client profile timezone

Revision ID: 20260526_client_timezone
Revises: 20260525_remove_viber
Create Date: 2026-05-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.timezones import DEFAULT_TIMEZONE

revision = "20260526_client_timezone"
down_revision = "20260525_remove_viber"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default=DEFAULT_TIMEZONE),
    )
    op.alter_column("clients", "timezone", server_default=None)


def downgrade() -> None:
    op.drop_column("clients", "timezone")
