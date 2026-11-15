from fastapi.testclient import TestClient
from src.main import create_app
from src.schemas.astronaut import (
    DISCLAIMER,
    CrewStatus,
    QuestsResponse,
    QuestLogResponse,
    ScienceContextResponse,
    PulseMeasurementResponse,
    ScenarioResponse,
    CircadianResponse,
)


def test_crew_status_mock(app):
    with TestClient(app) as client:
        resp = client.get("/api/v1/crew/CREW-001/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] == DISCLAIMER
        assert data["crew_id"] == "CREW-001"
        assert 0 <= data["readiness"]["score"] <= 100
        assert data["readiness"]["status"] in ("normal", "watch", "act", "call_ground")
        assert data["readiness"]["status_icon"] in ("circle-check", "triangle", "diamond", "octagon")
        assert data["data_quality"] in ("good", "sensor_issue")

        systems = {s["name"]: s for s in data["body_systems"]}
        expected_systems = {"heart", "lungs", "sleep_brain", "muscles_bones", "immune"}
        assert set(systems.keys()) == expected_systems

        for s in systems.values():
            assert s["status"] in ("normal", "watch", "act", "call_ground")
            assert s["status_icon"] in ("circle-check", "triangle", "diamond", "octagon")
            assert s["evidence_level"] in ("established", "emerging", "illustrative")
            assert "value" in s
            assert "unit" in s
            assert "baseline_low" in s
            assert "baseline_high" in s
            assert "trend" in s
            assert isinstance(s["series"], list)
            assert isinstance(s["forecast"], list)

        # Validate against Pydantic schema
        validated = CrewStatus(**data)
        assert validated.crew_id == "CREW-001"


def test_quests_mock(app):
    with TestClient(app) as client:
        resp = client.get("/api/v1/quests")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] == DISCLAIMER
        assert len(data["quests"]) == 5

        for q in data["quests"]:
            assert "title" in q
            assert "target" in q
            assert "unit" in q
            assert "period" in q
            assert "rationale" in q
            assert "source" in q
            assert q["evidence_level"] in ("established", "emerging", "illustrative")

        validated = QuestsResponse(**data)
        assert len(validated.quests) == 5


def test_quest_log_mock(app):
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/quests/quest-resistive/log",
            json={"event_id": "evt-resistive-test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] == DISCLAIMER
        assert data["quest_id"] == "quest-resistive"
        assert data["event_id"] == "evt-resistive-test"
        assert data["xp_gained"] > 0
        assert data["progress"] == 1.0
        assert isinstance(data["unlocked"], list)

        validated = QuestLogResponse(**data)
        assert validated.xp_gained > 0


def test_science_context_mock(app):
    with TestClient(app) as client:
        resp = client.get("/api/v1/science-context")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] == DISCLAIMER
        assert len(data["cards"]) >= 6

        # Check required topics
        signals = [sig for card in data["cards"] for sig in card["linked_signals"]]
        assert any("treg" in s for s in signals)

        # Spaceflight-Treg link must be marked "emerging"
        treg_card = [c for c in data["cards"] if "treg" in c["id"]][0]
        assert treg_card["evidence_level"] == "emerging"

        for card in data["cards"]:
            assert "title" in card
            assert "plain_summary" in card
            assert "why_it_matters" in card
            assert card["evidence_level"] in ("established", "emerging", "illustrative")
            assert len(card["sources"]) > 0
            assert len(card["linked_signals"]) > 0

        validated = ScienceContextResponse(**data)
        assert len(validated.cards) >= 6


def test_measurements_pulse_mock(app):
    with TestClient(app) as client:
        # Accepted pulse
        resp_accepted = client.post(
            "/api/v1/measurements/pulse",
            json={"hr": 72.0, "hrv": 45.0, "signal_quality": "good", "source": "wearable_ppg"},
        )
        assert resp_accepted.status_code == 200
        data_acc = resp_accepted.json()
        assert data_acc["disclaimer"] == DISCLAIMER
        assert data_acc["status"] == "accepted"
        assert "message" in data_acc
        assert "recorded_at" in data_acc
        assert data_acc["measurement_id"] is not None

        # Rejected pulse (poor quality)
        resp_rejected = client.post(
            "/api/v1/measurements/pulse",
            json={"hr": 72.0, "hrv": 45.0, "signal_quality": "poor", "source": "wearable_ppg"},
        )
        assert resp_rejected.status_code == 200
        data_rej = resp_rejected.json()
        assert data_rej["disclaimer"] == DISCLAIMER
        assert data_rej["status"] == "rejected"

        validated = PulseMeasurementResponse(**data_acc)
        assert validated.status == "accepted"


def test_scenario_mock(app):
    with TestClient(app) as client:
        scenarios = ["coordinated_drift", "sensor_fault", "comms_blackout", "dust_storm", "reset"]
        for sc in scenarios:
            resp = client.post("/api/v1/scenario", json={"type": sc})
            assert resp.status_code == 200
            data = resp.json()
            assert data["disclaimer"] == DISCLAIMER
            assert data["active_scenario"] == sc
            assert "message" in data
            assert "started_at" in data
            assert isinstance(data["parameters"], dict)

            validated = ScenarioResponse(**data)
            assert validated.active_scenario == sc


def test_circadian_mock(app):
    with TestClient(app) as client:
        resp = client.get("/api/v1/circadian/CREW-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] == DISCLAIMER
        assert data["crew_id"] == "CREW-001"
        assert "phase_offset_hours" in data
        assert "suggested_shift" in data
        assert "days_to_realign" in data
        assert "model" in data
        assert isinstance(data["assumptions"], list)
        assert "environment_profile" in data
        env = data["environment_profile"]
        assert "light_lux" in env
        assert "color_temperature_k" in env
        assert "blue_wavelength_attenuation" in env
        assert "temperature_c" in env
        assert "scheduled_dark_hours" in env

        validated = CircadianResponse(**data)
        assert validated.crew_id == "CREW-001"
