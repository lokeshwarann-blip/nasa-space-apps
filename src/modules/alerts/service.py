import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from src.models.alerts import AlertAuditRecord, AlertInstance
from src.models.crew import CrewMember
from src.modules.alerts.schemas import (
    VALID_ALERT_TRANSITIONS,
    AlertAcknowledgeRequest,
    AlertAssignRequest,
    AlertCreate,
    AlertDismissRequest,
    AlertEscalateRequest,
    AlertInstanceListResponse,
    AlertInstanceResponse,
    AlertResolveRequest,
)
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService


class AlertService:
    """Service handling clinical alert lifecycles, deduplication, escalation, and audit logging."""

    @staticmethod
    async def create_alert(
        session: Any,
        alert_in: AlertCreate,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Ingests an alert with idempotency deduplication and delayed observation detection."""
        # Normalize event timestamp to UTC ISO string for deterministic deduplication
        event_time_utc = (
            alert_in.event_time.astimezone(timezone.utc)
            if alert_in.event_time.tzinfo
            else alert_in.event_time.replace(tzinfo=timezone.utc)
        )
        event_iso = event_time_utc.isoformat()
        idempotency_key = f"{alert_in.crew_member_id}:{alert_in.source_finding_id}:{event_iso}"

        # DEDUPLICATION CHECK: Check if alert already exists for this exact finding and event time
        existing_stmt = (
            select(AlertInstance)
            .where(AlertInstance.idempotency_key == idempotency_key)
            .options(selectinload(AlertInstance.audit_records))
        )
        existing = await session.scalar(existing_stmt)
        if existing is not None:
            # Idempotently return existing alert without creating duplicates
            return AlertInstanceResponse.model_validate(existing)

        # Verify crew member exists
        crew_stmt = select(CrewMember).where(CrewMember.id == alert_in.crew_member_id)
        crew = await session.scalar(crew_stmt)
        if crew is None:
            raise AppException(
                message=f"Crew member '{alert_in.crew_member_id}' not found.",
                code="not_found",
                status_code=404,
            )

        now = datetime.now(timezone.utc)
        # DELAYED OBSERVATION HANDLING:
        # If the historical event time is older than 1 hour relative to ingestion, flag as delayed
        delay_seconds = (now - event_time_utc).total_seconds()
        is_delayed = delay_seconds > 3600.0

        count_stmt = select(func.count(AlertInstance.id))
        total_count = await session.scalar(count_stmt) or 0
        alert_identifier = f"ALT-{now.year}-{alert_in.indicator.upper()[:4]}-{total_count + 1:04d}"

        alert = AlertInstance(
            alert_identifier=alert_identifier,
            crew_member_id=alert_in.crew_member_id,
            assessment_id=alert_in.assessment_id,
            source_finding_id=alert_in.source_finding_id,
            idempotency_key=idempotency_key,
            rule_id=alert_in.rule_id,
            rule_version=alert_in.rule_version,
            indicator=alert_in.indicator,
            priority=alert_in.priority,
            status="open",
            summary=alert_in.summary,
            details=alert_in.details,
            event_time=event_time_utc,
            is_delayed=is_delayed,
            delivery_status="NO_DELIVERY_PROVIDER",
        )
        session.add(alert)
        await session.flush()

        audit = AlertAuditRecord(
            alert_id=alert.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="CREATED",
            previous_status="none",
            new_status="open",
            reason=f"Alert triggered by clinical rule {alert_in.rule_id} (version {alert_in.rule_version}). Delayed: {is_delayed}",
            transition_time=now,
        )
        session.add(audit)

        await session.commit()
        return await AlertService.get_alert(session=session, alert_id=alert.id, actor_identity=actor_identity)

    @staticmethod
    async def list_alerts(
        session: Any,
        crew_member_id: uuid.UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        indicator: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity | None = None,
    ) -> AlertInstanceListResponse:
        """Retrieves clinical alerts enforcing object-level authorization."""
        if identity is None:
            raise AppException(
                message="Authentication required.",
                code="unauthorized",
                status_code=401,
            )

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
                    message="Crew members are forbidden from querying alerts of other crew members.",
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

        stmt = select(AlertInstance).options(selectinload(AlertInstance.audit_records))
        count_stmt = select(func.count(AlertInstance.id))

        if target_crew_id is not None:
            stmt = stmt.where(AlertInstance.crew_member_id == target_crew_id)
            count_stmt = count_stmt.where(AlertInstance.crew_member_id == target_crew_id)

        if status:
            stmt = stmt.where(AlertInstance.status == status.lower())
            count_stmt = count_stmt.where(AlertInstance.status == status.lower())

        if priority:
            stmt = stmt.where(AlertInstance.priority == priority.upper())
            count_stmt = count_stmt.where(AlertInstance.priority == priority.upper())

        if indicator:
            stmt = stmt.where(AlertInstance.indicator == indicator.lower())
            count_stmt = count_stmt.where(AlertInstance.indicator == indicator.lower())

        if start_time:
            stmt = stmt.where(AlertInstance.event_time >= start_time)
            count_stmt = count_stmt.where(AlertInstance.event_time >= start_time)

        if end_time:
            stmt = stmt.where(AlertInstance.event_time <= end_time)
            count_stmt = count_stmt.where(AlertInstance.event_time <= end_time)

        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(AlertInstance.event_time.desc(), AlertInstance.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        alerts = result.scalars().all()

        return AlertInstanceListResponse(
            items=[AlertInstanceResponse.model_validate(a) for a in alerts],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_alert(
        session: Any,
        alert_id: uuid.UUID,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Retrieves an alert instance with complete audit history, enforcing access boundaries."""
        stmt = (
            select(AlertInstance)
            .where(AlertInstance.id == alert_id)
            .options(selectinload(AlertInstance.audit_records))
        )
        alert = await session.scalar(stmt)
        if alert is None:
            raise AppException(
                message=f"Alert instance '{alert_id}' not found.",
                code="not_found",
                status_code=404,
            )

        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(alert.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="You do not have permission to access this alert.",
                    code="forbidden",
                    status_code=403,
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            await AuthService.enforce_crew_access(
                session=session,
                identity=actor_identity,
                target_crew_member_id=alert.crew_member_id,
                action="ACCESS_HEALTH_RECORD",
            )

        return AlertInstanceResponse.model_validate(alert)

    @staticmethod
    async def acknowledge_alert(
        session: Any,
        alert_id: uuid.UUID,
        req: AlertAcknowledgeRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Acknowledges an open or assigned alert."""
        stmt = (
            select(AlertInstance)
            .where(AlertInstance.id == alert_id)
            .options(selectinload(AlertInstance.audit_records))
        )
        alert = await session.scalar(stmt)
        if alert is None:
            raise AppException(
                message=f"Alert instance '{alert_id}' not found.",
                code="not_found",
                status_code=404,
            )

        # Crew member can acknowledge their own alerts; flight surgeon/admin can acknowledge assigned
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(alert.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="You do not have permission to acknowledge this alert.",
                    code="forbidden",
                    status_code=403,
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            await AuthService.enforce_crew_access(
                session=session,
                identity=actor_identity,
                target_crew_member_id=alert.crew_member_id,
                action="ACCESS_HEALTH_RECORD",
            )

        current_status = alert.status.lower()
        if current_status == "acknowledged":
            # Idempotent return
            return AlertInstanceResponse.model_validate(alert)

        allowed = VALID_ALERT_TRANSITIONS.get(current_status, [])
        if "acknowledged" not in allowed:
            raise AppException(
                message=(
                    f"Invalid approval status transition from '{current_status}' to 'acknowledged'. "
                    f"Permitted transitions from '{current_status}': {allowed}"
                ),
                code="invalid_transition",
                status_code=400,
            )

        prev_status = alert.status
        now = datetime.now(timezone.utc)
        alert.status = "acknowledged"
        alert.acknowledged_at = now
        alert.acknowledged_by = actor_identity.user_id

        audit = AlertAuditRecord(
            alert_id=alert.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="ACKNOWLEDGED",
            previous_status=prev_status,
            new_status="acknowledged",
            reason=req.notes or "Alert acknowledged by user.",
            transition_time=now,
        )
        session.add(audit)

        await session.commit()
        return await AlertService.get_alert(session=session, alert_id=alert.id, actor_identity=actor_identity)

    @staticmethod
    async def assign_alert(
        session: Any,
        alert_id: uuid.UUID,
        req: AlertAssignRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Assigns an alert to a flight surgeon or medical reviewer (Flight Surgeon / Admin only)."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can assign alerts.",
                code="forbidden",
                status_code=403,
            )

        stmt = (
            select(AlertInstance)
            .where(AlertInstance.id == alert_id)
            .options(selectinload(AlertInstance.audit_records))
        )
        alert = await session.scalar(stmt)
        if alert is None:
            raise AppException(
                message=f"Alert instance '{alert_id}' not found.",
                code="not_found",
                status_code=404,
            )

        current_status = alert.status.lower()
        allowed = VALID_ALERT_TRANSITIONS.get(current_status, [])
        if "assigned" not in allowed:
            raise AppException(
                message=(
                    f"Invalid approval status transition from '{current_status}' to 'assigned'. "
                    f"Permitted transitions from '{current_status}': {allowed}"
                ),
                code="invalid_transition",
                status_code=400,
            )

        prev_status = alert.status
        now = datetime.now(timezone.utc)
        alert.status = "assigned"
        alert.assigned_to = req.assigned_to
        alert.assigned_at = now

        audit = AlertAuditRecord(
            alert_id=alert.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="ASSIGNED",
            previous_status=prev_status,
            new_status="assigned",
            reason=f"Assigned to {req.assigned_to}. Notes: {req.assignment_notes or 'None'}",
            transition_time=now,
        )
        session.add(audit)

        await session.commit()
        return await AlertService.get_alert(session=session, alert_id=alert.id, actor_identity=actor_identity)

    @staticmethod
    async def resolve_alert(
        session: Any,
        alert_id: uuid.UUID,
        req: AlertResolveRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Records clinical resolution of an alert (Flight Surgeon / Admin only)."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can resolve alerts.",
                code="forbidden",
                status_code=403,
            )

        stmt = (
            select(AlertInstance)
            .where(AlertInstance.id == alert_id)
            .options(selectinload(AlertInstance.audit_records))
        )
        alert = await session.scalar(stmt)
        if alert is None:
            raise AppException(
                message=f"Alert instance '{alert_id}' not found.",
                code="not_found",
                status_code=404,
            )

        current_status = alert.status.lower()
        allowed = VALID_ALERT_TRANSITIONS.get(current_status, [])
        if "resolved" not in allowed:
            raise AppException(
                message=(
                    f"Invalid approval status transition from '{current_status}' to 'resolved'. "
                    f"Permitted transitions from '{current_status}': {allowed}"
                ),
                code="invalid_transition",
                status_code=400,
            )

        prev_status = alert.status
        now = datetime.now(timezone.utc)
        alert.status = "resolved"
        alert.resolved_at = now
        alert.resolved_by = actor_identity.user_id
        alert.resolution_reason = req.resolution_reason

        audit = AlertAuditRecord(
            alert_id=alert.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="RESOLVED",
            previous_status=prev_status,
            new_status="resolved",
            reason=req.resolution_reason,
            transition_time=now,
        )
        session.add(audit)

        await session.commit()
        return await AlertService.get_alert(session=session, alert_id=alert.id, actor_identity=actor_identity)

    @staticmethod
    async def dismiss_alert(
        session: Any,
        alert_id: uuid.UUID,
        req: AlertDismissRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Dismisses an alert with auditable clinical rationale (Flight Surgeon / Admin only)."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can dismiss alerts.",
                code="forbidden",
                status_code=403,
            )

        stmt = (
            select(AlertInstance)
            .where(AlertInstance.id == alert_id)
            .options(selectinload(AlertInstance.audit_records))
        )
        alert = await session.scalar(stmt)
        if alert is None:
            raise AppException(
                message=f"Alert instance '{alert_id}' not found.",
                code="not_found",
                status_code=404,
            )

        current_status = alert.status.lower()
        allowed = VALID_ALERT_TRANSITIONS.get(current_status, [])
        if "dismissed" not in allowed:
            raise AppException(
                message=(
                    f"Invalid approval status transition from '{current_status}' to 'dismissed'. "
                    f"Permitted transitions from '{current_status}': {allowed}"
                ),
                code="invalid_transition",
                status_code=400,
            )

        prev_status = alert.status
        now = datetime.now(timezone.utc)
        alert.status = "dismissed"
        alert.dismissed_at = now
        alert.dismissed_by = actor_identity.user_id
        alert.dismissal_reason = req.dismissal_reason

        audit = AlertAuditRecord(
            alert_id=alert.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="DISMISSED",
            previous_status=prev_status,
            new_status="dismissed",
            reason=req.dismissal_reason,
            transition_time=now,
        )
        session.add(audit)

        await session.commit()
        return await AlertService.get_alert(session=session, alert_id=alert.id, actor_identity=actor_identity)

    @staticmethod
    async def escalate_alert(
        session: Any,
        alert_id: uuid.UUID,
        req: AlertEscalateRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> AlertInstanceResponse:
        """Escalates an alert to higher tier operational destinations without falsely claiming delivery."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can escalate alerts.",
                code="forbidden",
                status_code=403,
            )

        stmt = (
            select(AlertInstance)
            .where(AlertInstance.id == alert_id)
            .options(selectinload(AlertInstance.audit_records))
        )
        alert = await session.scalar(stmt)
        if alert is None:
            raise AppException(
                message=f"Alert instance '{alert_id}' not found.",
                code="not_found",
                status_code=404,
            )

        now = datetime.now(timezone.utc)
        alert.escalation_level = req.escalation_target
        # Policy guarantee: Do not pretend an external recipient was notified if no delivery provider confirms it
        alert.delivery_status = "NO_DELIVERY_PROVIDER"

        audit = AlertAuditRecord(
            alert_id=alert.id,
            actor_id=actor_identity.user_id,
            actor_role=actor_identity.role,
            action="ESCALATED",
            previous_status=alert.status,
            new_status=alert.status,
            reason=f"Escalated to {req.escalation_target}: {req.escalation_reason} (Delivery: NO_DELIVERY_PROVIDER)",
            transition_time=now,
        )
        session.add(audit)

        await session.commit()
        return await AlertService.get_alert(session=session, alert_id=alert.id, actor_identity=actor_identity)

