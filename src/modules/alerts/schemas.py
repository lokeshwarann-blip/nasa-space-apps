import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

AlertPriorityLiteral = Literal["INFO", "CAUTION", "CRITICAL", "EMERGENCY"]
AlertStatusLiteral = Literal["open", "acknowledged", "assigned", "resolved", "dismissed"]

VALID_ALERT_TRANSITIONS: dict[str, list[str]] = {
    "open": ["acknowledged", "assigned", "dismissed"],
    "acknowledged": ["assigned", "resolved", "dismissed"],
    "assigned": ["acknowledged", "resolved", "dismissed"],
    "resolved": ["open"],  # Reopen with medical justification
    "dismissed": ["open"],  # Reopen with justification
}


class AlertCreate(BaseModel):
    """Payload to create an alert instance from an approved clinical rule finding."""
    crew_member_id: uuid.UUID
    assessment_id: uuid.UUID | None = None
    source_finding_id: str = Field(..., max_length=128)
    rule_id: str = Field(..., max_length=64)
    rule_version: str = Field(..., max_length=32)
    indicator: str = Field(..., max_length=64)
    priority: AlertPriorityLiteral = Field(..., description="Derived strictly from approved clinical rule finding severity")
    summary: str = Field(..., max_length=255)
    details: dict[str, Any] | None = None
    event_time: datetime = Field(..., description="Actual historical timestamp when physiological event occurred")


class AlertAcknowledgeRequest(BaseModel):
    """Payload to acknowledge an open alert."""
    notes: str | None = None


class AlertAssignRequest(BaseModel):
    """Payload to assign an alert to a specific medical officer / flight surgeon."""
    assigned_to: str = Field(..., min_length=1, max_length=128, description="User ID or role of assignee")
    assignment_notes: str | None = None


class AlertResolveRequest(BaseModel):
    """Payload to record medical resolution of an alert."""
    resolution_reason: str = Field(..., min_length=5, description="Documented medical or clinical justification")


class AlertDismissRequest(BaseModel):
    """Payload to dismiss an alert."""
    dismissal_reason: str = Field(..., min_length=5, description="Auditable justification for dismissal")


class AlertEscalateRequest(BaseModel):
    """Payload to escalate an alert to higher tier operational/medical destinations."""
    escalation_target: str = Field(..., description="Operational destination, e.g. FLIGHT_SURGEON_ON_CALL, MISSION_CONTROL")
    escalation_reason: str = Field(..., min_length=5)


class AlertAuditRecordResponse(BaseModel):
    """Audit record capturing every alert transition and escalation action."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    actor_id: str
    actor_role: str
    action: str
    previous_status: str
    new_status: str
    reason: str | None = None
    transition_time: datetime
    metadata_snapshot: dict[str, Any] | None = None


class AlertInstanceResponse(BaseModel):
    """Response DTO for clinical alerts."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_identifier: str
    crew_member_id: uuid.UUID
    assessment_id: uuid.UUID | None = None
    source_finding_id: str
    idempotency_key: str
    rule_id: str
    rule_version: str
    indicator: str
    priority: str
    status: str
    summary: str
    details: dict[str, Any] | None = None
    event_time: datetime
    is_delayed: bool
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    assigned_to: str | None = None
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_reason: str | None = None
    dismissed_at: datetime | None = None
    dismissed_by: str | None = None
    dismissal_reason: str | None = None
    escalation_level: str
    delivery_status: str
    audit_records: list[AlertAuditRecordResponse] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertInstanceListResponse(BaseModel):
    """Paginated collection of alert instances."""
    items: list[AlertInstanceResponse]
    total: int
    limit: int
    offset: int

