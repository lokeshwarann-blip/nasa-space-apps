import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from src.models.crew import CrewMember
from src.models.tasks import TaskAuditRecord, TaskDefinition, TaskInstance
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService
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


class TaskService:
    """Service handling reusable task definitions, crew assignments, and idempotent completions."""

    @staticmethod
    async def create_definition(
        session: Any,
        def_in: TaskDefinitionCreate,
        actor_identity: AuthenticatedIdentity,
    ) -> TaskDefinitionResponse:
        """Creates a reusable task blueprint/template (Flight Surgeon / Admin only)."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can configure task definitions.",
                code="forbidden",
                status_code=403,
            )

        existing_stmt = select(TaskDefinition).where(
            TaskDefinition.definition_identifier == def_in.definition_identifier
        )
        existing = await session.scalar(existing_stmt)
        if existing is not None:
            raise AppException(
                message=f"Task definition with identifier '{def_in.definition_identifier}' already exists.",
                code="conflict",
                status_code=409,
            )

        task_def = TaskDefinition(
            definition_identifier=def_in.definition_identifier,
            title=def_in.title,
            description=def_in.description,
            category=def_in.category,
            target_measurement_type=def_in.target_measurement_type,
            target_check_in_type=def_in.target_check_in_type,
            recurrence_config=def_in.recurrence_config,
            is_active=def_in.is_active,
            created_by=actor_identity.user_id,
        )
        session.add(task_def)
        await session.commit()
        await session.refresh(task_def)
        return TaskDefinitionResponse.model_validate(task_def)

    @staticmethod
    async def list_definitions(
        session: Any,
        category: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TaskDefinitionListResponse:
        """Lists configured task definitions."""
        stmt = select(TaskDefinition)
        count_stmt = select(func.count(TaskDefinition.id))

        if category:
            stmt = stmt.where(TaskDefinition.category == category.upper())
            count_stmt = count_stmt.where(TaskDefinition.category == category.upper())

        if is_active is not None:
            stmt = stmt.where(TaskDefinition.is_active == is_active)
            count_stmt = count_stmt.where(TaskDefinition.is_active == is_active)

        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(TaskDefinition.definition_identifier.asc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        definitions = result.scalars().all()

        return TaskDefinitionListResponse(
            items=[TaskDefinitionResponse.model_validate(d) for d in definitions],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def create_instance(
        session: Any,
        inst_in: TaskInstanceCreate,
        actor_identity: AuthenticatedIdentity,
    ) -> TaskInstanceResponse:
        """Assigns a task instance to an astronaut with a bounded due window (Flight Surgeon / Admin only)."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can assign tasks.",
                code="forbidden",
                status_code=403,
            )

        if inst_in.due_start >= inst_in.due_end:
            raise AppException(
                message="Task due_start must strictly precede due_end.",
                code="invalid_window",
                status_code=400,
            )

        # Verify crew member exists
        crew_stmt = select(CrewMember).where(CrewMember.id == inst_in.crew_member_id)
        crew = await session.scalar(crew_stmt)
        if crew is None:
            raise AppException(
                message=f"Crew member '{inst_in.crew_member_id}' not found.",
                code="not_found",
                status_code=404,
            )

        if inst_in.task_definition_id:
            def_stmt = select(TaskDefinition).where(TaskDefinition.id == inst_in.task_definition_id)
            task_def = await session.scalar(def_stmt)
            if task_def is None:
                raise AppException(
                    message=f"Task definition '{inst_in.task_definition_id}' not found.",
                    code="not_found",
                    status_code=404,
                )

        task = TaskInstance(
            task_definition_id=inst_in.task_definition_id,
            crew_member_id=inst_in.crew_member_id,
            title=inst_in.title,
            category=inst_in.category,
            status="PENDING",
            due_start=inst_in.due_start,
            due_end=inst_in.due_end,
        )
        session.add(task)
        await session.flush()

        audit = TaskAuditRecord(
            task_instance_id=task.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="CREATED",
            previous_status=None,
            new_status="PENDING",
            details=f"Task assigned for due window {inst_in.due_start.isoformat()} to {inst_in.due_end.isoformat()}",
            recorded_at=datetime.now(timezone.utc),
        )
        session.add(audit)

        await session.commit()
        return await TaskService.get_instance(session=session, task_id=task.id, actor_identity=actor_identity)

    @staticmethod
    async def list_instances(
        session: Any,
        crew_member_id: uuid.UUID | None = None,
        status: str | None = None,
        category: str | None = None,
        due_from: datetime | None = None,
        due_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity | None = None,
    ) -> TaskInstanceListResponse:
        """Retrieves assigned tasks enforcing object-level authorization."""
        if identity is None:
            raise AppException(
                message="Authentication required.",
                code="unauthorized",
                status_code=401,
            )

        # Enforce BOLA access boundaries
        target_crew_id = crew_member_id
        if identity.role == "CREW_MEMBER":
            if identity.crew_member_id is None:
                raise AppException(
                    message="Crew member identity is not linked to a crew record.",
                    code="forbidden",
                    status_code=403,
                )
            user_crew_id = uuid.UUID(identity.crew_member_id)
            if crew_member_id is not None and crew_member_id != user_crew_id:
                raise AppException(
                    message="Crew members are forbidden from querying tasks of other crew members.",
                    code="forbidden",
                    status_code=403,
                )
            target_crew_id = user_crew_id
        elif identity.role == "FLIGHT_SURGEON":
            if target_crew_id is not None:
                await AuthService.enforce_crew_access(
                    session=session,
                    identity=identity,
                    target_crew_member_id=target_crew_id,
                    action="ACCESS_HEALTH_RECORD",
                )

        stmt = (
            select(TaskInstance)
            .options(
                selectinload(TaskInstance.task_definition),
                selectinload(TaskInstance.audit_records),
            )
        )
        count_stmt = select(func.count(TaskInstance.id))

        if target_crew_id is not None:
            stmt = stmt.where(TaskInstance.crew_member_id == target_crew_id)
            count_stmt = count_stmt.where(TaskInstance.crew_member_id == target_crew_id)

        if status:
            stmt = stmt.where(TaskInstance.status == status.upper())
            count_stmt = count_stmt.where(TaskInstance.status == status.upper())

        if category:
            stmt = stmt.where(TaskInstance.category == category.upper())
            count_stmt = count_stmt.where(TaskInstance.category == category.upper())

        if due_from:
            stmt = stmt.where(TaskInstance.due_end >= due_from)
            count_stmt = count_stmt.where(TaskInstance.due_end >= due_from)

        if due_to:
            stmt = stmt.where(TaskInstance.due_start <= due_to)
            count_stmt = count_stmt.where(TaskInstance.due_start <= due_to)

        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(TaskInstance.due_start.asc(), TaskInstance.created_at.asc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        return TaskInstanceListResponse(
            items=[TaskInstanceResponse.model_validate(t) for t in tasks],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_instance(
        session: Any,
        task_id: uuid.UUID,
        actor_identity: AuthenticatedIdentity,
    ) -> TaskInstanceResponse:
        """Retrieves a single task instance with its audit trail, enforcing authorization."""
        stmt = (
            select(TaskInstance)
            .where(TaskInstance.id == task_id)
            .options(
                selectinload(TaskInstance.task_definition),
                selectinload(TaskInstance.audit_records),
            )
        )
        task = await session.scalar(stmt)
        if task is None:
            raise AppException(
                message=f"Task instance '{task_id}' not found.",
                code="not_found",
                status_code=404,
            )

        # Enforce BOLA authorization
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(task.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="You do not have permission to access this task.",
                    code="forbidden",
                    status_code=403,
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            await AuthService.enforce_crew_access(
                session=session,
                identity=actor_identity,
                target_crew_member_id=task.crew_member_id,
                action="ACCESS_HEALTH_RECORD",
            )

        return TaskInstanceResponse.model_validate(task)

    @staticmethod
    async def complete_task(
        session: Any,
        task_id: uuid.UUID,
        req: TaskCompleteRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> TaskInstanceResponse:
        """Completes a task instance idempotently."""
        stmt = (
            select(TaskInstance)
            .where(TaskInstance.id == task_id)
            .options(
                selectinload(TaskInstance.task_definition),
                selectinload(TaskInstance.audit_records),
            )
        )
        task = await session.scalar(stmt)
        if task is None:
            raise AppException(
                message=f"Task instance '{task_id}' not found.",
                code="not_found",
                status_code=404,
            )

        # Enforce BOLA authorization
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(task.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="You do not have permission to complete this task.",
                    code="forbidden",
                    status_code=403,
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            await AuthService.enforce_crew_access(
                session=session,
                identity=actor_identity,
                target_crew_member_id=task.crew_member_id,
                action="ACCESS_HEALTH_RECORD",
            )

        # IDEMPOTENCY CHECK: If already completed, return existing without re-running transition
        if task.status == "COMPLETED":
            return TaskInstanceResponse.model_validate(task)

        if task.status == "CANCELLED":
            raise AppException(
                message="Cannot complete a task that has been cancelled.",
                code="invalid_state",
                status_code=400,
            )

        prev_status = task.status
        task.status = "COMPLETED"
        task.completed_at = datetime.now(timezone.utc)
        task.completion_source = req.completion_source
        task.reference_measurement_id = req.reference_measurement_id
        task.reference_check_in_id = req.reference_check_in_id
        task.completion_notes = req.completion_notes

        audit = TaskAuditRecord(
            task_instance_id=task.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="COMPLETED",
            previous_status=prev_status,
            new_status="COMPLETED",
            details=f"Completed via {req.completion_source}. Notes: {req.completion_notes or 'None'}",
            recorded_at=datetime.now(timezone.utc),
        )
        session.add(audit)

        await session.commit()
        return await TaskService.get_instance(session=session, task_id=task.id, actor_identity=actor_identity)

    @staticmethod
    async def cancel_task(
        session: Any,
        task_id: uuid.UUID,
        req: TaskCancelRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> TaskInstanceResponse:
        """Cancels an assigned task (Flight Surgeon / Admin only)."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can cancel tasks.",
                code="forbidden",
                status_code=403,
            )

        stmt = (
            select(TaskInstance)
            .where(TaskInstance.id == task_id)
            .options(
                selectinload(TaskInstance.task_definition),
                selectinload(TaskInstance.audit_records),
            )
        )
        task = await session.scalar(stmt)
        if task is None:
            raise AppException(
                message=f"Task instance '{task_id}' not found.",
                code="not_found",
                status_code=404,
            )

        if task.status == "CANCELLED":
            return TaskInstanceResponse.model_validate(task)

        if task.status == "COMPLETED":
            raise AppException(
                message="Cannot cancel a task that has already been completed.",
                code="invalid_state",
                status_code=400,
            )

        prev_status = task.status
        task.status = "CANCELLED"
        task.cancelled_at = datetime.now(timezone.utc)
        task.cancellation_reason = req.cancellation_reason

        audit = TaskAuditRecord(
            task_instance_id=task.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="CANCELLED",
            previous_status=prev_status,
            new_status="CANCELLED",
            details=req.cancellation_reason,
            recorded_at=datetime.now(timezone.utc),
        )
        session.add(audit)

        await session.commit()
        return await TaskService.get_instance(session=session, task_id=task.id, actor_identity=actor_identity)
