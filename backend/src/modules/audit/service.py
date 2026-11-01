import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit import AuditEvent

logger = logging.getLogger("astronaut_health.audit")

# Redacted keys: strictly forbid passwords, tokens, raw biometric values, and clinical notes
PROHIBITED_AUDIT_KEYS = {
    "password",
    "hashed_password",
    "token",
    "access_token",
    "authorization",
    "secret",
    "value_numeric",
    "value_structured",
    "findings",
    "symptom_identifiers",
    "controlled_notes",
    "medical_notes",
    "notes",
}


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Sanitizes audit metadata to guarantee no credentials or PHI are persisted to audit trails."""
    if not metadata:
        return None

    sanitized: dict[str, Any] = {}
    for key, val in metadata.items():
        if any(prohibited in key.lower() for prohibited in PROHIBITED_AUDIT_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(val, dict):
            sanitized[key] = sanitize_audit_metadata(val)
        else:
            sanitized[key] = val
    return sanitized


async def record_audit_event(
    session: AsyncSession,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Records an immutable audit event in the database with strict data minimization."""
    sanitized_meta = sanitize_audit_metadata(metadata)

    event = AuditEvent(
        id=uuid.uuid4(),
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        occurred_at=datetime.now(timezone.utc),
        metadata_=sanitized_meta,
    )
    session.add(event)
    await session.flush()

    logger.info(
        f"AUDIT: actor='{actor}' action='{action}' resource='{resource_type}:{resource_id}'"
    )
    return event

