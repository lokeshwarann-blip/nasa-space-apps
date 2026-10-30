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
    from src.models.crew import CrewMember
    from src.models.telemetry import HealthMeasurement


class TaskDefinition(Base, TimestampMixin):
    """Reusable blueprint/template for crew health and wellness tasks."""

    __tablename__ = "task_definitions"
    __table_args__ = (
        CheckConstraint(
            "category IN ('MEASUREMENT_REMINDER', 'WELLNESS_CHECK_IN', 'FOLLOW_UP_ACTION', 'GENERAL')",
            name="chk_task_definition_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    definition_identifier: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique identifier for template (e.g. TASK-DEF-DAILY-VITALS)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="MEASUREMENT_REMINDER, WELLNESS_CHECK_IN, FOLLOW_UP_ACTION, GENERAL",
    )
    target_measurement_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Target telemetry type (e.g. heart_rate, blood_pressure)",
    )
    target_check_in_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="WELLNESS or SYMPTOM",
    )
    recurrence_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Schedule configuration (e.g. frequency, interval, due_window_hours)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Actor who authorized this schedule definition",
    )

    # Relationships
    instances: Mapped[list["TaskInstance"]] = relationship(
        "TaskInstance",
        back_populates="task_definition",
    )


class TaskInstance(Base, TimestampMixin):
    """Crew-specific task assignment with due windows and completion records."""

    __tablename__ = "task_instances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'CANCELLED', 'MISSED')",
            name="chk_task_instance_status",
        ),
        Index("ix_task_crew_status", "crew_member_id", "status"),
        Index("ix_task_due_window", "due_start", "due_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
        comment="PENDING, COMPLETED, CANCELLED, MISSED",
    )
    due_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Start of due window (UTC)",
    )
    due_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Deadline / end of due window (UTC)",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when task was fulfilled (UTC)",
    )
    completion_source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="CREW_PORTAL, DEVICE_SYNC, FLIGHT_SURGEON",
    )
    reference_measurement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("health_measurements.id", ondelete="SET NULL"),
        nullable=True,
        comment="Associated telemetry observation if fulfilled by measurement",
    )
    reference_check_in_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Associated check-in UUID if fulfilled by wellness report",
    )
    completion_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    task_definition: Mapped["TaskDefinition | None"] = relationship(
        "TaskDefinition",
        back_populates="instances",
    )
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
    )
    audit_records: Mapped[list["TaskAuditRecord"]] = relationship(
        "TaskAuditRecord",
        back_populates="task_instance",
        cascade="all, delete-orphan",
        order_by="TaskAuditRecord.recorded_at.desc()",
    )


class TaskAuditRecord(Base):
    """Audit record capturing every state transition and administrative action for tasks."""

    __tablename__ = "task_audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_instances.id", ondelete="CASCADE"),
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
        comment="CREATED, COMPLETED, CANCELLED, UPDATED",
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    task_instance: Mapped["TaskInstance"] = relationship(
        "TaskInstance",
        back_populates="audit_records",
    )
