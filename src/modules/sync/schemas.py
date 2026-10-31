import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

SyncEventTypeLiteral = Literal["MEASUREMENT", "WELLNESS_CHECK_IN", "SYMPTOM_CHECK_IN"]
SyncStatusLiteral = Literal["accepted", "duplicate", "conflict", "rejected"]


class SyncEventItem(BaseModel):
    """Single offline event submitted within a synchronization batch."""
    model_config = ConfigDict(from_attributes=True)

    client_event_id: uuid.UUID = Field(..., description="Stable client-generated event UUID for idempotency")
    crew_member_id: uuid.UUID = Field(..., description="Astronaut subject UUID")
    event_type: SyncEventTypeLiteral = Field(..., description="MEASUREMENT, WELLNESS_CHECK_IN, or SYMPTOM_CHECK_IN")
    schema_version: str = Field("1.0", max_length=16, description="Payload schema version (e.g. 1.0)")
    client_event_at: datetime = Field(..., description="Client timestamp when event was recorded offline (UTC)")
    measured_at: datetime = Field(..., description="Timestamp when physiological measurement occurred (UTC)")
    source: dict[str, Any] = Field(default_factory=dict, description="Hardware device, app version, input method provenance")
    payload: dict[str, Any] = Field(..., description="Structured domain payload")


class SyncBatchRequest(BaseModel):
    """Bounded batch of events recorded by an authenticated client during offline operations."""
    batch_id: str = Field(..., max_length=128, description="Client-generated unique batch identifier")
    client_sync_at: datetime = Field(..., description="Client timestamp when synchronization upload was dispatched")
    events: list[SyncEventItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Bounded list of events (1 to 100 per batch)",
    )


class SyncEventResult(BaseModel):
    """Per-event reconciliation outcome."""
    client_event_id: uuid.UUID
    status: SyncStatusLiteral
    entity_id: uuid.UUID | None = None
    error_code: str | None = None
    message: str | None = None


class SyncBatchSummary(BaseModel):
    """Summary metrics of batch processing."""
    total_events: int
    accepted_count: int
    duplicate_count: int
    conflict_count: int
    rejected_count: int


class SyncBatchResponse(BaseModel):
    """Response returned for a batch synchronization request."""
    batch_id: str
    server_received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: SyncBatchSummary
    results: list[SyncEventResult]

