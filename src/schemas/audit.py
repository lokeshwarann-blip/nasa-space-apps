import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AuditEventBase(BaseModel):
    actor: str = Field(..., max_length=128)
    action: str = Field(..., max_length=64)
    resource_type: str = Field(..., max_length=64)
    resource_id: str = Field(..., max_length=128)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class AuditEventCreate(AuditEventBase):
    pass


class AuditEventRead(AuditEventBase):
    id: uuid.UUID
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

