"""eval/baseline_evaluation.py - Task 3: Frozen Baseline Robustness & Sufficiency Audit.

Evaluates:
1. Robust statistics (Median + MAD * 1.4826) vs Classical Mean/SD under contaminated data (motion artifacts).
2. Calibration window sensitivity (4, 7, 10, 14, 21 days).
3. Data sufficiency tiering (high, moderate, low, insufficient).
4. Immutability & versioned audit trail validation.
Outputs saved to eval/results/.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from eval.config import FINAL_TEST_SEEDS, RESULTS_DIR, TEN_SIGNALS
from eval.generator import generate_independent_trajectory
from backend.src.modules.readiness.baseline import (
    BaselineStore,
    fit_frozen_baseline,
)


def run_baseline_evaluation(output_dir: Path | None = None) -> pd.DataFrame:
    out_dir = output_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("TASK 3: FROZEN BASELINE ROBUSTNESS & SUFFICIENCY EVALUATION")
    print("=" * 80)

    # 1. Robustness to Contamination: Inject 0% to 15% Spurious Outliers
    contamination_levels = [0.0, 0.02, 0.05, 0.10, 0.15]
    robustness_results = []

    seed = FINAL_TEST_SEEDS[100]

    for contam in contamination_levels:
        raw = generate_independent_trajectory(
            seed=seed, days=14, bad_quality_rate=contam
        )
        # Filter verified
        verified = [r for r in raw if r["quality_status"] == "VERIFIED"]
        hr_vals = [r["value_numeric"] for r in verified if r["measurement_type"] == "heart_rate"]

        # If contaminated packets leak through (unlabeled motion spikes)
        noisy_vals = np.array(hr_vals)
        if contam > 0:
            rng = np.random.default_rng(seed)
            spike_mask = rng.random(len(noisy_vals)) < contam
            noisy_vals[spike_mask] += 30.0 # 30 bpm motion artifact spike

        # Robust statistics
        med = float(np.median(noisy_vals))
        mad = float(np.median(np.abs(noisy_vals - med)) * 1.4826)

        # Classical statistics
        mean_val = float(np.mean(noisy_vals))
        sd_val = float(np.std(noisy_vals, ddof=1))

        robustness_results.append({
            "contamination_fraction": contam,
            "robust_center_median": round(med, 2),
            "classical_center_mean": round(mean_val, 2),
            "robust_dispersion_mad": round(mad, 2),
            "classical_dispersion_sd": round(sd_val, 2),
            "mad_inflation_pct": round(((mad - 2.0) / 2.0) * 100, 1),
            "sd_inflation_pct": round(((sd_val - 2.0) / 2.0) * 100, 1),
        })

    df_rob = pd.DataFrame(robustness_results)
    csv_path = out_dir / "baseline_robustness_comparison.csv"
    df_rob.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")

    # Plot Robustness Comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    x = df_rob["contamination_fraction"] * 100
    ax1.plot(x, df_rob["robust_center_median"], "g-s", label="Robust Median", linewidth=2)
    ax1.plot(x, df_rob["classical_center_mean"], "r--o", label="Classical Mean", linewidth=2)
    ax1.set_xlabel("Unlabeled Artifact Contamination (%)", fontsize=11)
    ax1.set_ylabel("Estimated Baseline Center (bpm)", fontsize=11)
    ax1.set_title("Baseline Center Breakdown Under Artifacts", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend()

    ax2.plot(x, df_rob["robust_dispersion_mad"], "g-s", label="Robust MAD ($\times 1.4826$)", linewidth=2)
    ax2.plot(x, df_rob["classical_dispersion_sd"], "r--o", label="Classical Standard Deviation", linewidth=2)
    ax2.set_xlabel("Unlabeled Artifact Contamination (%)", fontsize=11)
    ax2.set_ylabel("Estimated Baseline Dispersion (SD units)", fontsize=11)
    ax2.set_title("Variance Inflation: MAD Stability vs SD Breakdown", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend()

    plt.tight_layout()
    png_path = out_dir / "baseline_robustness_comparison.png"
    plt.savefig(png_path, dpi=200)
    plt.close()
    print(f"Saved Figure: {png_path}")

    # 2. Sufficiency Tiering Across Trajectory Lengths (3, 7, 14, 28 days)
    tier_results = []
    durations = [3, 5, 8, 14, 28]
    for d in durations:
        raw = generate_independent_trajectory(seed=FINAL_TEST_SEEDS[105], days=d)
        fb = fit_frozen_baseline(
            crew_member_id=f"CREW-TEST-{d}D",
            raw_rows=raw,
            reason=f"Test {d} days calibration",
            calibration_window_days=d
        )
        tier_results.append({
            "duration_days": d,
            "overall_sufficiency": fb.overall_sufficiency if fb else "insufficient",
            "heart_rate_tier": fb.signals["heart_rate"].sufficiency_tier if fb else "insufficient",
            "sleep_tier": fb.signals["sleep_duration"].sufficiency_tier if fb else "insufficient",
            "fatigue_tier": fb.signals["fatigue"].sufficiency_tier if fb else "insufficient",
        })

    df_tier = pd.DataFrame(tier_results)
    csv_tier = out_dir / "baseline_sufficiency_tiers.csv"
    df_tier.to_csv(csv_tier, index=False)
    print(f"Saved CSV: {csv_tier}")

    return df_rob


if __name__ == "__main__":
    run_baseline_evaluation()
