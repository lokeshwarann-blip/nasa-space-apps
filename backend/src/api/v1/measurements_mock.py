import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.models import CrewMember, HealthMeasurement
from src.schemas.astronaut import (
    PulseMeasurementRequest,
    PulseMeasurementResponse,
)

router = APIRouter(prefix="/measurements", tags=["Measurements"])

SIGNAL_QUALITY_ORDER: dict[str, int] = {
    "corrupted": 0,
    "unusable": 0,
    "poor": 1,
    "fair": 2,
    "good": 3,
    "excellent": 4,
}


@router.post(
    "/pulse",
    response_model=PulseMeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Pulse Telemetry Reading",
    description="Validates and accepts pulse rate and HRV telemetry for operational trend tracking.",
)
async def ingest_pulse(
    payload: PulseMeasurementRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_db),
) -> PulseMeasurementResponse:
    """Validates pulse telemetry, checks configurable signal quality threshold, and stores accepted readings."""
    settings = getattr(getattr(request, "app", None), "state", None)
    settings = getattr(settings, "settings", None) or get_settings()

    min_quality = getattr(settings, "MIN_PULSE_SIGNAL_QUALITY", "fair").lower()
    min_rank = SIGNAL_QUALITY_ORDER.get(min_quality, 2)
    current_rank = SIGNAL_QUALITY_ORDER.get(payload.signal_quality.lower(), 0)

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    if current_rank < min_rank:
        return PulseMeasurementResponse(
            status="rejected",
            message=(
                f"Pulse measurement rejected: signal quality '{payload.signal_quality}' is below minimum threshold '{min_quality}'. "
                "Reading not scored for physiological readiness. Please check sensor placement or check with flight surgeon."
            ),
            recorded_at=now_iso,
            measurement_id=None,
        )

    # Resolve or create target crew member for persistence
    crew: Optional[CrewMember] = None
    target_crew_id = payload.crew_id or "CREW-001"

    stmt = select(CrewMember).where(CrewMember.crew_id == target_crew_id)
    res = await session.execute(stmt)
    crew = res.scalar_one_or_none()

    if crew is None:
        crew = CrewMember(
            crew_id=target_crew_id,
            status="ACTIVE",
            profile_metadata={"role": "Astronaut", "callsign": target_crew_id},
        )
        session.add(crew)
        await session.flush()

    # Store accepted measurement(s)
    measurement_id = uuid.uuid4()
    hr_measurement = HealthMeasurement(
        id=measurement_id,
        crew_member_id=crew.id,
        measurement_type="heart_rate",
        value_numeric=payload.hr,
        unit="bpm",
        measured_at=now_dt,
        recorded_at=now_dt,
        input_method="WEARABLE_SENSOR",
        quality_status="VERIFIED",
        provenance={
            "source": payload.source,
            "signal_quality": payload.signal_quality,
        },
        context_metadata={"signal_quality": payload.signal_quality},
    )
    session.add(hr_measurement)

    if payload.hrv is not None:
        hrv_measurement = HealthMeasurement(
            id=uuid.uuid4(),
            crew_member_id=crew.id,
            measurement_type="hrv",
            value_numeric=payload.hrv,
            unit="ms",
            measured_at=now_dt,
            recorded_at=now_dt,
            input_method="WEARABLE_SENSOR",
            quality_status="VERIFIED",
            provenance={
                "source": payload.source,
                "signal_quality": payload.signal_quality,
            },
            context_metadata={"signal_quality": payload.signal_quality},
        )
        session.add(hrv_measurement)

    await session.commit()

    return PulseMeasurementResponse(
        status="accepted",
        message="Pulse measurement accepted for physiological baseline trend monitoring.",
        recorded_at=now_iso,
        measurement_id=f"pulse-{measurement_id.hex[:8]}",
    )
