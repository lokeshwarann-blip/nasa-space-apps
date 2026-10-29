from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def test_liveness_probe_root(client: TestClient):
    """Verify GET /health/live returns 200 OK and live status."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "live"
    assert "timestamp" in data
    # Verify correlation ID is propagated in response headers
    assert "X-Request-ID" in response.headers


def test_liveness_probe_v1(client: TestClient):
    """Verify GET /api/v1/health/live returns 200 OK."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "live"


def test_readiness_probe_success_when_db_healthy(client: TestClient):
    """Verify GET /health/ready returns 200 OK and connected when DB check succeeds."""
    with patch("src.api.v1.health.check_db_connection", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = True
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert "version" in data


def test_readiness_probe_fails_503_when_db_unavailable(client: TestClient):
    """Verify GET /health/ready returns 503 and unhealthy when DB check fails."""
    with patch("src.api.v1.health.check_db_connection", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = False
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"

