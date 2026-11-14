import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.readiness.schemas import (
    BaselineMetadata,
    BaselineRecalibrateRequest,
    CrewReadinessResponse,
    ReadinessOverviewResponse,
)
from src.modules.readiness.service import ReadinessService

router = APIRouter(tags=["Crew Readiness (Decision Support)"])

# Defaults suit the 14-day scenario data (daily view). For hourly-scale data try freq=3h&window=8&min_periods=4.
_FREQ = Query(default="1d", description="Resampling interval, e.g. '3h' or '1d'")
_WINDOW = Query(default=7, ge=3, le=60, description="Baseline window (number of intervals)")
_MIN_PERIODS = Query(default=3, ge=2, le=30, description="Minimum intervals before a baseline exists")
_ALERT_N = Query(default=3, ge=2, le=10, description="Consecutive off-baseline intervals that raise an alert")


@router.get(
    "/readiness",
    response_model=CrewReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crew Readiness Score, Forecast and Drift Alerts",
    description=(
        "Compares each metric to the crew member's frozen baseline and returns a 0-100 readiness "
        "score, next-interval adaptive conformal forecast, univariate drift alerts, and Ledoit-Wolf Mahalanobis "
        "multivariate anomaly indicators. Decision support only; not a diagnosis or disease probability."
    ),
)
async def get_crew_readiness(
    crew_id: uuid.UUID | None = Query(default=None, description="Target crew member UUID (required for medical reviewers)"),
    start_time: datetime | None = Query(default=None, description="Start time in UTC"),
    end_time: datetime | None = Query(default=None, description="End time in UTC"),
    freq: str = _FREQ,
    window: int = _WINDOW,
    min_periods: int = _MIN_PERIODS,
    alert_n: int = _ALERT_N,
    include_series: bool = Query(default=True, description="Include the readiness history for charts"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> CrewReadinessResponse:
    return await ReadinessService.get_readiness(
        session=session, identity=identity, crew_id=crew_id,
        start_time=start_time, end_time=end_time,
        freq=freq, window=window, min_periods=min_periods, alert_n=alert_n,
        include_series=include_series,
    )


@router.get(
    "/readiness/overview",
    response_model=ReadinessOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Readiness For Every Crew Member The Caller May See",
    description="One card per assigned crew member (a crew member sees only themselves). No history series.",
)
async def get_readiness_overview(
    freq: str = _FREQ,
    window: int = _WINDOW,
    min_periods: int = _MIN_PERIODS,
    alert_n: int = _ALERT_N,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> ReadinessOverviewResponse:
    return await ReadinessService.get_overview(
        session=session, identity=identity,
        freq=freq, window=window, min_periods=min_periods, alert_n=alert_n,
    )


@router.post(
    "/readiness/baseline/recalibrate",
    response_model=BaselineMetadata,
    status_code=status.HTTP_200_OK,
    summary="Explicitly Recalibrate Crew Baseline",
    description=(
        "Triggers an explicit recalibration of an astronaut's frozen baseline with an audit reason "
        "(e.g. mission phase change). Appends a new immutable baseline version while preserving history."
    ),
)
async def recalibrate_baseline(
    request: BaselineRecalibrateRequest,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> BaselineMetadata:
    return await ReadinessService.recalibrate_baseline(
        session=session, identity=identity, request=request
    )


@router.get(
    "/readiness/baseline",
    response_model=BaselineMetadata,
    status_code=status.HTTP_200_OK,
    summary="Get Active Frozen Baseline Metadata",
    description="Retrieves the active frozen baseline metadata, confidence tier, and quality exclusions.",
)
async def get_active_baseline(
    crew_id: uuid.UUID = Query(..., description="Target crew member UUID"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> BaselineMetadata:
    return await ReadinessService.get_active_baseline(
        session=session, identity=identity, crew_id=crew_id
    )
