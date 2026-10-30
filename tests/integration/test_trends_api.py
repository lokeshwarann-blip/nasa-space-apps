import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_access_token


@pytest.fixture
def test_crew():
    return {
        "crew_1": uuid.uuid4(),
        "crew_2": uuid.uuid4(),
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


@pytest.fixture
def surgeon_token(test_crew):
    return create_access_token(
        subject="flight_surgeon_beck",
        role="FLIGHT_SURGEON",
        assigned_crew_ids=[str(test_crew["crew_1"])],
    )


def test_trends_empty_history(client: TestClient, test_crew, crew_1_token):
    """Verify querying trends with zero historical records returns valid empty structure."""
    response = client.get(
        "/api/v1/trends/heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["observation_count"] == 0
    assert len(data["observations"]) == 0
    assert data["statistics"]["count"] == 0
    assert data["statistics"]["mean"] is None
    assert data["baseline"]["baseline_status"] == "UNAVAILABLE"


def test_trends_single_observation(client: TestClient, test_crew, crew_1_token):
    """Verify trends for single observation calculates mean but marks std_dev unavailable."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 72.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )

    response = client.get(
        "/api/v1/trends/heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["observation_count"] == 1
    assert data["statistics"]["count"] == 1
    assert data["statistics"]["mean"] == 72.0
    assert data["statistics"]["sample_std_dev"] is None
    assert "sample_std_dev" in data["statistics"]["unavailable_reasons"]


def test_trends_multiple_observations_and_statistics(client: TestClient, test_crew, crew_1_token):
    """Verify trends calculation on multiple observations."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=2)
    hr_values = [60.0, 70.0, 80.0]

    for i, val in enumerate(hr_values):
        client.post(
            "/api/v1/measurements",
            headers={"Authorization": f"Bearer {crew_1_token}"},
            json={
                "crew_member_id": str(test_crew["crew_1"]),
                "measurement_type": "heart_rate",
                "value_numeric": val,
                "unit": "bpm",
                "measured_at": (base_time + timedelta(minutes=i * 10)).isoformat(),
            },
        )

    response = client.get(
        "/api/v1/trends/heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["observation_count"] == 3
    assert data["statistics"]["minimum"] == 60.0
    assert data["statistics"]["maximum"] == 80.0
    assert data["statistics"]["mean"] == 70.0
    assert data["statistics"]["median"] == 70.0
    assert data["statistics"]["sample_std_dev"] == 10.0


def test_trends_invalidated_observations_excluded_from_stats(client: TestClient, test_crew, crew_1_token):
    """Verify invalidated observations are excluded from derived statistics and counted separately."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=3)
    created_ids = []

    for i, val in enumerate([70.0, 72.0, 190.0]):  # 190 will be invalidated
        res = client.post(
            "/api/v1/measurements",
            headers={"Authorization": f"Bearer {crew_1_token}"},
            json={
                "crew_member_id": str(test_crew["crew_1"]),
                "measurement_type": "heart_rate",
                "value_numeric": val,
                "unit": "bpm",
                "measured_at": (base_time + timedelta(minutes=i * 15)).isoformat(),
            },
        )
        created_ids.append(res.json()["id"])

    # Invalidate the third measurement
    client.post(
        f"/api/v1/measurements/{created_ids[2]}/invalidate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"reason": "Sensor motion artifact during treadmill run"},
    )

    response = client.get(
        "/api/v1/trends/heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data_quality"]["total_records_ingested"] == 3
    assert data["data_quality"]["valid_observations_count"] == 2
    assert data["data_quality"]["invalidated_observations_count"] == 1
    # Mean of 70 and 72 is 71 (190 excluded!)
    assert data["statistics"]["count"] == 2
    assert data["statistics"]["mean"] == 71.0


def test_trends_coverage_gap_detection(client: TestClient, test_crew, crew_1_token):
    """Verify temporal gaps exceeding gap_threshold_seconds are flagged."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=6)
    # Point 1 and Point 2 are 3 hours apart
    t1 = base_time.isoformat()
    t2 = (base_time + timedelta(hours=3)).isoformat()

    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 70.0,
            "unit": "bpm",
            "measured_at": t1,
        },
    )
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 72.0,
            "unit": "bpm",
            "measured_at": t2,
        },
    )

    # Query with 1-hour gap threshold (3600 seconds)
    response = client.get(
        "/api/v1/trends/heart_rate?gap_threshold_seconds=3600",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["coverage_gaps"]) == 1
    gap = data["coverage_gaps"][0]
    assert gap["gap_duration_hours"] == 3.0


def test_trend_summary_endpoint(client: TestClient, test_crew, crew_1_token):
    """Verify GET /api/v1/trends/{type}/summary returns aggregate metrics without raw points."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "spo2",
            "value_numeric": 98.0,
            "unit": "%",
            "measured_at": measured_at,
        },
    )

    response = client.get(
        "/api/v1/trends/spo2/summary",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["measurement_type"] == "spo2"
    assert "statistics" in data
    assert "data_quality" in data
    # Raw observation series is omitted in summary
    assert "observations" not in data


def test_personal_baseline_endpoint_unavailable_then_configured(client: TestClient, test_crew, crew_1_token):
    """Verify empirical baseline returns UNAVAILABLE when <10, and CONFIGURED when >=10."""
    # 1. Zero observations -> UNAVAILABLE
    res_empty = client.get(
        "/api/v1/baselines/heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_empty.status_code == 200
    assert res_empty.json()["baseline_status"] == "UNAVAILABLE"

    # 2. Ingest 10 observations
    base_time = datetime.now(timezone.utc) - timedelta(days=2)
    for i in range(10):
        client.post(
            "/api/v1/measurements",
            headers={"Authorization": f"Bearer {crew_1_token}"},
            json={
                "crew_member_id": str(test_crew["crew_1"]),
                "measurement_type": "heart_rate",
                "value_numeric": 70.0 + (i % 3),
                "unit": "bpm",
                "measured_at": (base_time + timedelta(hours=i * 2)).isoformat(),
            },
        )

    # 3. Query baseline -> CONFIGURED with actual metrics
    res_configured = client.get(
        "/api/v1/baselines/heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_configured.status_code == 200
    data = res_configured.json()
    assert data["baseline_status"] == "CONFIGURED"
    assert data["observation_count"] >= 10
    assert data["baseline_values"]["baseline_mean"] > 69.0


def test_trends_cross_crew_access_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify crew member cannot inspect another crew member's longitudinal trends."""
    response = client.get(
        f"/api/v1/trends/heart_rate?crew_id={test_crew['crew_2']}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_trends_invalid_bounded_window_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify chronological violation (start > end) and window exceeding 90 days are rejected."""
    t_now = datetime.now(timezone.utc)
    t_past = t_now - timedelta(days=10)

    t_now_str = t_now.strftime("%Y-%m-%dT%H:%M:%SZ")
    t_past_str = t_past.strftime("%Y-%m-%dT%H:%M:%SZ")

    # start_time later than end_time
    res_inverted = client.get(
        f"/api/v1/trends/heart_rate?start_time={t_now_str}&end_time={t_past_str}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_inverted.status_code == 400
    assert res_inverted.json()["error"]["code"] == "invalid_timestamp"

    # Window > 90 days (e.g. 120 days)
    t_ancient_str = (t_now - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_oversized = client.get(
        f"/api/v1/trends/heart_rate?start_time={t_ancient_str}&end_time={t_now_str}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_oversized.status_code == 400
    assert res_oversized.json()["error"]["code"] == "invalid_timestamp"


def test_trends_unsupported_type_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify unsupported indicator type returns 400 with unsupported_measurement_type."""
    response = client.get(
        "/api/v1/trends/alien_radiation_level",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_measurement_type"
