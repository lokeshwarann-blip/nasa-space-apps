from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from src.api.v1.quests_mock import calculate_streak_update
from src.core.database import get_db
from src.main import create_app
from src.schemas.astronaut import TeamStreakResponse


@pytest.fixture
def seeded_app(db_session):
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def test_team_streak_consecutive_days():
    """Consecutive days increment current and longest streak."""
    t0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=1)

    curr, longest, freeze = calculate_streak_update(
        current_streak=3,
        longest_streak=5,
        freeze_days_remaining=2,
        last_activity_date=t0,
        new_activity_date=t1,
    )
    assert curr == 4
    assert longest == 5
    assert freeze == 2


def test_team_streak_same_day():
    """Multiple routine logs on the same calendar day maintain current streak."""
    t0 = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)

    curr, longest, freeze = calculate_streak_update(
        current_streak=3,
        longest_streak=5,
        freeze_days_remaining=2,
        last_activity_date=t0,
        new_activity_date=t1,
    )
    assert curr == 3
    assert longest == 5
    assert freeze == 2


def test_team_streak_freeze_days_protection():
    """1 missed day uses 1 freeze day; 2 missed days use 2 freeze days."""
    t0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    # 1 missed day (t0 + 2 days) -> 1 freeze day consumed
    t_gap1 = t0 + timedelta(days=2)
    curr1, longest1, freeze1 = calculate_streak_update(
        current_streak=4,
        longest_streak=4,
        freeze_days_remaining=2,
        last_activity_date=t0,
        new_activity_date=t_gap1,
    )
    assert curr1 == 5
    assert longest1 == 5
    assert freeze1 == 1

    # 2 missed days (t0 + 3 days) -> 2 freeze days consumed
    t_gap2 = t0 + timedelta(days=3)
    curr2, longest2, freeze2 = calculate_streak_update(
        current_streak=4,
        longest_streak=10,
        freeze_days_remaining=2,
        last_activity_date=t0,
        new_activity_date=t_gap2,
    )
    assert curr2 == 5
    assert longest2 == 10
    assert freeze2 == 0


def test_team_streak_exhausted_freeze_resets():
    """Missing more days than available freeze days resets streak to 1."""
    t0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    # 3 missed days (t0 + 4 days) exceeds 2 freeze days
    t_gap3 = t0 + timedelta(days=4)

    curr, longest, freeze = calculate_streak_update(
        current_streak=8,
        longest_streak=8,
        freeze_days_remaining=2,
        last_activity_date=t0,
        new_activity_date=t_gap3,
    )
    assert curr == 1
    assert longest == 8
    assert freeze == 2


def test_team_streak_shared_across_crew_no_rankings(seeded_app):
    """Team streak endpoint returns collective shared streak with zero individual rankings."""
    with TestClient(seeded_app) as client:
        # Initial empty streak
        resp = client.get("/api/v1/quests/streak")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_streak" in data
        assert "longest_streak" in data
        assert "freeze_days_remaining" in data
        # No rankings anywhere in payload
        assert "rank" not in data
        assert "leaderboard" not in data

        # Log routine updates collective streak
        client.post("/api/v1/quests/quest-resistive/log", json={"event_id": "streak-log-1"})
        resp2 = client.get("/api/v1/quests/streak")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["current_streak"] >= 1

        validated = TeamStreakResponse(**data2)
        assert validated.freeze_days_remaining >= 0
