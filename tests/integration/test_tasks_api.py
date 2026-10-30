"""Integration tests for the Wellness Tasks and Reminders API.

Verifies:
- Task definition creation and recurrence configuration.
- Least privilege & unauthorized task changes (BOLA prevention).
- Bounded due window validation.
- Idempotent task completion.
- Unconfigured schedules behavior (no auto-invented tasks).
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
# 1. Task Definition & Scheduling Tests
# ==============================================================================

def test_task_definition_and_scheduling(client: TestClient, flight_surgeon_token, test_crew):
    """Verifies that authorized medical officers can configure task definitions and schedule instances."""
    # 1. Create reusable definition
    def_res = client.post(
        "/api/v1/tasks/definitions",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "definition_identifier": "TASK-DEF-AM-VITALS",
            "title": "Daily Morning Biometric Vitals",
            "description": "Acquire resting blood pressure and heart rate using portable monitor.",
            "category": "MEASUREMENT_REMINDER",
            "target_measurement_type": "blood_pressure",
            "recurrence_config": {
                "frequency": "DAILY",
                "interval": 1,
                "due_window_hours": 4.0,
            },
        },
    )
    assert def_res.status_code == 201
    def_data = def_res.json()
    assert def_data["definition_identifier"] == "TASK-DEF-AM-VITALS"
    def_id = def_data["id"]

    # 2. Schedule task instance for crew 1
    now = datetime.now(timezone.utc)
    due_start = now + timedelta(hours=1)
    due_end = due_start + timedelta(hours=4)

    task_res = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "task_definition_id": def_id,
            "crew_member_id": str(test_crew["crew_1"]),
            "title": "Daily Morning Biometric Vitals - Sol 42",
            "category": "MEASUREMENT_REMINDER",
            "due_start": due_start.isoformat(),
            "due_end": due_end.isoformat(),
        },
    )
    assert task_res.status_code == 201
    task_data = task_res.json()
    assert task_data["status"] == "PENDING"
    assert task_data["crew_member_id"] == str(test_crew["crew_1"])
    assert len(task_data["audit_records"]) == 1
    assert task_data["audit_records"][0]["action"] == "CREATED"


# ==============================================================================
# 2. Unauthorized Task Changes (BOLA & Least Privilege)
# ==============================================================================

def test_unauthorized_task_changes(client: TestClient, crew_1_token, crew_2_token, flight_surgeon_token, test_crew):
    """Verifies that crew members cannot configure definitions, assign tasks, cancel tasks, or alter others' tasks."""
    # 1. Crew cannot create task definition
    def_res = client.post(
        "/api/v1/tasks/definitions",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "definition_identifier": "UNAUTHORIZED-DEF",
            "title": "Unauthorized",
            "category": "GENERAL",
        },
    )
    assert def_res.status_code == 403

    # 2. Crew cannot schedule task instances
    now = datetime.now(timezone.utc)
    assign_res = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "title": "Self Assigned",
            "category": "GENERAL",
            "due_start": now.isoformat(),
            "due_end": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert assign_res.status_code == 403

    # Create task for crew 1 as flight surgeon
    create_res = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "title": "Crew 1 Check-In",
            "category": "WELLNESS_CHECK_IN",
            "due_start": now.isoformat(),
            "due_end": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert create_res.status_code == 201
    task_id = create_res.json()["id"]

    # 3. Crew cannot cancel task
    cancel_res = client.post(
        f"/api/v1/tasks/{task_id}/cancel",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"cancellation_reason": "I don't want to do this"},
    )
    assert cancel_res.status_code == 403

    # 4. Crew 2 cannot view or complete Crew 1's task (BOLA prevention)
    bola_get = client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {crew_2_token}"},
    )
    assert bola_get.status_code == 403

    bola_complete = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {crew_2_token}"},
        json={"completion_source": "CREW_PORTAL"},
    )
    assert bola_complete.status_code == 403


# ==============================================================================
# 3. Idempotent Task Completion Tests
# ==============================================================================

def test_idempotent_task_completion(client: TestClient, flight_surgeon_token, crew_1_token, test_crew):
    """Verifies that fulfilling a task is idempotent and does not produce duplicate completion records."""
    now = datetime.now(timezone.utc)
    create_res = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "title": "Resting Heart Rate Capture",
            "category": "MEASUREMENT_REMINDER",
            "due_start": now.isoformat(),
            "due_end": (now + timedelta(hours=3)).isoformat(),
        },
    )
    task_id = create_res.json()["id"]

    measurement_id = str(uuid.uuid4())
    completion_payload = {
        "completion_source": "DEVICE_SYNC",
        "reference_measurement_id": measurement_id,
        "completion_notes": "Captured during morning scheduled window.",
    }

    # First completion
    c1 = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=completion_payload,
    )
    assert c1.status_code == 200
    data_1 = c1.json()
    assert data_1["status"] == "COMPLETED"
    assert data_1["completed_at"] is not None
    audit_count_1 = len(data_1["audit_records"])

    # Second completion (idempotent call)
    c2 = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json=completion_payload,
    )
    assert c2.status_code == 200
    data_2 = c2.json()
    assert data_2["status"] == "COMPLETED"
    assert len(data_2["audit_records"]) == audit_count_1, "Idempotent completion must not duplicate audit records"


# ==============================================================================
# 4. Unconfigured Schedules & Due Window Validation
# ==============================================================================

def test_unconfigured_schedules(client: TestClient, crew_1_token, test_crew):
    """Verifies that an astronaut with no configured schedules receives empty task list."""
    res = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0
    assert len(res.json()["items"]) == 0


def test_invalid_task_due_window(client: TestClient, flight_surgeon_token, test_crew):
    """Verifies that due_start >= due_end is rejected with 400 Bad Request."""
    now = datetime.now(timezone.utc)
    res = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "title": "Inverted Window",
            "category": "GENERAL",
            "due_start": (now + timedelta(hours=2)).isoformat(),
            "due_end": now.isoformat(),  # End precedes start!
        },
    )
    assert res.status_code == 400
    assert "due_start must strictly precede due_end" in res.json()["error"]["message"]

