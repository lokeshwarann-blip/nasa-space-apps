from typing import Any
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Detailed error object returned across all API endpoints."""

    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Root error response wrapper."""

    error: ErrorDetail

