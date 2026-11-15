"""Quests, XP, streaks, and unlocks migration

Revision ID: 005_quests_and_xp
Revises: 004_phase9_sync_records
Create Date: 2026-11-15 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "005_quests_and_xp"
down_revision: Union[str, None] = "004_phase9_sync_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Quests Table
    op.create_table(
        "quests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("target", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("evidence_level", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. Quest Progress Table
    op.create_table(
        "quest_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("quest_id", sa.String(length=64), sa.ForeignKey("quests.id"), nullable=False),
        sa.Column("crew_id", sa.String(length=64), nullable=False, server_default="team"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. XP Events Table
    op.create_table(
        "xp_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(length=128), unique=True, index=True, nullable=False),
        sa.Column("quest_id", sa.String(length=64), sa.ForeignKey("quests.id"), nullable=False),
        sa.Column("crew_id", sa.String(length=64), nullable=False, server_default="team"),
        sa.Column("xp_gained", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. Streaks Table
    op.create_table(
        "streaks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("streak_type", sa.String(length=32), nullable=False, server_default="team"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freeze_days_remaining", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("last_activity_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. Unlocks Table
    op.create_table(
        "unlocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("crew_id", sa.String(length=64), nullable=False, server_default="team"),
        sa.Column("unlock_key", sa.String(length=64), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("crew_id", "unlock_key", name="uq_crew_unlock"),
    )


def downgrade() -> None:
    op.drop_table("unlocks")
    op.drop_table("streaks")
    op.drop_table("xp_events")
    op.drop_table("quest_progress")
    op.drop_table("quests")
