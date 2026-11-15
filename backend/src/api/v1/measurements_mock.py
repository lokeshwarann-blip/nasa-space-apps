import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from src.schemas.astronaut import (
    PulseMeasurementRequest,
    PulseMeasurementResponse,
)

router = APIRouter(prefix="/measurements", tags=["Measurements Mock"])


@router.post(
    "/pulse",
    response_model=PulseMeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Pulse Telemetry Reading",
    description="Validates and accepts pulse rate and HRV telemetry for operational trend tracking.",
)
async def ingest_pulse(payload: PulseMeasurementRequest) -> PulseMeasurementResponse:
    """Mock endpoint accepting or rejecting pulse telemetry based on signal quality."""
    now_iso = datetime.now(timezone.utc).isoformat()
    if payload.signal_quality.lower() in ("poor", "unusable", "corrupted") or payload.hr < 30.0 or payload.hr > 220.0:
        return PulseMeasurementResponse(
            status="rejected",
            message="Pulse measurement rejected due to degraded signal quality or anomalous reading. Check sensor placement.",
            recorded_at=now_iso,
            measurement_id=None,
        )

    return PulseMeasurementResponse(
        status="accepted",
        message="Pulse measurement accepted for physiological baseline trend monitoring.",
        recorded_at=now_iso,
        measurement_id=f"pulse-{uuid.uuid4().hex[:8]}",
    )
