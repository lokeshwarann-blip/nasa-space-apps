import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, Index, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class AuditEvent(Base):
    """Immutable audit log recording user and system actions on sensitive resources."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_actor_occurred_at", "actor", "occurred_at"),
        Index("ix_audit_resource_occurred_at", "resource_type", "resource_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Actor identity: crew_id, user_id, or system service name",
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Operation: CREATE, READ, UPDATE, DELETE, INGEST, ASSESS, LOGIN",
    )
    resource_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Entity type: crew_member, health_measurement, assessment, clinical_rule",
    )
    resource_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Target resource identifier or UUID",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="UTC timestamp of the audited action",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="Non-sensitive operational context (IP, request_id, user-agent). No PHI or credentials.",
    )

