import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

TaskCategoryLiteral = Literal["MEASUREMENT_REMINDER", "WELLNESS_CHECK_IN", "FOLLOW_UP_ACTION", "GENERAL"]
TaskStatusLiteral = Literal["PENDING", "COMPLETED", "CANCELLED", "MISSED"]


class TaskDefinitionBase(BaseModel):
    """Reusable blueprint schema for scheduled tasks."""
    model_config = ConfigDict(from_attributes=True)

    definition_identifier: str = Field(..., max_length=64, description="Unique code for task definition")
    title: str = Field(..., max_length=255, description="Clear task label (e.g. Daily Morning Blood Pressure)")
    description: str | None = Field(None, description="Detailed instructions for the astronaut")
    category: TaskCategoryLiteral = Field(..., description="Task category")
    target_measurement_type: str | None = Field(None, max_length=64, description="Target telemetry type if applicable")
    target_check_in_type: str | None = Field(None, max_length=32, description="Target check-in type if applicable")
    recurrence_config: dict[str, Any] | None = Field(
        None,
        description="Recurrence pattern: e.g. {'frequency': 'DAILY', 'interval': 1, 'due_window_hours': 4.0}",
    )
    is_active: bool = Field(True, description="Whether definition is active for scheduling")


class TaskDefinitionCreate(TaskDefinitionBase):
    """Payload to create a new task definition."""
    pass


class TaskDefinitionResponse(TaskDefinitionBase):
    """Response DTO for task definitions."""
    id: uuid.UUID
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskDefinitionListResponse(BaseModel):
    """Paginated collection of task definitions."""
    items: list[TaskDefinitionResponse]
    total: int
    limit: int
    offset: int


class TaskInstanceBase(BaseModel):
    """Base attributes for an assigned task instance."""
    model_config = ConfigDict(from_attributes=True)

    crew_member_id: uuid.UUID
    title: str = Field(..., max_length=255)
    category: TaskCategoryLiteral
    due_start: datetime
    due_end: datetime
    task_definition_id: uuid.UUID | None = None


class TaskInstanceCreate(TaskInstanceBase):
    """Payload to assign a task instance to an astronaut."""
    pass


class TaskCompleteRequest(BaseModel):
    """Payload to record completion of a task instance (idempotent)."""
    completion_source: str = Field("CREW_PORTAL", max_length=64)
    reference_measurement_id: uuid.UUID | None = None
    reference_check_in_id: uuid.UUID | None = None
    completion_notes: str | None = None


class TaskCancelRequest(BaseModel):
    """Payload to cancel an assigned task."""
    cancellation_reason: str = Field(..., min_length=3, description="Justification for cancelling the task")


class TaskAuditRecordResponse(BaseModel):
    """Audit record capturing task lifecycle actions."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_instance_id: uuid.UUID
    actor_id: str
    actor_role: str
    action: str
    previous_status: str | None = None
    new_status: str
    details: str | None = None
    recorded_at: datetime


class TaskInstanceResponse(TaskInstanceBase):
    """Assigned task instance response DTO."""
    id: uuid.UUID
    status: str
    completed_at: datetime | None = None
    completion_source: str | None = None
    reference_measurement_id: uuid.UUID | None = None
    reference_check_in_id: uuid.UUID | None = None
    completion_notes: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    audit_records: list[TaskAuditRecordResponse] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskInstanceListResponse(BaseModel):
    """Paginated collection of task instances."""
    items: list[TaskInstanceResponse]
    total: int
    limit: int
    offset: int

