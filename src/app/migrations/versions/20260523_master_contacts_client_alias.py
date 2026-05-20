"""master contact fields and client_alias on master_clients

Revision ID: 20260523_master_contacts
Revises: 20260521_booking_attendance
Create Date: 2026-05-23

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260523_master_contacts"
down_revision = "20260521_booking_attendance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("master_profiles", sa.Column("contact_email", sa.String(length=320), nullable=True))
    op.add_column("master_profiles", sa.Column("contact_phone", sa.String(length=50), nullable=True))
    op.add_column("master_profiles", sa.Column("telegram", sa.String(length=100), nullable=True))
    op.add_column("master_profiles", sa.Column("viber", sa.String(length=100), nullable=True))
    op.add_column("master_clients", sa.Column("client_alias", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("master_clients", "client_alias")
    op.drop_column("master_profiles", "viber")
    op.drop_column("master_profiles", "telegram")
    op.drop_column("master_profiles", "contact_phone")
    op.drop_column("master_profiles", "contact_email")
