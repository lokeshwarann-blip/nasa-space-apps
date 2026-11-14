import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.models import (
    Base,
    User,
    CrewMember,
    HealthMeasurement,
)
from src.core.security import create_access_token, hash_password
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from test.fixtures import TEST_USERS


def test_crew_readiness_overview_and_endpoints(client: TestClient, db_session, test_settings):
    """E2E verification of crew readiness calculation, drift alerts, and trends compatibility."""
    scenario_file = Path(__file__).resolve().parent.parent.parent.parent / "test" / "health_readings_scenario.json"
    crew_file = Path(__file__).resolve().parent.parent.parent.parent / "test" / "crew_members.json"

    with open(scenario_file, "r", encoding="utf-8") as f:
        readings = json.load(f)
    with open(crew_file, "r", encoding="utf-8") as f:
        crews = json.load(f)

    # Ingest test data into database
    sync_session = db_session._sync
    for c in crews:
        sync_session.add(CrewMember(
            id=uuid.UUID(c["id"]),
            crew_id=c["crew_id"],
            status=c["status"],
            profile_metadata=c["profile_metadata"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ))
    for u in TEST_USERS:
        sync_session.add(User(
            id=uuid.uuid4(),
            username=u["username"],
            hashed_password=hash_password(u["password"]),
            role=u["role"],
            is_active=True,
            crew_member_id=uuid.UUID(u["crew_member_id"]) if u["crew_member_id"] else None,
            assigned_crew_ids=[str(cid) for cid in u["assigned_crew_ids"]]
        ))
    for r in readings:
        sync_session.add(HealthMeasurement(
            id=uuid.UUID(r["id"]),
            crew_member_id=uuid.UUID(r["crew_member_id"]),
            measurement_type=r["measurement_type"],
            value_numeric=r["value_numeric"],
            unit=r["unit"],
            measured_at=datetime.fromisoformat(r["measured_at"].replace("Z", "+00:00")),
            recorded_at=datetime.fromisoformat(r["recorded_at"].replace("Z", "+00:00")),
            input_method=r["input_method"],
            provenance=r["provenance"],
            quality_status=r["quality_status"],
            context_metadata=r["context_metadata"]
        ))
    sync_session.commit()

    # Generate token for flight surgeon
    fs = [u for u in TEST_USERS if u["username"] == "flight_surgeon"][0]
    token = create_access_token(
        subject=fs["username"],
        role=fs["role"],
        assigned_crew_ids=fs["assigned_crew_ids"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Overview check
    overview_resp = client.get("/api/v1/readiness/overview", headers=headers)
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert len(overview_data.get("crews", [])) == 6

    crews_by_id = {str(c["crew_id"]): c for c in overview_data["crews"]}

    # CREW-003 should have deteriorated readiness and drift alerts
    c3_uuid = crews[2]["id"]
    assert c3_uuid in crews_by_id
    c3 = crews_by_id[c3_uuid]
    assert c3["status"] == "CRITICAL"
    assert c3["data_status"] == "COMPLETE"
    assert c3["readiness"] < 70.0
    assert len(c3["drift_alerts"]) >= 2
    assert len(c3["incidents"]) >= 1

    # 2. Detail endpoint check
    detail_resp = client.get(f"/api/v1/readiness?crew_id={c3_uuid}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["status"] == "CRITICAL"
    assert detail_data["data_status"] == "COMPLETE"
    assert "drift_alerts" in detail_data
    assert "incidents" in detail_data
    assert "forecast" in detail_data
    assert len(detail_data["readiness_series"]) > 0

    # 3. Trends compatibility check
    for mtype in ["sleep_duration", "radiation_dose_rate", "stress", "mood", "fatigue"]:
        trend_resp = client.get(f"/api/v1/trends/{mtype}?crew_id={c3_uuid}", headers=headers)
        assert trend_resp.status_code == 200
