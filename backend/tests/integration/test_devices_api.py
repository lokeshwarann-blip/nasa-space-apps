"""Integration tests for Sensor Device Adapters and Future Analytical Model APIs.

Verifies:
- External device envelope ingestion, credential authentication, and parsing.
- Duplicate provider event deduplication.
- Unauthorized device submission rejection (BOLA prevention).
- Missing/invalid credentials rejection (401).
- Unsupported provider rejection (400).
- Future model analysis endpoint returning not_configured by default.
"""
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_access_token
from src.models.crew import CrewMember
from src.modules.adapters.base import (
    CanonicalMeasurementDTO,
    DeviceAdapterInterface,
    DevicePayloadEnvelope,
)
from src.modules.adapters.registry import device_adapter_registry
from src.modules.models.service import AnalysisService


class MockHeartRateDeviceAdapter(DeviceAdapterInterface):
    """Explicitly labeled mock adapter for isolated interface testing only."""
    provider_id = "MOCK_BIOHARNESS"
    version = "1.0.0"
    is_connected = True
    supported_measurement_types = ["heart_rate"]

    def validate_credentials(self, credentials: dict[str, str] | None) -> bool:
        if not credentials:
            return False
        return credentials.get("device_token") == "valid-device-token-123"

    def parse_and_validate(self, envelope: DevicePayloadEnvelope) -> list[CanonicalMeasurementDTO]:
        raw = envelope.raw_data
        bpm = float(raw["pulse_rate"])
        return [
            CanonicalMeasurementDTO(
                measurement_type="heart_rate",
                value_numeric=bpm,
                unit="bpm",
                measured_at=envelope.measured_at,
            )
        ]


@pytest.fixture
def test_crew(db_session):
    """Creates test crew members in database."""
    crew_1_id = uuid.uuid4()
    crew_2_id = uuid.uuid4()

    c1 = CrewMember(
        id=crew_1_id,
        crew_id="CREW-042",
        status="ACTIVE",
        profile_metadata={"name": "Astronaut Mark"},
    )
    c2 = CrewMember(
        id=crew_2_id,
        crew_id="CREW-043",
        status="ACTIVE",
        profile_metadata={"name": "Astronaut Lewis"},
    )
    db_session.add_all([c1, c2])
    return {
        "crew_1": crew_1_id,
        "crew_2": crew_2_id,
    }


@pytest.fixture
def crew_1_token(test_crew):
    return create_access_token(
        subject="astronaut_mark",
        role="CREW_MEMBER",
        crew_member_id=str(test_crew["crew_1"]),
    )


@pytest.fixture
def crew_2_token(test_crew):
    return create_access_token(
        subject="astronaut_lewis",
        role="CREW_MEMBER",
        crew_member_id=str(test_crew["crew_2"]),
    )


@pytest.fixture(autouse=True)
def manage_mock_adapter():
    """Registers mock adapter for isolated tests and ensures clean teardown."""
    mock_adapter = MockHeartRateDeviceAdapter()
    device_adapter_registry.register(mock_adapter)
    yield
    device_adapter_registry.clear()
    AnalysisService.clear()


# ==============================================================================
# 1. Device Ingestion & Authentication Tests
# ==============================================================================

def test_device_telemetry_ingestion(client: TestClient, crew_1_token, test_crew):
    """Verifies that an authenticated external device envelope is parsed and persisted."""
    now = datetime.now(timezone.utc)
    envelope = {
        "provider_id": "MOCK_BIOHARNESS",
        "device_id": "BH-001",
        "event_id": "DEV-EVT-001",
        "crew_member_id": str(test_crew["crew_1"]),
        "measured_at": now.isoformat(),
        "raw_data": {"pulse_rate": 76.5},
        "credentials": {"device_token": "valid-device-token-123"},
    }

    res = client.post(
        "/api/v1/devices/ingest",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=envelope,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["provider_id"] == "MOCK_BIOHARNESS"
    assert data["records_ingested"] == 1
    assert data["records"][0]["status"] == "ingested"
    assert data["records"][0]["value_numeric"] == 76.5


def test_duplicate_provider_events(client: TestClient, crew_1_token, test_crew):
    """Verifies that re-transmitting the same device event_id is deduplicated idempotently."""
    now = datetime.now(timezone.utc)
    envelope = {
        "provider_id": "MOCK_BIOHARNESS",
        "device_id": "BH-002",
        "event_id": "DEV-EVT-DUP-99",
        "crew_member_id": str(test_crew["crew_1"]),
        "measured_at": now.isoformat(),
        "raw_data": {"pulse_rate": 82.0},
        "credentials": {"device_token": "valid-device-token-123"},
    }

    # First ingestion
    r1 = client.post("/api/v1/devices/ingest", headers={"Authorization": f"Bearer {crew_1_token}"}, json=envelope)
    assert r1.status_code == 201
    assert r1.json()["records"][0]["status"] == "ingested"

    # Second ingestion with identical event_id
    r2 = client.post("/api/v1/devices/ingest", headers={"Authorization": f"Bearer {crew_1_token}"}, json=envelope)
    assert r2.status_code == 201
    assert r2.json()["records"][0]["status"] == "duplicate"


def test_missing_or_invalid_credentials(client: TestClient, crew_1_token, test_crew):
    """Verifies that invalid or missing device credentials are rejected with 401 Unauthorized."""
    now = datetime.now(timezone.utc)
    envelope = {
        "provider_id": "MOCK_BIOHARNESS",
        "device_id": "BH-003",
        "event_id": "DEV-EVT-AUTH-FAIL",
        "crew_member_id": str(test_crew["crew_1"]),
        "measured_at": now.isoformat(),
        "raw_data": {"pulse_rate": 75.0},
        "credentials": {"device_token": "invalid-wrong-token"},  # Wrong!
    }

    res = client.post("/api/v1/devices/ingest", headers={"Authorization": f"Bearer {crew_1_token}"}, json=envelope)
    assert res.status_code == 401
    assert "invalid_credentials" in res.json()["error"]["code"]


def test_unsupported_provider(client: TestClient, crew_1_token, test_crew):
    """Verifies that unconfigured or unsupported device providers are rejected with 400."""
    now = datetime.now(timezone.utc)
    envelope = {
        "provider_id": "NONEXISTENT_HARDWARE_VENDOR",
        "device_id": "UNKNOWN-001",
        "event_id": "DEV-EVT-UNKNOWN",
        "crew_member_id": str(test_crew["crew_1"]),
        "measured_at": now.isoformat(),
        "raw_data": {"val": 10},
    }

    res = client.post("/api/v1/devices/ingest", headers={"Authorization": f"Bearer {crew_1_token}"}, json=envelope)
    assert res.status_code == 400
    assert "unsupported_provider" in res.json()["error"]["code"]


def test_device_bola_prevention(client: TestClient, crew_1_token, test_crew):
    """Verifies that crew member 1 cannot submit telemetry targeting crew member 2."""
    now = datetime.now(timezone.utc)
    envelope = {
        "provider_id": "MOCK_BIOHARNESS",
        "device_id": "BH-004",
        "event_id": "DEV-EVT-BOLA",
        "crew_member_id": str(test_crew["crew_2"]),  # Target is crew 2!
        "measured_at": now.isoformat(),
        "raw_data": {"pulse_rate": 70.0},
        "credentials": {"device_token": "valid-device-token-123"},
    }

    res = client.post("/api/v1/devices/ingest", headers={"Authorization": f"Bearer {crew_1_token}"}, json=envelope)
    assert res.status_code == 403


# ==============================================================================
# 2. Future Model Analysis Endpoint Tests
# ==============================================================================

def test_future_model_analysis_not_configured_by_default(client: TestClient, crew_1_token, test_crew):
    """Verifies that the future model analysis endpoint safely reports not_configured by default."""
    res = client.post(
        "/api/v1/models/analyze",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "provider_id": "DEEP_SPACE_CARDIAC_AI",
            "capability": "trend_forecasting",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "not_configured"
    assert "not configured" in data["message"].lower()
    assert "Strictly prohibited from influencing clinical decisions" in data["limitations"]

