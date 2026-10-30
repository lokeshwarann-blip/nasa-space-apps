import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity, require_roles
from src.core.database import get_db
from src.modules.alerts.schemas import (
    AlertAcknowledgeRequest,
    AlertAssignRequest,
    AlertCreate,
    AlertDismissRequest,
    AlertEscalateRequest,
    AlertInstanceListResponse,
    AlertInstanceResponse,
    AlertResolveRequest,
)
from src.modules.alerts.service import AlertService
from src.modules.auth.identity_provider import AuthenticatedIdentity

router = APIRouter(prefix="/alerts", tags=["Clinical Alerts Lifecycle"])


@router.get(
    "",
    response_model=AlertInstanceListResponse,
    summary="List clinical alerts",
    description="Query alerts with multi-parameter filtering and object-level authorization.",
)
async def list_alerts(
    crew_member_id: uuid.UUID | None = Query(None, description="Filter by astronaut UUID"),
    status: str | None = Query(None, description="open, acknowledged, assigned, resolved, dismissed"),
    priority: str | None = Query(None, description="INFO, CAUTION, CRITICAL, EMERGENCY"),
    indicator: str | None = Query(None, description="Filter by telemetry indicator"),
    start_time: datetime | None = Query(None, description="Filter alerts after event_time (UTC)"),
    end_time: datetime | None = Query(None, description="Filter alerts before event_time (UTC)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.list_alerts(
        session=session,
        crew_member_id=crew_member_id,
        status=status,
        priority=priority,
        indicator=indicator,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        identity=identity,
    )


@router.post(
    "",
    response_model=AlertInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger/ingest a clinical alert (deduplicated)",
    description="Creates an alert instance from a clinical finding. Idempotently deduplicates repeated findings. Restricted to Flight Surgeons and Administrators.",
)
async def create_alert(
    alert_in: AlertCreate,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.create_alert(
        session=session,
        alert_in=alert_in,
        actor_identity=identity,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertInstanceResponse,
    summary="Get alert instance by ID",
    description="Retrieves a specific alert with complete audit transition trail, enforcing access boundaries.",
)
async def get_alert(
    alert_id: uuid.UUID,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.get_alert(
        session=session,
        alert_id=alert_id,
        actor_identity=identity,
    )


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertInstanceResponse,
    summary="Acknowledge an alert",
    description="Transitions an open or assigned alert to acknowledged. Permitted for the assigned astronaut or medical reviewers.",
)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    req: AlertAcknowledgeRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.acknowledge_alert(
        session=session,
        alert_id=alert_id,
        req=req,
        actor_identity=identity,
    )


@router.post(
    "/{alert_id}/assign",
    response_model=AlertInstanceResponse,
    summary="Assign alert to flight surgeon",
    description="Assigns alert to a designated medical reviewer. Restricted to Flight Surgeons and Administrators.",
)
async def assign_alert(
    alert_id: uuid.UUID,
    req: AlertAssignRequest,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.assign_alert(
        session=session,
        alert_id=alert_id,
        req=req,
        actor_identity=identity,
    )


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertInstanceResponse,
    summary="Resolve clinical alert",
    description="Records medical resolution of an alert with clinical justification. Restricted to Flight Surgeons and Administrators.",
)
async def resolve_alert(
    alert_id: uuid.UUID,
    req: AlertResolveRequest,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.resolve_alert(
        session=session,
        alert_id=alert_id,
        req=req,
        actor_identity=identity,
    )


@router.post(
    "/{alert_id}/dismiss",
    response_model=AlertInstanceResponse,
    summary="Dismiss alert",
    description="Dismisses an alert with auditable clinical rationale. Restricted to Flight Surgeons and Administrators.",
)
async def dismiss_alert(
    alert_id: uuid.UUID,
    req: AlertDismissRequest,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.dismiss_alert(
        session=session,
        alert_id=alert_id,
        req=req,
        actor_identity=identity,
    )


@router.post(
    "/{alert_id}/escalate",
    response_model=AlertInstanceResponse,
    summary="Escalate alert to operational destination",
    description="Escalates an alert to higher tier medical or flight operations destinations. Records delivery status accurately without false confirmation. Restricted to Flight Surgeons and Admins.",
)
async def escalate_alert(
    alert_id: uuid.UUID,
    req: AlertEscalateRequest,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AlertService.escalate_alert(
        session=session,
        alert_id=alert_id,
        req=req,
        actor_identity=identity,
    )
