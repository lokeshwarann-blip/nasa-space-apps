"""Unit tests for Phase 3.1 demo seeding command."""
import asyncio
from sqlalchemy import select

from src.models import CrewMember, User, HealthMeasurement
from src.models.quests import Quest, TeamStreak, Unlock
from src.modules.readiness.baseline import BaselineStore
from src.seed import seed_database


class TestPhase3SeedCommand:
    """Test suite verifying one-command seeding on an isolated database."""

    def test_seed_empty_database(self, db_session):
        """Seeding on an empty database creates crew-001, baselines, quests, streaks, and cards."""
        async def _run():
            return await seed_database(clean=True, session=db_session)

        summary = asyncio.run(_run())

        assert summary["crew_id"] == "CREW-001"
        assert summary["quests_available"] == 5
        assert summary["cards_available"] >= 6
        assert summary["baseline_sufficiency"] in ("high", "moderate")
        assert summary["current_streak"] == 5

        # 1. Verify Crew Member
        crew_stmt = select(CrewMember).where(CrewMember.crew_id == "CREW-001")
        crew = db_session._sync.execute(crew_stmt).scalar_one_or_none()
        assert crew is not None
        assert crew.status == "ACTIVE"
        assert crew.profile_metadata.get("role") == "Commander"

        # 1b. Verify User
        user_stmt = select(User).where(User.username == "crew-001")
        user = db_session._sync.execute(user_stmt).scalar_one_or_none()
        assert user is not None
        assert user.role == "CREW_MEMBER"
        assert user.crew_member_id == crew.id

        # 2. Verify Baseline Measurements
        m_stmt = select(HealthMeasurement).where(HealthMeasurement.crew_member_id == crew.id)
        measurements = db_session._sync.execute(m_stmt).scalars().all()
        assert len(measurements) > 50
        assert all(m.quality_status == "VERIFIED" for m in measurements)

        # Verify Frozen Baseline in BaselineStore
        baseline = BaselineStore.get_active(str(crew.id))
        assert baseline is not None
        assert baseline.overall_sufficiency in ("high", "moderate")

        # 3. Verify Quests & Team Streak
        quests_stmt = select(Quest)
        quests = db_session._sync.execute(quests_stmt).scalars().all()
        assert len(quests) == 5
        quest_ids = {q.id for q in quests}
        assert "quest-resistive" in quest_ids
        assert "quest-circadian-light" in quest_ids

        streak_stmt = select(TeamStreak).where(TeamStreak.streak_type == "team")
        streak = db_session._sync.execute(streak_stmt).scalar_one_or_none()
        assert streak is not None
        assert streak.current_streak == 5
        assert streak.freeze_days_remaining == 2

        # 4. Verify Initial Card Unlock
        unlock_stmt = select(Unlock).where(Unlock.crew_id == "team")
        unlocks = db_session._sync.execute(unlock_stmt).scalars().all()
        assert any(u.unlock_key == "sc-fluid-shift" for u in unlocks)

    def test_seed_database_idempotency(self, db_session):
        """Repeated seeding does not duplicate records or cause unique constraint violations."""
        async def _run():
            await seed_database(clean=False, session=db_session)
            return await seed_database(clean=False, session=db_session)

        summary2 = asyncio.run(_run())

        assert summary2["crew_id"] == "CREW-001"
        crew_count = len(db_session._sync.execute(select(CrewMember).where(CrewMember.crew_id == "CREW-001")).scalars().all())
        assert crew_count == 1

        quests_count = len(db_session._sync.execute(select(Quest)).scalars().all())
        assert quests_count == 5
