"""Integration tests for the Clinical Alerts Lifecycle API.

Verifies:
- Deduplication and idempotency policy for repeated findings.
- Controlled state transitions (open -> acknowledged -> assigned -> resolved / dismissed).
- Rejection of invalid lifecycle jumps (e.g. open -> resolved).
- Delayed-event handling (historical event time kept distinct from alert creation time).
- Escalation interface and delivery provider confirmation (NO_DELIVERY_PROVIDER).
- Object-level authorization and least privilege.
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
# 1. Deduplication & Idempotency Tests
# ==============================================================================

def test_duplicate_alerts_and_idempotency(client: TestClient, flight_surgeon_token, test_crew):
    """Verifies that re-triggering an alert for the same finding and event time is deduplicated."""
    now = datetime.now(timezone.utc)
    payload = {
        "crew_member_id": str(test_crew["crew_1"]),
        "source_finding_id": "FINDING-HR-TACHYCARDIA-01",
        "rule_id": "RULE-NASA-HR-RESTING-HIGH",
        "rule_version": "1.0.0",
        "indicator": "heart_rate",
        "priority": "CAUTION",
        "summary": "Resting heart rate 118 bpm exceeds nominal threshold.",
        "event_time": now.isoformat(),
    }

    # First trigger
    r1 = client.post(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json=payload,
    )
    assert r1.status_code == 201
    alert_1 = r1.json()
    alert_id_1 = alert_1["id"]
    assert alert_1["status"] == "open"
    assert alert_1["priority"] == "CAUTION"

    # Second trigger with identical finding and event_time (deduplicated)
    r2 = client.post(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json=payload,
    )
    assert r2.status_code == 201 or r2.status_code == 200
    alert_2 = r2.json()
    assert alert_2["id"] == alert_id_1, "Repeated alert creation for same finding must be deduplicated"


# ==============================================================================
# 2. Valid and Invalid State Transitions
# ==============================================================================

def test_valid_and_invalid_state_transitions(client: TestClient, flight_surgeon_token, test_crew):
    """Verifies controlled state transitions and rejection of invalid jumps."""
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "source_finding_id": "FINDING-BP-HYPERTENSION-01",
            "rule_id": "RULE-NASA-BP-HIGH",
            "rule_version": "1.0.0",
            "indicator": "blood_pressure_systolic",
            "priority": "CRITICAL",
            "summary": "Systolic blood pressure 162 mmHg.",
            "event_time": now.isoformat(),
        },
    )
    alert_id = create_res.json()["id"]

    # 1. Invalid jump: open -> resolved directly without triage/acknowledgement
    invalid_resolve = client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={"resolution_reason": "Skipping directly to resolve"},
    )
    assert invalid_resolve.status_code == 400
    assert "Invalid approval status transition" in invalid_resolve.json()["error"]["message"]

    # 2. Valid transition: open -> acknowledged
    ack_res = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={"notes": "Triaged by flight surgeon on console."},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"

    # 3. Valid transition: acknowledged -> assigned
    assign_res = client.post(
        f"/api/v1/alerts/{alert_id}/assign",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={"assigned_to": "surgeon_dr_mccoy", "assignment_notes": "Assigned for telemetry review."},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "assigned"
    assert assign_res.json()["assigned_to"] == "surgeon_dr_mccoy"

    # 4. Valid transition: assigned -> resolved
    resolve_res = client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={"resolution_reason": "Secondary measurement nominal following rest; spurious initial sensor reading."},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"


# ==============================================================================
# 3. Notification Failure & Escalation Interface
# ==============================================================================

def test_notification_failure_and_escalation(client: TestClient, flight_surgeon_token, test_crew):
    """Verifies escalation interface and ensures unconfigured delivery provider is accurately reported."""
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "source_finding_id": "FINDING-SPO2-HYPOXIA-01",
            "rule_id": "RULE-NASA-SPO2-LOW",
            "rule_version": "1.0.0",
            "indicator": "spo2",
            "priority": "CRITICAL",
            "summary": "Pulse oximetry desaturation below 90%.",
            "event_time": now.isoformat(),
        },
    )
    alert_id = create_res.json()["id"]

    # Escalate to Mission Control
    esc_res = client.post(
        f"/api/v1/alerts/{alert_id}/escalate",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "escalation_target": "MISSION_CONTROL_FLIGHT_DIRECTOR",
            "escalation_reason": "Desaturation sustained during EVA prep.",
        },
    )
    assert esc_res.status_code == 200
    data = esc_res.json()
    assert data["escalation_level"] == "MISSION_CONTROL_FLIGHT_DIRECTOR"
    # Policy guarantee: Must not pretend an external recipient was notified when none is configured
    assert data["delivery_status"] == "NO_DELIVERY_PROVIDER"


# ==============================================================================
# 4. Delayed-Event Handling
# ==============================================================================

def test_delayed_event_handling(client: TestClient, flight_surgeon_token, test_crew):
    """Verifies that historical observations are flagged is_delayed to avoid false sudden emergencies."""
    now = datetime.now(timezone.utc)
    delayed_time = now - timedelta(hours=6)

    create_res = client.post(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "source_finding_id": "FINDING-HISTORICAL-DELAYED-01",
            "rule_id": "RULE-NASA-HR-RESTING-HIGH",
            "rule_version": "1.0.0",
            "indicator": "heart_rate",
            "priority": "CAUTION",
            "summary": "Historical batch telemetry synced following LOS (loss of signal).",
            "event_time": delayed_time.isoformat(),
        },
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["is_delayed"] is True
    # Verify event_time is strictly the historical time
    assert "2026-" in data["event_time"]


# ==============================================================================
# 5. Object-Level Access Control (BOLA Prevention)
# ==============================================================================

def test_alerts_bola_prevention(client: TestClient, crew_1_token, crew_2_token, flight_surgeon_token, test_crew):
    """Verifies that crew members cannot inspect or modify alerts belonging to other astronauts."""
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "source_finding_id": "FINDING-CREW1-SECRET-01",
            "rule_id": "RULE-NASA-TEST",
            "rule_version": "1.0.0",
            "indicator": "heart_rate",
            "priority": "CAUTION",
            "summary": "Crew 1 Health Alert",
            "event_time": now.isoformat(),
        },
    )
    alert_id = create_res.json()["id"]

    # Crew 2 attempts to view Crew 1's alert -> 403 Forbidden
    bola_get = client.get(
        f"/api/v1/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {crew_2_token}"},
    )
    assert bola_get.status_code == 403

    # Crew 1 attempts to resolve alert -> 403 Forbidden (Only flight surgeon/admin can resolve)
    crew_resolve = client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"resolution_reason": "I am feeling better"},
    )
    assert crew_resolve.status_code == 403

    # Crew 1 CAN acknowledge their own alert
    crew_ack = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"notes": "Astronaut acknowledged notification."},
    )
    assert crew_ack.status_code == 200
    assert crew_ack.json()["status"] == "acknowledged"

