"""Initial Phase 2 schema for astronaut health monitoring

Revision ID: 001_phase2_schema
Revises: 
Create Date: 2026-10-30 01:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_phase2_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crew Members Table
    op.create_table(
        "crew_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("crew_id", sa.String(length=32), nullable=False, comment="Pseudonymous crew identifier (e.g., CREW-042)"),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("profile_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crew_members_crew_id", "crew_members", ["crew_id"], unique=True)

    # 2. Missions Table
    op.create_table(
        "missions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_identifier", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("mission_phase", sa.String(length=32), server_default="PRE_FLIGHT", nullable=False),
        sa.Column("operational_environment", sa.String(length=32), server_default="MICROGRAVITY", nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_missions_mission_identifier", "missions", ["mission_identifier"], unique=True)

    # 3. Mission Memberships Table
    op.create_table(
        "mission_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crew_member_id", "mission_id", "role", name="uq_crew_mission_role"),
    )
    op.create_index("ix_mission_memberships_crew_member_id", "mission_memberships", ["crew_member_id"])
    op.create_index("ix_mission_memberships_mission_id", "mission_memberships", ["mission_id"])

    # 4. Health Measurements Table
    op.create_table(
        "health_measurements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("measurement_type", sa.String(length=64), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_structured", sa.JSON(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_method", sa.String(length=32), server_default="WEARABLE_SENSOR", nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(length=32), server_default="VERIFIED", nullable=False),
        sa.Column("context_metadata", sa.JSON(), nullable=True),
        sa.CheckConstraint("value_numeric IS NOT NULL OR value_structured IS NOT NULL", name="chk_measurement_has_value"),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_measurement_crew_measured_at", "health_measurements", ["crew_member_id", "measured_at"])
    op.create_index("ix_measurement_type_measured_at", "health_measurements", ["measurement_type", "measured_at"])

    # 5. Wellness Check-Ins Table
    op.create_table(
        "wellness_checkins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("sleep_duration_hours", sa.Float(), nullable=False),
        sa.Column("sleep_quality", sa.Integer(), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=False),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.Column("fatigue", sa.Integer(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.CheckConstraint("sleep_duration_hours >= 0.0 AND sleep_duration_hours <= 24.0", name="chk_sleep_duration_range"),
        sa.CheckConstraint("sleep_quality >= 1 AND sleep_quality <= 5", name="chk_sleep_quality_range"),
        sa.CheckConstraint("mood >= 1 AND mood <= 5", name="chk_mood_range"),
        sa.CheckConstraint("stress >= 1 AND stress <= 5", name="chk_stress_range"),
        sa.CheckConstraint("fatigue >= 1 AND fatigue <= 5", name="chk_fatigue_range"),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wellness_crew_measured_at", "wellness_checkins", ["crew_member_id", "measured_at"])

    # 6. Symptom Check-Ins Table
    op.create_table(
        "symptom_checkins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("crew_member_id", sa.UUID(), nullable=False),
        sa.Column("symptom_identifiers", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("onset_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("controlled_notes", sa.String(length=500), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.CheckConstraint("severity IN ('MILD', 'MODERATE', 'SEVERE')", name="chk_symptom_severity"),
        sa.ForeignKeyConstraint(["crew_member_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symptom_crew_onset_time", "symptom_checkins", ["crew_member_id", "onset_time"])

    # 7. Guidance Sources Table
    op.create_table(
        "guidance_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_identifier", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=False),
        sa.Column("document_url", sa.String(length=512), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("review_state", sa.String(length=32), server_default="APPROVED", nullable=False),
        sa.Column("reviewer_metadata", sa.JSON(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guidance_sources_source_identifier", "guidance_sources", ["source_identifier"], unique=True)

    # 8. Clinical Rules Table
    op.create_table(
        "clinical_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guidance_source_id", sa.UUID(), nullable=False),
        sa.Column("rule_identifier", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("applicable_context", sa.String(length=64), server_default="MICROGRAVITY", nullable=False),
        sa.Column("measurement_type", sa.String(length=64), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("review_state", sa.String(length=32), server_default="APPROVED", nullable=False),
        sa.Column("approval_status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guidance_source_id"], ["guidance_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_rules_rule_identifier", "clinical_rules", ["rule_identifier"], unique=True)
    op.create_index("ix_clinical_rules_measurement_type", "clinical_rules", ["measurement_type"])

    # 9. Assessments Table
    op.create_table(
        "assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column("ruleset_version", sa.String(length=64), nullable=False),
        sa.Column("assessment_status", sa.String(length=32), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("input_measurement_ids", sa.JSON(), nullable=False),
        sa.Column("data_quality_info", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("assessment_status IN ('NOMINAL', 'CAUTION', 'CRITICAL', 'INSUFFICIENT_DATA')", name="chk_assessment_status"),
        sa.ForeignKeyConstraint(["subject_id"], ["crew_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_subject_assessed_at", "assessments", ["subject_id", "assessed_at"])

    # 10. Audit Events Table
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_actor_occurred_at", "audit_events", ["actor", "occurred_at"])
    op.create_index("ix_audit_resource_occurred_at", "audit_events", ["resource_type", "resource_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("assessments")
    op.drop_table("clinical_rules")
    op.drop_table("guidance_sources")
    op.drop_table("symptom_checkins")
    op.drop_table("wellness_checkins")
    op.drop_table("health_measurements")
    op.drop_table("mission_memberships")
    op.drop_table("missions")
    op.drop_table("crew_members")

