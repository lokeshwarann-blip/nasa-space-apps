import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CrewMemberBase(BaseModel):
    crew_id: str = Field(..., max_length=32, description="Pseudonymous crew identifier")
    status: str = Field(default="ACTIVE", max_length=32)
    profile_metadata: dict[str, Any] = Field(default_factory=dict)


class CrewMemberCreate(CrewMemberBase):
    pass


class CrewMemberRead(CrewMemberBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

