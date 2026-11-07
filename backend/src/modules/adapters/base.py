import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CanonicalMeasurementDTO(BaseModel):
    """Normalized biometric observation parsed by a provider adapter."""
    model_config = ConfigDict(from_attributes=True)

    measurement_type: str = Field(..., description="Registry indicator type (e.g. heart_rate)")
    value_numeric: float = Field(..., description="Finite numeric reading in canonical or convertible unit")
    unit: str = Field(..., description="Reading unit (e.g. bpm, degC, mmHg)")
    measured_at: datetime = Field(..., description="Physiological observation timestamp in UTC")
    context_metadata: dict[str, Any] | None = None
    quality_status: str = Field("VERIFIED", description="Signal quality status (VERIFIED, NOISY, DEGRADED)")


class DevicePayloadEnvelope(BaseModel):
    """Standard envelope for incoming telemetry payloads from external health hardware."""
    model_config = ConfigDict(from_attributes=True)

    provider_id: str = Field(..., max_length=64, description="Provider/manufacturer code (e.g. BIOHARNESS, OMRON)")
    device_id: str = Field(..., max_length=128, description="Hardware serial number or device identifier")
    event_id: str = Field(..., max_length=128, description="Provider unique event UUID for deduplication")
    crew_member_id: uuid.UUID = Field(..., description="Subject astronaut UUID")
    measured_at: datetime = Field(..., description="Measurement timestamp from device clock (UTC)")
    transmitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Transmission dispatch timestamp (UTC)",
    )
    raw_data: dict[str, Any] = Field(..., description="Vendor-specific reading dictionary")
    credentials: dict[str, str] | None = Field(
        None,
        description="Device access token, mutual auth signature, or API key",
    )


class DeviceAdapterInterface(ABC):
    """Abstract provider-neutral adapter for authenticated health devices or data services."""

    provider_id: str
    version: str
    is_connected: bool = False  # Set to True only when actual hardware link is verified
    supported_measurement_types: list[str] = []

    @abstractmethod
    def validate_credentials(self, credentials: dict[str, str] | None) -> bool:
        """Verifies mutual auth tokens, API keys, or HMAC signatures from device."""
        pass

    @abstractmethod
    def parse_and_validate(self, envelope: DevicePayloadEnvelope) -> list[CanonicalMeasurementDTO]:
        """Parses vendor-specific raw_data and validates plausible physiological constraints."""
        pass

