"""Readiness service: loads verified readings, manages frozen baselines, and runs readiness engine."""
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from starlette.concurrency import run_in_threadpool
import pandas as pd

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models import HealthMeasurement
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService
from src.modules.readiness.baseline import (
    BaselineStore,
    FrozenBaseline,
    fit_frozen_baseline,
)
from src.modules.readiness.model import analyze, from_measurements
from src.modules.readiness.schemas import (
    BaselineMetadata,
    BaselineRecalibrateRequest,
    CrewReadinessResponse,
    FeatureAttribution,
    MahalanobisAlert,
    ReadinessOverviewResponse,
    SignalBaselineSchema,
)

MIN_OBSERVATIONS = 10   # below this, say INSUFFICIENT_DATA instead of guessing
MAX_ROWS = 20000
_FREQ_RE = re.compile(r"^(\d{1,2})([hHdD])$")


def _normalize_freq(freq: str) -> str:
    m = _FREQ_RE.match(freq or "")
    if not m:
        raise AppException(
            message="freq must look like '3h' or '1d'.",
            code="bad_request",
            status_code=400,
        )
    n, unit = m.groups()
    return f"{n}h" if unit.lower() == "h" else f"{n}D"


def _plain(v: Any) -> Any:
    """Enum -> its value, so the model sees plain strings."""
    return getattr(v, "value", v)


def _to_baseline_metadata_schema(fb: FrozenBaseline | None) -> BaselineMetadata | None:
    if not fb:
        return None
    sig_schemas = {}
    for m, s in fb.signals.items():
        sig_schemas[m] = SignalBaselineSchema(
            metric=s.metric,
            center=s.center,
            effective_dispersion=s.effective_dispersion,
            n_observations=s.n_observations,
            n_valid_days=s.n_valid_days,
            coverage_fraction=s.coverage_fraction,
            sufficiency_tier=s.sufficiency_tier,
        )
    return BaselineMetadata(
        version_id=fb.version_id,
        created_at=fb.created_at,
        calibration_window_start=fb.calibration_window_start,
        calibration_window_end=fb.calibration_window_end,
        recalibration_reason=fb.recalibration_reason,
        method=fb.method,
        total_raw_rows=fb.total_raw_rows,
        quality_exclusions_count=fb.quality_exclusions_count,
        overall_sufficiency=fb.overall_sufficiency,
        signals=sig_schemas,
    )


class ReadinessService:
    @staticmethod
    def _resolve_crew_id(identity: AuthenticatedIdentity, crew_id: uuid.UUID | None) -> uuid.UUID:
        if crew_id is not None:
            return crew_id
        if identity.crew_member_id:
            return uuid.UUID(identity.crew_member_id)
        raise AppException(
            message="crew_id is required for medical reviewers.",
            code="bad_request",
            status_code=400,
        )

    @staticmethod
    async def _fetch_rows(session: AsyncSession, crew_id: uuid.UUID,
                          start_time: datetime | None, end_time: datetime | None) -> list[dict]:
        stmt = (
            select(
                HealthMeasurement.crew_member_id,
                HealthMeasurement.measurement_type,
                HealthMeasurement.value_numeric,
                HealthMeasurement.measured_at,
                HealthMeasurement.quality_status,
            )
            .where(HealthMeasurement.crew_member_id == crew_id)
            .order_by(HealthMeasurement.measured_at)
            .limit(MAX_ROWS)
        )
        if start_time is not None:
            stmt = stmt.where(HealthMeasurement.measured_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(HealthMeasurement.measured_at <= end_time)
        result = await session.execute(stmt)
        rows = []
        for r in result.all():
            d = dict(r._mapping)
            d["measurement_type"] = _plain(d["measurement_type"])
            d["quality_status"] = _plain(d["quality_status"])
            rows.append(d)
        return rows

    @staticmethod
    def build(crew_id: uuid.UUID, rows: list[dict], freq: str, window: int,
              min_periods: int, alert_n: int, include_series: bool = True) -> CrewReadinessResponse:
        insufficient = CrewReadinessResponse(
            crew_id=crew_id,
            status="INSUFFICIENT_DATA",
            data_status="INSUFFICIENT_DATA",
            readiness_category="INSUFFICIENT_DATA",
            data_sufficiency="insufficient",
            observations_used=len(rows),
        )
        if len(rows) < MIN_OBSERVATIONS:
            return insufficient

        # Get or initialize frozen baseline (never silently updates if already frozen)
        cid_str = str(crew_id)
        active_baseline = BaselineStore.get_active(cid_str)
        if active_baseline is None:
            active_baseline = fit_frozen_baseline(
                crew_member_id=cid_str,
                raw_rows=rows,
                reason="Initial baseline fit",
                calibration_window_days=window,
                min_observations=min_periods
            )
            if active_baseline:
                BaselineStore.save(active_baseline)

        # Prepare raw measurement dataframe for sensor-fault check (Task 27)
        raw_df = pd.DataFrame(rows) if rows else None

        result = analyze(
            from_measurements(rows),
            freq=_normalize_freq(freq),
            window=window,
            min_periods=min_periods,
            alert_n=alert_n,
            frozen_baseline=active_baseline,
            raw_measurements_df=raw_df
        ).get(cid_str)

        if not result or result["readiness"] is None:
            # If sensor faults detected, forward the descriptive error status
            if result and result.get("data_status") == "FAULTY_SENSOR":
                return CrewReadinessResponse(
                    crew_id=crew_id,
                    status=result.get("status", "INSUFFICIENT_DATA"),
                    data_status="FAULTY_SENSOR",
                    readiness_category="INSUFFICIENT_DATA",
                    data_sufficiency="insufficient",
                    observations_used=len(rows),
                )
            return insufficient

        # Map Mahalanobis alert if present
        mahal_obj = None
        if result.get("mahalanobis_alert"):
            ma = result["mahalanobis_alert"]
            contribs = [FeatureAttribution(**c) for c in ma.get("top_contributors", [])]
            mahal_obj = MahalanobisAlert(
                distance_squared=ma["distance_squared"],
                threshold=ma["threshold"],
                degrees_of_freedom=ma["degrees_of_freedom"],
                top_contributors=contribs,
                message=ma["message"]
            )

        return CrewReadinessResponse(
            crew_id=crew_id,
            status=result["status"],
            data_status=result.get("data_status", "COMPLETE"),
            readiness_category=result.get("readiness_category", "NOMINAL"),
            data_sufficiency=result.get("data_sufficiency", "moderate"),
            readiness=result["readiness"],
            readiness_series=result["readiness_series"] if include_series else [],
            forecast=result["forecast"],
            drift_alerts=result.get("drift_alerts", []),
            incidents=result.get("incidents", []),
            environmental_alerts=result.get("environmental_alerts", []),
            mahalanobis_alert=mahal_obj,
            baseline_metadata=_to_baseline_metadata_schema(active_baseline),
            observations_used=len(rows),
        )

    @staticmethod
    async def get_readiness(session: AsyncSession, identity: AuthenticatedIdentity,
                            crew_id: uuid.UUID | None, start_time: datetime | None,
                            end_time: datetime | None, freq: str, window: int,
                            min_periods: int, alert_n: int,
                            include_series: bool = True) -> CrewReadinessResponse:
        target = ReadinessService._resolve_crew_id(identity, crew_id)
        await AuthService.enforce_crew_access(
            session=session, identity=identity,
            target_crew_member_id=target, action="ACCESS_HEALTH_RECORD",
        )
        rows = await ReadinessService._fetch_rows(session, target, start_time, end_time)
        return await run_in_threadpool(
            ReadinessService.build, target, rows, freq, window, min_periods, alert_n, include_series
        )

    @staticmethod
    async def get_overview(session: AsyncSession, identity: AuthenticatedIdentity,
                           freq: str, window: int, min_periods: int,
                           alert_n: int) -> ReadinessOverviewResponse:
        ids = list(identity.assigned_crew_ids or [])
        if not ids and identity.crew_member_id:
            ids = [identity.crew_member_id]
        crews = [
            await ReadinessService.get_readiness(
                session, identity, uuid.UUID(cid), None, None,
                freq, window, min_periods, alert_n, include_series=False)
            for cid in ids
        ]
        return ReadinessOverviewResponse(crews=crews)

    @staticmethod
    async def recalibrate_baseline(
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        request: BaselineRecalibrateRequest
    ) -> BaselineMetadata:
        """Explicit recalibration call creating a new frozen baseline version with documented audit reason.
        
        Guarantees that baselines are never silently updated during routine querying.
        """
        await AuthService.enforce_crew_access(
            session=session, identity=identity,
            target_crew_member_id=request.crew_id, action="ACCESS_HEALTH_RECORD",
        )
        rows = await ReadinessService._fetch_rows(session, request.crew_id, None, None)
        if len(rows) < MIN_OBSERVATIONS:
            raise AppException(
                message=f"Insufficient observations to recalibrate ({len(rows)} < {MIN_OBSERVATIONS}).",
                code="insufficient_data",
                status_code=400,
            )

        new_baseline = await run_in_threadpool(
            fit_frozen_baseline,
            crew_member_id=str(request.crew_id),
            raw_rows=rows,
            reason=request.reason,
            calibration_window_days=request.calibration_window_days,
            method=request.method
        )
        if not new_baseline:
            raise AppException(
                message="Failed to calibrate baseline from provided telemetry.",
                code="calibration_error",
                status_code=400,
            )

        BaselineStore.save(new_baseline)
        meta = _to_baseline_metadata_schema(new_baseline)
        assert meta is not None
        return meta

    @staticmethod
    async def get_active_baseline(
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        crew_id: uuid.UUID
    ) -> BaselineMetadata:
        await AuthService.enforce_crew_access(
            session=session, identity=identity,
            target_crew_member_id=crew_id, action="ACCESS_HEALTH_RECORD",
        )
        fb = BaselineStore.get_active(str(crew_id))
        if not fb:
            raise AppException(
                message="No active baseline found for this crew member.",
                code="not_found",
                status_code=404,
            )
        meta = _to_baseline_metadata_schema(fb)
        assert meta is not None
        return meta
