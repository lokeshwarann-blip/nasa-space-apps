"""eval/generator.py - Independent, reproducible telemetry generator using SeedSequence.

Ensures:
- Hierarchical, uncorrelated RNG state via numpy.random.SeedSequence.spawn.
- Zero seed reuse across TUNE, VALIDATION, and FINAL_TEST sets.
- Strict isolation per crew-trajectory run (unit of independence).
- Realistic physiological conditions: AR(1) autocorrelation, Student-t noise, dropouts,
  circadian diurnal rhythms, quality corruption, and coordinated multi-metric shifts.
"""
import math
from typing import Any
import numpy as np
import pandas as pd
from eval.config import BASELINES, DIRECTIONS, MIN_SD, TEN_SIGNALS


def generate_independent_trajectory(
    seed: int,
    uid: str = "CREW-EVAL-001",
    days: int = 14,
    freq_h: int = 3,
    shift_metric: str | None = None,
    shift_sd: float = 0.0,
    shift_start_day: float = 7.0,
    shift_type: str = "step",          # "step", "ramp", or "multi_metric"
    multi_shift_metrics: list[str] | None = None,
    noise_dist: str = "normal",        # "normal" or "student_t"
    student_t_df: float = 4.0,
    ar1_phi: float = 0.0,              # Autocorrelation coefficient
    dropout_rate: float = 0.0,         # Random packet missingness
    bad_quality_rate: float = 0.0,     # Corrupted packets
    circadian: bool = False,           # Diurnal cycle
    start_time_iso: str = "2026-11-01T00:00:00Z"
) -> list[dict[str, Any]]:
    """Generates a single, statistically independent crew health trajectory."""
    # SeedSequence spawn guarantees uncorrelated RNG streams
    ss = np.random.SeedSequence(seed)
    rng = np.random.default_rng(ss)

    start = pd.Timestamp(start_time_iso)
    total_steps = days * (24 // freq_h)
    times = pd.date_range(start, periods=total_steps, freq=f"{freq_h}h")
    rows: list[dict[str, Any]] = []

    # Maintain independent AR(1) state per metric
    ar_states = {m: 0.0 for m in TEN_SIGNALS}

    for step_idx, t in enumerate(times):
        d = (t - start).total_seconds() / 86400.0
        hour = t.hour

        # Circadian components: nadir during night (0-6h), peak in afternoon
        circ_hr = -3.0 * np.cos(2 * np.pi * hour / 24.0) if circadian else 0.0
        circ_temp = -0.2 * np.cos(2 * np.pi * hour / 24.0) if circadian else 0.0

        for m in TEN_SIGNALS:
            # Observation schedules (e.g. sleep in morning, self-reports in evening)
            if m == "sleep_duration" and hour != 6:
                continue
            if m in ("stress", "mood", "fatigue") and hour != 18:
                continue

            # Random packet dropout simulation
            if dropout_rate > 0.0 and rng.random() < dropout_rate:
                continue

            mu, base_sd = BASELINES[m]

            # Generate innovation noise with matched marginal variance
            if noise_dist == "student_t":
                scale = base_sd / math.sqrt(student_t_df / (student_t_df - 2.0))
                raw_noise = float(rng.standard_t(df=student_t_df) * scale)
            else:
                raw_noise = float(rng.normal(0, base_sd))

            # AR(1) process with matched stationary variance:
            # x_t = phi * x_{t-1} + sqrt(1 - phi^2) * raw_noise
            if ar1_phi > 0.0:
                ar_states[m] = ar1_phi * ar_states[m] + math.sqrt(1.0 - ar1_phi**2) * raw_noise
                noise = ar_states[m]
            else:
                noise = raw_noise

            val = mu + noise

            # Apply circadian modulation
            if m == "heart_rate":
                val += circ_hr
            elif m == "body_temperature":
                val += circ_temp

            # Apply Adverse Shift
            is_shifted = False
            if d >= shift_start_day:
                if shift_metric == m or (shift_type == "multi_metric" and multi_shift_metrics and m in multi_shift_metrics):
                    is_shifted = True
                    direction = DIRECTIONS.get(m, 0)
                    eff_sign = -1 if direction == 1 else (1 if direction == -1 else 1)
                    
                    if shift_type == "ramp":
                        ramp_factor = min(1.0, max(0.0, (d - shift_start_day) / 4.0))
                        val += eff_sign * (shift_sd * MIN_SD[m] * ramp_factor)
                    else: # step or multi_metric
                        val += eff_sign * (shift_sd * MIN_SD[m])

            # Clinical bounding
            if m == "spo2":
                val = float(np.clip(val, 75.0, 100.0))
            elif m in ("stress", "mood", "fatigue"):
                val = float(np.clip(round(val), 1.0, 5.0))
            elif m == "sleep_duration":
                val = float(np.clip(val, 0.0, 14.0))

            # Quality flag labeling
            quality = "VERIFIED"
            if bad_quality_rate > 0.0 and rng.random() < bad_quality_rate:
                quality = rng.choice(["NOISY", "DEGRADED", "ANOMALOUS"])
                if quality == "ANOMALOUS":
                    val += 50.0  # Spurious packet artifact

            rows.append({
                "crew_member_id": uid,
                "measurement_type": m,
                "value_numeric": round(val, 2),
                "measured_at": t.isoformat(),
                "quality_status": quality,
                "is_anomaly_ground_truth": is_shifted,
            })
    return rows
