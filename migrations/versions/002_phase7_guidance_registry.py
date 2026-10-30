"""Phase 7 schema for versioned evidence and guidance registry

Revision ID: 002_phase7_guidance_registry
Revises: 001_phase2_schema
Create Date: 2026-10-30 23:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_phase7_guidance_registry"
down_revision: Union[str, None] = "001_phase2_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Phase 7 source metadata columns to guidance_sources
    op.add_column("guidance_sources", sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("guidance_sources", sa.Column("access_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("guidance_sources", sa.Column("citation_reference", sa.String(length=255), nullable=True))
    op.add_column("guidance_sources", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("guidance_sources", sa.Column("health_indicator", sa.String(length=64), nullable=True))
    op.add_column("guidance_sources", sa.Column("spaceflight_hazard", sa.String(length=64), nullable=True))
    op.add_column("guidance_sources", sa.Column("mission_context", sa.String(length=64), nullable=True))
    op.add_column("guidance_sources", sa.Column("target_population", sa.String(length=64), nullable=True))
    op.add_column("guidance_sources", sa.Column("evidence_limitations", sa.Text(), nullable=True))
    op.add_column("guidance_sources", sa.Column("intended_use", sa.Text(), nullable=True))
    op.add_column("guidance_sources", sa.Column("next_review_date", sa.DateTime(timezone=True), nullable=True))

    # 2. Guidance Documents Table
    op.create_table(
        "guidance_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guidance_source_id", sa.UUID(), nullable=True),
        sa.Column("document_identifier", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("guidance_type", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("citation_reference", sa.String(length=255), nullable=True),
        sa.Column("topic", sa.String(length=128), nullable=True),
        sa.Column("health_indicator", sa.String(length=64), nullable=True),
        sa.Column("spaceflight_hazard", sa.String(length=64), nullable=True),
        sa.Column("mission_context", sa.String(length=64), nullable=True),
        sa.Column("target_population", sa.String(length=64), nullable=True),
        sa.Column("evidence_limitations", sa.Text(), nullable=True),
        sa.Column("intended_use", sa.Text(), nullable=True),
        sa.Column("approval_status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("superseded_by_id", sa.UUID(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guidance_source_id"], ["guidance_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["guidance_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "guidance_type IN ('EDUCATIONAL', 'OPERATIONAL_INSTRUCTION', 'CLINICAL_RULE')",
            name="chk_guidance_type",
        ),
        sa.CheckConstraint(
            "approval_status IN ('draft', 'under_review', 'approved', 'rejected', 'retired')",
            name="chk_guidance_approval_status",
        ),
    )
    op.create_index("ix_guidance_documents_document_identifier", "guidance_documents", ["document_identifier"], unique=True)
    op.create_index("ix_guidance_documents_guidance_source_id", "guidance_documents", ["guidance_source_id"])
    op.create_index("ix_guidance_documents_topic", "guidance_documents", ["topic"])
    op.create_index("ix_guidance_documents_health_indicator", "guidance_documents", ["health_indicator"])
    op.create_index("ix_guidance_documents_spaceflight_hazard", "guidance_documents", ["spaceflight_hazard"])
    op.create_index("ix_guidance_documents_mission_context", "guidance_documents", ["mission_context"])
    op.create_index("ix_guidance_documents_approval_status", "guidance_documents", ["approval_status"])

    # 3. Guidance Review Records Table
    op.create_table(
        "guidance_review_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guidance_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("reviewer_role", sa.String(length=64), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("decision_rationale", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["guidance_id"], ["guidance_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guidance_review_records_guidance_id", "guidance_review_records", ["guidance_id"])

    # 4. Link Clinical Rules to Guidance Documents
    op.add_column("clinical_rules", sa.Column("guidance_document_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_clinical_rules_guidance_document_id",
        "clinical_rules",
        "guidance_documents",
        ["guidance_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_clinical_rules_guidance_document_id", "clinical_rules", ["guidance_document_id"])


def downgrade() -> None:
    op.drop_constraint("fk_clinical_rules_guidance_document_id", "clinical_rules", type_="foreignkey")
    op.drop_index("ix_clinical_rules_guidance_document_id", "clinical_rules")
    op.drop_column("clinical_rules", "guidance_document_id")

    op.drop_table("guidance_review_records")
    op.drop_table("guidance_documents")

    op.drop_column("guidance_sources", "next_review_date")
    op.drop_column("guidance_sources", "intended_use")
    op.drop_column("guidance_sources", "evidence_limitations")
    op.drop_column("guidance_sources", "target_population")
    op.drop_column("guidance_sources", "mission_context")
    op.drop_column("guidance_sources", "spaceflight_hazard")
    op.drop_column("guidance_sources", "health_indicator")
    op.drop_column("guidance_sources", "summary")
    op.drop_column("guidance_sources", "citation_reference")
    op.drop_column("guidance_sources", "access_date")
    op.drop_column("guidance_sources", "publication_date")
