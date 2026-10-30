import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    """OAuth2 compatible token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Verified claims from a decoded JWT access token."""
    sub: str
    role: Literal["CREW_MEMBER", "FLIGHT_SURGEON", "ADMIN"]
    iss: str
    aud: str
    exp: int
    iat: int
    crew_member_id: str | None = None
    assigned_crew_ids: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    """User login credential payload."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class UserCreate(BaseModel):
    """User account creation payload with strict role validation."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["CREW_MEMBER", "FLIGHT_SURGEON", "ADMIN"]
    crew_member_id: uuid.UUID | None = None
    assigned_crew_ids: list[uuid.UUID] = Field(default_factory=list)


class UserRead(BaseModel):
    """Public user response model excluding sensitive password hashes."""
    id: uuid.UUID
    username: str
    role: str
    is_active: bool
    crew_member_id: uuid.UUID | None = None
    assigned_crew_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

