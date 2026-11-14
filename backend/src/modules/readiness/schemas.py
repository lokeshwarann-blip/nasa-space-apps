"""Response schemas for the crew readiness endpoints with frozen baselines,
Mahalanobis multivariate alerts, sensor-fault gating, and uncertainty bands.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ForecastBand(BaseModel):
    next: float
    lo: float
    hi: float
    method: str = "adaptive_conformal"


class ReadinessPoint(BaseModel):
    t: datetime
    score: float


class ReadinessAlert(BaseModel):
    metric: str
    direction: str = Field(description="'high' or 'low' relative to the person's own baseline")
    severity: str = Field(description="'watch' or 'high'")
    message: str


class DriftIncident(BaseModel):
    incident_id: str
    severity: str = Field(description="'watch' or 'high'")
    title: str = Field(description="Consolidated clinical summary, e.g. 'Cardiopulmonary & Sleep Strain'")
    metrics_involved: list[str]
    summary: str


class EnvironmentalAlert(BaseModel):
    hazard_type: str = Field(description="e.g. 'RADIATION_SOLAR_EVENT'")
    severity: str = Field(description="'watch' or 'high'")
    metric: str
    observed_value: float
    unit: str
    threshold: float
    message: str


class FeatureAttribution(BaseModel):
    metric: str
    contribution: float = Field(description="Feature contribution to squared Mahalanobis distance (z_i * (Sigma^-1 * z)_i)")
    percentage: float = Field(description="Percentage of total squared distance explained by this feature")
    z_score: float = Field(description="Standardized deviation from baseline")


class MahalanobisAlert(BaseModel):
    distance_squared: float
    threshold: float
    degrees_of_freedom: int
    threshold_method: str = Field(default="Hotelling_T2_F", description="Threshold calibration method")
    shrinkage_warning: str | None = Field(default=None, description="Warning if Ledoit-Wolf shrinkage is near identity")
    top_contributors: list[FeatureAttribution] = []
    message: str = Field(description="Combined anomaly indicator (explanatory attribution, not causal diagnosis)")


class SignalBaselineSchema(BaseModel):
    metric: str
    center: float
    effective_dispersion: float
    n_observations: int
    n_valid_days: int
    coverage_fraction: float
    sufficiency_tier: str = Field(description="'insufficient', 'low', 'moderate', 'high'")


class BaselineMetadata(BaseModel):
    version_id: str
    created_at: str
    calibration_window_start: str
    calibration_window_end: str
    recalibration_reason: str
    method: str
    total_raw_rows: int
    quality_exclusions_count: int
    overall_sufficiency: str = Field(description="'insufficient', 'low', 'moderate', 'high'")
    shrinkage_intensity: float = 0.0
    sample_size_ratio: float = 0.0
    signals: dict[str, SignalBaselineSchema] = {}


class BaselineRecalibrateRequest(BaseModel):
    crew_id: uuid.UUID
    reason: str = Field(description="Documented medical or operational reason, e.g., 'Mission phase transition to EVA'")
    calibration_window_days: int = Field(default=14, ge=4, le=60)
    method: str = Field(default="robust", description="'robust' (median/MAD) or 'mean_sd'")


class UncertaintyBand(BaseModel):
    score_lo: float
    score_hi: float
    confidence_tier: str


class CrewReadinessResponse(BaseModel):
    crew_id: uuid.UUID
    status: str = Field(description="Readiness status: 'NOMINAL', 'WATCH', 'CRITICAL', or 'INSUFFICIENT_DATA'")
    data_status: str = Field(default="COMPLETE", description="Data pipeline status: 'COMPLETE', 'INSUFFICIENT_DATA', or 'FAULTY_SENSOR'")
    readiness_category: str = Field(default="NOMINAL", description="'NOMINAL', 'WATCH', or 'CRITICAL'")
    data_sufficiency: str = Field(default="moderate", description="Data sufficiency tier: 'insufficient', 'low', 'moderate', 'high'")
    readiness: float | None = Field(default=None, description="0-100, 100 = at or better than own baseline")
    uncertainty_band: UncertaintyBand | None = None
    config_hash: str = Field(default="MELIORA-V1-CFG", description="Hash of active detector configuration and thresholds")
    readiness_series: list[ReadinessPoint] = []
    forecast: dict[str, ForecastBand] = {}
    drift_alerts: list[ReadinessAlert] = []
    incidents: list[DriftIncident] = []
    environmental_alerts: list[EnvironmentalAlert] = []
    mahalanobis_alert: MahalanobisAlert | None = None
    baseline_metadata: BaselineMetadata | None = None
    observations_used: int = 0
    disclaimer: str = (
        "Decision support only. Flags trends for review by a flight surgeon; not a diagnosis. "
        "Readiness scores and Mahalanobis distances are anomaly metrics, not medical risks or disease probabilities. "
        "Radiation absorbed dose rate (uGy/h) is an environmental overlay, never mixed into biological readiness."
    )


class ReadinessOverviewResponse(BaseModel):
    crews: list[CrewReadinessResponse]
