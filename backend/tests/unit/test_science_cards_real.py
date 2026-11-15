"""Tests for science context cards loaded from JSON with quest-driven unlock state."""
import pytest
from fastapi.testclient import TestClient


class TestScienceCards:
    """Science context card tests."""

    def test_science_cards_load_with_evidence_levels(self, client: TestClient):
        """Cards load from JSON, Treg card is marked emerging."""
        resp = client.get("/api/v1/science-context")
        assert resp.status_code == 200
        data = resp.json()
        cards = data["cards"]
        assert len(cards) == 6
        treg = next(c for c in cards if c["id"] == "sc-tregs")
        assert treg["evidence_level"] == "emerging"
        # All others are established
        for c in cards:
            if c["id"] != "sc-tregs":
                assert c["evidence_level"] == "established"

    def test_science_cards_initially_locked(self, client: TestClient):
        """All cards start unlocked=False before any quest logging."""
        resp = client.get("/api/v1/science-context")
        assert resp.status_code == 200
        for card in resp.json()["cards"]:
            assert card["unlocked"] is False

    def test_science_card_unlocks_via_quest_log(self, client: TestClient):
        """Logging a quest unlocks its mapped science card."""
        # Log quest-circadian-light -> should unlock sc-circadian-light
        log_resp = client.post(
            "/api/v1/quests/quest-circadian-light/log",
            json={"event_id": "sc-test-event-1"},
        )
        assert log_resp.status_code == 200

        resp = client.get("/api/v1/science-context")
        cards = {c["id"]: c for c in resp.json()["cards"]}
        assert cards["sc-circadian-light"]["unlocked"] is True
        # Tregs should still be locked (needs 3 events)
        assert cards["sc-tregs"]["unlocked"] is False

    def test_tregs_unlocks_after_three_quests(self, client: TestClient):
        """Tregs card unlocks after 3+ quest events logged."""
        for i, qid in enumerate(["quest-resistive", "quest-aerobic", "quest-hydration"]):
            client.post(f"/api/v1/quests/{qid}/log", json={"event_id": f"sc-tregs-evt-{i}"})

        resp = client.get("/api/v1/science-context")
        cards = {c["id"]: c for c in resp.json()["cards"]}
        assert cards["sc-tregs"]["unlocked"] is True
