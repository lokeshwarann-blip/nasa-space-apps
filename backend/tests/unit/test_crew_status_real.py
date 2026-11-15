import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.database import get_db
from src.main import create_app
from src.models import CrewMember, HealthMeasurement
from src.schemas.astronaut import (
    CrewStatus,
    StatusEnum,
    StatusIconEnum,
)


@pytest.fixture
def seeded_app(db_session):
    """FastAPI app instance with seeded DB session."""
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def test_crew_status_insufficient_data(seeded_app):
    """Insufficient data case returns valid structure with confidence=low."""
    with TestClient(seeded_app) as client:
        resp = client.get("/api/v1/crew/CREW-NONEXISTENT/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_quality"] == "good"
        assert data["readiness"]["confidence"] == "low"
        validated = CrewStatus(**data)
        assert validated.readiness.score is not None


def test_crew_status_sensor_fault(seeded_app, db_session):
    """Sensor-fault case: flatline sensor triggers data_quality='sensor_issue' and NEVER appears as a health alert."""
    sync_session = db_session._sync
    c_uuid = uuid.uuid4()
    sync_session.add(CrewMember(
        id=c_uuid,
        crew_id="CREW-FAULTY",
        status="ACTIVE",
        profile_metadata={"callsign": "Faulty"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ))
    # Add flatline readings (std < 1e-6 over >= 6 points)
    now = datetime.now(timezone.utc)
    for i in range(15):
        sync_session.add(HealthMeasurement(
            id=uuid.uuid4(),
            crew_member_id=c_uuid,
            measurement_type="heart_rate",
            value_numeric=70.0,  # Exact flatline
            unit="bpm",
            measured_at=now,
            recorded_at=now,
            input_method="WEARABLE_SENSOR",
            provenance="SENSOR_STREAM",
            quality_status="VERIFIED",
        ))
    sync_session.commit()

    with TestClient(seeded_app) as client:
        resp = client.get(f"/api/v1/crew/{c_uuid}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_quality"] == "sensor_issue"
        # Must NEVER appear as acute health alert (not act, not call_ground)
        assert data["readiness"]["status"] not in (StatusEnum.ACT, StatusEnum.CALL_GROUND)


def test_crew_status_normal(seeded_app, db_session):
    """Status NORMAL: healthy metrics within baseline."""
    sync_session = db_session._sync
    c_uuid = uuid.uuid4()
    sync_session.add(CrewMember(
        id=c_uuid,
        crew_id="CREW-NORMAL",
        status="ACTIVE",
        profile_metadata={"callsign": "Nominal"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ))
    now = datetime.now(timezone.utc)
    for i in range(20):
        sync_session.add(HealthMeasurement(
            id=uuid.uuid4(),
            crew_member_id=c_uuid,
            measurement_type="heart_rate",
            value_numeric=65.0 + (i % 3),
            unit="bpm",
            measured_at=now,
            recorded_at=now,
            input_method="WEARABLE_SENSOR",
            provenance="SENSOR_STREAM",
            quality_status="VERIFIED",
        ))
        sync_session.add(HealthMeasurement(
            id=uuid.uuid4(),
            crew_member_id=c_uuid,
            measurement_type="spo2",
            value_numeric=98.0 + (i % 2) * 0.5,
            unit="%",
            measured_at=now,
            recorded_at=now,
            input_method="WEARABLE_SENSOR",
            provenance="SENSOR_STREAM",
            quality_status="VERIFIED",
        ))
    sync_session.commit()

    with TestClient(seeded_app) as client:
        resp = client.get(f"/api/v1/crew/{c_uuid}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_quality"] == "good"
        assert data["readiness"]["status"] == StatusEnum.NORMAL
        assert data["readiness"]["status_icon"] == StatusIconEnum.CIRCLE_CHECK


def test_crew_status_watch_and_act_and_call_ground(seeded_app, db_session):
    """Tests score-to-status mapping across WATCH, ACT, and CALL_GROUND."""
    from src.api.v1.crew_mock import _map_readiness_status

    st_watch, icon_watch = _map_readiness_status("WATCH", 75, False)
    assert st_watch == StatusEnum.WATCH
    assert icon_watch == StatusIconEnum.TRIANGLE

    st_act, icon_act = _map_readiness_status("CRITICAL", 65, False)
    assert st_act == StatusEnum.ACT
    assert icon_act == StatusIconEnum.DIAMOND

    st_ground, icon_ground = _map_readiness_status("CALL_GROUND", 40, False)
    assert st_ground == StatusEnum.CALL_GROUND
    assert icon_ground == StatusIconEnum.OCTAGON
