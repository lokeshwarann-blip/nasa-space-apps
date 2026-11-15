import uuid
import pytest
from fastapi.testclient import TestClient

from src.core.database import get_db
from src.main import create_app
from src.schemas.astronaut import QuestsResponse, QuestLogResponse


@pytest.fixture
def seeded_app(db_session):
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def test_quests_seed_and_list(seeded_app):
    """GET /quests returns 5 seeded quests; unsourced marked 'illustrative'."""
    with TestClient(seeded_app) as client:
        resp = client.get("/api/v1/quests")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["quests"]) == 5
        
        # Check unsourced quest is marked illustrative
        unsourced = [q for q in data["quests"] if q["id"] == "quest-rest-routine"][0]
        assert unsourced["evidence_level"] == "illustrative"

        validated = QuestsResponse(**data)
        assert len(validated.quests) == 5


def test_quest_log_idempotency_and_xp(seeded_app):
    """POST /quests/{id}/log is idempotent on event_id with no double XP."""
    client_event_id = f"evt-test-{uuid.uuid4().hex[:8]}"

    with TestClient(seeded_app) as client:
        # First log
        resp1 = client.post(
            "/api/v1/quests/quest-resistive/log",
            json={"event_id": client_event_id},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["xp_gained"] == 50
        assert data1["progress"] == 1.0

        # Duplicate log (same event_id)
        resp2 = client.post(
            "/api/v1/quests/quest-resistive/log",
            json={"event_id": client_event_id},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        # Returns the same event result without raising error or creating duplicate rows
        assert data2["event_id"] == client_event_id
        assert data2["quest_id"] == "quest-resistive"


def test_quest_log_unlock_trigger(seeded_app):
    """Logging quests triggers unlock conditions."""
    with TestClient(seeded_app) as client:
        # 1st quest log triggers badge_circadian_alignment
        e1 = f"evt-u1-{uuid.uuid4().hex[:8]}"
        r1 = client.post("/api/v1/quests/quest-circadian-light/log", json={"event_id": e1})
        assert r1.status_code == 200
        assert "badge_circadian_alignment" in r1.json()["unlocked"]

        # Log 2 more quests to trigger bonus_rest_window (>= 3 events)
        e2 = f"evt-u2-{uuid.uuid4().hex[:8]}"
        e3 = f"evt-u3-{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/quests/quest-aerobic/log", json={"event_id": e2})
        r3 = client.post("/api/v1/quests/quest-hydration/log", json={"event_id": e3})
        assert r3.status_code == 200
        assert "bonus_rest_window" in r3.json()["unlocked"]
