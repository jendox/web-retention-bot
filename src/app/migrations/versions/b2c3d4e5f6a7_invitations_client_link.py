"""invitations client link and email mismatch flags

Revision ID: b2c3d4e5f6a7
Revises: f8a3c2d1b4e5
Create Date: 2026-05-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "f8a3c2d1b4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_clients_user_id_users",
        "clients",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index("ix_clients_user_id", "clients", ["user_id"], unique=False)

    op.add_column("invitations", sa.Column("target_client_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_invitations_target_client_id_clients",
        "invitations",
        "clients",
        ["target_client_id"],
        ["id"],
    )
    op.add_column("invitations", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_invitations_master_target_pending",
        "invitations",
        ["master_id", "target_client_id"],
        unique=False,
    )

    op.add_column("master_clients", sa.Column("linked_account_email", sa.String(length=320), nullable=True))
    op.add_column(
        "master_clients",
        sa.Column(
            "invite_email_mismatch",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("master_clients", "invite_email_mismatch")
    op.drop_column("master_clients", "linked_account_email")

    op.drop_index("ix_invitations_master_target_pending", table_name="invitations")
    op.drop_column("invitations", "revoked_at")
    op.drop_constraint("fk_invitations_target_client_id_clients", "invitations", type_="foreignkey")
    op.drop_column("invitations", "target_client_id")

    op.drop_index("ix_clients_user_id", table_name="clients")
    op.drop_constraint("fk_clients_user_id_users", "clients", type_="foreignkey")
    op.drop_column("clients", "user_id")
