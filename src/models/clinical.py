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
        default="APPROVED",
        nullable=False,
        comment="State: DRAFT, UNDER_REVIEW, APPROVED, SUPERSEDED",
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
        default="ACTIVE",
        nullable=False,
        comment="Status: ACTIVE, INACTIVE, DEPRECATED",
    )

    # Relationships
    clinical_rules: Mapped[list["ClinicalRule"]] = relationship(
        "ClinicalRule",
        back_populates="guidance_source",
        cascade="all, delete-orphan",
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
        default="APPROVED",
        nullable=False,
        comment="State: APPROVED, DRAFT, UNDER_REVIEW, SUPERSEDED",
    )
    approval_status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        nullable=False,
        comment="Status: ACTIVE, INACTIVE",
    )

    # Relationships
    guidance_source: Mapped["GuidanceSource"] = relationship(
        "GuidanceSource",
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

