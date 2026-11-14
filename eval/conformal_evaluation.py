"""eval/conformal_evaluation.py - Task 5: Finite-Sample Conformal Prediction Benchmark.

Addresses:
1. Finite-sample corrected quantile ceil((n+1)(1-alpha))/n.
2. Chronological calibration/test split within each person, eliminating leakage.
3. Adaptive Conformal Inference (ACI) step updates under temporal dependence.
4. Benchmarks against Persistence and Person-Mean baselines.
5. Empirical coverage, interval width, and exact Clopper-Pearson coverage CIs.
Outputs saved to eval/results/.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from eval.config import FINAL_TEST_SEEDS, RESULTS_DIR, TEN_SIGNALS
from eval.generator import generate_independent_trajectory
from eval.stats import clopper_pearson_interval


def run_conformal_evaluation(n_eval_runs: int = 20, days: int = 28, output_dir: Path | None = None) -> pd.DataFrame:
    out_dir = output_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("TASK 5: CONFORMAL FORECAST UNCERTAINTY & COVERAGE BENCHMARK")
    print(f"Evaluating {n_eval_runs} independent 28-day trajectories on FINAL_TEST_SEEDS")
    print("=" * 80)

    eval_seeds = FINAL_TEST_SEEDS[:n_eval_runs]
    target_coverage = 0.90
    alpha = 0.10
    gamma = 0.05 # ACI step size

    signal_metrics = {m: {
        "raw_ewma_covered": 0, "raw_ewma_width": [], "raw_ewma_mae": [],
        "conformal_covered": 0, "conformal_width": [], "conformal_mae": [],
        "persistence_mae": [], "mean_mae": [], "total_steps": 0
    } for m in TEN_SIGNALS}

    for seed in eval_seeds:
        raw = generate_independent_trajectory(seed=seed, days=days, freq_h=3, ar1_phi=0.3)
        df = pd.DataFrame(raw)
        df["measured_at"] = pd.to_datetime(df["measured_at"], utc=True)
        # Resample daily
        daily = df.pivot_table(index="measured_at", columns="measurement_type", values="value_numeric", aggfunc="mean").resample("1D").mean()

        for m in TEN_SIGNALS:
            if m not in daily.columns:
                continue
            s = daily[m].dropna()
            vals = s.values
            if len(vals) < 14:
                continue

            # Chronological split: First 7 days calibration; remaining days test
            cal_n = 7
            adaptive_alpha = alpha

            for t in range(cal_n, len(vals) - 1):
                history = vals[:t + 1]
                actual_next = vals[t + 1]

                # 1. Point predictions
                # EWMA prediction
                ewm_series = pd.Series(history).ewm(alpha=0.4, adjust=False).mean()
                pred_ewma = float(ewm_series.iloc[-1])
                # Persistence prediction
                pred_pers = float(history[-1])
                # Person-mean prediction
                pred_mean = float(np.mean(history))

                # 2. Residuals on calibration history
                in_sample_preds = ewm_series.shift(1).dropna().values
                in_sample_actuals = history[1:]
                residuals = np.abs(in_sample_actuals - in_sample_preds)
                k_res = len(residuals)

                # A. Raw uncorrected percentile (10th-90th)
                q_raw = float(np.percentile(residuals, 90.0))
                lo_raw, hi_raw = pred_ewma - q_raw, pred_ewma + q_raw

                # B. Finite-sample corrected adaptive conformal quantile
                p_level = min(1.0, np.ceil((k_res + 1) * (1.0 - adaptive_alpha)) / k_res)
                q_conf = float(np.quantile(residuals, p_level))
                lo_conf, hi_conf = pred_ewma - q_conf, pred_ewma + q_conf

                # Check coverage
                raw_covered = 1 if (lo_raw <= actual_next <= hi_raw) else 0
                conf_covered = 1 if (lo_conf <= actual_next <= hi_conf) else 0

                # Adaptive Conformal step update (Gibbs & Candes)
                err_t = 0 if conf_covered else 1
                adaptive_alpha = max(0.01, min(0.50, adaptive_alpha + gamma * (alpha - err_t)))

                # Record metrics
                m_dict = signal_metrics[m]
                m_dict["raw_ewma_covered"] += raw_covered
                m_dict["raw_ewma_width"].append(hi_raw - lo_raw)
                m_dict["raw_ewma_mae"].append(abs(actual_next - pred_ewma))

                m_dict["conformal_covered"] += conf_covered
                m_dict["conformal_width"].append(hi_conf - lo_conf)
                m_dict["conformal_mae"].append(abs(actual_next - pred_ewma))

                m_dict["persistence_mae"].append(abs(actual_next - pred_pers))
                m_dict["mean_mae"].append(abs(actual_next - pred_mean))
                m_dict["total_steps"] += 1

    summary_rows = []
    for m in TEN_SIGNALS:
        d = signal_metrics[m]
        tot = max(1, d["total_steps"])

        raw_cov_pct = (d["raw_ewma_covered"] / tot) * 100.0
        conf_cov_pct = (d["conformal_covered"] / tot) * 100.0
        conf_ci = clopper_pearson_interval(d["conformal_covered"], tot)

        summary_rows.append({
            "signal": m,
            "raw_coverage_pct": round(raw_cov_pct, 1),
            "raw_mean_width": round(float(np.mean(d["raw_ewma_width"])), 2),
            "conformal_coverage_pct": round(conf_cov_pct, 1),
            "conformal_ci_95": f"[{conf_ci.ci_lower*100:.1f}%, {conf_ci.ci_upper*100:.1f}%]",
            "conformal_mean_width": round(float(np.mean(d["conformal_width"])), 2),
            "ewma_mae": round(float(np.mean(d["conformal_mae"])), 3),
            "persistence_mae": round(float(np.mean(d["persistence_mae"])), 3),
            "person_mean_mae": round(float(np.mean(d["mean_mae"])), 3),
            "total_eval_points": tot,
        })
        print(f"[{m:<22}] Raw Coverage: {raw_cov_pct:4.1f}% -> Conformal: {conf_cov_pct:4.1f}% (Target: 90%) | Width: {np.mean(d['conformal_width']):.2f}")

    df_conf = pd.DataFrame(summary_rows)
    csv_path = out_dir / "conformal_forecast_benchmark.csv"
    df_conf.to_csv(csv_path, index=False)
    print(f"\nSaved CSV: {csv_path}")

    # Plot Coverage Comparison across signals
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

    signals_abbrev = [s.replace("_", "\n") for s in df_conf["signal"]]
    x = np.arange(len(signals_abbrev))
    width = 0.35

    ax1.axhline(90.0, color="gray", linestyle="--", linewidth=1.5, label="Target Coverage (90%)")
    ax1.bar(x - width/2, df_conf["raw_coverage_pct"], width, label="Raw Percentile EWMA", color="#d9534f")
    ax1.bar(x + width/2, df_conf["conformal_coverage_pct"], width, label="Finite-Sample Conformal EWMA", color="#5cb85c")
    ax1.set_ylabel("Empirical Coverage (%)", fontsize=11)
    ax1.set_title("90% Forecast Coverage: Raw vs Conformal", fontsize=12, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(signals_abbrev, fontsize=8)
    ax1.set_ylim(40, 105)
    ax1.grid(True, linestyle="--", alpha=0.5, axis="y")
    ax1.legend(loc="lower right")

    # Plot MAE Comparison: EWMA vs Persistence vs Person-Mean
    ax2.plot(signals_abbrev, df_conf["ewma_mae"], "g-o", label="EWMA MAE", linewidth=2)
    ax2.plot(signals_abbrev, df_conf["persistence_mae"], "b--s", label="Persistence MAE", linewidth=2)
    ax2.plot(signals_abbrev, df_conf["person_mean_mae"], "r:^", label="Person-Mean MAE", linewidth=2)
    ax2.set_ylabel("Mean Absolute Error (Signal Units)", fontsize=11)
    ax2.set_title("Forecast Point Accuracy: EWMA vs Baselines", fontsize=12, fontweight="bold")
    ax2.tick_params(axis="x", labelrotation=45)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

    plt.tight_layout()
    png_path = out_dir / "conformal_coverage_comparison.png"
    plt.savefig(png_path, dpi=200)
    plt.close()
    print(f"Saved Figure: {png_path}")

    return df_conf


if __name__ == "__main__":
    run_conformal_evaluation()
