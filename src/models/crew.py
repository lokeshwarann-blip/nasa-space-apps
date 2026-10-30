import uuid
from typing import TYPE_CHECKING, Any
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.mission import MissionMembership
    from src.models.telemetry import HealthMeasurement
    from src.models.wellness import WellnessCheckIn, SymptomCheckIn
    from src.models.clinical import Assessment


class CrewMember(Base, TimestampMixin):
    """Crew member entity tracking pseudonymous identity and operational status.
    
    Adheres strictly to PHI minimization and data policy: never stores fabricated
    records or unverified medical baselines.
    """

    __tablename__ = "crew_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    crew_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        comment="Pseudonymous crew identifier (e.g., CREW-042)",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        nullable=False,
        comment="Operational status: ACTIVE, INACTIVE, RETIRED, SUSPENDED",
    )
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Non-sensitive operational metadata (e.g. callsign, specialization, flight role)",
    )

    # Relationships
    mission_memberships: Mapped[list["MissionMembership"]] = relationship(
        "MissionMembership",
        back_populates="crew_member",
        cascade="all, delete-orphan",
    )
    measurements: Mapped[list["HealthMeasurement"]] = relationship(
        "HealthMeasurement",
        back_populates="crew_member",
        cascade="all, delete-orphan",
    )
    wellness_checkins: Mapped[list["WellnessCheckIn"]] = relationship(
        "WellnessCheckIn",
        back_populates="crew_member",
        cascade="all, delete-orphan",
    )
    symptom_checkins: Mapped[list["SymptomCheckIn"]] = relationship(
        "SymptomCheckIn",
        back_populates="crew_member",
        cascade="all, delete-orphan",
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        "Assessment",
        back_populates="crew_member",
        cascade="all, delete-orphan",
    )

