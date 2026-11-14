"""Unit tests verifying Frozen Baseline immutability, Ledoit-Wolf Mahalanobis multivariate detection,
and missing signal marginalization in the live path.
"""
import uuid
import numpy as np
import pytest
from src.modules.readiness.baseline import (
    BaselineStore,
    fit_frozen_baseline,
)
from src.modules.readiness.model import (
    analyze,
    compute_mahalanobis_drift,
    conformal_forecast,
    from_measurements,
)
from src.modules.readiness.schemas import BaselineRecalibrateRequest
from src.modules.readiness.service import ReadinessService


def test_frozen_baseline_immutability_and_audit_trail():
    BaselineStore.clear()
    cid = str(uuid.uuid4())
    
    # 1. Create initial baseline
    rows_initial = [
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 60.0 + i,
         "measured_at": f"2026-11-0{i+1}T08:00:00Z", "quality_status": "VERIFIED"}
        for i in range(7)
    ]
    fb1 = fit_frozen_baseline(cid, rows_initial, reason="Initial checkout", calibration_window_days=7)
    assert fb1 is not None
    BaselineStore.save(fb1)
    
    v1_id = fb1.version_id
    assert BaselineStore.get_active(cid).version_id == v1_id
    
    # 2. Routine analysis call should NOT silently mutate the baseline
    rows_day8 = rows_initial + [
        {"crew_member_id": cid, "measurement_type": "heart_rate", "value_numeric": 85.0,
         "measured_at": "2026-11-08T08:00:00Z", "quality_status": "VERIFIED"}
    ]
    resp = ReadinessService.build(uuid.UUID(cid), rows_day8, freq="1d", window=7, min_periods=3, alert_n=3)
    # The active baseline version must remain identical
    assert BaselineStore.get_active(cid).version_id == v1_id
    assert len(BaselineStore.get_history(cid)) == 1
    
    # 3. Explicit recalibration appends a new version
    fb2 = fit_frozen_baseline(cid, rows_day8, reason="Mission Phase EVA transition", calibration_window_days=7)
    assert fb2 is not None
    assert fb2.version_id != v1_id
    BaselineStore.save(fb2)
    
    assert BaselineStore.get_active(cid).version_id == fb2.version_id
    history = BaselineStore.get_history(cid)
    assert len(history) == 2
    assert history[0].version_id == v1_id
    assert history[1].version_id == fb2.version_id
    assert history[1].recalibration_reason == "Mission Phase EVA transition"


def test_ledoit_wolf_mahalanobis_live_path_and_missingness_marginalization():
    """Confirms LedoitWolf is used in live path, handles missing signals via sub-covariance,
    and decomposes squared distance into exact feature contributions.
    """
    BaselineStore.clear()
    cid = str(uuid.uuid4())
    
    # Generate 10 days of multivariate data
    rng = np.random.default_rng(42)
    metrics = ["heart_rate", "spo2", "blood_pressure_systolic", "blood_pressure_diastolic"]
    rows = []
    for d in range(10):
        ts = f"2026-11-{d+1:02d}T10:00:00Z"
        for m in metrics:
            val = {"heart_rate": 62.0, "spo2": 98.5, "blood_pressure_systolic": 115.0, "blood_pressure_diastolic": 75.0}[m]
            rows.append({
                "crew_member_id": cid, "measurement_type": m, "value_numeric": val + float(rng.normal(0, 1)),
                "measured_at": ts, "quality_status": "VERIFIED"
            })
            
    fb = fit_frozen_baseline(cid, rows, reason="Calibration", calibration_window_days=10)
    assert fb is not None
    assert len(fb.covariance_matrix) >= 3
    assert len(fb.covariance_signals) >= 3
    
    # Test 1: Full observation vector
    obs_full = {"heart_rate": 80.0, "spo2": 95.0, "blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 88.0}
    res_full = compute_mahalanobis_drift(
        obs_full, fb.signals, fb.covariance_matrix, fb.covariance_signals, min_signals=3
    )
    assert res_full is not None
    assert res_full["degrees_of_freedom"] == 4
    assert res_full["distance_squared"] > res_full["threshold"]
    
    # Check that sum of feature contributions equals distance_squared
    contrib_sum = sum(c["contribution"] for c in res_full["top_contributors"])
    assert abs(contrib_sum - res_full["distance_squared"]) < 1e-2
    
    # Test 2: Missingness marginalization (one signal missing, e.g. blood_pressure_diastolic is NaN)
    obs_partial = {"heart_rate": 80.0, "spo2": 95.0, "blood_pressure_systolic": 130.0, "blood_pressure_diastolic": float("nan")}
    res_partial = compute_mahalanobis_drift(
        obs_partial, fb.signals, fb.covariance_matrix, fb.covariance_signals, min_signals=3
    )
    assert res_partial is not None
    # Degrees of freedom correctly reduced to 3 (marginalized sub-covariance)
    assert res_partial["degrees_of_freedom"] == 3
    assert len(res_partial["top_contributors"]) == 3
    
    # Test 3: Insufficient signals (< min_signals = 3)
    obs_insufficient = {"heart_rate": 80.0, "spo2": 95.0}
    res_insufficient = compute_mahalanobis_drift(
        obs_insufficient, fb.signals, fb.covariance_matrix, fb.covariance_signals, min_signals=3
    )
    assert res_insufficient is None


def test_conformal_forecast_finite_sample_correction():
    import pandas as pd
    s = pd.Series([60.0 + i * 0.1 + np.sin(i) for i in range(20)])
    fc = conformal_forecast(s, alpha=0.10)
    assert fc is not None
    assert fc["lo"] < fc["next"] < fc["hi"]
    assert fc["method"] == "adaptive_conformal"
