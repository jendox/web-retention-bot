"""booking cancel and reschedule comments

Revision ID: 20260524_booking_comments
Revises: 20260523_master_contacts
Create Date: 2026-05-24

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260524_booking_comments"
down_revision = "20260523_master_contacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("cancel_comment", sa.String(length=500), nullable=True))
    op.add_column("bookings", sa.Column("reschedule_comment", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "reschedule_comment")
    op.drop_column("bookings", "cancel_comment")
