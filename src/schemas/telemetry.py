import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthMeasurementBase(BaseModel):
    crew_member_id: uuid.UUID
    measurement_type: str = Field(..., max_length=64)
    value_numeric: float | None = None
    value_structured: dict[str, Any] | None = None
    unit: str = Field(..., max_length=32)
    measured_at: datetime
    input_method: str = Field(default="WEARABLE_SENSOR", max_length=32)
    provenance: dict[str, Any] = Field(default_factory=dict)
    quality_status: str = Field(default="VERIFIED", max_length=32)
    context_metadata: dict[str, Any] | None = None

    @field_validator("measured_at")
    @classmethod
    def validate_timezone_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (UTC required).")
        return dt


class HealthMeasurementCreate(HealthMeasurementBase):
    pass


class HealthMeasurementRead(HealthMeasurementBase):
    id: uuid.UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

