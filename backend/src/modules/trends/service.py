import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    InvalidTimestampError,
    InvalidValueError,
    UnsupportedMeasurementTypeError,
)
from src.models.telemetry import HealthMeasurement
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService, AuthorizationError
from src.modules.telemetry.registry import measurement_registry
from src.modules.trends.calculator import (
    calculate_personal_baseline,
    compute_statistics,
    detect_coverage_gaps,
    detect_statistical_outliers,
)
from src.modules.trends.schemas import (
    BaselineResponse,
    DataQualitySummary,
    TrendObservation,
    TrendSeriesResponse,
    TrendSummaryResponse,
)

MAX_TREND_WINDOW_DAYS = 90
DEFAULT_GAP_THRESHOLD_SECONDS = 3600.0  # 1 hour


class TrendService:
    """Longitudinal trend and empirical baseline calculation service."""

    @staticmethod
    def _resolve_target_crew(
        identity: AuthenticatedIdentity,
        crew_id: uuid.UUID | None,
    ) -> uuid.UUID:
        """Resolves target crew member UUID and validates authorization scopes."""
        if identity.role == "CREW_MEMBER":
            if not identity.crew_member_id:
                raise AuthorizationError("Crew identity is not bound to a valid crew member.")
            user_crew = uuid.UUID(identity.crew_member_id)
            if crew_id is not None and crew_id != user_crew:
                raise AuthorizationError("Crew members may only query their own trends and baselines.")
            return user_crew

        # For Flight Surgeons and Admins, target crew_id must be provided and authorized
        if crew_id is None:
            raise InvalidValueError("Query parameter 'crew_id' is required for medical reviewer roles.")

        if not AuthService.verify_object_level_crew_access(identity, crew_id):
            raise AuthorizationError(
                f"User '{identity.username}' is not authorized to access health data for crew '{crew_id}'."
            )

        return crew_id

    @staticmethod
    def _validate_bounded_window(
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> tuple[datetime | None, datetime | None]:
        """Validates that time bounds are timezone-aware, chronological, and bounded."""
        now_utc = datetime.now(timezone.utc)

        if start_time is not None:
            if start_time.tzinfo is None:
                raise InvalidTimestampError("start_time must be timezone-aware (UTC).")

        if end_time is not None:
            if end_time.tzinfo is None:
                raise InvalidTimestampError("end_time must be timezone-aware (UTC).")

        if start_time and end_time:
            if start_time > end_time:
                raise InvalidTimestampError("start_time cannot be later than end_time.")

            span_days = (end_time - start_time).total_seconds() / 86400.0
            if span_days > MAX_TREND_WINDOW_DAYS:
                raise InvalidTimestampError(
                    f"Requested time window of {span_days:.1f} days exceeds maximum allowable span of {MAX_TREND_WINDOW_DAYS} days."
                )

        return start_time, end_time

    @classmethod
    async def get_trend_series(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        measurement_type: str,
        crew_id: uuid.UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        gap_threshold_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS,
    ) -> TrendSeriesResponse:
        """Computes comprehensive longitudinal trends and statistical analysis."""
        # 1. Type validation
        defn = measurement_registry.get(measurement_type)
        if defn is None or not defn.is_numeric:
            raise UnsupportedMeasurementTypeError(measurement_type)

        # 2. Authorization & Bounded Window Validation
        target_crew = cls._resolve_target_crew(identity, crew_id)
        start_time, end_time = cls._validate_bounded_window(start_time, end_time)

        # 3. Query historical records (chronological order)
        query = (
            select(HealthMeasurement)
            .where(
                HealthMeasurement.crew_member_id == target_crew,
                HealthMeasurement.measurement_type == measurement_type,
            )
            .order_by(HealthMeasurement.measured_at.asc(), HealthMeasurement.id.asc())
        )
        if start_time:
            query = query.where(HealthMeasurement.measured_at >= start_time)
        if end_time:
            query = query.where(HealthMeasurement.measured_at <= end_time)

        query = query.limit(limit)
        result = await session.execute(query)
        all_records = result.scalars().all()

        # 4. Separate valid observations from invalidated readings
        valid_records = [
            m for m in all_records
            if m.quality_status != "INVALIDATED" and m.value_numeric is not None
        ]
        invalidated_count = len([m for m in all_records if m.quality_status == "INVALIDATED"])

        valid_values = [m.value_numeric for m in valid_records]  # type: ignore
        valid_timestamps = [
            m.measured_at.replace(tzinfo=timezone.utc) if m.measured_at.tzinfo is None else m.measured_at
            for m in valid_records
        ]

        # 5. Compute Statistics & Outliers
        stats = compute_statistics(valid_values)
        outlier_flags = detect_statistical_outliers(valid_values)
        coverage_gaps = detect_coverage_gaps(valid_timestamps, gap_threshold_seconds)

        # 6. Empirical Personal Baseline (requires min 10 observations)
        baseline = calculate_personal_baseline(
            values=valid_values,
            timestamps=valid_timestamps,
            crew_id=target_crew,
            measurement_type=measurement_type,
            canonical_unit=defn.canonical_unit,
        )

        # 7. Assemble Trend Observations with Provenance
        trend_observations: list[TrendObservation] = []
        for i, m in enumerate(valid_records):
            is_outlier, note = outlier_flags[i]
            ts = m.measured_at.replace(tzinfo=timezone.utc) if m.measured_at.tzinfo is None else m.measured_at
            trend_observations.append(
                TrendObservation(
                    id=m.id,
                    measured_at=ts,
                    value_numeric=m.value_numeric,  # type: ignore
                    unit=m.unit,
                    quality_status=m.quality_status,
                    is_statistical_outlier=is_outlier,
                    outlier_observation=note,
                    provenance=m.provenance,
                )
            )

        # 8. Data quality & freshness
        latest_time = valid_timestamps[-1] if valid_timestamps else None
        freshness_sec = (
            round((datetime.now(timezone.utc) - latest_time).total_seconds(), 1)
            if latest_time
            else None
        )
        data_quality = DataQualitySummary(
            total_records_ingested=len(all_records),
            valid_observations_count=len(valid_records),
            invalidated_observations_count=invalidated_count,
            latest_observation_at=latest_time,
            freshness_seconds=freshness_sec,
        )

        return TrendSeriesResponse(
            crew_member_id=target_crew,
            measurement_type=measurement_type,
            canonical_unit=defn.canonical_unit,
            time_window={
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "timezone": "UTC",
            },
            observation_count=len(valid_records),
            observations=trend_observations,
            data_quality=data_quality,
            coverage_gaps=coverage_gaps,
            statistics=stats,
            baseline=baseline,
        )

    @classmethod
    async def get_trend_summary(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        measurement_type: str,
        crew_id: uuid.UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> TrendSummaryResponse:
        """Returns statistical summary and data quality without transmitting entire raw series."""
        series = await cls.get_trend_series(
            session=session,
            identity=identity,
            measurement_type=measurement_type,
            crew_id=crew_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )
        return TrendSummaryResponse(
            crew_member_id=series.crew_member_id,
            measurement_type=series.measurement_type,
            canonical_unit=series.canonical_unit,
            time_window=series.time_window,
            observation_count=series.observation_count,
            data_quality=series.data_quality,
            statistics=series.statistics,
            baseline=series.baseline,
        )

    @classmethod
    async def get_personal_baseline(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        measurement_type: str,
        crew_id: uuid.UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> BaselineResponse:
        """Retrieves or calculates empirical personal baseline solely from verified historical data."""
        series = await cls.get_trend_series(
            session=session,
            identity=identity,
            measurement_type=measurement_type,
            crew_id=crew_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )
        if series.baseline:
            return series.baseline

        defn = measurement_registry.get(measurement_type)
        target_crew = cls._resolve_target_crew(identity, crew_id)
        return BaselineResponse(
            crew_member_id=target_crew,
            measurement_type=measurement_type,
            canonical_unit=defn.canonical_unit if defn else "unknown",
            baseline_status="UNAVAILABLE",
            unavailable_reason="No historical data available for baseline calculation.",
            observation_count=0,
        )
