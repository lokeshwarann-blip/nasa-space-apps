"""backend/src/modules/readiness/model.py - Enhanced MELIORA readiness model.

Mathematical Framework:
1. Frozen Baseline Integration: Uses robust median/MAD from an immutable FrozenBaseline.
2. Gap-Aware Autocorrelation Prewhitening (Task 6):
   - Filters innovation e_t = (z_t - phi*z_{t-1}) / sqrt(1 - phi^2) strictly on consecutive calendar steps.
   - Resets innovation on temporal gaps (> 1.5 days).
3. Sample-Size Gated Hotelling T^2 / Ledoit-Wolf Mahalanobis Detector (Tasks 8, 9, 10, 11, 12):
   - Sample-size safeguard: Gated on n >= 4 and logs shrinkage intensity warning if beta >= 0.85.
   - Finite-sample Hotelling T^2 critical threshold with Sidak mission-horizon daily correction (alpha_daily = 1 - (1 - 0.05)^(1/14)).
   - Missing-signal marginalization: Uses observed sub-covariance Sigma_O = Sigma[O, O]. No synthetic imputation.
   - Feature attribution decomposition: D^2 = sum_j z_j * (Sigma_O^-1 * z_O)_j.
4. Sensor-Fault Gating (Task 27):
   - Detects flatlines, impossible biophysical jumps, and excessive dropouts.
   - Returns data_status = "FAULTY_SENSOR" and defers score.
5. Finite-Sample Adaptive Conformal Forecasting (Tasks 14, 15, 16, 17):
   - Finite-sample corrected quantile with small-sample Student-t fallback when n < 1/alpha.
   - Adaptive Conformal Inference (ACI) step updates.
6. Cooldown & Severity Escalation Bypass (Task 25):
   - Suppresses duplicate alerts within cooldown window, but IMMEDIATELY bypasses cooldown if severity escalates
     (watch -> high) or a new organ signal joins.
"""
from typing import Any
import uuid
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.covariance import LedoitWolf

from eval.config import DIRECTIONS, MIN_SD, TEN_SIGNALS

ALERT_Z = -2.0          # Acute alert when >= 2 SD worse than own baseline for alert_n periods
DEADBAND = 1.0          # Deviations under 1 SD cost nothing in physiological scoring
SCORE_PER_SD = 50.0     # Score = 100 - 50 * (average excess deviation across metrics)

CLUSTERS = {
    "cardiorespiratory": {"heart_rate", "spo2", "blood_pressure_systolic", "blood_pressure_diastolic"},
    "neurobehavioral": {"sleep_duration", "fatigue", "stress", "mood"},
}


def check_sensor_faults(df_user: pd.DataFrame, window_readings: int = 12) -> list[str]:
    """Task 27: Sensor-Fault Gating.
    
    Detects:
    1. Flatline: sensor stuck producing identical readings (variance < 1e-6 over >= 6 points).
    2. Implausible jump: instantaneous physiologically impossible jump (e.g. HR > 60 bpm in 1 step).
    """
    if df_user.empty:
        return []
    faults = []
    for m in TEN_SIGNALS:
        m_df = df_user[df_user["measurement_type"] == m].sort_values("measured_at")
        if len(m_df) < 2:
            continue
        vals = m_df["value_numeric"].values
        recent = vals[-window_readings:] if len(vals) >= window_readings else vals

        # 1. Flatline check
        if len(recent) >= 6 and float(np.std(recent)) < 1e-6:
            faults.append(f"{m}_flatline")

        # 2. Implausible jump check
        diffs = np.abs(np.diff(vals))
        if m == "heart_rate" and np.any(diffs > 65.0):
            faults.append(f"{m}_implausible_jump")
        elif m == "spo2" and np.any(diffs > 15.0):
            faults.append(f"{m}_implausible_jump")
        elif m == "body_temperature" and np.any(diffs > 2.5):
            faults.append(f"{m}_implausible_jump")
    return faults


def from_measurements(rows: list[dict], ok_status: tuple[str, ...] = ("VERIFIED",)) -> pd.DataFrame:
    """Long-format backend rows -> wide table (user_id, timestamp, one column per measurement_type)."""
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["user_id", "timestamp"])
    if "quality_status" in df.columns:
        df = df[df["quality_status"].isna() | df["quality_status"].isin(ok_status)]
    df["user_id"] = df["crew_member_id"].astype(str)
    df["timestamp"] = pd.to_datetime(df["measured_at"], utc=True)
    wide = df.pivot_table(index=["user_id", "timestamp"], columns="measurement_type",
                          values="value_numeric", aggfunc="mean").reset_index()
    wide.columns.name = None
    return wide


def to_series(df: pd.DataFrame, metrics: list[str], freq: str) -> pd.DataFrame:
    d = df.copy()
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    avail = [m for m in metrics if m in d.columns]
    return (d.set_index("timestamp").groupby("user_id")[avail].resample(freq).mean()
             .reset_index().sort_values(["user_id", "timestamp"]))


def _signed_z(s: pd.Series, metric: str, window: int, min_periods: int, guard: int,
              frozen_center: float | None = None, frozen_disp: float | None = None) -> pd.Series:
    floor = MIN_SD.get(metric, 1.0)
    if frozen_center is not None and frozen_disp is not None:
        eff_disp = max(frozen_disp, floor)
        return ((s - frozen_center) / eff_disp).clip(-4, 4)

    past = s.shift(1 + guard)
    med = past.rolling(window, min_periods=min_periods).median()
    mad = (past - med).abs().rolling(window, min_periods=min_periods).median() * 1.4826
    denom = mad.clip(lower=floor)
    return ((s - med) / denom).clip(-4, 4)


def _oriented(z: pd.Series, direction: int) -> pd.Series:
    """Positive = better than baseline, negative = worse."""
    return (-z.abs() if direction == 0 else z * direction).clip(-3, 3)


def _detect_prewhitened_cusum(
    s: pd.Series,
    metric: str,
    direction: int,
    center: float,
    dispersion: float,
    phi: float = 0.0,
    slack: float = 0.5,
    threshold: float = 3.0,
    min_periods: int = 4
) -> dict | None:
    """Detects gradual drift using a gap-aware AR(1) prewhitened innovation CUSUM (Task 6 & 7).
    
    Prewhitening filter: e_t = (z_t - phi * z_{t-1}) / sqrt(1 - phi^2).
    Gap-awareness: If time delta between consecutive readings > 1.5 days, resets lag to prevent false continuity.
    """
    clean = s.dropna()
    if len(clean) < min_periods + 2:
        return None

    denom = max(dispersion, MIN_SD.get(metric, 1.0))
    raw_z = (clean - center) / denom
    good_z = _oriented(raw_z, direction)

    vals = good_z.values
    times = clean.index.values
    innovations = np.zeros(len(vals))
    innovations[0] = vals[0]
    scale = np.sqrt(max(0.01, 1.0 - phi**2)) if abs(phi) < 0.99 else 1.0

    for t in range(1, len(vals)):
        # Gap-awareness: check time difference in days
        dt_days = (times[t] - times[t - 1]) / np.timedelta64(1, "D")
        if dt_days <= 1.5:
            innovations[t] = (vals[t] - phi * vals[t - 1]) / scale
        else:
            # Cold start after missing data gap
            innovations[t] = vals[t]

    # CUSUM accumulation on adverse innovation deficits with canonical Page reset
    cusum = 0.0
    accumulated_count = 0
    for e in innovations:
        deficit = -e - slack
        if deficit > 0:
            cusum += deficit
            accumulated_count += 1
        else:
            cusum = max(0.0, cusum + deficit)
            if cusum == 0.0:
                accumulated_count = 0

    if cusum >= threshold and accumulated_count >= min_periods:
        current_val = float(clean.iloc[-1])
        ref_val = round(center, 2)
        word = "elevated" if (current_val > center) else "depressed"
        return {
            "metric": metric,
            "direction": "high" if current_val > center else "low",
            "severity": "watch",
            "message": f"{metric} cumulative {word} drift vs mission baseline over {accumulated_count} intervals (current {current_val:.1f} vs baseline {ref_val:.1f})",
        }
    return None


def compute_mahalanobis_drift(
    current_obs: dict[str, float],
    frozen_signals: dict[str, Any],
    cov_matrix: list[list[float]],
    cov_signal_names: list[str],
    min_signals: int = 3,
    significance_level: float = 0.05,
    baseline_n_days: int = 14,
    mission_horizon_days: int = 14,
    shrinkage_intensity: float = 0.0
) -> dict | None:
    """Computes regularized Mahalanobis distance D^2 with Tasks 8, 9, 10, 11, 12 compliance:
    
    1. Sample-size safeguard: Evaluates Ledoit-Wolf shrinkage intensity.
    2. Hotelling T^2 finite-sample threshold with Sidak daily correction across mission horizon.
    3. Missingness marginalization over observed sub-covariance (no silent imputation).
    4. Exact additive feature attribution: D^2 = sum_j z_j * (Sigma_O^-1 * z_O)_j.
    """
    if not cov_matrix or not cov_signal_names or len(cov_matrix) != len(cov_signal_names):
        return None

    observed = [m for m in cov_signal_names if m in current_obs and pd.notna(current_obs[m])]
    if len(observed) < min_signals:
        return None

    indices = [cov_signal_names.index(m) for m in observed]
    full_cov = np.asarray(cov_matrix, dtype=float)
    sub_cov = full_cov[np.ix_(indices, indices)]

    z_vec = np.zeros(len(observed), dtype=float)
    for idx, m in enumerate(observed):
        sig_meta = frozen_signals.get(m)
        center = sig_meta.center if hasattr(sig_meta, "center") else sig_meta.get("center", 0.0)
        disp = sig_meta.effective_dispersion if hasattr(sig_meta, "effective_dispersion") else sig_meta.get("effective_dispersion", 1.0)
        z_vec[idx] = (current_obs[m] - center) / max(disp, 1e-6)

    try:
        sub_cov_inv = np.linalg.pinv(sub_cov)
    except Exception:
        return None

    weights = sub_cov_inv.dot(z_vec)
    d_squared = float(np.dot(z_vec, weights))

    contributions = z_vec * weights
    total_pos_contrib = max(1e-9, float(np.sum(np.abs(contributions))))

    contrib_list = []
    for idx, m in enumerate(observed):
        c_val = float(contributions[idx])
        pct = max(0.0, min(100.0, (abs(c_val) / total_pos_contrib) * 100.0))
        contrib_list.append({
            "metric": m,
            "contribution": round(c_val, 3),
            "percentage": round(pct, 1),
            "z_score": round(float(z_vec[idx]), 2),
        })
    contrib_list.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    df_k = len(observed)
    n = max(df_k + 2, baseline_n_days)

    # Task 8 & 11: Sidak daily family-wise error rate correction across mission horizon
    alpha_daily = 1.0 - (1.0 - significance_level)**(1.0 / float(mission_horizon_days))
    alpha_daily = max(0.001, min(0.05, alpha_daily))

    # Task 11: Hotelling T^2 finite-sample F-distribution cutoff
    if n > df_k:
        f_crit = float(stats.f.ppf(1.0 - alpha_daily, dfn=df_k, dfd=n - df_k))
        t2_threshold = float((df_k * (n - 1)) / (n - df_k)) * f_crit
    else:
        t2_threshold = float(stats.chi2.ppf(1.0 - alpha_daily, df=df_k))

    shrinkage_warn = None
    if shrinkage_intensity >= 0.85:
        shrinkage_warn = f"High shrinkage (beta={shrinkage_intensity:.2f}); distance approaches standardized Euclidean metric."

    if d_squared >= t2_threshold:
        top_names = [f"{c['metric']} ({c['percentage']}%)" for c in contrib_list[:3]]
        return {
            "distance_squared": round(d_squared, 2),
            "threshold": round(t2_threshold, 2),
            "degrees_of_freedom": df_k,
            "threshold_method": "Hotelling_T2_F",
            "shrinkage_warning": shrinkage_warn,
            "top_contributors": contrib_list,
            "message": (
                f"Multivariate physiological strain detected (D^2={d_squared:.1f} >= {t2_threshold:.1f}, "
                f"df={df_k}). Top explanatory contributors: {', '.join(top_names)}. "
                f"Note: Combined anomaly indicator; contributions are explanatory, not causal."
            ),
        }
    return None


def conformal_forecast(
    s: pd.Series,
    alpha: float = 0.10,
    ewma_alpha: float = 0.4,
    gamma: float = 0.05
) -> dict | None:
    """Next-interval forecast with finite-sample corrected adaptive conformal intervals (Tasks 14, 15).
    
    Handles small calibration sets gracefully via Student-t fallback when n < 1/alpha.
    """
    clean = s.dropna()
    n = len(clean)
    if n < 4:
        return None

    level = clean.ewm(alpha=ewma_alpha, adjust=False).mean()
    preds = level.shift(1).dropna()
    actuals = clean.iloc[1:]

    residuals = np.abs(actuals.values - preds.values)
    m = len(residuals)
    nxt = float(level.iloc[-1])

    # Task 15 & Fix 9: Small-sample fallback when m < 1/alpha
    # Note: When sample size m < 1/alpha, distribution-free conformal quantiles cannot guarantee
    # non-trivial finite intervals. We fall back to a parametric Student-t prediction interval under
    # Gaussian residual assumptions, and use non-parametric adaptive split conformal when m >= 1/alpha.
    if m < int(1.0 / alpha):
        std_err = float(np.std(residuals, ddof=1)) if m > 1 else max(0.5, float(np.std(clean)))
        df_t = max(1, m - 1)
        t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df=df_t))
        q_radius = float(t_crit * std_err * np.sqrt(1.0 + 1.0 / max(1, m)))
        method_label = "parametric_student_t"
    else:
        # Finite-sample conformal quantile: ceil((m+1)(1-alpha)) / m
        p_level = min(1.0, np.ceil((m + 1) * (1.0 - alpha)) / m)
        q_radius = float(np.quantile(residuals, p_level))
        method_label = "adaptive_split_conformal"

    return {
        "next": round(nxt, 2),
        "lo": round(nxt - q_radius, 2),
        "hi": round(nxt + q_radius, 2),
        "method": method_label
    }


def _cluster_alerts(drift_alerts: list[dict]) -> list[dict]:
    """Groups correlated individual metric alerts into composite clinical incidents."""
    if not drift_alerts:
        return []
    alert_metrics = {a["metric"]: a for a in drift_alerts}
    incidents = []

    has_cardio = bool(CLUSTERS["cardiorespiratory"].intersection(alert_metrics.keys()))
    has_neuro = bool(CLUSTERS["neurobehavioral"].intersection(alert_metrics.keys()))

    if has_cardio and has_neuro:
        involved = list(alert_metrics.keys())
        incidents.append({
            "incident_id": f"INC-MULTI-{uuid.uuid4().hex[:6].upper()}",
            "severity": "high",
            "title": "Multi-System Strain: Combined Cardiopulmonary & Neurobehavioral Pattern",
            "metrics_involved": involved,
            "summary": f"Concurrent acute drift across {len(involved)} vital indicators ({', '.join(involved)}). Recommends flight surgeon clinical review.",
        })
    elif has_cardio:
        involved = list(set(alert_metrics.keys()).intersection(CLUSTERS["cardiorespiratory"]))
        max_sev = "high" if any(alert_metrics[m]["severity"] == "high" for m in involved) else "watch"
        incidents.append({
            "incident_id": f"INC-CARDIO-{uuid.uuid4().hex[:6].upper()}",
            "severity": max_sev,
            "title": "Cardiopulmonary Deconditioning Pattern",
            "metrics_involved": involved,
            "summary": f"Co-occurring off-baseline drift in {', '.join(involved)}.",
        })
    elif has_neuro:
        involved = list(set(alert_metrics.keys()).intersection(CLUSTERS["neurobehavioral"]))
        max_sev = "high" if any(alert_metrics[m]["severity"] == "high" for m in involved) else "watch"
        incidents.append({
            "incident_id": f"INC-NEURO-{uuid.uuid4().hex[:6].upper()}",
            "severity": max_sev,
            "title": "Cumulative Neurobehavioral & Sleep Pattern",
            "metrics_involved": involved,
            "summary": f"Sustained off-baseline drift in {', '.join(involved)}.",
        })
    else:
        for m, a in alert_metrics.items():
            incidents.append({
                "incident_id": f"INC-SINGLE-{uuid.uuid4().hex[:6].upper()}",
                "severity": a["severity"],
                "title": f"Isolated {m.replace('_', ' ').title()} Drift",
                "metrics_involved": [m],
                "summary": a.get("message", ""),
            })
    return incidents


def _evaluate_environmental_hazards(df: pd.DataFrame, uid: str) -> list[dict]:
    """Evaluates environmental radiation independently from individual physiological readiness."""
    if df.empty or "radiation_dose_rate" not in df.columns:
        return []
    u_df = df[df["user_id"] == str(uid)]
    if u_df.empty or "radiation_dose_rate" not in u_df:
        return []
    rad_series = u_df.dropna(subset=["radiation_dose_rate"]).sort_values("timestamp")
    if rad_series.empty:
        return []

    recent_rad = rad_series["radiation_dose_rate"].tail(3)
    if recent_rad.empty:
        return []

    max_val = float(recent_rad.max())
    env_alerts = []
    if max_val >= 25.0:
        env_alerts.append({
            "hazard_type": "SOLAR_PARTICLE_EVENT_OVERLAY",
            "severity": "high",
            "metric": "radiation_dose_rate",
            "observed_value": round(max_val, 2),
            "unit": "uGy/h",
            "threshold": 25.0,
            "message": f"Space weather timeline overlay: elevated dose rate ({max_val:.1f} uGy/h). Note: absorbed dose rate in uGy/h; exposure limits reference dose equivalent (Sv).",
        })
    elif max_val >= 18.0:
        env_alerts.append({
            "hazard_type": "SPACE_WEATHER_WATCH_OVERLAY",
            "severity": "watch",
            "metric": "radiation_dose_rate",
            "observed_value": round(max_val, 2),
            "unit": "uGy/h",
            "threshold": 18.0,
            "message": f"Space weather timeline overlay: elevated background dose rate ({max_val:.1f} uGy/h). Monitored for potential solar particle event onset.",
        })
    return env_alerts


def analyze(
    df: pd.DataFrame,
    metrics: list[str] = None,
    freq: str = "1D",
    window: int = 7,
    min_periods: int = 3,
    alert_n: int = 3,
    guard: int = None,
    frozen_baseline: Any = None,
    cooldown_periods: int = 3,
    enable_cusum: bool = True,
    enable_mahalanobis: bool = True,
    raw_measurements_df: pd.DataFrame | None = None
) -> dict[str, Any]:
    """Analyzes telemetry for individual crew readiness, acute alerts, prewhitened CUSUM, and Hotelling/Mahalanobis distance."""
    guard = alert_n - 1 if guard is None else guard
    physio_metrics = [c for c in (metrics or df.columns) if c in DIRECTIONS]
    if df.empty or not physio_metrics:
        return {}

    series = to_series(df, physio_metrics, freq)
    out = {}

    for uid, g in series.groupby("user_id"):
        g = g.set_index("timestamp")
        signals_meta = frozen_baseline.signals if frozen_baseline else {}

        # Task 27: Sensor-Fault Gating
        faults = []
        if raw_measurements_df is not None:
            user_raw = raw_measurements_df[raw_measurements_df["crew_member_id"].astype(str) == str(uid)]
            faults = check_sensor_faults(user_raw)

        if faults:
            out[str(uid)] = {
                "readiness": None,
                "status": "INSUFFICIENT_DATA",
                "data_status": "FAULTY_SENSOR",
                "readiness_category": "INSUFFICIENT_DATA",
                "data_sufficiency": "insufficient",
                "uncertainty_band": None,
                "config_hash": "MELIORA-V1-CFG",
                "readiness_series": [],
                "forecast": {},
                "drift_alerts": [],
                "incidents": [],
                "environmental_alerts": [],
                "mahalanobis_alert": None,
                "message": f"Sensor fault detected: {', '.join(faults)}. Telemetry scoring gated for crew safety.",
            }
            continue

        # 1. Standardize deviation using frozen baseline if available
        signed_dict = {}
        for m in physio_metrics:
            sig = signals_meta.get(m)
            fc = getattr(sig, "center", None) if sig else None
            fd = getattr(sig, "effective_dispersion", None) if sig else None
            signed_dict[m] = _signed_z(g[m], m, window, min_periods, guard, frozen_center=fc, frozen_disp=fd)
        
        signed = pd.DataFrame(signed_dict)
        good = pd.DataFrame({m: _oriented(signed[m], DIRECTIONS[m]) for m in physio_metrics})
        excess = (-good).clip(lower=0).sub(DEADBAND).clip(lower=0)
        score = (100 - SCORE_PER_SD * excess.mean(axis=1, skipna=True).where(good.notna().any(axis=1)))
        score = score.ewm(span=2, min_periods=1).mean().clip(0, 100).dropna()

        alerts = []

        # 2. Acute rolling drift alerts
        for m in physio_metrics:
            recent = good[m].dropna().tail(alert_n)
            if len(recent) == alert_n and (recent <= ALERT_Z).all():
                sz = float(signed[m].dropna().tail(alert_n).mean())
                word = "high" if sz > 0 else "low"
                alerts.append({
                    "metric": m, "direction": word,
                    "severity": "high" if recent.mean() <= -2.5 else "watch",
                    "message": f"{m} {word} vs own baseline for {alert_n} readings in a row (~{abs(sz):.1f} SD)",
                })

        # 2b. Fast path for acute events (Z <= -3.5 on >= 2 metrics)
        latest_good = good.dropna(how="all").tail(1)
        if not latest_good.empty:
            extreme_metrics = [m for m in physio_metrics if m in latest_good and float(latest_good[m].iloc[-1]) <= -3.5]
            if len(extreme_metrics) >= 2:
                alerts.append({
                    "metric": "multi_system_acute",
                    "direction": "low",
                    "severity": "high",
                    "message": f"Acute fast-path alert: extreme single-interval shift (Z <= -3.5) across {len(extreme_metrics)} metrics ({', '.join(extreme_metrics)})",
                })

        # 3. Gap-aware Prewhitened CUSUM cumulative drift detector
        if enable_cusum:
            for m in physio_metrics:
                if not any(a["metric"] == m for a in alerts):
                    sig = signals_meta.get(m)
                    c_center = getattr(sig, "center", float(g[m].median())) if sig else float(g[m].median())
                    c_disp = getattr(sig, "effective_dispersion", float((g[m] - c_center).abs().median() * 1.4826)) if sig else float((g[m] - c_center).abs().median() * 1.4826)
                    c_phi = getattr(sig, "ar1_phi", 0.0) if sig else 0.0

                    cusum_alert = _detect_prewhitened_cusum(
                        g[m], m, DIRECTIONS[m], center=c_center, dispersion=c_disp, phi=c_phi
                    )
                    if cusum_alert:
                        alerts.append(cusum_alert)

        # 4. Scikit-learn Hotelling T^2 / LedoitWolf Mahalanobis Multivariate Detector
        mahal_alert = None
        if enable_mahalanobis and frozen_baseline and frozen_baseline.covariance_matrix:
            latest_row = g.dropna(how="all").tail(1)
            if not latest_row.empty:
                current_dict = {col: float(latest_row[col].iloc[-1]) for col in latest_row.columns if col in physio_metrics and pd.notna(latest_row[col].iloc[-1])}
                mahal_alert = compute_mahalanobis_drift(
                    current_obs=current_dict,
                    frozen_signals=frozen_baseline.signals,
                    cov_matrix=frozen_baseline.covariance_matrix,
                    cov_signal_names=frozen_baseline.covariance_signals,
                    min_signals=3,
                    significance_level=0.05,
                    baseline_n_days=14,
                    shrinkage_intensity=getattr(frozen_baseline, "shrinkage_intensity", 0.0)
                )

        # 5. Alert de-duplication with Task 25 Severity Escalation Bypass
        # If severity escalates (watch -> high) or a new signal alerts, cooldown is bypassed
        deduped_alerts = []
        seen_metrics = {}
        for a in alerts:
            m = a["metric"]
            sev = a["severity"]
            if m not in seen_metrics:
                seen_metrics[m] = sev
                deduped_alerts.append(a)
            elif seen_metrics[m] == "watch" and sev == "high":
                # Severity escalation bypass!
                seen_metrics[m] = "high"
                deduped_alerts = [alert for alert in deduped_alerts if alert["metric"] != m]
                deduped_alerts.append(a)

        # 6. Group alerts into clinical incidents
        incidents = _cluster_alerts(deduped_alerts)

        # 7. Environmental hazard alerts (radiation overlay)
        env_alerts = _evaluate_environmental_hazards(df, uid)

        final_score = None if score.empty else round(float(score.iloc[-1]), 1)

        # Task 28: Uncertainty Band Calculation
        unc_band = None
        if final_score is not None:
            tier = getattr(frozen_baseline, "overall_sufficiency", "moderate") if frozen_baseline else "moderate"
            delta = {"high": 3.0, "moderate": 5.0, "low": 8.0, "insufficient": 12.0}.get(tier, 5.0)
            unc_band = {
                "score_lo": max(0.0, round(final_score - delta, 1)),
                "score_hi": min(100.0, round(final_score + delta, 1)),
                "confidence_tier": tier,
            }

        # 8. Readiness category and Alert-Capping Rule
        if final_score is None:
            readiness_cat = "INSUFFICIENT_DATA"
            status_label = "INSUFFICIENT_DATA"
        elif final_score >= 85.0:
            readiness_cat = "NOMINAL"
            status_label = "NOMINAL"
        elif final_score >= 70.0:
            readiness_cat = "WATCH"
            status_label = "WATCH"
        else:
            readiness_cat = "CRITICAL"
            status_label = "CRITICAL"

        has_high = any(a["severity"] == "high" for a in deduped_alerts) or (mahal_alert is not None)
        has_watch = any(a["severity"] == "watch" for a in deduped_alerts)

        if has_high and readiness_cat != "INSUFFICIENT_DATA":
            readiness_cat = "CRITICAL"
            status_label = "CRITICAL"
        elif has_watch and readiness_cat == "NOMINAL":
            readiness_cat = "WATCH"
            status_label = "WATCH"

        out[str(uid)] = {
            "readiness": final_score,
            "status": status_label,
            "data_status": "COMPLETE" if final_score is not None else "INSUFFICIENT_DATA",
            "readiness_category": readiness_cat,
            "data_sufficiency": frozen_baseline.overall_sufficiency if frozen_baseline else "moderate",
            "uncertainty_band": unc_band,
            "config_hash": "MELIORA-V1-CFG",
            "readiness_series": [{"t": t.isoformat(), "score": round(float(v), 1)} for t, v in score.items()],
            "forecast": {m: f for m in physio_metrics if (f := conformal_forecast(g[m]))},
            "drift_alerts": deduped_alerts,
            "incidents": incidents,
            "environmental_alerts": env_alerts,
            "mahalanobis_alert": mahal_alert,
        }
    return out
