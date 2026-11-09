"""Database seeding script for local test environment.

Populates the database with:
1. The 6 pseudonymous crew members from test/crew_members.json
2. Standard test user accounts (crew members, flight surgeon, admin)
3. 480 timestamped physiological health measurements from test/health_readings.json

Usage:
    python test/seed_test_db.py
    python test/seed_test_db.py --clean   # Clears test data before re-seeding
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import uuid

# Ensure backend and test directory are in python search path
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
_TEST_DIR = Path(__file__).resolve().parent

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_engine, get_session_factory
from src.core.security import hash_password
from src.models import (
    Base,
    CrewMember,
    HealthMeasurement,
    User,
)

try:
    from test.fixtures import TEST_USERS
except (ImportError, ModuleNotFoundError):
    from fixtures import TEST_USERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_test_db")

_DATA_DIR = Path(__file__).resolve().parent
_CREW_FILE = _DATA_DIR / "crew_members.json"
_READINGS_FILE = _DATA_DIR / "health_readings.json"


async def seed_database(clean: bool = False) -> None:
    """Executes the test database seeding routine."""
    settings = get_settings()
    logger.info("Connecting to database: %s", settings.async_database_url)

    engine = get_engine()
    
    # Ensure all tables exist in the target database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = get_session_factory()

    async with session_factory() as session:
        if clean:
            logger.info("Cleaning existing test measurements, users, and crew records...")
            await session.execute(delete(HealthMeasurement))
            await session.execute(delete(User))
            await session.execute(delete(CrewMember))
            await session.commit()
            logger.info("Clean completed.")

        # 1. Seed Crew Members
        with open(_CREW_FILE, "r", encoding="utf-8") as f:
            crew_records = json.load(f)

        seeded_crew_count = 0
        for c in crew_records:
            cid = uuid.UUID(c["id"])
            stmt = select(CrewMember).where(CrewMember.id == cid)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            created_at_dt = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
            updated_at_dt = datetime.fromisoformat(c["updated_at"].replace("Z", "+00:00"))

            if existing:
                existing.crew_id = c["crew_id"]
                existing.status = c["status"]
                existing.profile_metadata = c["profile_metadata"]
                existing.updated_at = updated_at_dt
            else:
                member = CrewMember(
                    id=cid,
                    crew_id=c["crew_id"],
                    status=c["status"],
                    profile_metadata=c["profile_metadata"],
                    created_at=created_at_dt,
                    updated_at=updated_at_dt,
                )
                session.add(member)
                seeded_crew_count += 1

        await session.commit()
        logger.info("Seeded/updated %d crew members.", len(crew_records))

        # 2. Seed Test Users
        seeded_user_count = 0
        for u in TEST_USERS:
            stmt = select(User).where(User.username == u["username"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            crew_uuid = uuid.UUID(u["crew_member_id"]) if u["crew_member_id"] else None

            if existing:
                existing.role = u["role"]
                existing.crew_member_id = crew_uuid
                existing.assigned_crew_ids = u["assigned_crew_ids"]
                existing.hashed_password = hash_password(u["password"])
            else:
                user = User(
                    username=u["username"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    is_active=True,
                    crew_member_id=crew_uuid,
                    assigned_crew_ids=u["assigned_crew_ids"],
                )
                session.add(user)
                seeded_user_count += 1

        await session.commit()
        logger.info("Seeded/updated %d test user accounts.", len(TEST_USERS))

        # 3. Seed Health Measurements
        with open(_READINGS_FILE, "r", encoding="utf-8") as f:
            readings = json.load(f)

        seeded_measurement_count = 0
        for m in readings:
            mid = uuid.UUID(m["id"])
            stmt = select(HealthMeasurement).where(HealthMeasurement.id == mid)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            measured_at_dt = datetime.fromisoformat(m["measured_at"].replace("Z", "+00:00"))
            recorded_at_dt = datetime.fromisoformat(m["recorded_at"].replace("Z", "+00:00"))

            if not existing:
                measurement = HealthMeasurement(
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
                )
                session.add(measurement)
                seeded_measurement_count += 1

        await session.commit()
        logger.info("Seeded %d new health measurements (%d total in file).", seeded_measurement_count, len(readings))

    # Print summary table
    print("\n" + "=" * 70)
    print("TEST DATABASE SEEDING COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Crew Members Available:   {len(crew_records)}")
    print(f"Health Measurements:      {len(readings)} (spanning 48 hours)")
    print("\nTest User Accounts Created:")
    print(f"{'Username':<18} {'Password':<15} {'Role':<16} {'Assigned Scope'}")
    print("-" * 70)
    for u in TEST_USERS:
        scope = u["crew_member_id"] if u["crew_member_id"] else f"{len(u['assigned_crew_ids'])} crew members"
        print(f"{u['username']:<18} {u['password']:<15} {u['role']:<16} {scope}")
    print("=" * 70)
    print("\nYou can now log in via POST /api/v1/auth/token and query live trends!")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the test database with crew data, user accounts, and vitals.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe existing test crew, users, and measurements before seeding.",
    )
    args = parser.parse_args()

    try:
        asyncio.run(seed_database(clean=args.clean))
    except Exception as exc:
        logger.error("Failed to seed database: %s", exc)
        print("\n[ERROR] Could not connect to PostgreSQL database.")
        print("Please ensure PostgreSQL is running (e.g., via 'docker compose up -d db').\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
