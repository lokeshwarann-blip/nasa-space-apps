import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Quest(Base, TimestampMixin):
    __tablename__ = "quests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=True)
    evidence_level: Mapped[str] = mapped_column(String(32), nullable=False)


class QuestProgress(Base, TimestampMixin):
    __tablename__ = "quest_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quest_id: Mapped[str] = mapped_column(String(64), ForeignKey("quests.id"), nullable=False)
    crew_id: Mapped[str] = mapped_column(String(64), nullable=False, default="team")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class XPEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    quest_id: Mapped[str] = mapped_column(String(64), ForeignKey("quests.id"), nullable=False)
    crew_id: Mapped[str] = mapped_column(String(64), nullable=False, default="team")
    xp_gained: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class TeamStreak(Base, TimestampMixin):
    __tablename__ = "streaks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    streak_type: Mapped[str] = mapped_column(String(32), default="team", nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    freeze_days_remaining: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    last_activity_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Unlock(Base):
    __tablename__ = "unlocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    crew_id: Mapped[str] = mapped_column(String(64), nullable=False, default="team")
    unlock_key: Mapped[str] = mapped_column(String(64), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("crew_id", "unlock_key", name="uq_crew_unlock"),
    )
