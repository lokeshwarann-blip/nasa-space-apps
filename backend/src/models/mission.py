import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.crew import CrewMember


class Mission(Base, TimestampMixin):
    """Spaceflight or analog mission entity."""

    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    mission_identifier: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Mission designation code (e.g., ISS-EXP-71, ARTEMIS-II)",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    mission_phase: Mapped[str] = mapped_column(
        String(32),
        default="PRE_FLIGHT",
        nullable=False,
        comment="Phase: PRE_FLIGHT, LAUNCH_ASCENT, ORBIT, LUNAR_SURFACE, REENTRY, POST_FLIGHT",
    )
    operational_environment: Mapped[str] = mapped_column(
        String(32),
        default="MICROGRAVITY",
        nullable=False,
        comment="Environment: MICROGRAVITY, LUNAR_SURFACE, MARS_SURFACE, ANALOG, EARTH_1G",
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    memberships: Mapped[list["MissionMembership"]] = relationship(
        "MissionMembership",
        back_populates="mission",
        cascade="all, delete-orphan",
    )


class MissionMembership(Base, TimestampMixin):
    """Crew-to-mission association with authorization-relevant roles and validity periods."""

    __tablename__ = "mission_memberships"
    __table_args__ = (
        UniqueConstraint("crew_member_id", "mission_id", "role", name="uq_crew_mission_role"),
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
    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Mission role: COMMANDER, PILOT, FLIGHT_ENGINEER, MEDICAL_OFFICER, SPECIALIST",
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
        back_populates="mission_memberships",
    )
    mission: Mapped["Mission"] = relationship(
        "Mission",
        back_populates="memberships",
    )

