"""Tests for simulation scenario activations and crew status reflections."""
import pytest
from fastapi.testclient import TestClient
from src.core.database import get_db
from src.main import create_app
from src.schemas.astronaut import ScenarioType, StatusEnum


@pytest.fixture
def seeded_app(db_session):
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


class TestScenarioManagement:
    """Test suite for POST /scenario switching and /crew/{id}/status reflection."""

    def test_scenario_sensor_fault(self, seeded_app):
        """sensor_fault scenario shows data_quality 'sensor_issue' and NEVER a health alert."""
        with TestClient(seeded_app) as client:
            resp = client.post("/api/v1/scenario", json={"type": "sensor_fault"})
            assert resp.status_code == 200
            assert resp.json()["active_scenario"] == ScenarioType.SENSOR_FAULT

            status_resp = client.get("/api/v1/crew/CREW-001/status")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert data["data_quality"] == "sensor_issue"
            # Hard rule: faulty sensor must NEVER appear as acute health alert (not ACT, not CALL_GROUND)
            assert data["readiness"]["status"] not in (StatusEnum.ACT, StatusEnum.CALL_GROUND)

    def test_scenario_coordinated_drift(self, seeded_app):
        """coordinated_drift triggers detectors and reflects multi-signal shift."""
        with TestClient(seeded_app) as client:
            resp = client.post("/api/v1/scenario", json={"type": "coordinated_drift"})
            assert resp.status_code == 200
            assert resp.json()["active_scenario"] == ScenarioType.COORDINATED_DRIFT

            status_resp = client.get("/api/v1/crew/CREW-001/status")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert data["data_quality"] == "good"
            assert data["readiness"]["score"] <= 75
            assert data["readiness"]["status"] in (StatusEnum.WATCH, StatusEnum.ACT)

    def test_scenario_comms_blackout(self, seeded_app):
        """comms_blackout reflects autonomous mode with low uplink confidence."""
        with TestClient(seeded_app) as client:
            resp = client.post("/api/v1/scenario", json={"type": "comms_blackout"})
            assert resp.status_code == 200
            assert resp.json()["active_scenario"] == ScenarioType.COMMS_BLACKOUT

            status_resp = client.get("/api/v1/crew/CREW-001/status")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert data["readiness"]["confidence"] == "low"

    def test_scenario_dust_storm(self, seeded_app):
        """dust_storm reflects elevated environmental stress parameters."""
        with TestClient(seeded_app) as client:
            resp = client.post("/api/v1/scenario", json={"type": "dust_storm"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["active_scenario"] == ScenarioType.DUST_STORM
            assert "ambient_dust_index" in data["parameters"]

            status_resp = client.get("/api/v1/crew/CREW-001/status")
            assert status_resp.status_code == 200

    def test_scenario_reset(self, seeded_app):
        """reset clears active perturbations and restores nominal simulation state."""
        with TestClient(seeded_app) as client:
            resp = client.post("/api/v1/scenario", json={"type": "reset"})
            assert resp.status_code == 200
            assert resp.json()["active_scenario"] == ScenarioType.RESET

            status_resp = client.get("/api/v1/crew/CREW-001/status")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert data["data_quality"] == "good"
