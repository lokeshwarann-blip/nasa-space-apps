import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WellnessCheckInBase(BaseModel):
    crew_member_id: uuid.UUID
    sleep_duration_hours: float = Field(..., ge=0.0, le=24.0)
    sleep_quality: int = Field(..., ge=1, le=5)
    mood: int = Field(..., ge=1, le=5)
    stress: int = Field(..., ge=1, le=5)
    fatigue: int = Field(..., ge=1, le=5)
    measured_at: datetime
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("measured_at")
    @classmethod
    def validate_timezone_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (UTC required).")
        return dt


class WellnessCheckInCreate(WellnessCheckInBase):
    pass


class WellnessCheckInRead(WellnessCheckInBase):
    id: uuid.UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SymptomCheckInBase(BaseModel):
    crew_member_id: uuid.UUID
    symptom_identifiers: list[str] = Field(..., min_length=1)
    severity: Literal["MILD", "MODERATE", "SEVERE"]
    onset_time: datetime
    controlled_notes: str | None = Field(default=None, max_length=500)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("onset_time")
    @classmethod
    def validate_timezone_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (UTC required).")
        return dt


class SymptomCheckInCreate(SymptomCheckInBase):
    pass


class SymptomCheckInRead(SymptomCheckInBase):
    id: uuid.UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

