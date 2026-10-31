"""Unit tests for sensor adapters and future model interfaces."""
import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from src.models.telemetry import HealthMeasurement
from src.modules.adapters.base import (
    CanonicalMeasurementDTO,
    DeviceAdapterInterface,
    DevicePayloadEnvelope,
)
from src.modules.adapters.registry import DeviceAdapterRegistry
from src.modules.models.base import (
    MANDATORY_MODEL_LIMITATIONS,
    AnalysisProviderInterface,
    AnalysisRequest,
    AnalysisResultDTO,
)
from src.modules.models.service import AnalysisService


class MockDisabledAnalysisProvider(AnalysisProviderInterface):
    """Explicit mock analytical model provider labeled as disabled."""
    provider_id = "MOCK_AI_CARDIAC_FORECASTER"
    model_version = "0.1.0-alpha"
    is_enabled = False  # Strictly disabled
    capabilities = ["trend_forecasting"]

    def analyze(self, observations, context):
        return AnalysisResultDTO(
            provider_id=self.provider_id,
            model_version=self.model_version,
            status="success",
            message="Mock analysis completed.",
        )


class MockFailingAnalysisProvider(AnalysisProviderInterface):
    """Explicit mock model provider that raises an exception during execution."""
    provider_id = "MOCK_FAILING_PROVIDER"
    model_version = "1.0.0"
    is_enabled = True
    capabilities = ["signal_denoising"]

    def analyze(self, observations, context):
        raise RuntimeError("Mathematical divergence in mock numerical solver")


def test_device_payload_envelope_validation():
    """Verifies strict Pydantic boundary validation for incoming device envelopes."""
    now = datetime.now(timezone.utc)
    envelope = DevicePayloadEnvelope(
        provider_id="BIOHARNESS",
        device_id="BH-SERIAL-0042",
        event_id="EVT-VENDOR-991",
        crew_member_id=uuid.uuid4(),
        measured_at=now,
        raw_data={"hr_raw": 78},
        credentials={"api_key": "valid-key-mock"},
    )
    assert envelope.provider_id == "BIOHARNESS"
    assert envelope.credentials["api_key"] == "valid-key-mock"

    # Missing raw_data rejected
    with pytest.raises(ValidationError):
        DevicePayloadEnvelope(
            provider_id="BIOHARNESS",
            device_id="BH-SERIAL-0042",
            event_id="EVT-VENDOR-991",
            crew_member_id=uuid.uuid4(),
            measured_at=now,
            raw_data=None,  # Invalid
        )


def test_unregistered_model_provider_safety_gating():
    """Verifies that an unconfigured analysis provider returns explicit not_configured, never inventing fake outputs."""
    AnalysisService.clear()
    providers = AnalysisService.list_providers()
    assert len(providers) == 0, "No model providers must be active by default!"


def test_disabled_model_provider_safety():
    """Verifies that a registered but disabled model provider reports disabled status."""
    AnalysisService.clear()
    provider = MockDisabledAnalysisProvider()
    AnalysisService.register_provider(provider)

    listed = AnalysisService.list_providers()
    assert len(listed) == 1
    assert listed[0]["is_enabled"] is False

    AnalysisService.clear()


def test_model_result_mandatory_limitations_preserved():
    """Verifies that analytical results strictly carry the mandatory clinical limitations disclaimer."""
    result = AnalysisResultDTO(
        provider_id="TEST_ANALYTICS",
        status="success",
        message="Test run",
    )
    assert "Strictly prohibited from influencing clinical decisions" in result.limitations

