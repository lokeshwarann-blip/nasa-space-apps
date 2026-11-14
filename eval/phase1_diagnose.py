"""eval/phase1_diagnose.py - Phase 1 Diagnosis and Systematic Ablation Suite.

Evaluates on VALIDATION_SEEDS (20000-20999) at matched FAR ~0.10:
1. Benchmark: Per-signal CUSUM (primary target to beat)
2. Baseline MELIORA
3. Ablation 1: No prewhitening (raw standardized z-score into CUSUM)
4. Ablation 2: No persistence rule (no 3-day consecutive requirement, no 4-period CUSUM gate)
5. Ablation 3: No MAD scaling (use sample standard deviation instead of 1.4826 * MAD)
6. Ablation 4: No alert cooldown (no 3-day suppression window)
7. Ablation 5: No incident grouping (raw signal alerts vs composite clusters)

Logs every iteration to eval/results/iteration_log.csv.
"""
from pathlib import Path
import math
import numpy as np
import pandas as pd
from eval.config import (
    BASELINES,
    CONFIG_YAML_PATH,
    DIRECTIONS,
    MIN_SD,
    RESULTS_DIR,
    TEN_SIGNALS,
    TUNE_SEEDS,
    VALIDATION_SEEDS,
)
from eval.generator import generate_independent_trajectory
from backend.src.modules.readiness.baseline import fit_frozen_baseline
from backend.src.modules.readiness.model import (
    analyze,
    compute_mahalanobis_drift,
    from_measurements,
    to_series,
    _signed_z,
    _oriented,
)

ITERATION_LOG_PATH = RESULTS_DIR / "iteration_log.csv"


def calibrate_threshold(method_name: str, tune_seeds: list[int], target_far: float = 0.10) -> float:
    """Calibrate detector threshold on TUNE_SEEDS to hit target FAR ~0.10."""
    scores = []
    for seed in tune_seeds:
        raw = generate_independent_trajectory(seed=seed, days=14, ar1_phi=0.3)
        df = from_measurements(raw)
        daily = to_series(df, TEN_SIGNALS, freq="1D")

        if method_name == "per_signal_cusum":
            max_c = 0.0
            for m in TEN_SIGNALS:
                if m not in daily.columns:
                    continue
                vals = daily[m].dropna().values
                mu, sd = BASELINES[m]
                z = (vals - mu) / max(sd, MIN_SD[m])
                c_p, c_m = 0.0, 0.0
                for v in z:
                    c_p = max(0.0, c_p + v - 0.5)
                    c_m = max(0.0, c_m - v - 0.5)
                    max_c = max(max_c, c_p, c_m)
            scores.append(max_c)

        elif method_name in ("baseline_meliora", "ablate_prewhitening", "ablate_persistence",
                             "ablate_mad", "ablate_cooldown", "ablate_grouping"):
            # Use calibration window for baseline
            fb = fit_frozen_baseline("TUNE", raw, calibration_window_days=7)
            # Evaluate maximum CUSUM or deviation
            max_score = 0.0
            for m in TEN_SIGNALS:
                if m not in daily.columns:
                    continue
                vals = daily[m].dropna().values
                sig = fb.signals.get(m)
                center = sig.center if sig else BASELINES[m][0]
                if method_name == "ablate_mad":
                    m_raw = [r["value_numeric"] for r in raw[:len(raw)//2] if r["measurement_type"] == m]
                    disp = float(np.std(m_raw, ddof=1)) if len(m_raw) > 2 else BASELINES[m][1]
                else:
                    disp = sig.effective_dispersion if sig else BASELINES[m][1]
                phi = sig.ar1_phi if (sig and "ablate_prewhitening" not in method_name) else 0.0

                z = (vals - center) / max(disp, MIN_SD[m])
                c_p, c_m = 0.0, 0.0
                for idx, v in enumerate(z):
                    if idx > 0 and phi > 0.0:
                        e = (v - phi * z[idx - 1]) / np.sqrt(max(0.01, 1.0 - phi**2))
                    else:
                        e = v
                    c_p = max(0.0, c_p + e - 0.5)
                    c_m = max(0.0, c_m - e - 0.5)
                    max_score = max(max_score, c_p, c_m)
            scores.append(max_score)

    thresh = float(np.quantile(scores, 1.0 - target_far))
    return thresh


def evaluate_detector(
    method_name: str,
    threshold: float,
    val_seeds: list[int],
) -> dict:
    """Evaluates a detector configuration across all required benchmark conditions on VALIDATION_SEEDS."""
    n_runs = len(val_seeds)
    scenarios = [
        ("null", {}),
        ("0.5_sd", {"shift_metric": "heart_rate", "shift_sd": 0.5, "shift_start_day": 7.0}),
        ("1.0_sd", {"shift_metric": "heart_rate", "shift_sd": 1.0, "shift_start_day": 7.0}),
        ("2.0_sd", {"shift_metric": "heart_rate", "shift_sd": 2.0, "shift_start_day": 7.0}),
        ("coord_4x08", {"shift_type": "multi_metric", "multi_shift_metrics": ["heart_rate", "blood_pressure_systolic", "spo2", "hrv"], "shift_sd": 0.8, "shift_start_day": 7.0}),
        ("ramp_1.5", {"shift_type": "ramp", "shift_metric": "heart_rate", "shift_sd": 1.5, "shift_start_day": 7.0}),
        ("misspec_null", {"noise_dist": "student_t", "student_t_df": 3.0, "circadian": True}),
    ]

    results = {}
    delays_1sd = []

    for sc_name, sc_kwargs in scenarios:
        alert_count = 0
        delays = []

        for s_idx, seed in enumerate(val_seeds):
            uid = f"VAL-{s_idx}"
            raw = generate_independent_trajectory(seed=seed, uid=uid, days=14, ar1_phi=0.3, **sc_kwargs)
            df = from_measurements(raw)
            daily = to_series(df, TEN_SIGNALS, freq="1D")

            # Check sequential alerting
            earliest_alert_day = None
            triggered = False

            # Frozen baseline fitted on first 7 days
            fb = fit_frozen_baseline(uid, raw, calibration_window_days=7)
            if "ablate_mad" in method_name:
                # Ablation 3: sample standard deviation instead of MAD
                for m, sig in fb.signals.items():
                    m_raw = [r["value_numeric"] for r in raw[:len(raw)//2] if r["measurement_type"] == m]
                    s_std = float(np.std(m_raw, ddof=1)) if len(m_raw) > 2 else sig.effective_dispersion
                    sig.effective_dispersion = max(s_std, MIN_SD.get(m, 1.0))

            for d_idx in range(len(daily)):
                sub = daily.iloc[:d_idx + 1]
                day_num = d_idx

                if method_name == "per_signal_cusum":
                    # Standalone Per-Signal CUSUM across all 10 signals
                    for m in TEN_SIGNALS:
                        if m not in sub.columns:
                            continue
                        vals = sub[m].dropna().values
                        mu, sd = BASELINES[m]
                        z = (vals - mu) / max(sd, MIN_SD[m])
                        c_p, c_m = 0.0, 0.0
                        for v in z:
                            c_p = max(0.0, c_p + v - 0.5)
                            c_m = max(0.0, c_m - v - 0.5)
                        if c_p >= threshold or c_m >= threshold:
                            triggered = True
                            earliest_alert_day = day_num
                            break

                elif method_name in ("baseline_meliora", "ablate_cooldown", "ablate_grouping"):
                    # Baseline MELIORA & variants
                    for m in TEN_SIGNALS:
                        if m not in sub.columns:
                            continue
                        vals = sub[m].dropna().values
                        if len(vals) < 4:  # min_periods = 4
                            continue
                        sig = fb.signals.get(m)
                        center = sig.center if sig else BASELINES[m][0]
                        disp = sig.effective_dispersion if sig else BASELINES[m][1]
                        phi = sig.ar1_phi if sig else 0.0

                        z = (vals - center) / max(disp, MIN_SD[m])
                        scale = np.sqrt(max(0.01, 1.0 - phi**2))
                        c_pos = 0.0
                        accum_cnt = 0
                        for idx, v in enumerate(z):
                            e = (v - phi * z[idx - 1]) / scale if idx > 0 else v
                            defic = -(-e) - 0.5 if DIRECTIONS.get(m, 0) == 1 else (e - 0.5)
                            if defic > 0:
                                c_pos += defic
                                accum_cnt += 1
                            else:
                                c_pos = max(0.0, c_pos + defic)
                                if c_pos == 0:
                                    accum_cnt = 0
                        if c_pos >= threshold and accum_cnt >= 4:
                            triggered = True
                            earliest_alert_day = day_num
                            break

                    # Also acute alert (3-day persistence rule)
                    for m in TEN_SIGNALS:
                        if m not in sub.columns:
                            continue
                        vals = sub[m].dropna().values
                        if len(vals) >= 3:
                            recent_3 = vals[-3:]
                            sig = fb.signals.get(m)
                            center = sig.center if sig else BASELINES[m][0]
                            disp = sig.effective_dispersion if sig else BASELINES[m][1]
                            z_recent = (recent_3 - center) / max(disp, MIN_SD[m])
                            if (z_recent >= 2.0).all() or (z_recent <= -2.0).all():
                                triggered = True
                                earliest_alert_day = day_num
                                break

                elif method_name == "ablate_prewhitening":
                    # Ablation 1: No prewhitening (phi = 0.0)
                    for m in TEN_SIGNALS:
                        if m not in sub.columns:
                            continue
                        vals = sub[m].dropna().values
                        sig = fb.signals.get(m)
                        center = sig.center if sig else BASELINES[m][0]
                        disp = sig.effective_dispersion if sig else BASELINES[m][1]
                        z = (vals - center) / max(disp, MIN_SD[m])
                        c_pos, c_neg = 0.0, 0.0
                        accum_cnt = 0
                        for v in z:
                            c_pos = max(0.0, c_pos + v - 0.5)
                            c_neg = max(0.0, c_neg - v - 0.5)
                            if c_pos > 0 or c_neg > 0:
                                accum_cnt += 1
                            else:
                                accum_cnt = 0
                        if (c_pos >= threshold or c_neg >= threshold) and accum_cnt >= 4:
                            triggered = True
                            earliest_alert_day = day_num
                            break

                elif method_name == "ablate_persistence":
                    # Ablation 2: No persistence rule (alert immediately when two-sided CUSUM crosses threshold)
                    for m in TEN_SIGNALS:
                        if m not in sub.columns:
                            continue
                        vals = sub[m].dropna().values
                        sig = fb.signals.get(m)
                        center = sig.center if sig else BASELINES[m][0]
                        disp = sig.effective_dispersion if sig else BASELINES[m][1]
                        phi = sig.ar1_phi if sig else 0.0
                        z = (vals - center) / max(disp, MIN_SD[m])
                        scale = np.sqrt(max(0.01, 1.0 - phi**2))
                        c_pos = 0.0
                        c_neg = 0.0
                        for idx, v in enumerate(z):
                            e = (v - phi * z[idx - 1]) / scale if idx > 0 else v
                            c_pos = max(0.0, c_pos + e - 0.5)
                            c_neg = max(0.0, c_neg - e - 0.5)
                        if c_pos >= threshold or c_neg >= threshold:
                            triggered = True
                            earliest_alert_day = day_num
                            break

                elif method_name == "ablate_mad":
                    # Ablation 3: No MAD scaling (dispersion is sample standard deviation)
                    for m in TEN_SIGNALS:
                        if m not in sub.columns:
                            continue
                        vals = sub[m].dropna().values
                        sig = fb.signals.get(m)
                        center = sig.center if sig else BASELINES[m][0]
                        disp = sig.effective_dispersion if sig else BASELINES[m][1]
                        phi = sig.ar1_phi if sig else 0.0
                        z = (vals - center) / max(disp, MIN_SD[m])
                        scale = np.sqrt(max(0.01, 1.0 - phi**2))
                        c_pos = 0.0
                        accum_cnt = 0
                        for idx, v in enumerate(z):
                            e = (v - phi * z[idx - 1]) / scale if idx > 0 else v
                            defic = abs(e) - 0.5
                            if defic > 0:
                                c_pos += defic
                                accum_cnt += 1
                            else:
                                c_pos = max(0.0, c_pos + defic)
                                if c_pos == 0:
                                    accum_cnt = 0
                        if c_pos >= threshold and accum_cnt >= 4:
                            triggered = True
                            earliest_alert_day = day_num
                            break

                if triggered:
                    break

            if "null" in sc_name:
                if triggered:
                    alert_count += 1
            else:
                if triggered and earliest_alert_day is not None and earliest_alert_day >= 7:
                    alert_count += 1
                    delays.append(earliest_alert_day - 7.0)

        rate = alert_count / float(n_runs)
        results[sc_name] = rate
        if sc_name == "1.0_sd":
            delays_1sd = delays

    med_delay = float(np.median(delays_1sd)) if delays_1sd else 0.0
    return {
        "far_achieved": round(results["null"], 3),
        "det_0_5_sd": round(results["0.5_sd"] * 100, 1),
        "det_1_0_sd": round(results["1.0_sd"] * 100, 1),
        "det_2_0_sd": round(results["2.0_sd"] * 100, 1),
        "det_coord_4x08": round(results["coord_4x08"] * 100, 1),
        "median_delay": round(med_delay, 1),
        "det_ramp": round(results["ramp_1.5"] * 100, 1),
        "misspecified_null_far": round(results["misspec_null"], 3),
    }


def main():
    print("=" * 80)
    print("PHASE 1: DIAGNOSE & SYSTEMATIC ABLATION ON VALIDATION_SEEDS")
    print(f"Target FAR: 0.10 (+/- 0.03). Evaluating {len(VALIDATION_SEEDS[:50])} validation runs.")
    print("=" * 80)

    tune_seeds = TUNE_SEEDS[:50]
    val_seeds = VALIDATION_SEEDS[:50]

    methods = [
        ("Benchmark: Per-Signal CUSUM", "per_signal_cusum", "BENCHMARK_TARGET"),
        ("Baseline MELIORA", "baseline_meliora", "BASELINE"),
        ("Ablation 1: No Prewhitening (Raw CUSUM)", "ablate_prewhitening", "INVESTIGATE"),
        ("Ablation 2: No Persistence Rule (No min periods)", "ablate_persistence", "INVESTIGATE"),
        ("Ablation 3: No MAD Scaling (Sample StdDev)", "ablate_mad", "INVESTIGATE"),
        ("Ablation 4: No Cooldown (Raw Alerts)", "ablate_cooldown", "INVESTIGATE"),
        ("Ablation 5: No Incident Grouping", "ablate_grouping", "INVESTIGATE"),
    ]

    log_rows = []

    for label, method_key, initial_decision in methods:
        thresh = calibrate_threshold(method_key, tune_seeds, target_far=0.10)
        res = evaluate_detector(method_key, thresh, val_seeds)
        print(f"\n[{label}] (Threshold: {thresh:.2f})", flush=True)
        print(f"  • FAR Achieved:        {res['far_achieved']:.3f}", flush=True)
        print(f"  • Detection 0.5 SD:    {res['det_0_5_sd']:.1f}%", flush=True)
        print(f"  • Detection 1.0 SD:    {res['det_1_0_sd']:.1f}%", flush=True)
        print(f"  • Detection 2.0 SD:    {res['det_2_0_sd']:.1f}%", flush=True)
        print(f"  • Coordinated 4x0.8 SD:{res['det_coord_4x08']:.1f}%", flush=True)
        print(f"  • Median Delay:        {res['median_delay']:.1f} days", flush=True)
        print(f"  • Ramp Shift Detection:{res['det_ramp']:.1f}%", flush=True)
        print(f"  • Misspecified Null FAR:{res['misspecified_null_far']:.3f}", flush=True)

        log_rows.append({
            "change": label,
            "far_achieved": res["far_achieved"],
            "det_0_5_sd": res["det_0_5_sd"],
            "det_1_0_sd": res["det_1_0_sd"],
            "det_2_0_sd": res["det_2_0_sd"],
            "det_coord_4x08": res["det_coord_4x08"],
            "median_delay": res["median_delay"],
            "det_ramp": res["det_ramp"],
            "misspecified_null_far": res["misspecified_null_far"],
            "decision": initial_decision,
        })

    df_log = pd.DataFrame(log_rows)
    df_log.to_csv(ITERATION_LOG_PATH, index=False)
    print(f"\nSaved Iteration Log: {ITERATION_LOG_PATH}")


if __name__ == "__main__":
    main()
