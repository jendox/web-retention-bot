"""add master default_currency

Revision ID: f8a3c2d1b4e5
Revises: 1d00330f9213
Create Date: 2026-05-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8a3c2d1b4e5"
down_revision: Union[str, Sequence[str], None] = "1d00330f9213"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "master_profiles",
        sa.Column("default_currency", sa.String(length=3), nullable=False, server_default="BYN"),
    )


def downgrade() -> None:
    op.drop_column("master_profiles", "default_currency")
