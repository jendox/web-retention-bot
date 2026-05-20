"""remove viber channel and master contact field

Revision ID: 20260525_remove_viber
Revises: 20260524_booking_comments
Create Date: 2026-05-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260525_remove_viber"
down_revision = "20260524_booking_comments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM notification_deliveries WHERE channel = 'viber'"))
    op.execute(sa.text("DELETE FROM user_notification_preferences WHERE channel = 'viber'"))
    op.execute(sa.text("DELETE FROM notification_channels WHERE kind = 'viber'"))
    op.drop_column("master_profiles", "viber")


def downgrade() -> None:
    op.add_column("master_profiles", sa.Column("viber", sa.String(length=100), nullable=True))
