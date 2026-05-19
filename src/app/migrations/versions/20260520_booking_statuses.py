"""booking statuses, updated_at, indexes

Revision ID: 20260520_booking_statuses
Revises: 20260519_initial
Create Date: 2026-05-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_booking_statuses"
down_revision: Union[str, Sequence[str], None] = "20260519_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS_CHECK = "status IN ('SCHEDULED', 'COMPLETED', 'NO_SHOW', 'CANCELLED')"


def _drop_status_check_if_exists() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT c.conname INTO constraint_name
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'bookings'
              AND c.contype = 'c'
              AND pg_get_constraintdef(c.oid) ILIKE '%status%'
              AND pg_get_constraintdef(c.oid) NOT ILIKE '%end_at%';

            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE bookings DROP CONSTRAINT %I', constraint_name);
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE bookings SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("bookings", "updated_at", nullable=False)

    # Initial schema stores status as VARCHAR (native_enum=False), not a PG enum type.
    _drop_status_check_if_exists()

    op.execute("UPDATE bookings SET status = 'SCHEDULED' WHERE status = 'scheduled'")
    op.execute("UPDATE bookings SET status = 'CANCELLED' WHERE status = 'cancelled'")
    op.execute(
        "UPDATE bookings SET status = 'COMPLETED' "
        "WHERE status = 'SCHEDULED' AND end_at < NOW() AT TIME ZONE 'UTC'"
    )

    op.create_check_constraint("ck_bookings_status", "bookings", _STATUS_CHECK)
    op.create_check_constraint("ch_start_end_at", "bookings", "end_at > start_at")
    op.create_index("ix_master_status_start_at", "bookings", ["master_id", "status", "start_at"], unique=False)
    op.create_index("ix_master_start_at", "bookings", ["master_id", "start_at"], unique=False)
    op.create_index("ix_client_start_at", "bookings", ["client_id", "start_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_client_start_at", table_name="bookings")
    op.drop_index("ix_master_start_at", table_name="bookings")
    op.drop_index("ix_master_status_start_at", table_name="bookings")
    op.drop_constraint("ch_start_end_at", "bookings", type_="check")
    op.drop_constraint("ck_bookings_status", "bookings", type_="check")

    op.execute("UPDATE bookings SET status = 'scheduled' WHERE status = 'SCHEDULED'")
    op.execute(
        "UPDATE bookings SET status = 'cancelled' "
        "WHERE status IN ('CANCELLED', 'COMPLETED', 'NO_SHOW')"
    )

    op.drop_column("bookings", "updated_at")
