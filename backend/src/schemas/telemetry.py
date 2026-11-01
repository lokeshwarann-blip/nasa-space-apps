import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_measurement_timestamp(dt: datetime) -> datetime:
    """Validates that timestamp is timezone-aware, not in the future, and not excessively stale."""
    if dt.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware (UTC required).")
    
    now_utc = datetime.now(timezone.utc)
    # Reject timestamps more than 5 minutes in the future (clock skew tolerance)
    if dt > now_utc + timedelta(minutes=5):
        raise ValueError("Measurement timestamp cannot be in the future.")
    
    # Reject timestamps older than 50 years
    if dt < now_utc - timedelta(days=365 * 50):
        raise ValueError("Measurement timestamp is excessively stale.")
    
    return dt


class MeasurementCreateRequest(BaseModel):
    """Payload for submitting an objective physiological measurement."""
    crew_member_id: uuid.UUID | None = Field(
        default=None,
        description="Target crew UUID. If omitted for CREW_MEMBER, defaults to authenticated user's ID.",
    )
    measurement_type: str = Field(..., min_length=2, max_length=64)
    value_numeric: float | None = None
    value_structured: dict[str, Any] | None = None
    unit: str = Field(..., min_length=1, max_length=32)
    measured_at: datetime
    input_method: str = Field(default="WEARABLE_SENSOR", max_length=32)
    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="Device identifier, sensor model, software build, calibration date",
    )
    context_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Posture, activity state, operator notes, ambient pressure",
    )

    @field_validator("measured_at")
    @classmethod
    def check_timestamp(cls, dt: datetime) -> datetime:
        return validate_measurement_timestamp(dt)

    @field_validator("value_numeric")
    @classmethod
    def check_finite_number(cls, v: float | None) -> float | None:
        if v is not None:
            if math.isnan(v) or math.isinf(v):
                raise ValueError("Measurement value must be a finite numeric value.")
        return v


class MeasurementResponse(BaseModel):
    """Normalized response schema for health measurements."""
    id: uuid.UUID
    crew_member_id: uuid.UUID
    measurement_type: str
    value_numeric: float | None = None
    value_structured: dict[str, Any] | None = None
    unit: str
    measured_at: datetime
    recorded_at: datetime
    input_method: str
    provenance: dict[str, Any]
    quality_status: str
    context_metadata: dict[str, Any] | None = None
    original_value: float | None = None
    original_unit: str | None = None
    conversion_audit: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class MeasurementInvalidateRequest(BaseModel):
    """Payload for marking an existing measurement as invalidated."""
    reason: str = Field(..., min_length=3, max_length=255, description="Auditable justification for invalidation")


class MeasurementListResponse(BaseModel):
    """Paginated collection of measurements."""
    items: list[MeasurementResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


# Backwards compatibility aliases for Phase 2
HealthMeasurementCreate = MeasurementCreateRequest
HealthMeasurementRead = MeasurementResponse
