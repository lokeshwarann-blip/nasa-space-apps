import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from src.modules.clinical.rules import ClinicalRuleFinding


class AssessmentRequest(BaseModel):
    """Payload to trigger an explainable clinical rule evaluation."""
    crew_member_id: uuid.UUID | None = Field(
        default=None,
        description="Target crew UUID. Defaults to authenticated crew member if omitted.",
    )
    operational_context: str = Field(
        default="MICROGRAVITY",
        description="Operational context (e.g. MICROGRAVITY, EVA, SLEEP, RESTING)",
    )
    evaluation_window_hours: float = Field(
        default=24.0,
        ge=0.5,
        le=168.0,
        description="Time horizon (in hours) of historical observations to evaluate.",
    )
    target_measurement_types: list[str] | None = Field(
        default=None,
        description="Optional subset of measurement types to evaluate.",
    )


class InputEvaluationSummary(BaseModel):
    """Audit of input observations analyzed during the assessment."""
    available_inputs: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    invalid_inputs: list[str] = Field(default_factory=list)
    stale_inputs: list[str] = Field(default_factory=list)
    out_of_scope_inputs: list[str] = Field(default_factory=list)


class AssessmentResponse(BaseModel):
    """Standardized, explainable assessment response."""
    id: uuid.UUID
    crew_member_id: uuid.UUID
    assessed_at: datetime
    engine_version: str = "engine-v1.0.0"
    ruleset_version: str
    assessment_status: Literal[
        "assessed_no_findings",
        "partially_assessed",
        "not_assessed",
        "insufficient_evidence",
        "needs_review",
    ]
    status_reason: str
    findings: list[ClinicalRuleFinding]
    input_evaluation: InputEvaluationSummary
    evaluated_measurement_ids: list[uuid.UUID]
    data_quality_info: dict[str, Any]
    technical_errors: list[dict[str, str]]
    reproducibility_hash: str

    model_config = ConfigDict(from_attributes=True)


class AssessmentListResponse(BaseModel):
    """Paginated collection of past assessments."""
    items: list[AssessmentResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

