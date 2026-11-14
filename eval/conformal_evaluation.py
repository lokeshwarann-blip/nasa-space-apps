"""eval/conformal_evaluation.py - Task 5 & Fix 9: Finite-Sample Adaptive Conformal Prediction Benchmark.

Methodological Deliverables:
1. Finite-sample split-conformal quantile ceil((n+1)(1-alpha))/n.
2. Parametric Student-t prediction interval fallback for small calibration sets (n < 1/alpha).
3. Chronological calibration/test split within each subject, eliminating data leakage.
4. Adaptive Conformal Inference (ACI) step updates under temporal dependence (Gibbs & Candes).
5. Comprehensive width reporting: mean conformal width vs signal SD and vs person-mean interval.
6. Stress test evaluation: coverage under level shifts, serial dependence (AR(1) phi), and missingness.
Outputs saved to eval/results/.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from eval.config import BASELINES, FINAL_TEST_SEEDS, MIN_SD, RESULTS_DIR, TEN_SIGNALS
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
    gamma = 0.05  # ACI step size

    signal_metrics = {m: {
        "raw_ewma_covered": 0, "raw_ewma_width": [], "raw_ewma_mae": [],
        "conformal_covered": 0, "conformal_width": [], "conformal_mae": [],
        "person_mean_covered": 0, "person_mean_width": [],
        "persistence_mae": [], "mean_mae": [], "total_steps": 0,
        "method_counts": {"parametric_student_t": 0, "adaptive_split_conformal": 0}
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

                # Point predictions
                ewm_series = pd.Series(history).ewm(alpha=0.4, adjust=False).mean()
                pred_ewma = float(ewm_series.iloc[-1])
                pred_pers = float(history[-1])
                pred_mean = float(np.mean(history))

                # Residuals on calibration history
                in_sample_preds = ewm_series.shift(1).dropna().values
                in_sample_actuals = history[1:]
                residuals = np.abs(in_sample_actuals - in_sample_preds)
                k_res = len(residuals)

                # A. Raw uncorrected percentile (10th-90th)
                q_raw = float(np.percentile(residuals, 90.0))
                lo_raw, hi_raw = pred_ewma - q_raw, pred_ewma + q_raw

                # B. Finite-sample conformal with Parametric Student-t Fallback
                if k_res < int(1.0 / adaptive_alpha):
                    std_err = float(np.std(residuals, ddof=1)) if k_res > 1 else max(0.5, float(np.std(history)))
                    df_t = max(1, k_res - 1)
                    t_crit = float(stats.t.ppf(1.0 - adaptive_alpha / 2.0, df=df_t))
                    q_conf = float(t_crit * std_err * np.sqrt(1.0 + 1.0 / max(1, k_res)))
                    method_used = "parametric_student_t"
                else:
                    p_level = min(1.0, np.ceil((k_res + 1) * (1.0 - adaptive_alpha)) / k_res)
                    q_conf = float(np.quantile(residuals, p_level))
                    method_used = "adaptive_split_conformal"

                lo_conf, hi_conf = pred_ewma - q_conf, pred_ewma + q_conf

                # Person-mean benchmark interval (parametric standard error)
                std_hist = float(np.std(history, ddof=1)) if len(history) > 1 else 1.0
                t_crit_pm = float(stats.t.ppf(1.0 - alpha / 2.0, df=max(1, len(history) - 1)))
                r_pm = t_crit_pm * std_hist * np.sqrt(1.0 + 1.0 / len(history))
                lo_pm, hi_pm = pred_mean - r_pm, pred_mean + r_pm

                # Check coverage
                raw_covered = 1 if (lo_raw <= actual_next <= hi_raw) else 0
                conf_covered = 1 if (lo_conf <= actual_next <= hi_conf) else 0
                pm_covered = 1 if (lo_pm <= actual_next <= hi_pm) else 0

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

                m_dict["person_mean_covered"] += pm_covered
                m_dict["person_mean_width"].append(hi_pm - lo_pm)

                m_dict["persistence_mae"].append(abs(actual_next - pred_pers))
                m_dict["mean_mae"].append(abs(actual_next - pred_mean))
                m_dict["total_steps"] += 1
                m_dict["method_counts"][method_used] += 1

    summary_rows = []
    for m in TEN_SIGNALS:
        d = signal_metrics[m]
        tot = max(1, d["total_steps"])

        raw_cov_pct = (d["raw_ewma_covered"] / tot) * 100.0
        conf_cov_pct = (d["conformal_covered"] / tot) * 100.0
        pm_cov_pct = (d["person_mean_covered"] / tot) * 100.0
        conf_ci = clopper_pearson_interval(d["conformal_covered"], tot)

        conf_w = float(np.mean(d["conformal_width"]))
        pm_w = float(np.mean(d["person_mean_width"]))
        sig_sd = BASELINES[m][1]
        width_sd_ratio = conf_w / max(1e-4, sig_sd)
        width_pm_ratio = conf_w / max(1e-4, pm_w)

        summary_rows.append({
            "signal": m,
            "raw_coverage_pct": round(raw_cov_pct, 1),
            "raw_mean_width": round(float(np.mean(d["raw_ewma_width"])), 2),
            "conformal_coverage_pct": round(conf_cov_pct, 1),
            "conformal_ci_95": f"[{conf_ci.ci_lower*100:.1f}%, {conf_ci.ci_upper*100:.1f}%]",
            "conformal_mean_width": round(conf_w, 2),
            "signal_sd": round(sig_sd, 2),
            "width_to_sd_ratio": round(width_sd_ratio, 2),
            "person_mean_mean_width": round(pm_w, 2),
            "person_mean_coverage_pct": round(pm_cov_pct, 1),
            "width_vs_person_mean_ratio": round(width_pm_ratio, 2),
            "ewma_mae": round(float(np.mean(d["conformal_mae"])), 3),
            "persistence_mae": round(float(np.mean(d["persistence_mae"])), 3),
            "person_mean_mae": round(float(np.mean(d["mean_mae"])), 3),
            "parametric_t_fallback_pct": round((d["method_counts"]["parametric_student_t"] / tot) * 100, 1),
            "adaptive_split_pct": round((d["method_counts"]["adaptive_split_conformal"] / tot) * 100, 1),
            "total_eval_points": tot,
        })
        print(f"[{m:<22}] Raw: {raw_cov_pct:4.1f}% -> Conformal: {conf_cov_pct:4.1f}% (Target: 90%) | Width: {conf_w:.2f} (SD={sig_sd}, Ratio={width_sd_ratio:.2f})")

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

    # Run Stress Tests (Fix 9)
    run_conformal_stress_tests(eval_seeds=eval_seeds, output_dir=out_dir)

    return df_conf


def run_conformal_stress_tests(eval_seeds: list[int], output_dir: Path) -> pd.DataFrame:
    """Fix 9: Stress tests conformal coverage under level shifts, serial dependence, and missingness."""
    print("\n" + "=" * 80)
    print("TASK 5 & FIX 9: CONFORMAL STRESS TESTS (SHIFTS, SERIAL DEPENDENCE, MISSINGNESS)")
    print("=" * 80)

    stress_scenarios = [
        {"name": "Nominal Stationary Null", "shift_sd": 0.0, "phi": 0.3, "dropout": 0.0},
        {"name": "Level Shift (+1.5 SD at Day 14)", "shift_sd": 1.5, "phi": 0.3, "dropout": 0.0},
        {"name": "Mild Autocorrelation (phi = 0.5)", "shift_sd": 0.0, "phi": 0.5, "dropout": 0.0},
        {"name": "Strong Autocorrelation (phi = 0.8)", "shift_sd": 0.0, "phi": 0.8, "dropout": 0.0},
        {"name": "Intermittent Missingness (25% Dropouts)", "shift_sd": 0.0, "phi": 0.3, "dropout": 0.25},
    ]

    stress_results = []
    alpha = 0.10
    gamma = 0.05

    for scen in stress_scenarios:
        covered_count = 0
        total_evals = 0
        widths = []

        for seed in eval_seeds[:15]:
            raw = generate_independent_trajectory(
                seed=seed + 12000, days=28, freq_h=3,
                ar1_phi=scen["phi"],
                shift_metric="heart_rate" if scen["shift_sd"] > 0 else None,
                shift_sd=scen["shift_sd"],
                shift_start_day=14.0,
                dropout_rate=scen["dropout"]
            )
            df = pd.DataFrame(raw)
            df["measured_at"] = pd.to_datetime(df["measured_at"], utc=True)
            hr = df[df["measurement_type"] == "heart_rate"].resample("1D", on="measured_at")["value_numeric"].mean().dropna()
            vals = hr.values
            if len(vals) < 14:
                continue

            cal_n = 7
            adaptive_alpha = alpha

            for t in range(cal_n, len(vals) - 1):
                history = vals[:t + 1]
                actual_next = vals[t + 1]

                ewm_series = pd.Series(history).ewm(alpha=0.4, adjust=False).mean()
                pred_ewma = float(ewm_series.iloc[-1])

                in_sample_preds = ewm_series.shift(1).dropna().values
                in_sample_actuals = history[1:]
                residuals = np.abs(in_sample_actuals - in_sample_preds)
                k_res = len(residuals)

                if k_res < int(1.0 / adaptive_alpha):
                    std_err = float(np.std(residuals, ddof=1)) if k_res > 1 else max(0.5, float(np.std(history)))
                    t_crit = float(stats.t.ppf(1.0 - adaptive_alpha / 2.0, df=max(1, k_res - 1)))
                    q_conf = float(t_crit * std_err * np.sqrt(1.0 + 1.0 / max(1, k_res)))
                else:
                    p_level = min(1.0, np.ceil((k_res + 1) * (1.0 - adaptive_alpha)) / k_res)
                    q_conf = float(np.quantile(residuals, p_level))

                lo, hi = pred_ewma - q_conf, pred_ewma + q_conf
                is_cov = 1 if (lo <= actual_next <= hi) else 0
                covered_count += is_cov
                total_evals += 1
                widths.append(hi - lo)

                # ACI update
                adaptive_alpha = max(0.01, min(0.50, adaptive_alpha + gamma * (alpha - (1 - is_cov))))

        cov_pct = (covered_count / max(1, total_evals)) * 100.0
        ci = clopper_pearson_interval(covered_count, max(1, total_evals))

        stress_results.append({
            "scenario": scen["name"],
            "empirical_coverage_pct": round(cov_pct, 1),
            "coverage_95_ci": f"[{ci.ci_lower*100:.1f}%, {ci.ci_upper*100:.1f}%]",
            "mean_interval_width": round(float(np.mean(widths)), 2) if widths else 0.0,
            "total_points_evaluated": total_evals,
        })
        print(f"[{scen['name']:<42}] Coverage: {cov_pct:4.1f}% [{ci.ci_lower*100:.1f}%, {ci.ci_upper*100:.1f}%] | Mean Width: {np.mean(widths):.2f}")

    df_stress = pd.DataFrame(stress_results)
    stress_csv = output_dir / "conformal_stress_tests.csv"
    df_stress.to_csv(stress_csv, index=False)
    print(f"Saved CSV: {stress_csv}")
    return df_stress


if __name__ == "__main__":
    run_conformal_evaluation()
