import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CoverageGap(BaseModel):
    """Detectable gap in observation coverage exceeding expected duration."""
    gap_start: datetime
    gap_end: datetime
    gap_duration_seconds: float
    gap_duration_hours: float


class DataQualitySummary(BaseModel):
    """Metadata regarding telemetry coverage and data integrity."""
    total_records_ingested: int
    valid_observations_count: int
    invalidated_observations_count: int
    latest_observation_at: datetime | None = None
    freshness_seconds: float | None = None


class SummaryStatistics(BaseModel):
    """Deterministic descriptive statistics derived from actual observations."""
    count: int
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    median: float | None = None
    sample_std_dev: float | None = None
    calculation_method: str = "EXACT_ARITHMETIC_DETERMINISTIC"
    unavailable_reasons: dict[str, str] = Field(default_factory=dict)


class BaselineResponse(BaseModel):
    """Personal baseline derived solely from actual historical observations."""
    crew_member_id: uuid.UUID
    measurement_type: str
    canonical_unit: str
    baseline_status: Literal["CONFIGURED", "UNAVAILABLE"]
    unavailable_reason: str | None = None
    method: str | None = None
    method_version: str | None = None
    calculated_at: datetime | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    observation_count: int = 0
    baseline_values: dict[str, float] | None = None


class TrendObservation(BaseModel):
    """Individual observation point within a longitudinal series."""
    id: uuid.UUID
    measured_at: datetime
    value_numeric: float
    unit: str
    quality_status: str
    is_statistical_outlier: bool = False
    outlier_observation: str | None = None  # Statistical note only, NEVER a clinical diagnosis
    provenance: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class TrendSeriesResponse(BaseModel):
    """Full longitudinal trend series response."""
    crew_member_id: uuid.UUID
    measurement_type: str
    canonical_unit: str
    time_window: dict[str, Any]
    observation_count: int
    observations: list[TrendObservation]
    data_quality: DataQualitySummary
    coverage_gaps: list[CoverageGap]
    statistics: SummaryStatistics
    baseline: BaselineResponse | None = None


class TrendSummaryResponse(BaseModel):
    """Condensed summary statistics response without full raw observation points."""
    crew_member_id: uuid.UUID
    measurement_type: str
    canonical_unit: str
    time_window: dict[str, Any]
    observation_count: int
    data_quality: DataQualitySummary
    statistics: SummaryStatistics
    baseline: BaselineResponse | None = None
