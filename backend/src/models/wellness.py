import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.crew import CrewMember


class WellnessCheckIn(Base):
    """Subjective daily crew self-assessment check-in."""

    __tablename__ = "wellness_checkins"
    __table_args__ = (
        CheckConstraint("sleep_duration_hours >= 0.0 AND sleep_duration_hours <= 24.0", name="chk_sleep_duration_range"),
        CheckConstraint("sleep_quality >= 1 AND sleep_quality <= 5", name="chk_sleep_quality_range"),
        CheckConstraint("mood >= 1 AND mood <= 5", name="chk_mood_range"),
        CheckConstraint("stress >= 1 AND stress <= 5", name="chk_stress_range"),
        CheckConstraint("fatigue >= 1 AND fatigue <= 5", name="chk_fatigue_range"),
        Index("ix_wellness_crew_measured_at", "crew_member_id", "measured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sleep_duration_hours: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Total sleep duration in hours (0.0 to 24.0)",
    )
    sleep_quality: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Subjective sleep rating on 1-5 scale (1=very poor, 5=excellent)",
    )
    mood: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Subjective mood rating on 1-5 scale (1=very low, 5=excellent)",
    )
    stress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Subjective stress rating on 1-5 scale (1=no stress, 5=extreme stress)",
    )
    fatigue: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Subjective fatigue rating on 1-5 scale (1=fully rested, 5=exhausted)",
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Time the check-in represents (UTC)",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Time the entry was stored (UTC)",
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Client device, application version, or input provenance",
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
        back_populates="wellness_checkins",
    )


class SymptomCheckIn(Base):
    """Structured crew symptom report with controlled vocabulary and severity."""

    __tablename__ = "symptom_checkins"
    __table_args__ = (
        CheckConstraint("severity IN ('MILD', 'MODERATE', 'SEVERE')", name="chk_symptom_severity"),
        Index("ix_symptom_crew_onset_time", "crew_member_id", "onset_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symptom_identifiers: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        comment="Structured symptom identifiers from standard vocabulary (e.g. ['HEADACHE', 'MOTION_SICKNESS'])",
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Reported severity: MILD, MODERATE, SEVERE",
    )
    onset_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Estimated onset timestamp in UTC",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Ingestion timestamp in UTC",
    )
    controlled_notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Controlled, non-sensitive narrative note (sanitized)",
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Submission client and device provenance",
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
        back_populates="symptom_checkins",
    )

