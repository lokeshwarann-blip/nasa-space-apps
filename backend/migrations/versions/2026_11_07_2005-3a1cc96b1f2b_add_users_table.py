
"""add users table

Revision ID: 3a1cc96b1f2b
Revises: 004_phase9_sync_records
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "3a1cc96b1f2b"
down_revision: Union[str, None] = "004_phase9_sync_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False,
                  comment="Unique login username"),
        sa.Column("hashed_password", sa.String(255), nullable=False,
                  comment="Cryptographically hashed password (Argon2id)"),
        sa.Column("role", sa.String(32), nullable=False,
                  comment="Logical role: CREW_MEMBER, FLIGHT_SURGEON, ADMIN"),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  comment="Account active status"),
        sa.Column("crew_member_id", sa.UUID(), nullable=True,
                  comment="Associated crew member identity for CREW_MEMBER role"),
        sa.Column("assigned_crew_ids", sa.JSON(), nullable=False,
                  comment="Authorized scope for FLIGHT_SURGEON: list of permitted crew member UUID strings"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["crew_member_id"],
            ["crew_members.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_index(
        "ix_users_crew_member_id", "users", ["crew_member_id"]
    )
    op.create_index(
        "ix_users_role", "users", ["role"]
    )
    op.create_index(
        "ix_users_username", "users", ["username"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_crew_member_id", table_name="users")
    op.drop_table("users")
