"""schedule override intervals

Revision ID: c9d0e1f2a3b4
Revises: b2c3d4e5f6a7
Create Date: 2026-05-17 20:20:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workday_override_intervals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("override_id", sa.Uuid(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["override_id"], ["workday_overrides.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("override_id", "start_time", name="uq_override_interval_start"),
    )
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(
            """
            SELECT id, start_time, end_time
            FROM workday_overrides
            WHERE is_closed = false AND start_time IS NOT NULL AND end_time IS NOT NULL
            """,
        ),
    )
    intervals_table = sa.table(
        "workday_override_intervals",
        sa.column("id", sa.Uuid()),
        sa.column("override_id", sa.Uuid()),
        sa.column("start_time", sa.Time()),
        sa.column("end_time", sa.Time()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        intervals_table,
        [
            {
                "id": uuid.uuid4(),
                "override_id": row.id,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "sort_order": 0,
            }
            for row in existing
        ],
    )
    op.drop_column("workday_overrides", "start_time")
    op.drop_column("workday_overrides", "end_time")


def downgrade() -> None:
    op.add_column("workday_overrides", sa.Column("end_time", sa.Time(), nullable=True))
    op.add_column("workday_overrides", sa.Column("start_time", sa.Time(), nullable=True))
    op.execute(
        """
        UPDATE workday_overrides
        SET start_time = first_interval.start_time,
            end_time = first_interval.end_time
        FROM (
            SELECT DISTINCT ON (override_id) override_id, start_time, end_time
            FROM workday_override_intervals
            ORDER BY override_id, sort_order ASC, start_time ASC
        ) AS first_interval
        WHERE workday_overrides.id = first_interval.override_id
        """,
    )
    op.drop_table("workday_override_intervals")
