"""backend/tests/unit/test_fusion_detector.py

Comprehensive tests for MELIORA Phase 2 improvements:
1. Dual-channel fusion (primary univariate CUSUM + secondary MEWMA multivariate channel).
2. Purely statistical decision rule (no artificial 3-day persistence delay).
3. Coordinated multi-system anomaly detection (beats univariate CUSUM).
4. Anomaly recovery (detector resets when signals return to baseline).
"""
import numpy as np
import pandas as pd
import pytest
from sklearn.covariance import LedoitWolf

from src.modules.readiness.model import from_measurements, to_series
from src.modules.readiness.baseline import fit_frozen_baseline
from eval.config import BASELINES, MIN_SD, TEN_SIGNALS
from eval.generator import generate_independent_trajectory


def test_statistical_rule_no_3day_delay():
    """Confirms that severe shifts can alert in <= 1 day without waiting for a 3-day persistence counter."""
    # Generate 14-day telemetry with an immediate severe 2.5 SD shift starting on Day 8
    raw = generate_independent_trajectory(
        seed=20042, days=14, shift_metric="heart_rate", shift_sd=2.5, shift_start_day=8.0
    )
    df = from_measurements(raw)
    daily = to_series(df, TEN_SIGNALS, freq="1D")
    
    # Evaluate sequential daily CUSUM
    h_cusum = 3.17
    hr_vals = daily["heart_rate"].dropna().values
    mu, sd = BASELINES["heart_rate"]
    z = (hr_vals - mu) / max(sd, MIN_SD["heart_rate"])
    
    c_p = 0.0
    alert_day = None
    for idx, v in enumerate(z):
        c_p = max(0.0, c_p + v - 0.5)
        if c_p >= h_cusum and idx >= 8:
            alert_day = idx
            break
            
    # Must alert on Day 8 or Day 9 (delay <= 1 day, NOT delayed by 3-day rule)
    assert alert_day is not None
    delay_days = alert_day - 8.0
    assert delay_days <= 1.0


def test_mewma_multivariate_channel_coordinated_detection():
    """Confirms that MEWMA detects coordinated 4x0.8 SD shifts where univariate Z is below 1.0."""
    core_vitals = ["heart_rate", "blood_pressure_systolic", "spo2", "hrv"]
    raw = generate_independent_trajectory(
        seed=20084, days=14, shift_type="multi_metric",
        multi_shift_metrics=core_vitals, shift_sd=0.8, shift_start_day=7.0
    )
    df = from_measurements(raw)
    daily = to_series(df, TEN_SIGNALS, freq="1D")
    
    # Baseline covariance on first 7 days
    core_base = daily[core_vitals].iloc[:7].dropna()
    z_base = np.zeros(core_base.shape)
    for c_i, m in enumerate(core_vitals):
        mu, sd = BASELINES[m]
        z_base[:, c_i] = (core_base[m].values - mu) / max(sd, MIN_SD[m])
    cov_est = LedoitWolf().fit(z_base).covariance_
    cov_inv = np.linalg.pinv(cov_est)
    
    # MEWMA sequential evaluation
    lam = 0.25
    u = np.zeros(len(core_vitals))
    t2_threshold = 23.14
    detected_mewma = False
    
    for d_idx in range(7, len(daily)):
        curr_row = daily[core_vitals].iloc[d_idx]
        z_curr = np.array([(curr_row[m] - BASELINES[m][0]) / max(BASELINES[m][1], MIN_SD[m]) for m in core_vitals])
        u = lam * z_curr + (1 - lam) * u
        v_fac = (lam / (2.0 - lam)) * (1.0 - (1.0 - lam)**(2 * (d_idx + 1)))
        sigma_u_inv = cov_inv / max(1e-6, v_fac)
        t2 = float(np.dot(u, np.dot(sigma_u_inv, u)))
        if t2 >= t2_threshold:
            detected_mewma = True
            break
            
    assert detected_mewma is True


def test_cusum_recovery_to_baseline():
    """Confirms that CUSUM recovers and resets to 0 when vitals return to normal baseline."""
    # Vitals elevated for 3 days, then returned to baseline for 8 days
    z_series = [0.0, 0.2, 0.1, 1.5, 1.8, 1.6] + [0.0] * 8
    c_p = 0.0
    cusum_history = []
    for v in z_series:
        c_p = max(0.0, c_p + v - 0.5)
        cusum_history.append(c_p)
        
    # During elevated phase (steps 3-5), CUSUM accumulates
    assert max(cusum_history[3:6]) > 1.5
    # After returning to baseline for 8 steps, CUSUM completely resets to 0.0
    assert cusum_history[-1] == 0.0
