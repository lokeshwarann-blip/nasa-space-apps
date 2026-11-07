import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas.telemetry import validate_measurement_timestamp


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
        return validate_measurement_timestamp(dt)


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
        return validate_measurement_timestamp(dt)


class SymptomCheckInCreate(SymptomCheckInBase):
    pass


class SymptomCheckInRead(SymptomCheckInBase):
    id: uuid.UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckInCreateRequest(BaseModel):
    """Unified check-in payload discriminating between subjective wellness and symptom reports."""
    check_in_type: Literal["WELLNESS", "SYMPTOM"]
    crew_member_id: uuid.UUID | None = Field(
        default=None,
        description="Target crew UUID. Defaults to authenticated crew member if omitted.",
    )
    # Wellness fields
    measured_at: datetime | None = None
    sleep_duration_hours: float | None = Field(default=None, ge=0.0, le=24.0)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    mood: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    fatigue: int | None = Field(default=None, ge=1, le=5)

    # Symptom fields
    symptom_identifiers: list[str] | None = None
    severity: Literal["MILD", "MODERATE", "SEVERE"] | None = None
    onset_time: datetime | None = None
    controlled_notes: str | None = Field(default=None, max_length=500)

    # Common
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_type_specific_requirements(self) -> "CheckInCreateRequest":
        if self.check_in_type == "WELLNESS":
            if self.sleep_duration_hours is None:
                raise ValueError("sleep_duration_hours is required for WELLNESS check-ins.")
            if self.sleep_quality is None or self.mood is None or self.stress is None or self.fatigue is None:
                raise ValueError("sleep_quality, mood, stress, and fatigue ratings (1-5) are required for WELLNESS check-ins.")
            if self.measured_at is None:
                raise ValueError("measured_at timestamp is required for WELLNESS check-ins.")
            self.measured_at = validate_measurement_timestamp(self.measured_at)

        elif self.check_in_type == "SYMPTOM":
            if not self.symptom_identifiers:
                raise ValueError("symptom_identifiers list is required for SYMPTOM check-ins.")
            if not self.severity:
                raise ValueError("severity rating ('MILD', 'MODERATE', 'SEVERE') is required for SYMPTOM check-ins.")
            if self.onset_time is None:
                raise ValueError("onset_time timestamp is required for SYMPTOM check-ins.")
            self.onset_time = validate_measurement_timestamp(self.onset_time)

        return self


class CheckInResponse(BaseModel):
    """Normalized response schema for crew check-ins."""
    id: uuid.UUID
    check_in_type: Literal["WELLNESS", "SYMPTOM"]
    crew_member_id: uuid.UUID
    recorded_at: datetime
    timestamp: datetime
    details: dict[str, Any]
    provenance: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class CheckInListResponse(BaseModel):
    """Paginated collection of crew check-ins."""
    items: list[CheckInResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
