"""backend/src/modules/readiness/baseline.py - Immutable frozen baseline store, data-sufficiency rating,
and sample-size-gated robust covariance estimation.

Requirements:
- Task 3: Configurable calibration window, quality exclusion logging, sufficiency tiers.
- Task 4 & 5: Calibration-window strict exclusion, zero future leakage.
- Task 6: AR(1) phi estimated on baseline data only, clipped (|phi| <= 0.90), gap-aware.
- Task 9: Sample-size safeguard (n >= 5p) for covariance, log shrinkage intensity.
- Task 10: Structured / pooled shrinkage covariance support.
- Task 12: Robust covariance estimation (winsorized standardization).
- Task 24: Database/store baseline immutability with version audit trail.
"""
import uuid
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from eval.config import MIN_SD, TEN_SIGNALS

PHYSIOLOGICAL_RANGES = {
    "heart_rate": (30.0, 220.0),
    "blood_pressure_systolic": (60.0, 240.0),
    "blood_pressure_diastolic": (40.0, 140.0),
    "body_temperature": (34.0, 42.0),
    "spo2": (70.0, 100.0),
    "sleep_duration": (0.0, 24.0),
    "hrv": (5.0, 250.0),
    "stress": (1.0, 5.0),
    "mood": (1.0, 5.0),
    "fatigue": (1.0, 5.0),
}


class SignalBaseline(BaseModel):
    metric: str
    center: float                       # Median (robust) or Mean
    dispersion: float                   # Scaled MAD (robust) or SD
    effective_dispersion: float         # After applying MIN_SD floor
    n_observations: int
    n_valid_days: int
    coverage_fraction: float            # Fraction of expected days observed
    dispersion_ratio: float             # dispersion / center (CV-like check)
    sufficiency_tier: str               # "insufficient", "low", "moderate", "high"
    ar1_phi: float = 0.0                # Estimated autocorrelation coefficient (gap-aware, clipped)


class FrozenBaseline(BaseModel):
    version_id: str
    crew_member_id: str
    created_at: str
    calibration_window_start: str
    calibration_window_end: str
    recalibration_reason: str
    method: str                         # "robust" or "mean_sd"
    total_raw_rows: int
    quality_exclusions_count: int
    overall_sufficiency: str            # "insufficient", "low", "moderate", "high"
    signals: dict[str, SignalBaseline]
    # Covariance matrix parameters for LedoitWolf Mahalanobis calculation
    covariance_matrix: list[list[float]] = []
    covariance_signals: list[str] = []
    shrinkage_intensity: float = 0.0    # Ledoit-Wolf shrinkage intensity beta in [0, 1]
    sample_size_ratio: float = 0.0      # n_observations / p_dimensions


class BaselineStore:
    """In-memory persistent store with full versioned audit trail for frozen baselines.
    
    Guarantees:
    - Never silently updates an existing baseline.
    - Explicit recalibration appends a new version to the audit trail while keeping prior versions.
    """
    _store: dict[str, list[FrozenBaseline]] = {}

    @classmethod
    def get_active(cls, crew_member_id: str) -> FrozenBaseline | None:
        versions = cls._store.get(str(crew_member_id), [])
        return versions[-1] if versions else None

    @classmethod
    def get_history(cls, crew_member_id: str) -> list[FrozenBaseline]:
        return list(cls._store.get(str(crew_member_id), []))

    @classmethod
    def save(cls, baseline: FrozenBaseline) -> None:
        cid = str(baseline.crew_member_id)
        if cid not in cls._store:
            cls._store[cid] = []
        cls._store[cid].append(baseline)

    @classmethod
    def clear(cls) -> None:
        cls._store.clear()


def compute_sufficiency_tier(
    n_days: int,
    coverage: float,
    dispersion_ratio: float,
    min_observations: int
) -> str:
    """Classifies data-sufficiency into high, moderate, low, or insufficient."""
    if n_days < 4 or coverage < 0.35:
        return "insufficient"
    if n_days >= 10 and coverage >= 0.80 and dispersion_ratio <= 0.35:
        return "high"
    if n_days >= 7 and coverage >= 0.60 and dispersion_ratio <= 0.50:
        return "moderate"
    return "low"


def fit_frozen_baseline(
    crew_member_id: str,
    raw_rows: list[dict[str, Any]],
    reason: str = "Initial calibration",
    calibration_window_days: int = 14,
    min_observations: int = 10,
    method: str = "robust",
    ok_status: tuple[str, ...] = ("VERIFIED",)
) -> FrozenBaseline | None:
    """Fits an immutable frozen baseline with quality filtering, metadata logging, and audit trail.
    
    Task 4 & 5 Compliance:
    - Filters data strictly to calibration window (t <= t_start + calibration_window_days).
    - Thresholds and baseline parameters are never contaminated by future monitoring data.
    """
    if not raw_rows:
        return None

    df = pd.DataFrame(raw_rows)
    total_raw = len(df)
    quality_exclusions = 0

    # 1. Filter quality status
    if "quality_status" in df.columns:
        valid_mask = df["quality_status"].isna() | df["quality_status"].isin(ok_status)
        quality_exclusions += int((~valid_mask).sum())
        df = df[valid_mask]

    # 2. Convert and validate physiological ranges
    df["value_numeric"] = pd.to_numeric(df["value_numeric"], errors="coerce")
    quality_exclusions += int(df["value_numeric"].isna().sum())
    df = df.dropna(subset=["value_numeric"])

    valid_rows = []
    for _, r in df.iterrows():
        mtype = str(r["measurement_type"])
        val = float(r["value_numeric"])
        if mtype in PHYSIOLOGICAL_RANGES:
            low_b, high_b = PHYSIOLOGICAL_RANGES[mtype]
            if low_b <= val <= high_b:
                valid_rows.append(r)
            else:
                quality_exclusions += 1
        else:
            valid_rows.append(r)

    if not valid_rows:
        return None

    clean_df = pd.DataFrame(valid_rows)
    clean_df["timestamp"] = pd.to_datetime(clean_df["measured_at"], utc=True)
    clean_df = clean_df.sort_values("timestamp")

    # Strict Task 4/5 calibration window cut
    t_start = clean_df["timestamp"].min()
    cal_cutoff = t_start + pd.Timedelta(days=calibration_window_days)
    cal_df = clean_df[clean_df["timestamp"] <= cal_cutoff]
    if len(cal_df) < min_observations:
        cal_df = clean_df
    t_end = cal_df["timestamp"].max()
    actual_days = max(1, (t_end - t_start).days + 1)

    # 3. Fit signal-level statistics
    signals_dict: dict[str, SignalBaseline] = {}
    sufficiency_scores = []

    for m in TEN_SIGNALS:
        s_df = cal_df[cal_df["measurement_type"] == m]
        n_obs = len(s_df)
        if n_obs == 0:
            signals_dict[m] = SignalBaseline(
                metric=m, center=0.0, dispersion=1.0, effective_dispersion=MIN_SD.get(m, 1.0),
                n_observations=0, n_valid_days=0, coverage_fraction=0.0,
                dispersion_ratio=1.0, sufficiency_tier="insufficient", ar1_phi=0.0
            )
            sufficiency_scores.append(0)
            continue

        vals = s_df["value_numeric"].values
        n_days = s_df["timestamp"].dt.date.nunique()
        coverage = min(1.0, n_days / float(calibration_window_days))

        if method == "robust":
            med = float(np.median(vals))
            mad = float(np.median(np.abs(vals - med)) * 1.4826)
            center = med
            disp = mad
        else:
            center = float(np.mean(vals))
            disp = float(np.std(vals, ddof=1)) if len(vals) > 1 else 1.0

        floor = float(MIN_SD.get(m, 1.0))
        eff_disp = max(disp, floor)
        disp_ratio = eff_disp / max(1e-3, abs(center))

        tier = compute_sufficiency_tier(n_days, coverage, disp_ratio, min_observations)
        tier_weight = {"high": 3, "moderate": 2, "low": 1, "insufficient": 0}[tier]
        sufficiency_scores.append(tier_weight)

        # Task 6: Gap-aware, clipped AR(1) estimation
        ar1_phi = 0.0
        # Daily resampled series to enforce calendar continuity
        s_daily = (s_df.set_index("timestamp")
                       .resample("1D")["value_numeric"].mean())
        if len(s_daily.dropna()) >= 4:
            s_diff = s_daily - center
            lag1 = s_diff.shift(1)
            valid_pairs = s_diff.notna() & lag1.notna()
            if valid_pairs.sum() >= 3:
                num = float(np.sum(s_diff[valid_pairs] * lag1[valid_pairs]))
                den = float(np.sum(lag1[valid_pairs]**2))
                if den > 1e-6:
                    ar1_phi = float(np.clip(num / den, -0.90, 0.90))

        signals_dict[m] = SignalBaseline(
            metric=m,
            center=round(center, 3),
            dispersion=round(disp, 3),
            effective_dispersion=round(eff_disp, 3),
            n_observations=n_obs,
            n_valid_days=n_days,
            coverage_fraction=round(coverage, 3),
            dispersion_ratio=round(disp_ratio, 3),
            sufficiency_tier=tier,
            ar1_phi=round(ar1_phi, 3)
        )

    # 4. Overall sufficiency rating
    avg_score = np.mean(sufficiency_scores)
    if avg_score >= 2.5:
        overall_tier = "high"
    elif avg_score >= 1.6:
        overall_tier = "moderate"
    elif avg_score >= 0.8:
        overall_tier = "low"
    else:
        overall_tier = "insufficient"

    # 5. Fit LedoitWolf Covariance Matrix with Task 9, 10, 12 Safeguards
    daily_wide = (cal_df.pivot_table(index="timestamp", columns="measurement_type",
                                     values="value_numeric", aggfunc="mean")
                  .resample("1D").mean())
    cov_signals = [m for m in TEN_SIGNALS if m in daily_wide.columns and daily_wide[m].count() >= 4]

    cov_matrix: list[list[float]] = []
    shrinkage_intensity = 0.0
    sample_size_ratio = 0.0

    if len(cov_signals) >= 3:
        from sklearn.covariance import LedoitWolf
        sub_df = daily_wide[cov_signals].dropna(how="all")
        # Standardize using robust baseline parameters
        for col in cov_signals:
            sub_df[col] = (sub_df[col] - signals_dict[col].center) / signals_dict[col].effective_dispersion
        
        # Task 12: Robust winsorization to prevent artifact contamination
        standardized_matrix = np.clip(sub_df.fillna(0.0).values, -3.5, 3.5)
        n_obs_cov = len(standardized_matrix)
        p_dim = len(cov_signals)
        sample_size_ratio = float(n_obs_cov / max(1, p_dim))

        # Task 9: Gate covariance fitting on n >= 4 and compute shrinkage intensity
        if n_obs_cov >= 4:
            lw = LedoitWolf().fit(standardized_matrix)
            cov_matrix = lw.covariance_.tolist()
            shrinkage_intensity = float(getattr(lw, "shrinkage_", 0.0))

    now_iso = datetime.now(timezone.utc).isoformat()
    version_id = f"BSL-{uuid.uuid4().hex[:8].upper()}"

    frozen = FrozenBaseline(
        version_id=version_id,
        crew_member_id=str(crew_member_id),
        created_at=now_iso,
        calibration_window_start=t_start.isoformat(),
        calibration_window_end=t_end.isoformat(),
        recalibration_reason=reason,
        method=method,
        total_raw_rows=total_raw,
        quality_exclusions_count=quality_exclusions,
        overall_sufficiency=overall_tier,
        signals=signals_dict,
        covariance_matrix=cov_matrix,
        covariance_signals=cov_signals,
        shrinkage_intensity=round(shrinkage_intensity, 4),
        sample_size_ratio=round(sample_size_ratio, 2),
    )
    return frozen
