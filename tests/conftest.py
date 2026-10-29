import pytest
from fastapi.testclient import TestClient

from src.core.config import Settings
from src.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provides isolated test configuration."""
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        SECRET_KEY="test-secret-key-that-is-at-least-32-chars-long!",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/astronaut_health_test",
        LOG_LEVEL="DEBUG",
    )


@pytest.fixture
def app(test_settings: Settings):
    """Provides a fresh FastAPI test application instance."""
    return create_app(settings=test_settings)


@pytest.fixture
def client(app):
    """Provides a standard TestClient for testing API endpoints."""
    with TestClient(app) as test_client:
        yield test_client

