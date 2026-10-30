from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.core.config import Settings
from src.core.database import get_db
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
def mock_db_session():
    """Provides a mock async database session for isolated API testing."""
    session = AsyncMock()
    session.add = MagicMock()  # Synchronous in SQLAlchemy
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def app(test_settings: Settings, mock_db_session):
    """Provides a fresh FastAPI test application instance with mocked database session."""
    application = create_app(settings=test_settings)

    async def _override_get_db():
        yield mock_db_session

    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest.fixture
def client(app):
    """Provides a standard TestClient for testing API endpoints."""
    with TestClient(app) as test_client:
        yield test_client

