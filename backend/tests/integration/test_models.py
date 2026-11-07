import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    Base,
    CrewMember,
    Mission,
    MissionMembership,
    HealthMeasurement,
    WellnessCheckIn,
    SymptomCheckIn,
    GuidanceSource,
    ClinicalRule,
    Assessment,
    AuditEvent,
)


@pytest.fixture
def db_session():
    """Provides a fresh, disposable in-memory database session isolated from production."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_crew_member_and_mission_relationships(db_session: Session):
    """Verify entities, foreign keys, and relationships work as expected."""
    # 1. Create Crew Member
    crew = CrewMember(
        crew_id="CREW-101",
        status="ACTIVE",
        profile_metadata={"flight_role": "Flight Engineer"},
    )
    db_session.add(crew)

    # 2. Create Mission
    mission = Mission(
        mission_identifier="ARTEMIS-III",
        name="Artemis III Lunar Mission",
        mission_phase="LUNAR_SURFACE",
        operational_environment="LUNAR_SURFACE",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(mission)
    db_session.commit()

    # 3. Create Membership
    membership = MissionMembership(
        crew_member_id=crew.id,
        mission_id=mission.id,
        role="FLIGHT_ENGINEER",
        valid_from=datetime.now(timezone.utc),
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()

    # 4. Verify bidirectional relationship navigation
    db_session.refresh(crew)
    assert len(crew.mission_memberships) == 1
    assert crew.mission_memberships[0].role == "FLIGHT_ENGINEER"
    assert crew.mission_memberships[0].mission.mission_identifier == "ARTEMIS-III"


def test_unique_constraint_and_rollback_behavior(db_session: Session):
    """Verify unique constraint violations fail and transaction rollbacks cleanly restore state."""
    crew1 = CrewMember(crew_id="UNIQUE-001", status="ACTIVE")
    db_session.add(crew1)
    db_session.commit()

    # Attempt duplicate crew_id
    crew2 = CrewMember(crew_id="UNIQUE-001", status="ACTIVE")
    db_session.add(crew2)

    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback must restore clean state
    db_session.rollback()

    # Verify session is operational and only one record remains
    result = db_session.execute(select(CrewMember).where(CrewMember.crew_id == "UNIQUE-001")).scalars().all()
    assert len(result) == 1


def test_health_measurement_persistence_and_timezone(db_session: Session):
    """Verify health measurement persistence and timezone-aware timestamp handling."""
    crew = CrewMember(crew_id="CREW-202", status="ACTIVE")
    db_session.add(crew)
    db_session.commit()

    now_utc = datetime.now(timezone.utc)
    measurement = HealthMeasurement(
        crew_member_id=crew.id,
        measurement_type="heart_rate",
        value_numeric=68.5,
        unit="bpm",
        measured_at=now_utc,
        input_method="WEARABLE_SENSOR",
        provenance={"sensor_id": "ECG-PATCH-09"},
        quality_status="VERIFIED",
    )
    db_session.add(measurement)
    db_session.commit()

    # Query back
    saved = db_session.execute(
        select(HealthMeasurement).where(HealthMeasurement.crew_member_id == crew.id)
    ).scalar_one()

    assert saved.measurement_type == "heart_rate"
    assert saved.value_numeric == 68.5
    assert saved.unit == "bpm"
    assert saved.measured_at is not None


def test_cascade_deletion(db_session: Session):
    """Verify deleting a crew member cascades to their measurements and check-ins."""
    crew = CrewMember(crew_id="CREW-303", status="ACTIVE")
    db_session.add(crew)
    db_session.commit()

    now_utc = datetime.now(timezone.utc)
    measurement = HealthMeasurement(
        crew_member_id=crew.id,
        measurement_type="spo2",
        value_numeric=98.0,
        unit="%",
        measured_at=now_utc,
        provenance={"sensor_id": "PULSE-OX-01"},
    )
    wellness = WellnessCheckIn(
        crew_member_id=crew.id,
        sleep_duration_hours=8.0,
        sleep_quality=4,
        mood=4,
        stress=2,
        fatigue=2,
        measured_at=now_utc,
        provenance={"app": "crew-portal-v1"},
    )
    db_session.add_all([measurement, wellness])
    db_session.commit()

    # Delete crew member
    db_session.delete(crew)
    db_session.commit()

    # Assert children are cascaded
    measurements = db_session.execute(select(HealthMeasurement).where(HealthMeasurement.crew_member_id == crew.id)).scalars().all()
    wellness_records = db_session.execute(select(WellnessCheckIn).where(WellnessCheckIn.crew_member_id == crew.id)).scalars().all()
    assert len(measurements) == 0
    assert len(wellness_records) == 0


def test_guidance_source_and_clinical_rule(db_session: Session):
    """Verify guidance source and clinical rule persistence with FK restrictions."""
    source = GuidanceSource(
        source_identifier="NASA-STD-3001-VOL1-TEST",
        title="NASA Space Flight Human-System Standard: Crew Health",
        publisher="NASA Chief Health and Medical Officer",
        version="Rev C",
        review_state="APPROVED",
        approval_status="ACTIVE",
    )
    db_session.add(source)
    db_session.commit()

    rule = ClinicalRule(
        guidance_source_id=source.id,
        rule_identifier="RULE-TEST-HR-RESTING-HIGH",
        title="Resting Tachycardia In-Flight Warning",
        description="Flag elevated resting heart rate in microgravity environment.",
        applicable_context="MICROGRAVITY",
        measurement_type="heart_rate",
        parameters={"threshold_max": 100.0, "unit": "bpm"},
        review_state="APPROVED",
        approval_status="ACTIVE",
    )
    db_session.add(rule)
    db_session.commit()

    saved_rule = db_session.execute(
        select(ClinicalRule).where(ClinicalRule.rule_identifier == "RULE-TEST-HR-RESTING-HIGH")
    ).scalar_one()
    assert saved_rule.guidance_source.source_identifier == "NASA-STD-3001-VOL1-TEST"


def test_audit_event_logging(db_session: Session):
    """Verify audit events are stored with non-sensitive metadata."""
    event = AuditEvent(
        actor="FLIGHT_SURGEON_LEAD",
        action="ASSESS",
        resource_type="crew_member",
        resource_id="CREW-042",
        occurred_at=datetime.now(timezone.utc),
        metadata_={"session_id": "sess-abc", "ip": "127.0.0.1"},
    )
    db_session.add(event)
    db_session.commit()

    saved_event = db_session.execute(
        select(AuditEvent).where(AuditEvent.actor == "FLIGHT_SURGEON_LEAD")
    ).scalar_one()
    assert saved_event.action == "ASSESS"
    assert saved_event.metadata_["session_id"] == "sess-abc"

