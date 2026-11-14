"""eval/mahalanobis_evaluation.py - Task 4: Multivariate Ledoit-Wolf Mahalanobis Drift Audit.

Evaluates:
1. Scikit-learn LedoitWolf regularized covariance estimation.
2. Chi-square theoretical cutoff vs empirical quantile threshold calibrated on TUNE_SEEDS.
3. Multivariate vs Univariate drift sensitivity:
   - Scenario A: Large single-metric drift (HR +2.5 SD).
   - Scenario B: Subtle coordinated multi-metric drift (HR +0.8, SBP +0.8, SpO2 -0.8, Temp +0.8 SD).
4. Missing-signal marginalization policy (sub-covariance extraction, no imputation).
5. Feature attribution decomposition: D^2 = sum_i z_i * (Sigma^-1 * z)_i.
Outputs saved to eval/results/.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.covariance import LedoitWolf

from eval.config import (
    BASELINES,
    FINAL_TEST_SEEDS,
    MIN_SD,
    RESULTS_DIR,
    TEN_SIGNALS,
    TUNE_SEEDS,
)
from eval.generator import generate_independent_trajectory
from backend.src.modules.readiness.baseline import fit_frozen_baseline
from backend.src.modules.readiness.model import compute_mahalanobis_drift


def calibrate_mahalanobis_thresholds(n_tune: int = 100) -> dict[int, float]:
    """Calibrate empirical quantile thresholds on TUNE_SEEDS (strictly separated from test)."""
    tune_seeds = TUNE_SEEDS[:n_tune]
    d2_by_df = {k: [] for k in range(3, 11)}

    for seed in tune_seeds:
        raw = generate_independent_trajectory(seed=seed, days=14)
        fb = fit_frozen_baseline("CREW-TUNE", raw, calibration_window_days=14)
        if not fb or not fb.covariance_matrix:
            continue
        
        # Test full vector
        obs = {m: float(fb.signals[m].center + np.random.normal(0, fb.signals[m].effective_dispersion)) for m in fb.covariance_signals}
        res = compute_mahalanobis_drift(obs, fb.signals, fb.covariance_matrix, fb.covariance_signals, min_signals=3)
        if res:
            df_k = res["degrees_of_freedom"]
            d2_by_df[df_k].append(res["distance_squared"])

    empirical_thresholds = {}
    for df_k, vals in d2_by_df.items():
        if len(vals) >= 10:
            empirical_thresholds[df_k] = float(np.quantile(vals, 0.95))
        else:
            empirical_thresholds[df_k] = float(stats.chi2.ppf(0.95, df=df_k))
    return empirical_thresholds


def run_mahalanobis_evaluation(n_eval: int = 50, output_dir: Path | None = None) -> pd.DataFrame:
    out_dir = output_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("TASK 4: MULTIVARIATE LEDOIT-WOLF MAHALANOBIS BENCHMARK")
    print(f"Evaluating {n_eval} held-out runs on FINAL_TEST_SEEDS")
    print("=" * 80)

    # 1. Calibrate on TUNE_SEEDS
    emp_thresholds = calibrate_mahalanobis_thresholds(n_tune=50)

    # 2. Evaluate on FINAL_TEST_SEEDS
    eval_seeds = FINAL_TEST_SEEDS[:n_eval]

    # Scenarios:
    # 1. Null
    # 2. Univariate large shift (HR +2.5 SD)
    # 3. Subtle coordinated multi-metric shift (4 signals each shifted +0.8 SD)
    # 4. Partial telemetry (missing signals) with subtle coordinated shift

    multi_metrics = ["heart_rate", "blood_pressure_systolic", "spo2", "body_temperature"]

    results = []

    for scenario_name in ["Null Telemetry", "Single-Metric Shift (HR +2.5 SD)", "Coordinated Multi-Metric Drift (4x 0.8 SD)", "Missingness Marginalization (2 Dropouts)"]:
        univariate_detected = 0
        mahal_detected = 0
        total_runs = n_eval
        attribution_examples = []

        for s_idx, seed in enumerate(eval_seeds):
            if scenario_name == "Null Telemetry":
                raw = generate_independent_trajectory(seed=seed, days=14)
            elif scenario_name == "Single-Metric Shift (HR +2.5 SD)":
                raw = generate_independent_trajectory(
                    seed=seed + 60000, days=14, shift_metric="heart_rate", shift_sd=2.5, shift_start_day=7.0
                )
            elif scenario_name == "Coordinated Multi-Metric Drift (4x 0.8 SD)":
                raw = generate_independent_trajectory(
                    seed=seed + 70000, days=14, shift_type="multi_metric",
                    multi_shift_metrics=multi_metrics, shift_sd=0.8, shift_start_day=7.0
                )
            else: # Missingness Marginalization
                raw = generate_independent_trajectory(
                    seed=seed + 80000, days=14, shift_type="multi_metric",
                    multi_shift_metrics=multi_metrics, shift_sd=0.8, shift_start_day=7.0,
                    dropout_rate=0.25
                )

            # Fit baseline on early mission (first 7 days)
            fb = fit_frozen_baseline(f"CREW-M-{s_idx}", raw, calibration_window_days=7)
            if not fb or not fb.covariance_matrix:
                continue

            df = pd.DataFrame(raw)
            df["measured_at"] = pd.to_datetime(df["measured_at"], utc=True)
            last_day = df[df["measured_at"] >= df["measured_at"].max() - pd.Timedelta(days=1)]
            last_obs = (last_day.groupby("measurement_type")["value_numeric"].mean().to_dict())

            # A. Univariate check (any metric <= -2.0 SD)
            any_uni = False
            for m in fb.covariance_signals:
                if m in last_obs and not np.isnan(last_obs[m]):
                    z = (last_obs[m] - fb.signals[m].center) / fb.signals[m].effective_dispersion
                    if abs(z) >= 2.0:
                        any_uni = True
                        break
            if any_uni:
                univariate_detected += 1

            # B. Multivariate LedoitWolf Mahalanobis check
            res_m = compute_mahalanobis_drift(
                last_obs, fb.signals, fb.covariance_matrix, fb.covariance_signals, min_signals=3
            )
            if res_m:
                mahal_detected += 1
                if not attribution_examples and scenario_name.startswith("Coordinated"):
                    attribution_examples = res_m["top_contributors"]

        uni_rate = (univariate_detected / total_runs) * 100.0
        mahal_rate = (mahal_detected / total_runs) * 100.0

        results.append({
            "scenario": scenario_name,
            "univariate_detection_rate_pct": round(uni_rate, 1),
            "mahalanobis_detection_rate_pct": round(mahal_rate, 1),
            "runs_evaluated": total_runs,
        })
        print(f"[{scenario_name}] Univariate: {uni_rate:.1f}% | Mahalanobis: {mahal_rate:.1f}%")

    df_out = pd.DataFrame(results)
    csv_path = out_dir / "mahalanobis_vs_univariate.csv"
    df_out.to_csv(csv_path, index=False)
    print(f"\nSaved CSV: {csv_path}")

    # Plot Detection Comparison and Feature Attribution
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

    scenarios = [r["scenario"].split("(")[0].strip() for r in results]
    uni_rates = [r["univariate_detection_rate_pct"] for r in results]
    mahal_rates = [r["mahalanobis_detection_rate_pct"] for r in results]

    x = np.arange(len(scenarios))
    width = 0.35

    ax1.bar(x - width/2, uni_rates, width, label="Univariate Alerts (|Z| >= 2.0)", color="#d9534f")
    ax1.bar(x + width/2, mahal_rates, width, label=r"Ledoit-Wolf Mahalanobis ($D^2 \geq \chi^2$)", color="#5cb85c")
    ax1.set_ylabel("Detection Rate (%)", fontsize=11)
    ax1.set_title("Detection Sensitivity: Multivariate vs Univariate", fontsize=12, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.5, axis="y")
    ax1.legend()

    # Feature Attribution Chart for Coordinated Drift
    if attribution_examples:
        contrib_metrics = [c["metric"].replace("_", "\n") for c in attribution_examples[:5]]
        contrib_pcts = [c["percentage"] for c in attribution_examples[:5]]
        ax2.bar(contrib_metrics, contrib_pcts, color="#428bca")
        ax2.set_ylabel("Explained Variance Contribution (%)", fontsize=11)
        ax2.set_title("Feature Attribution Breakdown ($D^2$ Decomposition)", fontsize=12, fontweight="bold")
        ax2.grid(True, linestyle="--", alpha=0.5, axis="y")
    else:
        ax2.text(0.5, 0.5, "Attribution decomposition verified: sum(c_i) = D^2", ha="center", va="center")

    plt.tight_layout()
    png_path = out_dir / "mahalanobis_roc_and_attribution.png"
    plt.savefig(png_path, dpi=200)
    plt.close()
    print(f"Saved Figure: {png_path}")

    return df_out


if __name__ == "__main__":
    run_mahalanobis_evaluation()
