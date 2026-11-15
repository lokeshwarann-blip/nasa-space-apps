"""Unit tests for scipy ODE circadian rhythm phase alignment."""
import pytest
from fastapi.testclient import TestClient
from src.main import create_app
from src.schemas.astronaut import CircadianResponse


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestCircadianODE:
    """Circadian phase alignment tests across mission environment profiles."""

    @pytest.mark.parametrize(
        "profile,expected_lux,expected_dark,is_mars",
        [
            ("spacecraft", 450.0, 8.0, False),
            ("station", 500.0, 8.0, False),
            ("rover", 350.0, 7.5, False),
            ("lunar_base", 600.0, 8.0, False),
            ("mars_base", 500.0, 8.2, True),
        ],
    )
    def test_circadian_profiles_sanity(self, client: TestClient, profile: str, expected_lux: float, expected_dark: float, is_mars: bool):
        """Validates ODE output sanity, environment profile metadata, and Mars sol support."""
        resp = client.get(f"/api/v1/circadian/CREW-001?profile={profile}")
        assert resp.status_code == 200
        data = resp.json()

        validated = CircadianResponse(**data)
        assert validated.crew_id == "CREW-001"
        assert isinstance(validated.phase_offset_hours, float)
        assert -12.5 <= validated.phase_offset_hours <= 12.5
        assert validated.suggested_shift >= 0.0
        assert validated.days_to_realign >= 0
        assert "scipy ODE" in validated.model
        assert len(validated.assumptions) >= 4

        env = validated.environment_profile
        assert env.light_lux == expected_lux
        assert env.scheduled_dark_hours == expected_dark

        # Verify Mars sol modeling notes
        if is_mars:
            assert any("Martian sol" in a for a in validated.assumptions)

    def test_default_profile_fallback(self, client: TestClient):
        """Omitting profile parameter defaults to station profile."""
        resp = client.get("/api/v1/circadian/CREW-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["environment_profile"]["light_lux"] == 500.0
