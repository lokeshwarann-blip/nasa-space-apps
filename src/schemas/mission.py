import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MissionBase(BaseModel):
    mission_identifier: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    mission_phase: str = Field(default="PRE_FLIGHT", max_length=32)
    operational_environment: str = Field(default="MICROGRAVITY", max_length=32)
    start_time: datetime | None = None
    end_time: datetime | None = None


class MissionCreate(MissionBase):
    pass


class MissionRead(MissionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissionMembershipBase(BaseModel):
    crew_member_id: uuid.UUID
    mission_id: uuid.UUID
    role: str = Field(..., max_length=64)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool = True


class MissionMembershipCreate(MissionMembershipBase):
    pass


class MissionMembershipRead(MissionMembershipBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

