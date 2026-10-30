import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.crew import CrewMember


class GuidanceSource(Base, TimestampMixin):
    """Source authority for clinical thresholds and aerospace health baselines (e.g. NASA-STD-3001)."""

    __tablename__ = "guidance_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_identifier: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Authoritative identifier (e.g., NASA-STD-3001-VOL1)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full title of the reference standard document",
    )
    publisher: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Issuing authority (e.g., NASA Office of the Chief Health and Medical Officer)",
    )
    document_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Direct link to published source document",
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Revision/Version string (e.g., Rev C)",
    )
    review_state: Mapped[str] = mapped_column(
        String(32),
        default="approved",
        nullable=False,
        comment="State: draft, under_review, approved, rejected, retired",
    )
    reviewer_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Reviewing flight surgeon or clinical panel metadata",
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_status: Mapped[str] = mapped_column(
        String(32),
        default="approved",
        nullable=False,
        comment="Status: draft, under_review, approved, rejected, retired",
    )
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Official publication or release date",
    )
    access_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date source was accessed or verified",
    )
    citation_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Page, section, or passage reference",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Concise summary with attribution",
    )
    health_indicator: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Relevant health indicator if specified",
    )
    spaceflight_hazard: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Relevant spaceflight hazard if specified",
    )
    mission_context: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Applicable mission context if specified",
    )
    target_population: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Target crew population",
    )
    evidence_limitations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Evidence limitations and intended scope",
    )
    intended_use: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Intended operational or educational use",
    )
    next_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiry or scheduled next review date",
    )

    # Relationships
    clinical_rules: Mapped[list["ClinicalRule"]] = relationship(
        "ClinicalRule",
        back_populates="guidance_source",
        cascade="all, delete-orphan",
    )
    guidance_documents: Mapped[list["GuidanceDocument"]] = relationship(
        "GuidanceDocument",
        back_populates="guidance_source",
        cascade="all, delete-orphan",
    )


class GuidanceDocument(Base, TimestampMixin):
    """Specific guidance record separating educational material, operational instructions, and clinical rules."""

    __tablename__ = "guidance_documents"
    __table_args__ = (
        CheckConstraint(
            "guidance_type IN ('EDUCATIONAL', 'OPERATIONAL_INSTRUCTION', 'CLINICAL_RULE')",
            name="chk_guidance_type",
        ),
        CheckConstraint(
            "approval_status IN ('draft', 'under_review', 'approved', 'rejected', 'retired')",
            name="chk_guidance_approval_status",
        ),
        Index("ix_guidance_topic_indicator", "topic", "health_indicator"),
        Index("ix_guidance_hazard_context", "spaceflight_hazard", "mission_context"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    guidance_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guidance_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_identifier: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique identifier for the guidance document (e.g. DOC-NASA-HRP-SLEEP-01)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    guidance_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="EDUCATIONAL, OPERATIONAL_INSTRUCTION, or CLINICAL_RULE",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Concise summary with attribution",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Guidance content, operational protocol, or educational details",
    )
    citation_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Page, section, or passage reference",
    )
    topic: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Subject topic (e.g. Cardiovascular, Sleep & Fatigue)",
    )
    health_indicator: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Associated health indicator (e.g. heart_rate, sleep_duration)",
    )
    spaceflight_hazard: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Spaceflight hazard (e.g. MICROGRAVITY, RADIATION, ISOLATION)",
    )
    mission_context: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Mission context (e.g. TRANSIT, LEO, LUNAR, MARS, EVA, ANY)",
    )
    target_population: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Target population",
    )
    evidence_limitations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Evidence limitations, contraindications, and caveats",
    )
    intended_use: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Intended clinical or educational use",
    )
    approval_status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
        index=True,
        comment="draft, under_review, approved, rejected, retired",
    )
    version: Mapped[str] = mapped_column(
        String(32),
        default="1.0.0",
        nullable=False,
    )
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guidance_documents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Points to replacement guidance document if superseded",
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Internal reviewer notes and administrative metadata (redacted for crew)",
    )

    # Relationships
    guidance_source: Mapped["GuidanceSource | None"] = relationship(
        "GuidanceSource",
        back_populates="guidance_documents",
    )
    review_records: Mapped[list["GuidanceReviewRecord"]] = relationship(
        "GuidanceReviewRecord",
        back_populates="guidance_document",
        cascade="all, delete-orphan",
        order_by="GuidanceReviewRecord.reviewed_at.desc()",
    )
    clinical_rules: Mapped[list["ClinicalRule"]] = relationship(
        "ClinicalRule",
        back_populates="guidance_document",
    )


class GuidanceReviewRecord(Base):
    """Auditable review record tracking status transitions and reviewer rationales."""

    __tablename__ = "guidance_review_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    guidance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guidance_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    reviewer_role: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    previous_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    new_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    decision_rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    metadata_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationship
    guidance_document: Mapped["GuidanceDocument"] = relationship(
        "GuidanceDocument",
        back_populates="review_records",
    )


class ClinicalRule(Base, TimestampMixin):
    """Source-attributed, deterministic clinical decision rule.
    
    Supporting a rule requires clear provenance; missing data must evaluate to
    UNKNOWN rather than assuming healthy state.
    """

    __tablename__ = "clinical_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    guidance_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guidance_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    guidance_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guidance_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_identifier: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique rule code (e.g., RULE-NASA-HR-RESTING-HIGH)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    applicable_context: Mapped[str] = mapped_column(
        String(64),
        default="MICROGRAVITY",
        nullable=False,
        comment="Operational context: MICROGRAVITY, EVA, SLEEP, EXERCISE, ANY",
    )
    measurement_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Target measurement type from registry (e.g., heart_rate)",
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Strict numerical boundaries, bounds, and thresholds",
    )
    review_state: Mapped[str] = mapped_column(
        String(32),
        default="approved",
        nullable=False,
        comment="State: approved, draft, under_review, rejected, retired",
    )
    approval_status: Mapped[str] = mapped_column(
        String(32),
        default="approved",
        nullable=False,
        comment="Status: approved, draft, under_review, rejected, retired",
    )

    # Relationships
    guidance_source: Mapped["GuidanceSource"] = relationship(
        "GuidanceSource",
        back_populates="clinical_rules",
    )
    guidance_document: Mapped["GuidanceDocument | None"] = relationship(
        "GuidanceDocument",
        back_populates="clinical_rules",
    )


class Assessment(Base):
    """Output of deterministic evaluation of crew measurements against clinical rules."""

    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "assessment_status IN ('assessed_no_findings', 'partially_assessed', 'not_assessed', 'insufficient_evidence', 'needs_review', 'NOMINAL', 'CAUTION', 'CRITICAL', 'INSUFFICIENT_DATA')",
            name="chk_assessment_status",
        ),
        Index("ix_assessment_subject_assessed_at", "subject_id", "assessed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp evaluation occurred in UTC",
    )
    engine_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Evaluation engine build/version identifier",
    )
    ruleset_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Ruleset version applied during assessment",
    )
    assessment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Overall status: NOMINAL, CAUTION, CRITICAL, INSUFFICIENT_DATA",
    )
    findings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Structured clinical rule evaluation findings and source citations",
    )
    input_measurement_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of UUID strings of health measurements evaluated",
    )
    data_quality_info: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Data completeness, latency, and sensor reliability metrics",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
        back_populates="assessments",
    )

