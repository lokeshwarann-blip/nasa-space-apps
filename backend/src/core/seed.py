import uuid
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.models.crew import CrewMember
from src.models.telemetry import HealthMeasurement
from src.models.wellness import WellnessCheckIn
from src.models.alerts import AlertInstance
from src.models.tasks import TaskInstance
from src.core.security import hash_password

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_FIXTURES_FILE = _REPO_ROOT / "test" / "health_readings_scenario.json"
if not _FIXTURES_FILE.exists():
    _FIXTURES_FILE = _REPO_ROOT / "test" / "health_readings.json"


async def seed_dev_data(session: AsyncSession) -> None:
    """Seeds local development database with essential testing accounts, telemetry, alerts, and tasks."""
    m_count = (await session.execute(select(func.count(HealthMeasurement.id)))).scalar_one()
    if m_count > 0:
        logger.info("Dev database already has %d measurements; skipping full seed.", m_count)
        return

    logger.info("Seeding initial development database users, vitals, alerts, and tasks...")

    # 1. Ensure crew members exist
    crew_records_file = _REPO_ROOT / "test" / "crew_members.json"
    if crew_records_file.exists():
        with open(crew_records_file, "r", encoding="utf-8") as f:
            crews_raw = json.load(f)
        for c in crews_raw:
            cid = uuid.UUID(c["id"])
            existing = (await session.execute(select(CrewMember).where(CrewMember.id == cid))).scalar_one_or_none()
            if not existing:
                session.add(CrewMember(
                    id=cid,
                    crew_id=c["crew_id"],
                    status=c.get("status", "ACTIVE"),
                    profile_metadata=c.get("profile_metadata", {})
                ))
        await session.flush()

    # Primary demo crew member
    crew_id = uuid.UUID("c1111111-1111-4111-8111-111111111111")
    default_pw_hash = hash_password("Password123!")

    # 2. Ensure test users exist
    test_users = [
        ("astro_watney", "CREW_MEMBER", crew_id, []),
        ("crew_astra", "CREW_MEMBER", crew_id, []),
        ("dr_stone", "FLIGHT_SURGEON", None, [str(crew_id)]),
        ("flight_surgeon", "FLIGHT_SURGEON", None, [str(crew_id)]),
        ("admin", "ADMIN", None, []),
    ]
    for uname, role, cm_id, assigned in test_users:
        u_exist = (await session.execute(select(User).where(User.username == uname))).scalar_one_or_none()
        if not u_exist:
            session.add(User(
                id=uuid.uuid4(),
                username=uname,
                hashed_password=default_pw_hash,
                role=role,
                is_active=True,
                crew_member_id=cm_id,
                assigned_crew_ids=assigned,
            ))
    await session.flush()

    # 3. Seed scenario measurements
    if _FIXTURES_FILE.exists():
        with open(_FIXTURES_FILE, "r", encoding="utf-8") as f:
            readings = json.load(f)
        for m in readings:
            mid = uuid.UUID(m["id"])
            measured_at_dt = datetime.fromisoformat(m["measured_at"].replace("Z", "+00:00"))
            recorded_at_dt = datetime.fromisoformat(m["recorded_at"].replace("Z", "+00:00"))
            session.add(HealthMeasurement(
                id=mid,
                crew_member_id=uuid.UUID(m["crew_member_id"]),
                measurement_type=m["measurement_type"],
                value_numeric=m["value_numeric"],
                unit=m["unit"],
                measured_at=measured_at_dt,
                recorded_at=recorded_at_dt,
                input_method=m.get("input_method", "WEARABLE_SENSOR"),
                provenance=m.get("provenance", {}),
                quality_status=m.get("quality_status", "VERIFIED"),
                context_metadata=m.get("context_metadata", {}),
            ))
        await session.flush()

    # 4. Current real-time vitals
    now = datetime.now(timezone.utc)
    for mtype, val, unit in [
        ("heart_rate", 68.0, "bpm"),
        ("spo2", 98.8, "%"),
        ("blood_pressure_systolic", 118.0, "mmHg"),
        ("blood_pressure_diastolic", 76.0, "mmHg"),
        ("body_temperature", 36.7, "degC"),
    ]:
        session.add(HealthMeasurement(
            id=uuid.uuid4(),
            crew_member_id=crew_id,
            measurement_type=mtype,
            value_numeric=val,
            unit=unit,
            measured_at=now,
            recorded_at=now,
            quality_status="VERIFIED",
            input_method="WEARABLE_SENSOR",
            provenance={"device": "BioHarness-V5"},
            context_metadata={"status": "NOMINAL"},
        ))

    # 5. Check-ins
    session.add_all([
        WellnessCheckIn(
            id=uuid.uuid4(),
            crew_member_id=crew_id,
            sleep_duration_hours=7.8,
            sleep_quality=4,
            mood=5,
            stress=2,
            fatigue=2,
            measured_at=now - timedelta(hours=6),
            recorded_at=now - timedelta(hours=6),
            provenance={"client": "CrewPortal-v1"}
        ),
        WellnessCheckIn(
            id=uuid.uuid4(),
            crew_member_id=crew_id,
            sleep_duration_hours=8.2,
            sleep_quality=5,
            mood=4,
            stress=1,
            fatigue=1,
            measured_at=now - timedelta(days=1),
            recorded_at=now - timedelta(days=1),
            provenance={"client": "CrewPortal-v1"}
        )
    ])

    # 6. Alerts
    session.add_all([
        AlertInstance(
            id=uuid.uuid4(),
            alert_identifier="ALT-2026-HR-001",
            crew_member_id=crew_id,
            source_finding_id="FINDING-HR-ELEVATED",
            idempotency_key=str(uuid.uuid4()),
            rule_id="RULE-HR-THRESHOLD",
            rule_version="1.0.0",
            indicator="heart_rate",
            priority="CAUTION",
            status="open",
            summary="Elevated resting heart rate detected during post-EVA review (88 bpm).",
            event_time=now - timedelta(hours=2),
            is_delayed=False
        ),
        AlertInstance(
            id=uuid.uuid4(),
            alert_identifier="ALT-2026-CO2-002",
            crew_member_id=crew_id,
            source_finding_id="FINDING-CABIN-CO2",
            idempotency_key=str(uuid.uuid4()),
            rule_id="RULE-ENV-CO2",
            rule_version="1.0.0",
            indicator="cabin_co2",
            priority="INFO",
            status="acknowledged",
            summary="Routine cabin CO2 scrubber nominal cycle completed.",
            event_time=now - timedelta(hours=5),
            is_delayed=False,
            acknowledged_at=now - timedelta(hours=4),
            acknowledged_by="flight_surgeon"
        )
    ])

    # 7. Today's Tasks
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999)
    session.add_all([
        TaskInstance(
            id=uuid.uuid4(),
            crew_member_id=crew_id,
            title="Morning Physiological Calibration & Resting ECG",
            category="MEASUREMENT_REMINDER",
            status="COMPLETED",
            due_start=today_start,
            due_end=today_end,
            completed_at=now - timedelta(hours=4)
        ),
        TaskInstance(
            id=uuid.uuid4(),
            crew_member_id=crew_id,
            title="Midday Hydration & SpO2 Sync Protocol",
            category="MEASUREMENT_REMINDER",
            status="PENDING",
            due_start=today_start,
            due_end=today_end,
            completed_at=None
        ),
        TaskInstance(
            id=uuid.uuid4(),
            crew_member_id=crew_id,
            title="Pre-Sleep Subjective Wellness Check-in",
            category="WELLNESS_CHECK_IN",
            status="PENDING",
            due_start=today_start,
            due_end=today_end,
            completed_at=None
        )
    ])

    await session.commit()
    logger.info("Dev seed data created successfully.")
