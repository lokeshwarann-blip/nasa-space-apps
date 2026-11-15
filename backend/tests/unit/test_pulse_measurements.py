"""Unit tests for POST /measurements/pulse telemetry ingestion."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.core.config import Settings
from src.main import create_app
from src.models import HealthMeasurement
from src.schemas.astronaut import DISCLAIMER, PulseMeasurementResponse


@pytest.fixture
def test_app(test_settings: Settings, db_session):
    """FastAPI test app with in-memory DB override."""
    application = create_app(settings=test_settings)

    from src.core.database import get_db

    async def _override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = _override_get_db
    return application


class TestPulseMeasurements:
    """Test suite for pulse measurement validation, threshold rejection, and storage."""

    def test_pulse_accepted_and_stored(self, test_app, db_session):
        """Accepted reading stores verified records in the database with provenance and returns measurement ID."""
        with TestClient(test_app) as client:
            resp = client.post(
                "/api/v1/measurements/pulse",
                json={
                    "hr": 74.5,
                    "hrv": 52.0,
                    "signal_quality": "good",
                    "source": "optical_ppg_sensor",
                    "crew_id": "CREW-001",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["disclaimer"] == DISCLAIMER
            assert data["status"] == "accepted"
            assert data["measurement_id"] is not None
            assert data["measurement_id"].startswith("pulse-")
            assert "trend" in data["message"].lower() or "accepted" in data["message"].lower()

            validated = PulseMeasurementResponse(**data)
            assert validated.status == "accepted"

            # Verify persisted records in database
            hex_prefix = data["measurement_id"].replace("pulse-", "")
            stmt = select(HealthMeasurement).where(HealthMeasurement.measurement_type == "heart_rate")
            rows = db_session._sync.execute(stmt).scalars().all()
            matched = [r for r in rows if str(r.id).replace("-", "").startswith(hex_prefix)]
            assert len(matched) == 1
            stored_hr = matched[0]
            assert stored_hr.value_numeric == 74.5
            assert stored_hr.quality_status == "VERIFIED"
            assert stored_hr.unit == "bpm"
            assert stored_hr.provenance["source"] == "optical_ppg_sensor"

            # Check HRV also stored
            hrv_stmt = select(HealthMeasurement).where(HealthMeasurement.measurement_type == "hrv")
            hrv_rows = db_session._sync.execute(hrv_stmt).scalars().all()
            assert len(hrv_rows) >= 1
            assert any(r.value_numeric == 52.0 for r in hrv_rows)

    def test_pulse_direct_route_accepted(self, test_app):
        """Route is accessible directly at /measurements/pulse as well as /api/v1/measurements/pulse."""
        with TestClient(test_app) as client:
            resp = client.post(
                "/measurements/pulse",
                json={
                    "hr": 68.0,
                    "signal_quality": "fair",
                    "source": "biochest_strap",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "accepted"
            assert data["measurement_id"] is not None

    def test_pulse_rejected_below_threshold_not_scored(self, test_app, db_session):
        """Readings with signal quality below configurable threshold are rejected and NOT stored or scored."""
        initial_count = len(db_session._sync.execute(select(HealthMeasurement)).scalars().all())

        with TestClient(test_app) as client:
            resp = client.post(
                "/api/v1/measurements/pulse",
                json={
                    "hr": 78.0,
                    "hrv": 35.0,
                    "signal_quality": "poor",
                    "source": "wearable_ppg",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "rejected"
            assert data["measurement_id"] is None
            assert "below minimum threshold" in data["message"]
            assert "not scored" in data["message"]
            assert "check with flight surgeon" in data["message"]

            validated = PulseMeasurementResponse(**data)
            assert validated.status == "rejected"
            assert validated.measurement_id is None

            # Verify NO measurement was stored in the database
            final_count = len(db_session._sync.execute(select(HealthMeasurement)).scalars().all())
            assert final_count == initial_count

    def test_pulse_configurable_threshold_override(self, db_session):
        """Configuring MIN_PULSE_SIGNAL_QUALITY to 'good' rejects 'fair' readings."""
        custom_settings = Settings(
            ENVIRONMENT="testing",
            DEBUG=True,
            SECRET_KEY="test-secret-key-that-is-at-least-32-chars-long!",
            DATABASE_URL="sqlite:///:memory:",
            MIN_PULSE_SIGNAL_QUALITY="good",
        )
        app = create_app(settings=custom_settings)

        from src.core.database import get_db

        async def _override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_get_db

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/measurements/pulse",
                json={
                    "hr": 70.0,
                    "signal_quality": "fair",
                    "source": "wearable_ppg",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "rejected"
            assert "below minimum threshold 'good'" in data["message"]

    @pytest.mark.parametrize(
        "invalid_payload,expected_loc",
        [
            ({"hr": 10.0, "signal_quality": "good", "source": "wearable"}, "hr"),  # hr < 20
            ({"hr": 290.0, "signal_quality": "good", "source": "wearable"}, "hr"),  # hr > 250
            ({"hr": "not-a-number", "signal_quality": "good", "source": "wearable"}, "hr"),  # non-numeric
            ({"signal_quality": "good", "source": "wearable"}, "hr"),  # missing hr
            ({"hr": 72.0, "hrv": -5.0, "signal_quality": "good", "source": "wearable"}, "hrv"),  # negative hrv
            ({"hr": 72.0, "signal_quality": "good", "source": ""}, "source"),  # empty source
            ({"hr": 72.0, "signal_quality": "   ", "source": "wearable"}, "signal_quality"),  # blank quality
            ({"hr": 72.0, "signal_quality": "ultra_hd", "source": "wearable"}, "signal_quality"),  # invalid quality
            ({"hr": 72.0, "signal_quality": "good"}, "source"),  # missing source
        ],
    )
    def test_pulse_invalid_inputs_return_422(self, test_app, invalid_payload, expected_loc):
        """Invalid schema, missing fields, or out-of-range physiological values are rejected with 422."""
        with TestClient(test_app) as client:
            resp = client.post("/api/v1/measurements/pulse", json=invalid_payload)
            assert resp.status_code == 422
            data = resp.json()
            details = data.get("error", {}).get("details", [])
            assert any(expected_loc in str(err.get("loc", [])) for err in details)
