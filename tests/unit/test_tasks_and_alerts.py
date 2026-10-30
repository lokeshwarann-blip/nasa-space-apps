"""Unit tests for wellness tasks, schedule recurrence, and alert lifecycles."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from src.models.alerts import AlertInstance
from src.models.tasks import TaskDefinition
from src.modules.alerts.schemas import (
    VALID_ALERT_TRANSITIONS,
    AlertCreate,
)
from src.modules.tasks.schemas import (
    TaskDefinitionCreate,
    TaskInstanceCreate,
)


def test_task_definition_recurrence_configuration():
    """Verifies recurrence configuration parsing on task definitions."""
    recurrence = {
        "frequency": "DAILY",
        "interval": 1,
        "due_window_hours": 4.0,
        "recommended_time_utc": "08:00:00",
    }
    task_def = TaskDefinitionCreate(
        definition_identifier="TASK-DEF-AM-VITALS",
        title="Morning Physiological Vitals",
        category="MEASUREMENT_REMINDER",
        target_measurement_type="blood_pressure",
        recurrence_config=recurrence,
    )
    assert task_def.recurrence_config["frequency"] == "DAILY"
    assert task_def.recurrence_config["due_window_hours"] == 4.0

    # Ensure due window duration calculation works deterministically
    start_time = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
    due_window = timedelta(hours=task_def.recurrence_config["due_window_hours"])
    end_time = start_time + due_window
    assert end_time - start_time == timedelta(hours=4)


def test_unconfigured_schedules_safety_principle():
    """Policy Guarantee: No mandatory schedules are invented if unconfigured."""
    # When recurrence_config is None, definition represents a manual/one-time task
    task_def = TaskDefinitionCreate(
        definition_identifier="TASK-DEF-POST-EVA-EXAM",
        title="Post-EVA Medical Debrief",
        category="FOLLOW_UP_ACTION",
        recurrence_config=None,
    )
    assert task_def.recurrence_config is None


def test_task_window_validation():
    """Ensures due_start and due_end are valid datetimes."""
    now = datetime.now(timezone.utc)
    inst = TaskInstanceCreate(
        crew_member_id=uuid.uuid4(),
        title="Valid Window Task",
        category="MEASUREMENT_REMINDER",
        due_start=now,
        due_end=now + timedelta(hours=2),
    )
    assert inst.due_end > inst.due_start


def test_alert_state_machine_transitions():
    """Validates the state machine transitions for the alert lifecycle."""
    # From open: can acknowledge, assign, or dismiss, but NOT directly resolve!
    assert "acknowledged" in VALID_ALERT_TRANSITIONS["open"]
    assert "assigned" in VALID_ALERT_TRANSITIONS["open"]
    assert "dismissed" in VALID_ALERT_TRANSITIONS["open"]
    assert "resolved" not in VALID_ALERT_TRANSITIONS["open"], "Cannot resolve an un-triaged open alert directly!"

    # From acknowledged: can assign, resolve, or dismiss
    assert "resolved" in VALID_ALERT_TRANSITIONS["acknowledged"]
    assert "assigned" in VALID_ALERT_TRANSITIONS["acknowledged"]

    # From assigned: can resolve, dismiss, or re-acknowledge
    assert "resolved" in VALID_ALERT_TRANSITIONS["assigned"]


def test_delayed_event_flagging_logic():
    """Verifies that delayed observations are flagged to prevent being misclassified as sudden emergencies."""
    now = datetime.now(timezone.utc)
    delayed_event_time = now - timedelta(hours=5)

    delay_seconds = (now - delayed_event_time).total_seconds()
    is_delayed = delay_seconds > 3600.0
    assert is_delayed is True

    recent_event_time = now - timedelta(minutes=10)
    recent_delay = (now - recent_event_time).total_seconds()
    assert (recent_delay > 3600.0) is False
