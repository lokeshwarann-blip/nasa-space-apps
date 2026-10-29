import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_settings_default_values():
    """Verify default application settings are properly initialized."""
    settings = Settings(
        SECRET_KEY="min-32-chars-long-secret-key-valid-for-tests!",
    )
    assert settings.PROJECT_NAME == "NASA Space Apps - Astronaut Health Monitor"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.ENVIRONMENT == "development"
    assert settings.POSTGRES_PORT == 5432
    assert "postgresql+asyncpg://" in settings.async_database_url


def test_settings_secret_key_too_short():
    """Verify that a SECRET_KEY shorter than 32 characters is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="short-key")
    error_str = str(exc_info.value)
    assert "at least 32 characters" in error_str or "string_too_short" in error_str


def test_settings_custom_database_url():
    """Verify explicit DATABASE_URL overrides individual connection parameters."""
    custom_url = "postgresql+asyncpg://user:pass@remotehost:5433/custom_db"
    settings = Settings(
        SECRET_KEY="min-32-chars-long-secret-key-valid-for-tests!",
        DATABASE_URL=custom_url,
    )
    assert settings.async_database_url == custom_url


def test_settings_auto_normalizes_standard_postgres_url():
    """Verify standard postgresql:// URL is converted to postgresql+asyncpg://."""
    sync_url = "postgresql://user:pass@remotehost:5433/custom_db"
    settings = Settings(
        SECRET_KEY="min-32-chars-long-secret-key-valid-for-tests!",
        DATABASE_URL=sync_url,
    )
    assert settings.async_database_url.startswith("postgresql+asyncpg://")
