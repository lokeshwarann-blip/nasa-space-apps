"""Phase 3.1: Database Seeding Routine for Astronaut Experience Demo.

Seeds:
1. Demo crew member 'CREW-001' (and associated test user account)
2. 14 days of verified physiological baseline telemetry and frozen baseline
3. Operational quests and initial collective team streak
4. Science context cards and initial unlocked card state

Usage:
    python backend/src/seed.py
    python backend/src/seed.py --clean
    python -m src.seed
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any
import uuid

# Ensure backend directory and repo root are in python search path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_engine, get_session_factory
from src.core.security import hash_password
from src.models.base import Base
from src.models import CrewMember, User, HealthMeasurement
from src.models.quests import Quest, QuestProgress, TeamStreak, Unlock
from src.modules.readiness.baseline import BaselineStore, fit_frozen_baseline
from src.api.v1.quests_mock import DEFAULT_SEEDED_QUESTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")

DEMO_CREW_ID_STR = "CREW-001"
DEMO_CREW_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, DEMO_CREW_ID_STR)

_CARDS_PATH = Path(__file__).resolve().parent / "data" / "science_cards.json"


async def seed_database(
    clean: bool = False,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Seeds the database with demo crew, 14-day baseline measurements, quests, and science cards.
    
    If an external session is provided, runs within that session without creating engines.
    Otherwise, creates engine and manages session lifecycle.
    """
    if session is not None:
        return await _execute_seed(session, clean=clean)

    settings = get_settings()
    logger.info("Connecting to database: %s", settings.async_database_url)
    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = get_session_factory()
    async with session_factory() as sess:
        return await _execute_seed(sess, clean=clean)


async def _execute_seed(session: AsyncSession, clean: bool = False) -> dict[str, Any]:
    """Internal execution logic for database seeding."""
    if clean:
        logger.info("Cleaning existing test measurements, crew, quests, and streak records...")
        await session.execute(delete(Unlock))
        await session.execute(delete(QuestProgress))
        await session.execute(delete(Quest))
        await session.execute(delete(TeamStreak))
        await session.execute(delete(HealthMeasurement))
        await session.execute(delete(User).where(User.username == "crew-001"))
        await session.execute(delete(CrewMember).where(CrewMember.crew_id == DEMO_CREW_ID_STR))
        await session.commit()
        BaselineStore.clear()
        logger.info("Clean completed.")

    # 1. Seed Demo Crew Member CREW-001
    stmt = select(CrewMember).where(CrewMember.crew_id == DEMO_CREW_ID_STR)
    crew_res = await session.execute(stmt)
    crew = crew_res.scalar_one_or_none()

    if crew is None:
        crew = CrewMember(
            id=DEMO_CREW_UUID,
            crew_id=DEMO_CREW_ID_STR,
            status="ACTIVE",
            profile_metadata={
                "callsign": "Ares",
                "role": "Commander",
                "specialization": "Aerospace Operations",
                "flight_experience_missions": 2,
            },
        )
        session.add(crew)
        await session.flush()
        logger.info("Created demo crew member %s (%s).", crew.crew_id, crew.id)
    else:
        logger.info("Demo crew member %s already exists.", crew.crew_id)

    # 1b. Seed Demo User Account for Authentication
    user_stmt = select(User).where(User.username == "crew-001")
    user_res = await session.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user is None:
        user = User(
            username="crew-001",
            hashed_password=hash_password("DemoPassword123!"),
            role="CREW_MEMBER",
            is_active=True,
            crew_member_id=crew.id,
            assigned_crew_ids=[],
        )
        session.add(user)
        await session.flush()
        logger.info("Created demo user account crew-001.")

    # 2. Seed 14 Days of Physiological Baseline Telemetry
    from eval.generator import generate_independent_trajectory

    raw_trajectory = generate_independent_trajectory(seed=1001, days=14)
    seeded_readings_count = 0

    # Check if baseline measurements already exist
    count_stmt = select(HealthMeasurement.id).where(HealthMeasurement.crew_member_id == crew.id).limit(1)
    has_readings = (await session.execute(count_stmt)).scalar_one_or_none() is not None

    parsed_rows_for_baseline: list[dict[str, Any]] = []

    for r in raw_trajectory:
        m_at = r["measured_at"]
        if isinstance(m_at, str):
            m_at = datetime.fromisoformat(m_at.replace("Z", "+00:00"))

        parsed_rows_for_baseline.append({
            "measurement_type": r["measurement_type"],
            "value_numeric": float(r["value_numeric"]),
            "measured_at": m_at,
            "quality_status": "VERIFIED",
        })

        if not has_readings:
            measurement = HealthMeasurement(
                id=uuid.uuid4(),
                crew_member_id=crew.id,
                measurement_type=r["measurement_type"],
                value_numeric=float(r["value_numeric"]),
                unit=r.get("unit", "standard"),
                measured_at=m_at,
                recorded_at=m_at,
                input_method="WEARABLE_SENSOR",
                quality_status="VERIFIED",
                provenance={"source": "seed_simulator", "seed": 1001},
                context_metadata={"phase": "baseline_calibration"},
            )
            session.add(measurement)
            seeded_readings_count += 1

    if seeded_readings_count > 0:
        logger.info("Seeded %d physiological baseline measurements for %s.", seeded_readings_count, crew.crew_id)

    # Fit & Store Frozen Baseline in BaselineStore
    frozen_bl = fit_frozen_baseline(
        crew_member_id=str(crew.id),
        raw_rows=parsed_rows_for_baseline,
        reason="Demonstration calibration window baseline",
        calibration_window_days=14,
    )
    BaselineStore.save(frozen_bl)
    # Also index by crew string id for flexible lookup
    if str(crew.crew_id) != str(crew.id):
        frozen_bl_display = fit_frozen_baseline(
            crew_member_id=str(crew.crew_id),
            raw_rows=parsed_rows_for_baseline,
            reason="Demonstration calibration window baseline",
            calibration_window_days=14,
        )
        BaselineStore.save(frozen_bl_display)
    logger.info("Calculated & registered frozen baseline for %s (sufficiency: %s).", crew.crew_id, frozen_bl.overall_sufficiency)

    # 3. Seed Operational Quests & Team Streak
    seeded_quests_count = 0
    for q_data in DEFAULT_SEEDED_QUESTS:
        q_stmt = select(Quest).where(Quest.id == q_data["id"])
        q_existing = (await session.execute(q_stmt)).scalar_one_or_none()
        if q_existing is None:
            new_quest = Quest(
                id=q_data["id"],
                title=q_data["title"],
                target=q_data["target"],
                unit=q_data["unit"],
                period=q_data["period"],
                rationale=q_data["rationale"],
                source=q_data.get("source"),
                evidence_level=q_data["evidence_level"],
            )
            session.add(new_quest)
            seeded_quests_count += 1

    # Seed Team Streak
    streak_stmt = select(TeamStreak).where(TeamStreak.streak_type == "team")
    streak = (await session.execute(streak_stmt)).scalar_one_or_none()
    if streak is None:
        streak = TeamStreak(
            streak_type="team",
            current_streak=5,
            longest_streak=12,
            freeze_days_remaining=2,
            last_activity_date=datetime.now(timezone.utc),
        )
        session.add(streak)
        logger.info("Created team streak (current: 5 days, freeze: 2 remaining).")

    # 4. Seed Science Context Cards Unlock State
    with open(_CARDS_PATH, "r", encoding="utf-8") as f:
        cards_data: list[dict] = json.load(f)

    # Unlock initial card 'sc-fluid-shift'
    initial_card_key = "sc-fluid-shift"
    unlock_stmt = select(Unlock).where(Unlock.crew_id == "team", Unlock.unlock_key == initial_card_key)
    existing_unlock = (await session.execute(unlock_stmt)).scalar_one_or_none()
    if existing_unlock is None:
        unlock = Unlock(
            crew_id="team",
            unlock_key=initial_card_key,
            unlocked_at=datetime.now(timezone.utc),
        )
        session.add(unlock)
        logger.info("Unlocked initial science context card '%s'.", initial_card_key)

    await session.commit()

    summary = {
        "crew_id": crew.crew_id,
        "crew_uuid": str(crew.id),
        "baseline_readings": seeded_readings_count or len(raw_trajectory),
        "baseline_sufficiency": frozen_bl.overall_sufficiency,
        "quests_available": len(DEFAULT_SEEDED_QUESTS),
        "cards_available": len(cards_data),
        "initial_unlocked_card": initial_card_key,
        "current_streak": streak.current_streak,
    }

    logger.info("Phase 3.1 Demo Seeding completed successfully: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3.1: Seed demo crew crew-001, baselines, quests, and science cards.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe existing test data before seeding.",
    )
    args = parser.parse_args()

    res = asyncio.run(seed_database(clean=args.clean))
    print("\n" + "=" * 65)
    print("ASTRONAUT EXPERIENCE DEMO DATA SEEDED SUCCESSFULLY (PHASE 3.1)")
    print("=" * 65)
    for k, v in res.items():
        print(f"  {k:<24}: {v}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
