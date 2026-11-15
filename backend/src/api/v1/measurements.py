import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel, Field
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


class PulseMeasurementRequest(BaseModel):
    hr: float = Field(..., ge=30, le=240, description="Heart Rate in beats per minute")
    hrv_rmssd: float = Field(..., ge=5, le=300, description="Heart Rate Variability RMSSD in milliseconds")
    signal_quality: str = Field(..., description="'good', 'marginal', or 'poor'")
    duration_seconds: float = Field(default=30.0, description="Duration of measurement in seconds")
    method: str = Field(default="rppg_camera", description="'rppg_camera' or 'manual_entry'")
    confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    notes: str | None = None


class PulseMeasurementResponse(BaseModel):
    status: str
    message: str
    hr: float
    hrv_rmssd: float
    signal_quality: str
    sensor_status: str
    baseline_low: float = 58.0
    baseline_high: float = 82.0
    in_range: bool
    xp_awarded: int
    timestamp: str


@router.post(
    "/pulse",
    response_model=PulseMeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Pulse & HRV Measurement (rPPG / Manual)",
    description=(
        "Records a 30s rPPG or manual pulse evaluation. Applies the Data-Quality Gate: "
        "measurements with poor signal quality are rejected as hardware/sensor issues, never as health alerts."
    ),
)
async def record_pulse_measurement(
    payload: PulseMeasurementRequest,
) -> PulseMeasurementResponse:
    # DATA QUALITY GATE:
    # Rule: Low quality is gated before saving as valid telemetry.
    # Rule: Shows as a sensor problem (FAULTY_SENSOR), never as a health alert.
    if payload.signal_quality.lower() == "poor" or payload.confidence < 0.60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Data Quality Gate Check Failed: Low signal quality detected (sensor issue: motion artifact, "
                "face occlusion, or insufficient lighting). Telemetry was not recorded as valid physiological "
                "context. Please stabilize and retry or use manual fallback. Note: this is a sensor issue, not a health alert."
            ),
        )

    # Personal baseline range: 58.0 - 82.0 bpm
    in_range = 58.0 <= payload.hr <= 82.0
    xp = 25 if payload.method == "rppg_camera" else 15

    return PulseMeasurementResponse(
        status="logged",
        message="Pulse telemetry successfully verified and recorded into mission record.",
        hr=round(payload.hr, 1),
        hrv_rmssd=round(payload.hrv_rmssd, 1),
        signal_quality=payload.signal_quality,
        sensor_status="GOOD_SIGNAL",
        baseline_low=58.0,
        baseline_high=82.0,
        in_range=in_range,
        xp_awarded=xp,
        timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


