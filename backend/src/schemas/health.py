from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    """Response model for process liveness probe."""

    status: Literal["live"] = "live"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReadinessResponse(BaseModel):
    """Response model for dependency readiness probe."""

    status: Literal["ready", "unhealthy"]
    database: Literal["connected", "disconnected"]
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

