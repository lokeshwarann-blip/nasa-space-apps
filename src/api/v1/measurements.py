import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.telemetry.service import TelemetryService
from src.schemas.telemetry import (
    MeasurementCreateRequest,
    MeasurementInvalidateRequest,
    MeasurementListResponse,
    MeasurementResponse,
)

router = APIRouter(prefix="/measurements", tags=["Health Telemetry"])


@router.post(
    "",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Physiological Measurement",
    description=(
        "Ingests an objective physiological measurement record. Validates type, unit, and finite bounds "
        "against the typed measurement registry. Preserves original values and provenance."
    ),
)
async def ingest_health_measurement(
    payload: MeasurementCreateRequest,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> MeasurementResponse:
    measurement = await TelemetryService.ingest_measurement(
        session=session,
        payload=payload,
        identity=identity,
    )
    await session.commit()
    return measurement


@router.get(
    "",
    response_model=MeasurementListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Health Measurements",
    description="Queries measurements matching optional filters with deterministic ordering and object-level scoping.",
)
async def list_health_measurements(
    crew_id: uuid.UUID | None = Query(default=None, description="Optional target crew member UUID"),
    measurement_type: str | None = Query(default=None, description="Filter by indicator type (e.g., heart_rate)"),
    start_time: datetime | None = Query(default=None, description="Filter records measured on or after UTC timestamp"),
    end_time: datetime | None = Query(default=None, description="Filter records measured on or before UTC timestamp"),
    limit: int = Query(default=50, ge=1, le=100, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> MeasurementListResponse:
    items, total = await TelemetryService.list_measurements(
        session=session,
        identity=identity,
        crew_id=crew_id,
        measurement_type=measurement_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return MeasurementListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.get(
    "/{measurement_id}",
    response_model=MeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Measurement by ID",
    description="Retrieves a single physiological measurement record by ID with authorization verification.",
)
async def get_measurement_by_id(
    measurement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> MeasurementResponse:
    return await TelemetryService.get_measurement_by_id(
        session=session,
        measurement_id=measurement_id,
        identity=identity,
    )


@router.post(
    "/{measurement_id}/invalidate",
    response_model=MeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Invalidate Measurement",
    description=(
        "Marks a measurement as invalidated with an auditable justification. "
        "Preserves the historical record and audit trail without deleting or silently rewriting data."
    ),
)
async def invalidate_measurement(
    measurement_id: uuid.UUID,
    invalidation: MeasurementInvalidateRequest,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> MeasurementResponse:
    measurement = await TelemetryService.invalidate_measurement(
        session=session,
        measurement_id=measurement_id,
        reason=invalidation.reason,
        identity=identity,
    )
    await session.commit()
    return measurement
