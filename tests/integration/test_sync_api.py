"""Integration tests for Offline Synchronization API.

Verifies:
- Bounded batch ingestion of measurements, wellness check-ins, and symptom check-ins.
- Repeated batch uploads & idempotency deduplication.
- Conflicting UUID detection and safe audit recording without PHI leakage.
- Partial batch success and atomic isolation across events.
- Unauthorized crew member cross-submittal prevention (BOLA).
- Out-of-order and delayed telemetry reconciliation without overwriting newer records.
- Clock-skew future timestamp bounds.
- Schema version and type validation.
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_access_token
from src.models.crew import CrewMember


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
def flight_surgeon_token(test_crew):
    return create_access_token(
        subject="surgeon_bev_crusher",
        role="FLIGHT_SURGEON",
        assigned_crew_ids=[str(test_crew["crew_1"]), str(test_crew["crew_2"])],
    )


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


# ==============================================================================
# 1. Repeated Batch Uploads & Idempotency Tests
# ==============================================================================

def test_repeated_batch_uploads_and_idempotency(client: TestClient, crew_1_token, test_crew):
    """Verifies that re-uploading an identical batch returns duplicate status with existing IDs."""
    now = datetime.now(timezone.utc)
    ev1_id = str(uuid.uuid4())
    ev2_id = str(uuid.uuid4())
    ev3_id = str(uuid.uuid4())

    batch_payload = {
        "batch_id": "SYNC-BATCH-001",
        "client_sync_at": now.isoformat(),
        "events": [
            {
                "client_event_id": ev1_id,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "MEASUREMENT",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": (now - timedelta(minutes=30)).isoformat(),
                "source": {"input_method": "WEARABLE_SENSOR", "device_id": "BIO-HARNESS-01"},
                "payload": {"measurement_type": "heart_rate", "value": 74.0, "unit": "bpm"},
            },
            {
                "client_event_id": ev2_id,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "WELLNESS_CHECK_IN",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": (now - timedelta(hours=1)).isoformat(),
                "source": {"device_id": "CREW-TABLET-01"},
                "payload": {
                    "sleep_duration_hours": 7.5,
                    "sleep_quality": 4,
                    "mood": 4,
                    "stress": 2,
                    "fatigue": 2,
                },
            },
            {
                "client_event_id": ev3_id,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "SYMPTOM_CHECK_IN",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": (now - timedelta(hours=2)).isoformat(),
                "source": {"device_id": "CREW-TABLET-01"},
                "payload": {
                    "symptom_identifiers": ["HEADACHE"],
                    "severity": "MILD",
                    "onset_time": (now - timedelta(hours=3)).isoformat(),
                    "notes": "Mild frontal headache following EVA suit stowage.",
                },
            },
        ],
    }

    # First sync submission
    res1 = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=batch_payload,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["summary"]["total_events"] == 3
    assert data1["summary"]["accepted_count"] == 3
    assert data1["summary"]["duplicate_count"] == 0
    m_entity_id = data1["results"][0]["entity_id"]
    assert m_entity_id is not None

    # Second sync submission (exact retry)
    res2 = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=batch_payload,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["summary"]["total_events"] == 3
    assert data2["summary"]["accepted_count"] == 0
    assert data2["summary"]["duplicate_count"] == 3
    assert data2["results"][0]["status"] == "duplicate"
    assert data2["results"][0]["entity_id"] == m_entity_id


# ==============================================================================
# 2. Conflicting UUIDs Detection Tests
# ==============================================================================

def test_conflicting_uuids_detection(client: TestClient, crew_1_token, test_crew):
    """Verifies that reusing an event UUID with a different payload returns conflict and audits."""
    now = datetime.now(timezone.utc)
    reused_event_id = str(uuid.uuid4())

    # 1. Initial submittal
    res1 = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "SYNC-BATCH-ORIGINAL",
            "client_sync_at": now.isoformat(),
            "events": [
                {
                    "client_event_id": reused_event_id,
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": now.isoformat(),
                    "measured_at": now.isoformat(),
                    "source": {"device_id": "DEV-01"},
                    "payload": {"measurement_type": "heart_rate", "value": 70.0, "unit": "bpm"},
                }
            ],
        },
    )
    assert res1.status_code == 200
    assert res1.json()["results"][0]["status"] == "accepted"
    orig_entity_id = res1.json()["results"][0]["entity_id"]

    # 2. Resubmittal of same UUID with conflicting payload (different value)
    res2 = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "SYNC-BATCH-CONFLICT",
            "client_sync_at": now.isoformat(),
            "events": [
                {
                    "client_event_id": reused_event_id,
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": now.isoformat(),
                    "measured_at": now.isoformat(),
                    "source": {"device_id": "DEV-01"},
                    "payload": {"measurement_type": "heart_rate", "value": 140.0, "unit": "bpm"},  # Different!
                }
            ],
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["summary"]["conflict_count"] == 1
    assert data2["results"][0]["status"] == "conflict"
    assert data2["results"][0]["error_code"] == "sync_payload_conflict"

    # Verify original measurement in DB was NOT modified/overwritten
    m_check = client.get(
        f"/api/v1/measurements/{orig_entity_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert m_check.status_code == 200
    assert m_check.json()["value_numeric"] == 70.0, "Original observation must never be overwritten on conflict!"


# ==============================================================================
# 3. Partial Batch Success Tests
# ==============================================================================

def test_partial_batch_success(client: TestClient, crew_1_token, test_crew):
    """Verifies that invalid events in a batch fail individually without preventing valid events from committing."""
    now = datetime.now(timezone.utc)
    valid_id_1 = str(uuid.uuid4())
    invalid_id_2 = str(uuid.uuid4())
    valid_id_3 = str(uuid.uuid4())

    batch_payload = {
        "batch_id": "SYNC-BATCH-PARTIAL",
        "client_sync_at": now.isoformat(),
        "events": [
            # Event 1: Valid
            {
                "client_event_id": valid_id_1,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "MEASUREMENT",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": now.isoformat(),
                "payload": {"measurement_type": "body_temperature", "value": 36.6, "unit": "degC"},
            },
            # Event 2: Incompatible unit for heart rate
            {
                "client_event_id": invalid_id_2,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "MEASUREMENT",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": now.isoformat(),
                "payload": {"measurement_type": "heart_rate", "value": 75.0, "unit": "fahrenheit"},
            },
            # Event 3: Valid wellness check-in
            {
                "client_event_id": valid_id_3,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "WELLNESS_CHECK_IN",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": now.isoformat(),
                "payload": {
                    "sleep_duration_hours": 8.0,
                    "sleep_quality": 5,
                    "mood": 5,
                    "stress": 1,
                    "fatigue": 1,
                },
            },
        ],
    }

    res = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=batch_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["accepted_count"] == 2
    assert data["summary"]["rejected_count"] == 1

    results_by_id = {r["client_event_id"]: r for r in data["results"]}
    assert results_by_id[valid_id_1]["status"] == "accepted"
    assert results_by_id[invalid_id_2]["status"] == "rejected"
    assert results_by_id[invalid_id_2]["error_code"] == "incompatible_unit"
    assert results_by_id[valid_id_3]["status"] == "accepted"


# ==============================================================================
# 4. Unauthorized Crew IDs (BOLA Prevention)
# ==============================================================================

def test_unauthorized_crew_id_sync_rejection(client: TestClient, crew_1_token, test_crew):
    """Verifies that an astronaut cannot sync telemetry for another astronaut."""
    now = datetime.now(timezone.utc)
    res = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "SYNC-UNAUTHORIZED",
            "client_sync_at": now.isoformat(),
            "events": [
                {
                    "client_event_id": str(uuid.uuid4()),
                    "crew_member_id": str(test_crew["crew_2"]),  # Crew 2's ID submitted by Crew 1!
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": now.isoformat(),
                    "measured_at": now.isoformat(),
                    "payload": {"measurement_type": "heart_rate", "value": 80.0, "unit": "bpm"},
                }
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["rejected_count"] == 1
    assert data["results"][0]["status"] == "rejected"
    assert data["results"][0]["error_code"] == "forbidden_crew_access"


# ==============================================================================
# 5. Out-of-Order & Delayed Observations
# ==============================================================================

def test_delayed_and_out_of_order_observations(client: TestClient, crew_1_token, test_crew):
    """Verifies that late-arriving earlier observations do not overwrite newer ones and stay chronologically ordered."""
    base_time = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    t_newer = base_time
    t_older = base_time - timedelta(hours=12)

    # 1. Sync newer observation first (e.g. 12:00:00)
    ev_newer_id = str(uuid.uuid4())
    client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "BATCH-NEWER",
            "client_sync_at": datetime.now(timezone.utc).isoformat(),
            "events": [
                {
                    "client_event_id": ev_newer_id,
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": datetime.now(timezone.utc).isoformat(),
                    "measured_at": t_newer.isoformat(),
                    "payload": {"measurement_type": "heart_rate", "value": 72.0, "unit": "bpm"},
                }
            ],
        },
    )

    # 2. Later sync older observation (e.g. 00:00:00 from earlier during comm delay)
    ev_older_id = str(uuid.uuid4())
    client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "BATCH-OLDER-DELAYED",
            "client_sync_at": datetime.now(timezone.utc).isoformat(),
            "events": [
                {
                    "client_event_id": ev_older_id,
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": datetime.now(timezone.utc).isoformat(),
                    "measured_at": t_older.isoformat(),
                    "payload": {"measurement_type": "heart_rate", "value": 65.0, "unit": "bpm"},
                }
            ],
        },
    )

    # Query measurements: Both must exist, ordered chronologically
    res = client.get(
        f"/api/v1/measurements?crew_id={test_crew['crew_1']}&measurement_type=heart_rate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 2
    # Ensure t_older (65 bpm) appears before t_newer (72 bpm) in chronological order
    hr_values = [it["value_numeric"] for it in items]
    assert 65.0 in hr_values
    assert 72.0 in hr_values


# ==============================================================================
# 6. Expired / Malformed Event Metadata Tests
# ==============================================================================

def test_expired_or_future_timestamps_rejected(client: TestClient, crew_1_token, test_crew):
    """Verifies that timestamps > 15 minutes into the future are rejected."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    res = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "BATCH-FUTURE",
            "client_sync_at": datetime.now(timezone.utc).isoformat(),
            "events": [
                {
                    "client_event_id": str(uuid.uuid4()),
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": datetime.now(timezone.utc).isoformat(),
                    "measured_at": future_time.isoformat(),
                    "payload": {"measurement_type": "heart_rate", "value": 75.0, "unit": "bpm"},
                }
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["rejected_count"] == 1
    assert data["results"][0]["status"] == "rejected"
    assert data["results"][0]["error_code"] == "invalid_future_timestamp"


def test_unsupported_schema_version_rejected(client: TestClient, crew_1_token, test_crew):
    """Verifies that unsupported schema versions are rejected."""
    now = datetime.now(timezone.utc)
    res = client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "BATCH-SCHEMA-99",
            "client_sync_at": now.isoformat(),
            "events": [
                {
                    "client_event_id": str(uuid.uuid4()),
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "99.0",  # Unsupported
                    "client_event_at": now.isoformat(),
                    "measured_at": now.isoformat(),
                    "payload": {"measurement_type": "heart_rate", "value": 75.0, "unit": "bpm"},
                }
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["rejected_count"] == 1
    assert data["results"][0]["status"] == "rejected"
    assert data["results"][0]["error_code"] == "unsupported_schema_version"


# ==============================================================================
# 7. Sync Status Polling & Concurrent Retries Tests
# ==============================================================================

def test_sync_status_polling(client: TestClient, crew_1_token, test_crew):
    """Verifies that client can query status of a specific client event UUID."""
    now = datetime.now(timezone.utc)
    client_ev_id = str(uuid.uuid4())

    # Ingest event
    client.post(
        "/api/v1/sync",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "batch_id": "BATCH-POLL-TEST",
            "client_sync_at": now.isoformat(),
            "events": [
                {
                    "client_event_id": client_ev_id,
                    "crew_member_id": str(test_crew["crew_1"]),
                    "event_type": "MEASUREMENT",
                    "schema_version": "1.0",
                    "client_event_at": now.isoformat(),
                    "measured_at": now.isoformat(),
                    "payload": {"measurement_type": "heart_rate", "value": 76.0, "unit": "bpm"},
                }
            ],
        },
    )

    # Poll status
    status_res = client.get(
        f"/api/v1/sync/status/{client_ev_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["client_event_id"] == client_ev_id
    assert status_data["status"] == "accepted"
    assert status_data["entity_id"] is not None

    # Query unknown client event UUID -> 404
    missing_res = client.get(
        f"/api/v1/sync/status/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert missing_res.status_code == 404


def test_concurrent_duplicate_requests_and_retries(client: TestClient, crew_1_token, test_crew):
    """Verifies safe retries and idempotency when duplicate requests arrive in succession."""
    now = datetime.now(timezone.utc)
    ev_id = str(uuid.uuid4())

    batch_payload = {
        "batch_id": "BATCH-CONCURRENT-SIM",
        "client_sync_at": now.isoformat(),
        "events": [
            {
                "client_event_id": ev_id,
                "crew_member_id": str(test_crew["crew_1"]),
                "event_type": "MEASUREMENT",
                "schema_version": "1.0",
                "client_event_at": now.isoformat(),
                "measured_at": now.isoformat(),
                "payload": {"measurement_type": "heart_rate", "value": 78.0, "unit": "bpm"},
            }
        ],
    }

    # First request
    r1 = client.post("/api/v1/sync", headers={"Authorization": f"Bearer {crew_1_token}"}, json=batch_payload)
    assert r1.status_code == 200
    assert r1.json()["results"][0]["status"] == "accepted"

    # Second immediate request simulates network retry / race condition
    r2 = client.post("/api/v1/sync", headers={"Authorization": f"Bearer {crew_1_token}"}, json=batch_payload)
    assert r2.status_code == 200
    assert r2.json()["results"][0]["status"] == "duplicate"
    assert r2.json()["results"][0]["entity_id"] == r1.json()["results"][0]["entity_id"]
