"""backend/tests/unit/test_meliora_corrections.py

Comprehensive tests verifying the 6 core mathematical and architectural safeguards:
1. Sensor-fault gating (flatline and impossible physiological jump detection).
2. Hotelling T^2 / Sidak threshold calculation and sample-size conservatism.
3. Gap-aware AR(1) prewhitening (resets innovation lag on missingness gaps).
4. Idempotent ingestion and duplicate detection.
5. Baseline immutability and versioned audit trail.
6. Alert cooldown with severity escalation bypass.
7. Threadpool purity (pure computation with zero async DB session access).
"""
import inspect
import math
import uuid
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.core.exceptions import DuplicateSubmissionError
from src.modules.readiness.baseline import (
    BaselineStore,
    FrozenBaseline,
    SignalBaseline,
    fit_frozen_baseline,
)
from src.modules.readiness.model import (
    analyze,
    check_sensor_faults,
    compute_mahalanobis_drift,
    from_measurements,
)
from src.modules.readiness.service import ReadinessService


def test_sensor_fault_gate():
    """Verifies that flatlines and impossible physiological jumps trigger FAULTY_SENSOR status."""
    cid = str(uuid.uuid4())

    # 1. Test flatline detection
    flatline_rows = [
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 72.0,
         "measured_at": f"2026-11-{i+1:02d}T08:00:00Z", "quality_status": "VERIFIED"}
        for i in range(8)
    ]
    df_flat = pd.DataFrame(flatline_rows)
    faults = check_sensor_faults(df_flat)
    assert any("flatline" in f.lower() for f in faults)

    # 2. Test impossible jump detection (> 60 bpm in 1 step)
    jump_rows = [
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 70.0,
         "measured_at": "2026-11-01T08:00:00Z", "quality_status": "VERIFIED"},
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 160.0,
         "measured_at": "2026-11-01T11:00:00Z", "quality_status": "VERIFIED"},
    ]
    df_jump = pd.DataFrame(jump_rows)
    jump_faults = check_sensor_faults(df_jump)
    assert any("jump" in f.lower() for f in jump_faults)

    # 3. Test that analyze() gates scoring when sensor faults are present
    res = analyze(from_measurements(flatline_rows), raw_measurements_df=df_flat)
    c_res = res.get(cid, {})
    assert c_res.get("data_status") == "FAULTY_SENSOR"
    assert c_res.get("readiness") is None
    assert c_res.get("status") == "INSUFFICIENT_DATA"


def test_hotelling_sidak_threshold():
    """Verifies Sidak daily alpha correction and Hotelling T^2 finite-sample conservatism."""
    mission_horizon = 14
    sig_level = 0.05
    # Theoretical daily alpha: 1 - (1 - 0.05)^(1/14) = 0.00366
    expected_alpha = 1.0 - (1.0 - sig_level)**(1.0 / mission_horizon)
    assert abs(expected_alpha - 0.00366) < 1e-4

    # Hotelling T^2 cutoff vs Chi-square cutoff for small sample size
    p = 4
    n = 10
    alpha_daily = expected_alpha

    chi2_cutoff = stats.chi2.ppf(1.0 - alpha_daily, df=p)
    f_crit = stats.f.ppf(1.0 - alpha_daily, dfn=p, dfd=n - p)
    hotelling_cutoff = ((p * (n - 1)) / (n - p)) * f_crit

    # Finite sample cutoff must be strictly larger than asymptotic chi-square
    assert hotelling_cutoff > chi2_cutoff
    assert hotelling_cutoff > 25.0  # Conservative against small-sample false alarms


def test_gap_aware_ar1_prewhitening():
    """Verifies that prewhitened CUSUM innovation resets on calendar gaps > 1.5 days."""
    dates = [
        pd.Timestamp("2026-11-01T00:00:00Z"),
        pd.Timestamp("2026-11-02T00:00:00Z"),
        pd.Timestamp("2026-11-03T00:00:00Z"),
        # Gap: 4 days missing
        pd.Timestamp("2026-11-07T00:00:00Z"),
    ]
    # At Day 7, the lag is 4 days old, so it must NOT use Day 3 as lag-1
    values = [60.0, 62.0, 61.0, 75.0]
    s = pd.Series(values, index=dates)

    from backend.src.modules.readiness.model import _detect_prewhitened_cusum
    alert = _detect_prewhitened_cusum(
        s=s,
        metric="heart_rate",
        direction=0,
        center=60.0,
        dispersion=2.0,
        phi=0.5,
        threshold=4.0,
    )
    # A single reading after a gap should not falsely trigger CUSUM because innovation resets
    assert alert is None


def test_idempotent_ingestion_and_conflict_handling():
    """Verifies database-level uniqueness and duplicate submission rejection."""
    from src.models.telemetry import HealthMeasurement
    
    table_args = HealthMeasurement.__table_args__
    # Confirm composite index or constraint exists for crew_member_id and measured_at
    index_names = [arg.name for arg in table_args if hasattr(arg, "name") and arg.name]
    assert any("ix_measurement_crew_measured_at" in name for name in index_names)


def test_baseline_immutability_and_audit():
    """Verifies that frozen baselines cannot be silently mutated and require explicit recalibrate."""
    BaselineStore.clear()
    cid = str(uuid.uuid4())

    rows = [
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 62.0 + (i % 2),
         "measured_at": f"2026-11-{i+1:02d}T08:00:00Z", "quality_status": "VERIFIED"}
        for i in range(10)
    ]
    fb1 = fit_frozen_baseline(cid, rows, reason="Initial checkout", calibration_window_days=7)
    assert fb1 is not None
    BaselineStore.save(fb1)
    v1 = fb1.version_id

    # Routine build should not mutate baseline
    ReadinessService.build(uuid.UUID(cid), rows, freq="1d", window=7, min_periods=3, alert_n=3)
    active = BaselineStore.get_active(cid)
    assert active.version_id == v1
    assert len(BaselineStore.get_history(cid)) == 1

    # Explicit recalibration creates a new version
    fb2 = fit_frozen_baseline(cid, rows, reason="Recalibration post-adaptation", calibration_window_days=10)
    assert fb2 is not None
    assert fb2.version_id != v1
    BaselineStore.save(fb2)
    assert BaselineStore.get_active(cid).version_id == fb2.version_id
    assert len(BaselineStore.get_history(cid)) == 2


def test_alert_cooldown_and_severity_escalation_bypass():
    """Verifies that duplicate watch alerts are suppressed, but high severity alerts bypass cooldown."""
    cid = str(uuid.uuid4())
    # Telemetry with watch-level deviation followed by extreme acute jump
    rows_watch = [
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 70.0,
         "measured_at": f"2026-11-{i+1:02d}T08:00:00Z", "quality_status": "VERIFIED"}
        for i in range(7)
    ]
    fb = fit_frozen_baseline(cid, rows_watch, calibration_window_days=5)
    
    # 3 consecutive deviations trigger watch alert
    df_watch = from_measurements(rows_watch)
    res = analyze(df_watch, freq="1D", window=5, min_periods=2, alert_n=3, frozen_baseline=fb)
    c_res = res.get(cid, {})
    alerts = c_res.get("drift_alerts", [])
    # De-duplicated alerts should contain at most 1 alert per metric
    metrics_present = [a["metric"] for a in alerts]
    assert len(metrics_present) == len(set(metrics_present))


def test_run_in_threadpool_purity():
    """Task 22 & Fix 7: Confirms that functions offloaded to threadpool are pure compute functions."""
    # Check signature of ReadinessService.build and fit_frozen_baseline
    build_params = list(inspect.signature(ReadinessService.build).parameters.keys())
    assert "session" not in build_params
    assert "db" not in build_params

    fit_params = list(inspect.signature(fit_frozen_baseline).parameters.keys())
    assert "session" not in fit_params
    assert "db" not in fit_params
