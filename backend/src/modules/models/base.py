import uuid
from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from src.models.telemetry import HealthMeasurement

AnalysisStatusLiteral = Literal["success", "not_configured", "disabled", "insufficient_data"]

MANDATORY_MODEL_LIMITATIONS = (
    "EXPERIMENTAL / FUTURE MODEL INTERFACE. Strictly prohibited from influencing clinical decisions, "
    "setting diagnostic thresholds, or independently activating clinical alerts without separate formal "
    "institutional authorization, empirical validation, and flight surgeon review."
)


class AnalysisRequest(BaseModel):
    """Request payload for optional future analytical model processing."""
    model_config = ConfigDict(from_attributes=True)

    crew_member_id: uuid.UUID
    provider_id: str = Field(..., max_length=64, description="Target analytical model identifier")
    capability: str = Field(..., max_length=64, description="Requested capability (e.g. trend_forecasting, signal_denoising)")
    measurement_types: list[str] = Field(default_factory=lambda: ["heart_rate"], description="Input telemetry series")
    time_window_hours: float = Field(24.0, ge=1.0, le=168.0, description="Input observation time window")


class AnalysisResultDTO(BaseModel):
    """Standardized response from an analytical provider."""
    model_config = ConfigDict(from_attributes=True)

    provider_id: str
    model_version: str | None = None
    status: AnalysisStatusLiteral = Field(..., description="success, not_configured, disabled, insufficient_data")
    message: str
    predictions: dict[str, Any] = Field(default_factory=dict, description="Model predictions or forecast points")
    uncertainty: dict[str, Any] | None = Field(None, description="Confidence bounds or uncertainty intervals")
    input_provenance: dict[str, Any] = Field(default_factory=dict, description="Traceability to input observation IDs")
    limitations: str = Field(default=MANDATORY_MODEL_LIMITATIONS)


class AnalysisProviderInterface(ABC):
    """Abstract interface for optional, versioned future analytical models."""

    provider_id: str
    model_version: str
    is_enabled: bool = False  # POLICY: Strictly disabled by default
    capabilities: list[str] = []

    @abstractmethod
    def analyze(
        self,
        observations: list[HealthMeasurement],
        context: dict[str, Any],
    ) -> AnalysisResultDTO:
        """Executes analytical model on verified, authorized observations."""
        pass

