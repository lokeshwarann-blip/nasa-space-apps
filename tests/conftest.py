import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.core.database import get_db
from src.main import create_app
from src.models import Base
from tests.db_adapter import AsyncSessionAdapter


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
def db_engine():
    """Provides an isolated, in-memory SQLite database engine for testing."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provides a fresh isolated database session adapted for async FastAPI dependencies."""
    with Session(db_engine) as session:
        yield AsyncSessionAdapter(session)


@pytest.fixture
def app(test_settings: Settings, db_session):
    """Provides a fresh FastAPI test application instance with isolated in-memory DB override."""
    application = create_app(settings=test_settings)

    async def _override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest.fixture
def client(app):
    """Provides a standard TestClient for testing API endpoints."""
    with TestClient(app) as test_client:
        yield test_client
