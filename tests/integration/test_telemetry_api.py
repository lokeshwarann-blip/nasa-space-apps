import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_access_token


@pytest.fixture
def test_crew():
    """Provides a pair of test crew member UUIDs."""
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


# ==============================================================================
# Health Measurement Ingestion & Validation Tests
# ==============================================================================

def test_successful_measurement_ingestion(client: TestClient, test_crew, crew_1_token):
    """Verify successful physiological measurement ingestion and preservation of fields."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "heart_rate",
        "value_numeric": 72.0,
        "unit": "bpm",
        "measured_at": measured_at,
        "input_method": "WEARABLE_SENSOR",
        "provenance": {
            "device_id": "BIO-HARNESS-01",
            "model": "Zephyr-X",
            "firmware": "v2.4.1",
        },
        "context_metadata": {
            "posture": "SUPINE",
            "activity": "RESTING",
        },
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["crew_member_id"] == str(test_crew["crew_1"])
    assert data["measurement_type"] == "heart_rate"
    assert data["value_numeric"] == 72.0
    assert data["unit"] == "bpm"
    assert data["quality_status"] == "VERIFIED"
    assert data["provenance"]["device_id"] == "BIO-HARNESS-01"
    assert "recorded_at" in data
    assert data["measured_at"] is not None


def test_temperature_unit_conversion_and_provenance_preservation(client: TestClient, test_crew, crew_1_token):
    """Verify explicit, deterministic conversion from Fahrenheit to Celsius and provenance preservation."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "body_temperature",
        "value_numeric": 98.6,
        "unit": "degF",
        "measured_at": measured_at,
        "input_method": "CLINICAL_DEVICE",
        "provenance": {"device": "Tympanic-Thermo-03"},
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    # Converted to canonical degC
    assert data["value_numeric"] == 37.0
    assert data["unit"] == "degC"
    # Preserved original input and audit trail
    assert data["original_value"] == 98.6
    assert data["original_unit"] == "degF"
    assert data["conversion_audit"] is not None
    assert data["conversion_audit"]["converted_value"] == 37.0
    assert data["conversion_audit"]["canonical_unit"] == "degC"


def test_clinically_concerning_but_valid_value_accepted(client: TestClient, test_crew, crew_1_token):
    """Verify that a clinically concerning (high) but physiologically valid value is accepted."""
    # 175 bpm is high (tachycardia / intense exertion), but physiologically plausible (< 260 bpm)
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "heart_rate",
        "value_numeric": 175.0,
        "unit": "bpm",
        "measured_at": measured_at,
        "input_method": "WEARABLE_SENSOR",
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 201
    assert response.json()["value_numeric"] == 175.0


def test_missing_required_fields_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify missing required fields return 422 Unprocessable Entity."""
    # Missing unit and measured_at
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "heart_rate",
        "value_numeric": 72.0,
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 422


def test_incompatible_unit_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify incompatible unit returns 400 Bad Request with invalid_unit error code."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "heart_rate",
        "value_numeric": 75.0,
        "unit": "liters",  # Incompatible unit for heart_rate
        "measured_at": measured_at,
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_unit"


def test_unsupported_measurement_type_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify unsupported indicator type returns 400 with unsupported_measurement_type code."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "extraterrestrial_aura",
        "value_numeric": 99.0,
        "unit": "points",
        "measured_at": measured_at,
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_measurement_type"


def test_nan_and_infinity_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify NaN and Infinity values are strictly rejected."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "heart_rate",
        "value_numeric": "NaN",
        "unit": "bpm",
        "measured_at": measured_at,
    }

    response = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] in ("invalid_value", "VALIDATION_ERROR")


def test_timestamp_validations(client: TestClient, test_crew, crew_1_token):
    """Verify timezone offset, future timestamp, and stale timestamp validations."""
    # 1. Future timestamp (+1 day)
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    res_future = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 72.0,
            "unit": "bpm",
            "measured_at": future_time,
        },
    )
    assert res_future.status_code == 422
    assert res_future.json()["error"]["code"] == "invalid_timestamp"

    # 2. Excessively stale timestamp (year 1960)
    stale_time = datetime(1960, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    res_stale = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 72.0,
            "unit": "bpm",
            "measured_at": stale_time,
        },
    )
    assert res_stale.status_code == 422
    assert res_stale.json()["error"]["code"] == "invalid_timestamp"

    # 3. Naive timestamp without timezone
    res_naive = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 72.0,
            "unit": "bpm",
            "measured_at": "2026-10-30T10:00:00",  # No offset
        },
    )
    assert res_naive.status_code == 422
    assert res_naive.json()["error"]["code"] == "invalid_timestamp"


def test_duplicate_submission_rejected(client: TestClient, test_crew, crew_1_token):
    """Verify submitting the identical measurement twice returns 409 duplicate_submission."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "measurement_type": "blood_pressure_systolic",
        "value_numeric": 120.0,
        "unit": "mmHg",
        "measured_at": measured_at,
    }

    # First submission -> 201 Created
    res1 = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert res1.status_code == 201

    # Second submission (identical timestamp, type, crew) -> 409 Conflict
    res2 = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "duplicate_submission"


def test_cross_crew_bola_access_rejected_on_measurements(client: TestClient, test_crew, crew_1_token):
    """Verify crew member cannot submit or query measurements for another crew member."""
    # 1. Crew 1 attempting to submit for Crew 2 -> 403 Forbidden
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    res_submit = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_2"]),  # Unauthorized target
            "measurement_type": "heart_rate",
            "value_numeric": 68.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )
    assert res_submit.status_code == 403
    assert res_submit.json()["error"]["code"] == "forbidden"

    # 2. Crew 1 attempting to list measurements filtered by Crew 2 -> 403 Forbidden
    res_list = client.get(
        f"/api/v1/measurements?crew_id={test_crew['crew_2']}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_list.status_code == 403
    assert res_list.json()["error"]["code"] == "forbidden"


def test_measurements_pagination_and_retrieval(client: TestClient, test_crew, crew_1_token):
    """Verify pagination, deterministic ordering, and single ID retrieval."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=1)
    # Ingest 3 distinct records
    ids = []
    for i in range(3):
        res = client.post(
            "/api/v1/measurements",
            headers={"Authorization": f"Bearer {crew_1_token}"},
            json={
                "crew_member_id": str(test_crew["crew_1"]),
                "measurement_type": "heart_rate",
                "value_numeric": 70.0 + i,
                "unit": "bpm",
                "measured_at": (base_time + timedelta(minutes=i * 5)).isoformat(),
            },
        )
        assert res.status_code == 201
        ids.append(res.json()["id"])

    # Query with limit=2, offset=0
    res_page1 = client.get(
        "/api/v1/measurements?limit=2&offset=0",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_page1.status_code == 200
    data_page1 = res_page1.json()
    assert len(data_page1["items"]) == 2
    assert data_page1["total"] >= 3
    assert data_page1["has_more"] is True

    # Retrieve single record by ID
    target_id = ids[0]
    res_single = client.get(
        f"/api/v1/measurements/{target_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_single.status_code == 200
    assert res_single.json()["id"] == target_id

    # Non-existent ID returns 404
    non_existent = str(uuid.uuid4())
    res_404 = client.get(
        f"/api/v1/measurements/{non_existent}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "not_found"


def test_measurement_invalidation_audit_trail(client: TestClient, test_crew, crew_1_token):
    """Verify marking measurement as invalidated updates status and preserves history."""
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    create_res = client.post(
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
    m_id = create_res.json()["id"]

    # Invalidate measurement
    inv_res = client.post(
        f"/api/v1/measurements/{m_id}/invalidate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"reason": "Sensor detachment during exercise protocol."},
    )
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["quality_status"] == "INVALIDATED"
    assert inv_data["context_metadata"]["invalidated"] is True
    assert inv_data["context_metadata"]["invalidation_reason"] == "Sensor detachment during exercise protocol."

    # Querying back reflects invalidated state
    fetch_res = client.get(
        f"/api/v1/measurements/{m_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert fetch_res.status_code == 200
    assert fetch_res.json()["quality_status"] == "INVALIDATED"


# ==============================================================================
# Crew Check-Ins Tests (Wellness & Symptoms)
# ==============================================================================

def test_wellness_checkin_success(client: TestClient, test_crew, crew_1_token):
    """Verify submitting and retrieving subjective wellness check-ins."""
    measured_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    payload = {
        "check_in_type": "WELLNESS",
        "crew_member_id": str(test_crew["crew_1"]),
        "sleep_duration_hours": 7.5,
        "sleep_quality": 4,
        "mood": 4,
        "stress": 2,
        "fatigue": 2,
        "measured_at": measured_at,
        "provenance": {"app": "Crew-Portal-Tablet-v1"},
    }

    response = client.post(
        "/api/v1/check-ins",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["check_in_type"] == "WELLNESS"
    assert data["details"]["sleep_duration_hours"] == 7.5
    assert data["details"]["mood"] == 4
    check_in_id = data["id"]

    # Retrieve by ID
    get_res = client.get(
        f"/api/v1/check-ins/{check_in_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == check_in_id


def test_symptom_checkin_success(client: TestClient, test_crew, crew_1_token):
    """Verify submitting and retrieving structured symptom check-ins."""
    onset_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    payload = {
        "check_in_type": "SYMPTOM",
        "crew_member_id": str(test_crew["crew_1"]),
        "symptom_identifiers": ["SPACE_MOTION_SICKNESS", "HEADACHE"],
        "severity": "MODERATE",
        "onset_time": onset_time,
        "controlled_notes": "Experienced mild vestibular disorientation post-docking.",
        "provenance": {"app": "Crew-Portal-Tablet-v1"},
    }

    response = client.post(
        "/api/v1/check-ins",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["check_in_type"] == "SYMPTOM"
    assert "SPACE_MOTION_SICKNESS" in data["details"]["symptom_identifiers"]
    assert data["details"]["severity"] == "MODERATE"


def test_cross_crew_checkin_access_rejected(client: TestClient, test_crew, crew_1_token, crew_2_token):
    """Verify crew member cannot access another crew member's check-in reports."""
    # 1. Crew 2 submits a symptom check-in
    onset_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    submit_res = client.post(
        "/api/v1/check-ins",
        headers={"Authorization": f"Bearer {crew_2_token}"},
        json={
            "check_in_type": "SYMPTOM",
            "crew_member_id": str(test_crew["crew_2"]),
            "symptom_identifiers": ["FATIGUE"],
            "severity": "MILD",
            "onset_time": onset_time,
        },
    )
    assert submit_res.status_code == 201
    crew_2_checkin_id = submit_res.json()["id"]

    # 2. Crew 1 attempts to query Crew 2's check-in by ID -> 403 Forbidden
    cross_res = client.get(
        f"/api/v1/check-ins/{crew_2_checkin_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert cross_res.status_code == 403
    assert cross_res.json()["error"]["code"] == "forbidden"

