import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.crew import CrewMember


class User(Base, TimestampMixin):
    """User account entity for authentication and role-based access control.
    
    Security Guarantee: Never stores plaintext passwords; stores salted, hashed passwords.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username", unique=True),
        Index("ix_users_role", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="Unique login username",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Cryptographically hashed password (Argon2id)",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Logical role: CREW_MEMBER, FLIGHT_SURGEON, ADMIN",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Account active status",
    )
    crew_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated crew member identity for CREW_MEMBER role",
    )
    assigned_crew_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Authorized scope for FLIGHT_SURGEON: list of permitted crew member UUID strings",
    )

    # Relationships
    crew_member: Mapped["CrewMember | None"] = relationship(
        "CrewMember",
        foreign_keys=[crew_member_id],
    )
