import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from src.schemas.crew import CrewMemberCreate, CrewMemberRead
from src.schemas.mission import MissionCreate, MissionMembershipCreate
from src.schemas.telemetry import HealthMeasurementCreate, HealthMeasurementRead
from src.schemas.wellness import (
    WellnessCheckInCreate,
    SymptomCheckInCreate,
)
from src.schemas.clinical import (
    GuidanceSourceCreate,
    ClinicalRuleCreate,
    AssessmentCreate,
)
from src.schemas.audit import AuditEventCreate


def test_crew_member_schemas():
    """Verify crew member serialization and schema validation."""
    data = {"crew_id": "CREW-042", "status": "ACTIVE", "profile_metadata": {"role": "Commander"}}
    create_schema = CrewMemberCreate(**data)
    assert create_schema.crew_id == "CREW-042"

    read_schema = CrewMemberRead(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **data,
    )
    assert read_schema.crew_id == "CREW-042"


def test_telemetry_schema_requires_timezone_aware():
    """Verify that naive datetimes without timezone are rejected."""
    naive_dt = datetime(2026, 10, 30, 12, 0, 0)  # No tzinfo
    with pytest.raises(ValidationError) as exc:
        HealthMeasurementCreate(
            crew_member_id=uuid.uuid4(),
            measurement_type="heart_rate",
            value_numeric=75.0,
            unit="bpm",
            measured_at=naive_dt,
        )
    assert "Timestamp must be timezone-aware" in str(exc.value)


def test_wellness_checkin_schema_bounds():
    """Verify wellness check-in numeric bounds on sleep, mood, stress."""
    # Invalid sleep hours > 24
    with pytest.raises(ValidationError):
        WellnessCheckInCreate(
            crew_member_id=uuid.uuid4(),
            sleep_duration_hours=25.0,
            sleep_quality=3,
            mood=3,
            stress=3,
            fatigue=3,
            measured_at=datetime.now(timezone.utc),
        )

    # Invalid mood score < 1
    with pytest.raises(ValidationError):
        WellnessCheckInCreate(
            crew_member_id=uuid.uuid4(),
            sleep_duration_hours=7.5,
            sleep_quality=3,
            mood=0,
            stress=3,
            fatigue=3,
            measured_at=datetime.now(timezone.utc),
        )


def test_symptom_checkin_severity_validation():
    """Verify symptom severity only accepts MILD, MODERATE, SEVERE."""
    with pytest.raises(ValidationError):
        SymptomCheckInCreate(
            crew_member_id=uuid.uuid4(),
            symptom_identifiers=["HEADACHE"],
            severity="CATASTROPHIC",  # Unallowed severity
            onset_time=datetime.now(timezone.utc),
        )

    valid_symptom = SymptomCheckInCreate(
        crew_member_id=uuid.uuid4(),
        symptom_identifiers=["HEADACHE", "VERTIGO"],
        severity="MILD",
        onset_time=datetime.now(timezone.utc),
    )
    assert valid_symptom.severity == "MILD"


def test_assessment_schema_status():
    """Verify assessment status enum constraint."""
    valid_assessment = AssessmentCreate(
        subject_id=uuid.uuid4(),
        assessed_at=datetime.now(timezone.utc),
        engine_version="engine-v1.0.0",
        ruleset_version="rules-2026.1",
        assessment_status="NOMINAL",
        findings={"heart_rate": "within_nominal_range"},
    )
    assert valid_assessment.assessment_status == "NOMINAL"

    with pytest.raises(ValidationError):
        AssessmentCreate(
            subject_id=uuid.uuid4(),
            assessed_at=datetime.now(timezone.utc),
            engine_version="engine-v1.0.0",
            ruleset_version="rules-2026.1",
            assessment_status="UNKNOWN_STATUS",
            findings={},
        )


def test_audit_event_schema():
    """Verify audit event serialization without PHI."""
    audit = AuditEventCreate(
        actor="FLIGHT_SURGEON_01",
        action="READ",
        resource_type="health_measurement",
        resource_id=str(uuid.uuid4()),
        metadata={"ip": "10.0.0.1", "request_id": "req-123"},
    )
    assert audit.actor == "FLIGHT_SURGEON_01"
    assert audit.metadata_["ip"] == "10.0.0.1"

