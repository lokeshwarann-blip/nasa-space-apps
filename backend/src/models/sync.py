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

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.crew import CrewMember


class SyncEventRecord(Base):
    """Database-enforced idempotency and reconciliation record for offline synchronization."""

    __tablename__ = "sync_event_records"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('MEASUREMENT', 'WELLNESS_CHECK_IN', 'SYMPTOM_CHECK_IN')",
            name="chk_sync_event_type",
        ),
        CheckConstraint(
            "sync_status IN ('accepted', 'duplicate', 'conflict', 'rejected')",
            name="chk_sync_status",
        ),
        Index("ix_sync_crew_received", "crew_member_id", "server_received_at"),
        Index("ix_sync_event_type_measured", "event_type", "measured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        index=True,
        nullable=False,
        comment="Client-generated stable event UUID for idempotency",
    )
    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="MEASUREMENT, WELLNESS_CHECK_IN, or SYMPTOM_CHECK_IN",
    )
    schema_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="1.0",
        comment="Payload schema version (e.g. 1.0)",
    )
    client_event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Client timestamp when event was recorded offline (UTC)",
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Subject measurement timestamp (UTC)",
    )
    server_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Server timestamp when batch was received (UTC)",
    )
    payload_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of normalized payload for conflict detection",
    )
    sync_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="accepted, duplicate, conflict, rejected",
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of created measurement or check-in record",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    crew_member: Mapped["CrewMember"] = relationship(
        "CrewMember",
    )

