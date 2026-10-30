import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.trends.service import TrendService
from src.modules.trends.schemas import (
    BaselineResponse,
    TrendSeriesResponse,
    TrendSummaryResponse,
)

router = APIRouter(tags=["Longitudinal Trends & Baselines"])


@router.get(
    "/trends/{measurement_type}",
    response_model=TrendSeriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Longitudinal Health Trend Series",
    description=(
        "Retrieves a longitudinal trend series of actual verified observations. "
        "Includes sample statistics, temporal gap detection, outlier labeling, and empirical baseline."
    ),
)
async def get_measurement_trends(
    measurement_type: str,
    crew_id: uuid.UUID | None = Query(default=None, description="Target crew member UUID (required for medical reviewers)"),
    start_time: datetime | None = Query(default=None, description="Start time in UTC"),
    end_time: datetime | None = Query(default=None, description="End time in UTC"),
    limit: int = Query(default=500, ge=1, le=1000, description="Maximum observations to return"),
    gap_threshold_seconds: float = Query(default=3600.0, ge=60.0, description="Duration in seconds to flag as a coverage gap"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> TrendSeriesResponse:
    return await TrendService.get_trend_series(
        session=session,
        identity=identity,
        measurement_type=measurement_type,
        crew_id=crew_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        gap_threshold_seconds=gap_threshold_seconds,
    )


@router.get(
    "/trends/{measurement_type}/summary",
    response_model=TrendSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Health Trend Summary Statistics",
    description="Returns aggregate descriptive statistics, data quality metrics, and baseline status without raw points.",
)
async def get_measurement_trend_summary(
    measurement_type: str,
    crew_id: uuid.UUID | None = Query(default=None, description="Target crew member UUID (required for medical reviewers)"),
    start_time: datetime | None = Query(default=None, description="Start time in UTC"),
    end_time: datetime | None = Query(default=None, description="End time in UTC"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> TrendSummaryResponse:
    return await TrendService.get_trend_summary(
        session=session,
        identity=identity,
        measurement_type=measurement_type,
        crew_id=crew_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/baselines/{measurement_type}",
    response_model=BaselineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Empirical Personal Baseline",
    description=(
        "Returns personal empirical baseline calculated from actual historical observations. "
        "Strictly returns baseline_status='UNAVAILABLE' if minimum sample requirements (10) are not satisfied. "
        "Never substitutes generic population baselines or fabricated data."
    ),
)
async def get_personal_baseline(
    measurement_type: str,
    crew_id: uuid.UUID | None = Query(default=None, description="Target crew member UUID (required for medical reviewers)"),
    start_time: datetime | None = Query(default=None, description="Start time in UTC"),
    end_time: datetime | None = Query(default=None, description="End time in UTC"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> BaselineResponse:
    return await TrendService.get_personal_baseline(
        session=session,
        identity=identity,
        measurement_type=measurement_type,
        crew_id=crew_id,
        start_time=start_time,
        end_time=end_time,
    )
