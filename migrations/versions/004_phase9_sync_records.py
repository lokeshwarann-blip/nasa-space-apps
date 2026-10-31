"""Phase 9 schema for offline synchronization API

Revision ID: 004_phase9_sync_records
Revises: 003_phase8_tasks_and_alerts
Create Date: 2026-10-31 00:27:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_phase9_sync_records"
down_revision: Union[str, None] = "003_phase8_tasks_and_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Sync Event Records Table
    op.create_table(
        "sync_event_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_event_id", sa.UUID(), nullable=False),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=16), server_default="1.0", nullable=False),
        sa.Column("client_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "event_type IN ('MEASUREMENT', 'WELLNESS_CHECK_IN', 'SYMPTOM_CHECK_IN')",
            name="chk_sync_event_type",
        ),
        sa.CheckConstraint(
            "sync_status IN ('accepted', 'duplicate', 'conflict', 'rejected')",
            name="chk_sync_status",
        ),
    )
    op.create_index("ix_sync_client_event_id", "sync_event_records", ["client_event_id"], unique=True)
    op.create_index("ix_sync_event_records_crew_member_id", "sync_event_records", ["crew_member_id"])
    op.create_index("ix_sync_crew_received", "sync_event_records", ["crew_member_id", "server_received_at"])
    op.create_index("ix_sync_event_type_measured", "sync_event_records", ["event_type", "measured_at"])


def downgrade() -> None:
    op.drop_table("sync_event_records")

