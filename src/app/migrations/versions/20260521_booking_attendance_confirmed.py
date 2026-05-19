"""booking attendance_confirmed_at

Revision ID: 20260521_booking_attendance
Revises: 20260520_booking_statuses
Create Date: 2026-05-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260521_booking_attendance"
down_revision: Union[str, Sequence[str], None] = "20260520_booking_statuses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("attendance_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bookings", "attendance_confirmed_at")
