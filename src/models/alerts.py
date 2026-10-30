import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    Boolean,
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
    from src.models.clinical import Assessment
    from src.models.crew import CrewMember


class AlertInstance(Base, TimestampMixin):
    """Clinical alert instance with traceable rule provenance, lifecycle states, and deduplication."""

    __tablename__ = "alert_instances"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('INFO', 'CAUTION', 'CRITICAL', 'EMERGENCY')",
            name="chk_alert_priority",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'assigned', 'resolved', 'dismissed')",
            name="chk_alert_status",
        ),
        Index("ix_alert_crew_status", "crew_member_id", "status"),
        Index("ix_alert_event_time", "event_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    alert_identifier: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Human-readable or tracking alert ID (e.g. ALT-2026-HR-001)",
    )
    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_finding_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Identifier of clinical finding triggering this alert",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Deduplication key (e.g. hash of crew_id:source_finding_id:event_time)",
    )
    rule_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Explicitly approved clinical rule triggering the alert",
    )
    rule_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    indicator: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Derived strictly from approved rule severity: INFO, CAUTION, CRITICAL, EMERGENCY",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="open",
        nullable=False,
        index=True,
        comment="open, acknowledged, assigned, resolved, dismissed",
    )
    summary: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Actual historical time physiological event occurred (UTC)",
    )
    is_delayed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if event_time differs substantially from telemetry ingestion time",
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Flight Surgeon or medical reviewer ID assigned",
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    resolution_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissed_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    dismissal_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    escalation_level: Mapped[str] = mapped_column(
        String(64),
        default="NONE",
        nullable=False,
    )
    delivery_status: Mapped[str] = mapped_column(
        String(64),
        default="NO_DELIVERY_PROVIDER",
        nullable=False,
        comment="NO_DELIVERY_PROVIDER, DELIVERY_PENDING, DELIVERED, DELIVERY_FAILED",
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
    )
    assessment: Mapped["Assessment | None"] = relationship(
        "Assessment",
    )
    audit_records: Mapped[list["AlertAuditRecord"]] = relationship(
        "AlertAuditRecord",
        back_populates="alert_instance",
        cascade="all, delete-orphan",
        order_by="AlertAuditRecord.transition_time.desc()",
    )


class AlertAuditRecord(Base):
    """Audit record capturing every state transition, assignment, and escalation for clinical alerts."""

    __tablename__ = "alert_audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    actor_role: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="CREATED, ACKNOWLEDGED, ASSIGNED, RESOLVED, DISMISSED, ESCALATED",
    )
    previous_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    new_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    transition_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    metadata_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationship
    alert_instance: Mapped["AlertInstance"] = relationship(
        "AlertInstance",
        back_populates="audit_records",
    )
