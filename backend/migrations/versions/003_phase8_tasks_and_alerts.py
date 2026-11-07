"""Phase 8 schema for wellness tasks and alert lifecycle

Revision ID: 003_phase8_tasks_and_alerts
Revises: 002_phase7_guidance_registry
Create Date: 2026-10-31 00:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_phase8_tasks_and_alerts"
down_revision: Union[str, None] = "002_phase7_guidance_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Task Definitions Table
    op.create_table(
        "task_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("definition_identifier", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("target_measurement_type", sa.String(length=64), nullable=True),
        sa.Column("target_check_in_type", sa.String(length=32), nullable=True),
        sa.Column("recurrence_config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "category IN ('MEASUREMENT_REMINDER', 'WELLNESS_CHECK_IN', 'FOLLOW_UP_ACTION', 'GENERAL')",
            name="chk_task_definition_category",
        ),
    )
    op.create_index("ix_task_definitions_definition_identifier", "task_definitions", ["definition_identifier"], unique=True)
    op.create_index("ix_task_definitions_category", "task_definitions", ["category"])

    # 2. Task Instances Table
    op.create_table(
        "task_instances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_definition_id", sa.UUID(), nullable=True),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("due_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_source", sa.String(length=64), nullable=True),
        sa.Column("reference_measurement_id", sa.UUID(), nullable=True),
        sa.Column("reference_check_in_id", sa.UUID(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_definition_id"], ["task_definitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reference_measurement_id"], ["health_measurements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'CANCELLED', 'MISSED')",
            name="chk_task_instance_status",
        ),
    )
    op.create_index("ix_task_instances_crew_member_id", "task_instances", ["crew_member_id"])
    op.create_index("ix_task_instances_status", "task_instances", ["status"])
    op.create_index("ix_task_crew_status", "task_instances", ["crew_member_id", "status"])
    op.create_index("ix_task_due_window", "task_instances", ["due_start", "due_end"])

    # 3. Task Audit Records Table
    op.create_table(
        "task_audit_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_instance_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_instance_id"], ["task_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_audit_records_task_instance_id", "task_audit_records", ["task_instance_id"])

    # 4. Alert Instances Table
    op.create_table(
        "alert_instances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alert_identifier", sa.String(length=64), nullable=False),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=True),
        sa.Column("source_finding_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("indicator", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_delayed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=128), nullable=True),
        sa.Column("assigned_to", sa.String(length=128), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_by", sa.String(length=128), nullable=True),
        sa.Column("dismissal_reason", sa.Text(), nullable=True),
        sa.Column("escalation_level", sa.String(length=64), server_default="NONE", nullable=False),
        sa.Column("delivery_status", sa.String(length=64), server_default="NO_DELIVERY_PROVIDER", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "priority IN ('INFO', 'CAUTION', 'CRITICAL', 'EMERGENCY')",
            name="chk_alert_priority",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'assigned', 'resolved', 'dismissed')",
            name="chk_alert_status",
        ),
    )
    op.create_index("ix_alert_instances_alert_identifier", "alert_instances", ["alert_identifier"], unique=True)
    op.create_index("ix_alert_instances_idempotency_key", "alert_instances", ["idempotency_key"], unique=True)
    op.create_index("ix_alert_instances_crew_member_id", "alert_instances", ["crew_member_id"])
    op.create_index("ix_alert_instances_source_finding_id", "alert_instances", ["source_finding_id"])
    op.create_index("ix_alert_instances_rule_id", "alert_instances", ["rule_id"])
    op.create_index("ix_alert_instances_indicator", "alert_instances", ["indicator"])
    op.create_index("ix_alert_instances_priority", "alert_instances", ["priority"])
    op.create_index("ix_alert_instances_status", "alert_instances", ["status"])
    op.create_index("ix_alert_crew_status", "alert_instances", ["crew_member_id", "status"])
    op.create_index("ix_alert_event_time", "alert_instances", ["event_time"])

    # 5. Alert Audit Records Table
    op.create_table(
        "alert_audit_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("transition_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["alert_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_audit_records_alert_id", "alert_audit_records", ["alert_id"])


def downgrade() -> None:
    op.drop_table("alert_audit_records")
    op.drop_table("alert_instances")
    op.drop_table("task_audit_records")
    op.drop_table("task_instances")
    op.drop_table("task_definitions")

