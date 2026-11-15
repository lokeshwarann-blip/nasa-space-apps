from functools import lru_cache
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ImmuneStressThresholds(BaseModel):
    """Configurable thresholds for evaluating immune-stress operational context."""
    # Sleep duration in hours (lower is worse)
    sleep_act: float = Field(default=5.0, description="Sleep duration in hours at or below which triggers ACT")
    sleep_watch: float = Field(default=6.5, description="Sleep duration in hours at or below which triggers WATCH")

    # HRV RMSSD in milliseconds (lower is worse)
    hrv_act: float = Field(default=25.0, description="HRV RMSSD in ms at or below which triggers ACT")
    hrv_watch: float = Field(default=40.0, description="HRV RMSSD in ms at or below which triggers WATCH")

    # Stress self-report rating 1-5 scale (higher is worse)
    stress_watch: float = Field(default=3.0, description="Subjective stress rating at or above which triggers WATCH")
    stress_act: float = Field(default=4.5, description="Subjective stress rating at or above which triggers ACT")

    # Cumulative radiation dose in mSv / mGy (higher is worse)
    dose_watch: float = Field(default=50.0, description="Cumulative absorbed radiation dose at or above which triggers WATCH")
    dose_act: float = Field(default=100.0, description="Cumulative absorbed radiation dose at or above which triggers ACT")


class Settings(BaseSettings):
    """Application settings validated via Pydantic v2 Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "NASA Space Apps - Astronaut Health Monitor"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "astronaut_health"
    DATABASE_URL: str | None = None

    # Database connection pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Security & Authentication Configuration
    SECRET_KEY: str = Field(
        default="insecure-default-key-for-dev-only-min-32-chars-long",
        min_length=32,
        description="Secret key for signing JWT tokens. Must be at least 32 characters.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "nasa-space-apps-auth"
    JWT_AUDIENCE: str = "nasa-space-apps-api"

    # Request limits
    MAX_REQUEST_BODY_SIZE_BYTES: int = 1_048_576  # 1 MB

    # CORS Settings
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Immune-stress context thresholds
    IMMUNE_STRESS_THRESHOLDS: ImmuneStressThresholds = Field(default_factory=ImmuneStressThresholds)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # In production, disallow obvious default keys
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v

    @property
    def async_database_url(self) -> str:
        """Returns the fully-qualified async SQLAlchemy connection URL."""
        if self.DATABASE_URL:
            # Normalize driver if standard postgresql:// was provided
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

