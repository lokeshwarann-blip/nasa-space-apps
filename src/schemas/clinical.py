import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GuidanceSourceBase(BaseModel):
    source_identifier: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    publisher: str = Field(..., max_length=255)
    document_url: str | None = None
    version: str = Field(..., max_length=32)
    review_state: str = Field(default="APPROVED", max_length=32)
    reviewer_metadata: dict[str, Any] | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approval_status: str = Field(default="ACTIVE", max_length=32)


class GuidanceSourceCreate(GuidanceSourceBase):
    pass


class GuidanceSourceRead(GuidanceSourceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicalRuleBase(BaseModel):
    guidance_source_id: uuid.UUID
    rule_identifier: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    description: str
    applicable_context: str = Field(default="MICROGRAVITY", max_length=64)
    measurement_type: str = Field(..., max_length=64)
    parameters: dict[str, Any]
    review_state: str = Field(default="APPROVED", max_length=32)
    approval_status: str = Field(default="ACTIVE", max_length=32)


class ClinicalRuleCreate(ClinicalRuleBase):
    pass


class ClinicalRuleRead(ClinicalRuleBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentBase(BaseModel):
    subject_id: uuid.UUID
    assessed_at: datetime
    engine_version: str = Field(..., max_length=64)
    ruleset_version: str = Field(..., max_length=64)
    assessment_status: Literal["NOMINAL", "CAUTION", "CRITICAL", "INSUFFICIENT_DATA"]
    findings: dict[str, Any]
    input_measurement_ids: list[str] = Field(default_factory=list)
    data_quality_info: dict[str, Any] = Field(default_factory=dict)

    @field_validator("assessed_at")
    @classmethod
    def validate_timezone_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (UTC required).")
        return dt


class AssessmentCreate(AssessmentBase):
    pass


class AssessmentRead(AssessmentBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

