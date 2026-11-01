import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity, require_roles
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.tasks.schemas import (
    TaskCancelRequest,
    TaskCompleteRequest,
    TaskDefinitionCreate,
    TaskDefinitionListResponse,
    TaskDefinitionResponse,
    TaskInstanceCreate,
    TaskInstanceListResponse,
    TaskInstanceResponse,
)
from src.modules.tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["Wellness Tasks & Reminders"])


# ==============================================================================
# Task Definitions Endpoints (Registered before dynamic /{task_id} routes)
# ==============================================================================

@router.get(
    "/definitions",
    response_model=TaskDefinitionListResponse,
    summary="List reusable task definitions",
    description="Retrieves registered task blueprints and scheduling templates.",
)
async def list_definitions(
    category: str | None = Query(None, description="MEASUREMENT_REMINDER, WELLNESS_CHECK_IN, FOLLOW_UP_ACTION, GENERAL"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.list_definitions(
        session=session,
        category=category,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/definitions",
    response_model=TaskDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reusable task definition",
    description="Configures a new task template with recurrence rules. Restricted to Flight Surgeons and Administrators.",
)
async def create_definition(
    def_in: TaskDefinitionCreate,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.create_definition(
        session=session,
        def_in=def_in,
        actor_identity=identity,
    )


# ==============================================================================
# Task Instances Endpoints
# ==============================================================================

@router.get(
    "",
    response_model=TaskInstanceListResponse,
    summary="List assigned task instances",
    description="Retrieves scheduled tasks. Astronauts only view their personal assignments.",
)
async def list_tasks(
    crew_member_id: uuid.UUID | None = Query(None, description="Filter by astronaut UUID"),
    status: str | None = Query(None, description="PENDING, COMPLETED, CANCELLED, MISSED"),
    category: str | None = Query(None, description="Task category"),
    due_from: datetime | None = Query(None, description="Filter tasks due after (UTC)"),
    due_to: datetime | None = Query(None, description="Filter tasks due before (UTC)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.list_instances(
        session=session,
        crew_member_id=crew_member_id,
        status=status,
        category=category,
        due_from=due_from,
        due_to=due_to,
        limit=limit,
        offset=offset,
        identity=identity,
    )


@router.post(
    "",
    response_model=TaskInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a task instance to an astronaut",
    description="Schedules a task instance for an astronaut with a bounded due window. Restricted to Flight Surgeons and Admins.",
)
async def create_task(
    inst_in: TaskInstanceCreate,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.create_instance(
        session=session,
        inst_in=inst_in,
        actor_identity=identity,
    )


@router.get(
    "/{task_id}",
    response_model=TaskInstanceResponse,
    summary="Get task instance by ID",
    description="Retrieves single task instance with its audit trail, enforcing object-level authorization.",
)
async def get_task(
    task_id: uuid.UUID,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.get_instance(
        session=session,
        task_id=task_id,
        actor_identity=identity,
    )


@router.post(
    "/{task_id}/complete",
    response_model=TaskInstanceResponse,
    summary="Complete a task instance (idempotent)",
    description="Records task completion and links telemetry or check-in references. Idempotent.",
)
async def complete_task(
    task_id: uuid.UUID,
    req: TaskCompleteRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.complete_task(
        session=session,
        task_id=task_id,
        req=req,
        actor_identity=identity,
    )


@router.post(
    "/{task_id}/cancel",
    response_model=TaskInstanceResponse,
    summary="Cancel an assigned task",
    description="Cancels a task assignment with justification. Restricted to Flight Surgeons and Administrators.",
)
async def cancel_task(
    task_id: uuid.UUID,
    req: TaskCancelRequest,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await TaskService.cancel_task(
        session=session,
        task_id=task_id,
        req=req,
        actor_identity=identity,
    )

