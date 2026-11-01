import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.crew import CrewMember


class HealthMeasurement(Base):
    """High-frequency physiological and biometric health measurement record."""

    __tablename__ = "health_measurements"
    __table_args__ = (
        CheckConstraint(
            "value_numeric IS NOT NULL OR value_structured IS NOT NULL",
            name="chk_measurement_has_value",
        ),
        Index("ix_measurement_crew_measured_at", "crew_member_id", "measured_at"),
        Index("ix_measurement_type_measured_at", "measurement_type", "measured_at"),
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
    measurement_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Type from registry: heart_rate, spo2, blood_pressure_systolic, etc.",
    )
    value_numeric: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Finite scalar measurement value",
    )
    value_structured: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Structured payload for complex indicators (e.g. waveform summary)",
    )
    unit: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Canonical or verified measurement unit (bpm, mmHg, degC, %)",
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Time the measurement occurred on the subject (UTC)",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Time the measurement was ingested into the system (UTC)",
    )
    input_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="WEARABLE_SENSOR",
        comment="Source input: WEARABLE_SENSOR, MANUAL_ENTRY, CLINICAL_DEVICE, LAB_REPORT",
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Provenance record: device_id, manufacturer, model, software_version",
    )
    quality_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="VERIFIED",
        comment="Data quality indicator: VERIFIED, UNVERIFIED, NOISY, DEGRADED, ANOMALOUS",
    )
    context_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Operational context: resting, post_exercise, eva, ambient_pressure_kpa",
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
        back_populates="measurements",
    )

