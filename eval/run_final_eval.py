"""eval/run_final_eval.py - Strictly held-out FINAL_TEST_SEEDS evaluation runner.

Execution Protocol:
- Evaluates seeds 40000-40199 (N=200) strictly ONCE.
- Uses frozen thresholds calibrated on TUNE_SEEDS:
    * Plain Z-score: z_crit = 2.21
    * Fair CUSUM: h_cusum = 4.47
    * Sum-of-Z: s_crit = 18.50
    * Dual Fusion: h_prim = 5.17, t2_sec = 51.48
- Intra-day correlation phi = 0.75.
- Theoretical daily-mean SE scaling.
- Outputs written strictly to eval/results/final/ (never overwriting validation results).
"""
from pathlib import Path
import math
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.covariance import LedoitWolf

from eval.config import BASELINES, MIN_SD, TEN_SIGNALS
from eval.generator import generate_independent_trajectory
from backend.src.modules.readiness.model import from_measurements, to_series

CORE_VITALS = ["heart_rate", "blood_pressure_systolic", "spo2", "hrv"]
FINAL_OUTPUT_DIR = Path("eval/results/final")


def compute_daily_se_map(phi: float = 0.75) -> dict[str, float]:
    """Computes theoretical standard error of daily mean under intra-day AR(1) correlation."""
    n_readings = {m: 8 for m in CORE_VITALS + ["blood_pressure_diastolic", "body_temperature"]}
    n_readings.update({"sleep_duration": 1, "stress": 1, "mood": 1, "fatigue": 1})
    gamma_map = {}
    for m, n in n_readings.items():
        if n == 1:
            gamma_map[m] = 1.0
        else:
            k_vec = np.arange(1, n)
            inf = 1.0 + 2.0 * np.sum((1.0 - k_vec / n) * (phi**k_vec))
            gamma_map[m] = float(np.sqrt(inf / n))
    return {m: max(BASELINES[m][1], MIN_SD[m]) * gamma_map[m] for m in TEN_SIGNALS}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float, float]:
    """Exact Clopper-Pearson 95% confidence interval for binomial proportion."""
    if n == 0:
        return 0.0, 0.0, 1.0
    point = k / float(n)
    low = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2.0, k, n - k + 1))
    high = 1.0 if k == n else float(stats.beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return point, low, high


def poisson_ci(k: int, exposure_days: float, alpha: float = 0.05) -> tuple[float, float, float]:
    """Exact Poisson rate 95% confidence interval per fortnight (14 crew-days)."""
    rate = (k / float(exposure_days)) * 14.0
    if k == 0:
        low = 0.0
        high = float(0.5 * stats.chi2.ppf(1.0 - alpha, 2)) / exposure_days * 14.0
    else:
        low = float(0.5 * stats.chi2.ppf(alpha / 2.0, 2 * k)) / exposure_days * 14.0
        high = float(0.5 * stats.chi2.ppf(1.0 - alpha / 2.0, 2 * (k + 1))) / exposure_days * 14.0
    return rate, low, high


def run_final_test_evaluation() -> None:
    FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eval_seeds = list(range(40000, 40200))
    n_eval = len(eval_seeds)
    exposure_days = n_eval * 7.0  # 1,400 scored monitoring crew-days (Task 4)
    phi_intra = 0.75
    lam = 0.25

    # Frozen thresholds calibrated on TUNE_SEEDS
    z_crit = 2.21
    h_cusum = 4.47
    s_crit = 18.50
    h_prim = 5.17
    t2_sec = 51.48

    daily_se = compute_daily_se_map(phi=phi_intra)

    print("=" * 85)
    print("MELIORA FINAL TEST SEEDS EVALUATION (STRICTLY ONCE)")
    print(f"Seed Range: 40000 - 40199 (N={n_eval} independent runs)")
    print(f"Scored Monitoring Exposure: {exposure_days:.0f} crew-days (Days 7-13)")
    print(f"Intra-day correlation phi: {phi_intra}")
    print(f"Frozen Thresholds: z_crit={z_crit}, h_cusum={h_cusum}, s_crit={s_crit}, h_prim={h_prim}, t2_sec={t2_sec}")
    print("=" * 85)

    all_scenarios = [
        ("Nominal Null", {}),
        ("Single 0.5 SD (HR)", {"shift_metric": "heart_rate", "shift_sd": 0.5, "shift_start_day": 7.0}),
        ("Single 1.0 SD (HR)", {"shift_metric": "heart_rate", "shift_sd": 1.0, "shift_start_day": 7.0}),
        ("Single 2.0 SD (HR)", {"shift_metric": "heart_rate", "shift_sd": 2.0, "shift_start_day": 7.0}),
        ("Multi 0.5 SD (4 Vitals)", {"shift_type": "multi_metric", "multi_shift_metrics": CORE_VITALS, "shift_sd": 0.5, "shift_start_day": 7.0}),
        ("Multi 0.8 SD (4 Vitals)", {"shift_type": "multi_metric", "multi_shift_metrics": CORE_VITALS, "shift_sd": 0.8, "shift_start_day": 7.0}),
        ("Multi 1.0 SD (4 Vitals)", {"shift_type": "multi_metric", "multi_shift_metrics": CORE_VITALS, "shift_sd": 1.0, "shift_start_day": 7.0}),
        ("Multi 2.0 SD (4 Vitals)", {"shift_type": "multi_metric", "multi_shift_metrics": CORE_VITALS, "shift_sd": 2.0, "shift_start_day": 7.0}),
        ("Ramp 1.5 SD (HR)", {"shift_type": "ramp", "shift_metric": "heart_rate", "shift_sd": 1.5, "shift_start_day": 7.0}),
    ]

    methods = ["Plain Z-score", "Per-Signal CUSUM (Fair)", "Sum-of-Z", "MELIORA Fusion"]
    results_table = []
    attribution_records = []

    for sc_name, sc_kwargs in all_scenarios:
        trajectories = []
        for seed in eval_seeds:
            raw = generate_independent_trajectory(seed=seed, days=14, ar1_phi=phi_intra, **sc_kwargs)
            df = from_measurements(raw)
            daily = to_series(df, TEN_SIGNALS, freq="1D")
            trajectories.append((raw, daily))

        for method in methods:
            alerts_count = 0
            delays = []
            prim_hits = 0
            sec_hits = 0
            both_hits = 0

            for raw, daily in trajectories:
                earliest_day = None
                triggered = False
                hit_p = False
                hit_s = False

                if method == "Plain Z-score":
                    for d_idx in range(7, len(daily)):
                        row = daily.iloc[d_idx]
                        z_max = max([abs((row[m] - BASELINES[m][0]) / daily_se[m])
                                     for m in TEN_SIGNALS if m in row and not np.isnan(row[m])], default=0.0)
                        if z_max >= z_crit:
                            triggered = True
                            earliest_day = d_idx
                            break

                elif method == "Per-Signal CUSUM (Fair)":
                    c_pos = {m: 0.0 for m in TEN_SIGNALS}
                    c_neg = {m: 0.0 for m in TEN_SIGNALS}
                    for d_idx in range(7, len(daily)):
                        row = daily.iloc[d_idx]
                        for m in TEN_SIGNALS:
                            if m not in row or np.isnan(row[m]):
                                continue
                            mu = BASELINES[m][0]
                            z = (row[m] - mu) / daily_se[m]
                            c_pos[m] = max(0.0, c_pos[m] + z - 0.5)
                            c_neg[m] = max(0.0, c_neg[m] - z - 0.5)
                            if c_pos[m] >= h_cusum or c_neg[m] >= h_cusum:
                                triggered = True
                                earliest_day = d_idx
                                break
                        if triggered:
                            break

                elif method == "Sum-of-Z":
                    for d_idx in range(7, len(daily)):
                        row = daily.iloc[d_idx]
                        sz = sum([((row[m] - BASELINES[m][0]) / daily_se[m])**2
                                  for m in TEN_SIGNALS if m in row and not np.isnan(row[m])])
                        if sz >= s_crit:
                            triggered = True
                            earliest_day = d_idx
                            break

                elif method == "MELIORA Fusion":
                    core_base = daily[CORE_VITALS].iloc[:7].dropna()
                    if len(core_base) >= 5:
                        z_base = np.zeros(core_base.shape)
                        for c_i, m in enumerate(CORE_VITALS):
                            mu, sd = BASELINES[m]
                            z_base[:, c_i] = (core_base[m].values - mu) / max(sd, MIN_SD[m])
                        cov_est = LedoitWolf().fit(z_base).covariance_
                        cov_inv = np.linalg.pinv(cov_est)
                    else:
                        cov_inv = np.eye(len(CORE_VITALS))

                    u = np.zeros(len(CORE_VITALS))
                    c_pos = {m: 0.0 for m in TEN_SIGNALS}
                    c_neg = {m: 0.0 for m in TEN_SIGNALS}

                    for d_idx in range(7, len(daily)):
                        row = daily.iloc[d_idx]

                        # Primary Channel: Fair CUSUM update
                        trig_p = False
                        for m in TEN_SIGNALS:
                            if m not in row or np.isnan(row[m]):
                                continue
                            mu = BASELINES[m][0]
                            z = (row[m] - mu) / daily_se[m]
                            c_pos[m] = max(0.0, c_pos[m] + z - 0.5)
                            c_neg[m] = max(0.0, c_neg[m] - z - 0.5)
                            if c_pos[m] >= h_prim or c_neg[m] >= h_prim:
                                trig_p = True

                        # Secondary Channel: MEWMA update
                        trig_s = False
                        core_row = row[CORE_VITALS]
                        if not core_row.isna().any():
                            z_curr = np.array([(core_row[m] - BASELINES[m][0]) / max(BASELINES[m][1], MIN_SD[m]) for m in CORE_VITALS])
                            u = lam * z_curr + (1.0 - lam) * u
                            t_step = d_idx - 6
                            v_fac = (lam / (2.0 - lam)) * (1.0 - (1.0 - lam)**(2 * t_step))
                            sigma_u_inv = cov_inv / max(1e-6, v_fac)
                            t2 = float(np.dot(u, np.dot(sigma_u_inv, u)))
                            if t2 >= t2_sec:
                                trig_s = True

                        if trig_p or trig_s:
                            triggered = True
                            earliest_day = d_idx
                            hit_p = trig_p
                            hit_s = trig_s
                            break

                if "Null" in sc_name:
                    if triggered:
                        alerts_count += 1
                        if method == "MELIORA Fusion":
                            if hit_p and hit_s:
                                both_hits += 1
                            elif hit_p:
                                prim_hits += 1
                            elif hit_s:
                                sec_hits += 1
                else:
                    if triggered and earliest_day is not None and earliest_day >= 7:
                        alerts_count += 1
                        delays.append(float(earliest_day - 7.0))
                        if method == "MELIORA Fusion":
                            if hit_p and hit_s:
                                both_hits += 1
                            elif hit_p:
                                prim_hits += 1
                            elif hit_s:
                                sec_hits += 1

            is_null = "Null" in sc_name
            if is_null:
                rate, ci_low, ci_high = poisson_ci(alerts_count, exposure_days)
                med_delay = "N/A"
            else:
                p_est, ci_low, ci_high = clopper_pearson(alerts_count, n_eval)
                rate = p_est * 100.0
                ci_low *= 100.0
                ci_high *= 100.0
                med_delay = round(float(np.median(delays)), 1) if delays else "N/A"

            results_table.append({
                "scenario": sc_name,
                "method": method,
                "is_null": is_null,
                "events_or_alerts": alerts_count,
                "total_evaluated": n_eval,
                "point_estimate": round(rate, 3),
                "ci_lower": round(ci_low, 3),
                "ci_upper": round(ci_high, 3),
                "median_delay_days": med_delay,
            })

            if method == "MELIORA Fusion":
                attribution_records.append({
                    "scenario": sc_name,
                    "total_alerts_or_detections": alerts_count,
                    "primary_cusum_only": prim_hits,
                    "secondary_mewma_only": sec_hits,
                    "both_channels": both_hits,
                    "primary_share_pct": round((prim_hits + both_hits) / max(1, alerts_count) * 100, 1),
                    "secondary_share_pct": round((sec_hits + both_hits) / max(1, alerts_count) * 100, 1),
                })

    df_results = pd.DataFrame(results_table)
    final_csv = FINAL_OUTPUT_DIR / "comprehensive_benchmark_final.csv"
    df_results.to_csv(final_csv, index=False)
    print(f"\nSaved Final Benchmark Results: {final_csv}")

    df_attr = pd.DataFrame(attribution_records)
    final_attr_csv = FINAL_OUTPUT_DIR / "fusion_channel_attribution_final.csv"
    df_attr.to_csv(final_attr_csv, index=False)
    print(f"Saved Final Channel Attribution: {final_attr_csv}")

    print("\n" + "=" * 85)
    print("FINAL BENCHMARK EVALUATION SUMMARY (SEEDS 40000-40199)")
    print("=" * 85)
    for sc in df_results["scenario"].unique():
        print(f"\nScenario: {sc}")
        sub = df_results[df_results["scenario"] == sc]
        for _, r in sub.iterrows():
            if r["is_null"]:
                print(f"  • {r['method']:25s}: FAR = {r['point_estimate']:.4f} [95% CI: {r['ci_lower']:.4f}, {r['ci_upper']:.4f}] ({int(r['events_or_alerts'])}/{int(r['total_evaluated'])})")
            else:
                print(f"  • {r['method']:25s}: Det = {r['point_estimate']:5.1f}% [95% CI: {r['ci_lower']:5.1f}%, {r['ci_upper']:5.1f}%] | Median Delay = {r['median_delay_days']}d")


if __name__ == "__main__":
    run_final_test_evaluation()
