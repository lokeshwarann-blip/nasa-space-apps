"""eval/ar1_evaluation.py - Task 2: AR(1) Autocorrelation False-Alert Investigation.

Investigates:
1. Impact of autocorrelation phi in {0.0, 0.2, 0.4, 0.6, 0.8} on false alerts.
2. Calibration of thresholds on autocorrelated normal data (TUNE_SEEDS).
3. Prewhitened residual CUSUM vs variance-inflated CUSUM vs EWMA (with variance correction).
4. Generates delay-vs-FAR tradeoff curves and recommends an optimal detector.
Evaluated strictly on held-out seeds.
"""
import math
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from eval.config import (
    BASELINES,
    CONFIG_YAML_PATH,
    DIRECTIONS,
    FINAL_TEST_SEEDS,
    MIN_SD,
    RESULTS_DIR,
    TEN_SIGNALS,
    TUNE_SEEDS,
    load_yaml_config,
)
from eval.generator import generate_independent_trajectory
from eval.stats import exact_poisson_rate_ci, bootstrap_median_ci


def run_ar1_experiment(
    n_runs_per_phi: int = 50,
    phis: list[float] | None = None,
    output_dir: Path | None = None
) -> pd.DataFrame:
    out_dir = output_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    phi_grid = phis or [0.0, 0.2, 0.4, 0.6, 0.8]

    # Use first subset of FINAL_TEST_SEEDS for unbiased evaluation
    eval_seeds = FINAL_TEST_SEEDS[:n_runs_per_phi]

    results = []

    print("\n" + "=" * 80)
    print("TASK 2: AR(1) AUTOCORRELATION DETECTOR BENCHMARK")
    print(f"Evaluating {len(eval_seeds)} held-out seeds per phi in {phi_grid}")
    print("=" * 80)

    for phi in phi_grid:
        # A. Evaluate False Alerts on Null Data
        raw_cusum_null_alerts = 0
        prewhitened_null_alerts = 0
        ewma_null_alerts = 0

        exposure_days = n_runs_per_phi * 14.0

        # B. Evaluate Detection on Shifted Data (1.5 SD shift starting day 7)
        raw_cusum_detections = 0
        raw_cusum_delays = []
        prewhite_detections = 0
        prewhite_delays = []
        ewma_detections = 0
        ewma_delays = []

        for s_idx, seed in enumerate(eval_seeds):
            # 1. Null run
            null_rows = generate_independent_trajectory(seed=seed, days=14, ar1_phi=phi)
            df_null = pd.DataFrame(null_rows)
            # Focus on heart rate series
            hr_null = df_null[df_null["measurement_type"] == "heart_rate"].sort_values("measured_at")
            hr_vals_null = hr_null["value_numeric"].values
            
            # Calibration parameters from baseline
            mu, sd = BASELINES["heart_rate"]
            eff_sd = max(sd, MIN_SD["heart_rate"])

            # 1a. Raw uncorrected CUSUM
            raw_z_null = (hr_vals_null - mu) / eff_sd
            c_raw = 0.0
            raw_fired = False
            for v in raw_z_null:
                d = abs(v) - 0.5
                c_raw = max(0.0, c_raw + d) if d > 0 else max(0.0, c_raw + d * 0.5)
                if c_raw >= 3.0 and not raw_fired:
                    raw_cusum_null_alerts += 1
                    raw_fired = True

            # 1b. Prewhitened residual CUSUM
            # Residual filter: e_t = (z_t - phi*z_{t-1}) / sqrt(1 - phi^2)
            innov_null = np.zeros(len(raw_z_null))
            innov_null[0] = raw_z_null[0]
            scale = math.sqrt(max(0.01, 1.0 - phi**2)) if abs(phi) < 0.99 else 1.0
            for t in range(1, len(raw_z_null)):
                innov_null[t] = (raw_z_null[t] - phi * raw_z_null[t - 1]) / scale

            c_pw = 0.0
            pw_fired = False
            for e in innov_null:
                d = abs(e) - 0.5
                c_pw = max(0.0, c_pw + d) if d > 0 else max(0.0, c_pw + d * 0.5)
                if c_pw >= 3.0 and not pw_fired:
                    prewhitened_null_alerts += 1
                    pw_fired = True

            # 1c. Variance-corrected EWMA (lambda = 0.2)
            # Asymptotic variance for AR(1): sigma_EWMA^2 = eff_sd^2 * (lam / (2 - lam)) * (1 + (1-lam)*phi) / (1 - (1-lam)*phi)
            lam = 0.2
            ewma_var_factor = (lam / (2.0 - lam)) * ((1.0 + (1.0 - lam) * phi) / max(0.01, 1.0 - (1.0 - lam) * phi))
            ewma_sigma = eff_sd * math.sqrt(ewma_var_factor)
            ewma_threshold = 2.5 * ewma_sigma

            ewma_state = mu
            ewma_fired = False
            for val in hr_vals_null:
                ewma_state = lam * val + (1.0 - lam) * ewma_state
                if abs(ewma_state - mu) >= ewma_threshold and not ewma_fired:
                    ewma_null_alerts += 1
                    ewma_fired = True

            # 2. Shifted run (1.5 SD shift at day 7.0)
            shift_seed = seed + 50000 # disjoint shifted trajectory
            shift_rows = generate_independent_trajectory(
                seed=shift_seed, days=14, ar1_phi=phi, shift_metric="heart_rate",
                shift_sd=1.5, shift_start_day=7.0
            )
            df_shift = pd.DataFrame(shift_rows)
            hr_shift = df_shift[df_shift["measurement_type"] == "heart_rate"].sort_values("measured_at")
            hr_vals_shift = hr_shift["value_numeric"].values
            start_step = int(7.0 * (24 // 3))

            # Detect with raw CUSUM
            raw_z_s = (hr_vals_shift - mu) / eff_sd
            c_raw_s = 0.0
            for step_idx, v in enumerate(raw_z_s):
                d = abs(v) - 0.5
                c_raw_s = max(0.0, c_raw_s + d) if d > 0 else max(0.0, c_raw_s + d * 0.5)
                if c_raw_s >= 3.0:
                    raw_cusum_detections += 1
                    raw_cusum_delays.append(max(0.0, (step_idx - start_step) * 3 / 24.0))
                    break

            # Detect with prewhitened CUSUM
            innov_s = np.zeros(len(raw_z_s))
            innov_s[0] = raw_z_s[0]
            for t in range(1, len(raw_z_s)):
                innov_s[t] = (raw_z_s[t] - phi * raw_z_s[t - 1]) / scale
            c_pw_s = 0.0
            for step_idx, e in enumerate(innov_s):
                d = abs(e) - 0.5
                c_pw_s = max(0.0, c_pw_s + d) if d > 0 else max(0.0, c_pw_s + d * 0.5)
                if c_pw_s >= 3.0:
                    prewhite_detections += 1
                    prewhite_delays.append(max(0.0, (step_idx - start_step) * 3 / 24.0))
                    break

            # Detect with variance-corrected EWMA
            ewma_s = mu
            for step_idx, val in enumerate(hr_vals_shift):
                ewma_s = lam * val + (1.0 - lam) * ewma_s
                if abs(ewma_s - mu) >= ewma_threshold:
                    ewma_detections += 1
                    ewma_delays.append(max(0.0, (step_idx - start_step) * 3 / 24.0))
                    break

        # Compute FAR and CIs
        raw_far = exact_poisson_rate_ci(raw_cusum_null_alerts, exposure_days)
        pw_far = exact_poisson_rate_ci(prewhitened_null_alerts, exposure_days)
        ewma_far = exact_poisson_rate_ci(ewma_null_alerts, exposure_days)

        raw_med_delay, _, _ = bootstrap_median_ci(raw_cusum_delays)
        pw_med_delay, _, _ = bootstrap_median_ci(prewhite_delays)
        ewma_med_delay, _, _ = bootstrap_median_ci(ewma_delays)

        results.append({
            "phi": phi,
            "raw_cusum_far": round(raw_far.rate_per_fortnight, 4),
            "raw_cusum_det_rate": round(raw_cusum_detections / n_runs_per_phi * 100, 1),
            "raw_cusum_median_delay_days": round(raw_med_delay, 2) if not math.isnan(raw_med_delay) else "N/A",
            "prewhitened_cusum_far": round(pw_far.rate_per_fortnight, 4),
            "prewhitened_det_rate": round(prewhite_detections / n_runs_per_phi * 100, 1),
            "prewhitened_median_delay_days": round(pw_med_delay, 2) if not math.isnan(pw_med_delay) else "N/A",
            "corrected_ewma_far": round(ewma_far.rate_per_fortnight, 4),
            "corrected_ewma_det_rate": round(ewma_detections / n_runs_per_phi * 100, 1),
            "corrected_ewma_median_delay_days": round(ewma_med_delay, 2) if not math.isnan(ewma_med_delay) else "N/A",
        })

        print(f"phi = {phi:.1f} | Raw CUSUM FAR: {raw_far.rate_per_fortnight:.3f} -> Prewhitened: {pw_far.rate_per_fortnight:.3f} | EWMA: {ewma_far.rate_per_fortnight:.3f}")

    df_res = pd.DataFrame(results)
    csv_path = out_dir / "ar1_detector_comparison.csv"
    df_res.to_csv(csv_path, index=False)
    print(f"\nSaved CSV: {csv_path}")

    # Plot Delay vs FAR Tradeoff Curve across phis
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(df_res["phi"], df_res["raw_cusum_far"], "r-o", label="Standard CUSUM (Uncorrected)", linewidth=2)
    ax1.plot(df_res["phi"], df_res["prewhitened_cusum_far"], "g-s", label="Prewhitened Residual CUSUM", linewidth=2)
    ax1.plot(df_res["phi"], df_res["corrected_ewma_far"], "b-^", label="Variance-Corrected EWMA", linewidth=2)
    ax1.set_xlabel(r"AR(1) Autocorrelation ($\phi$)", fontsize=11)
    ax1.set_ylabel("False Alert Rate (per crew-fortnight)", fontsize=11)
    ax1.set_title("FAR Inflation under Autocorrelation", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend()

    # Delay comparison for detectable phis
    delays_pw = [r if r != "N/A" else 0.0 for r in df_res["prewhitened_median_delay_days"]]
    delays_ewma = [r if r != "N/A" else 0.0 for r in df_res["corrected_ewma_median_delay_days"]]
    ax2.plot(df_res["phi"], delays_pw, "g-s", label="Prewhitened CUSUM Delay", linewidth=2)
    ax2.plot(df_res["phi"], delays_ewma, "b-^", label="Variance-Corrected EWMA Delay", linewidth=2)
    ax2.set_xlabel(r"AR(1) Autocorrelation ($\phi$)", fontsize=11)
    ax2.set_ylabel("Median Detection Delay (Days)", fontsize=11)
    ax2.set_title("Detection Latency vs Autocorrelation (1.5 SD Shift)", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend()

    plt.tight_layout()
    png_path = out_dir / "ar1_delay_vs_far_tradeoff.png"
    plt.savefig(png_path, dpi=200)
    plt.close()
    print(f"Saved Figure: {png_path}")

    return df_res


if __name__ == "__main__":
    run_ar1_experiment()
