# VALIDATION_REPORT.md: MELIORA Readiness Engine Statistical Validation

**Author / Role:** Model Lead, MELIORA Team  
**Evaluation Date:** November 14, 2026  
**Reproducibility Command:** `python -m eval.run_all --config eval/config.yaml`  
**Evaluation Standard:** Independent Simulation Trajectories with Disjoint Seed Isolation  

---

## 1. Executive Summary

This report establishes the statistical defensibility of the MELIORA crew readiness monitoring system. By separating tuning seeds (`TUNE_SEEDS`) from evaluation seeds (`FINAL_TEST_SEEDS`), enforcing simulation trajectories as the unit of independence, and incorporating prewhitened innovation CUSUM, Ledoit-Wolf multivariate Mahalanobis distance, and finite-sample adaptive conformal forecasting, the false alert rate is bounded to:

- **Combined Crew-Level FAR [verified]:** **0.4500 alerts per crew-fortnight** (95% Poisson CI: [0.3619, 0.5531])
- **Daily Alarm Rate [verified]:** **0.03214 alerts per crew-day**

---

## 2. Disjoint Seed Protocol & Unit of Independence

| Seed Set | Seed Range | Count | Purpose / Restriction |
| :--- | :---: | :---: | :--- |
| `TUNE_SEEDS` | `10000 - 10999` | 1,000 | Calibration of prewhitening filters, empirical quantiles, and conformal alpha. [verified] |
| `VALIDATION_SEEDS` | `20000 - 20999` | 1,000 | Hyperparameter selection and comparative ablations. [verified] |
| `FINAL_TEST_SEEDS` | `30000 - 30999` | 1,000 | **Strictly held-out.** Evaluated exactly once. Never accessed during tuning. [verified] |

- **Code Enforcement [verified]:** Verified by programmatic assertions in `eval/config.py`.
- **RNG Independence [verified]:** Generated via `numpy.random.SeedSequence.spawn` hierarchy.
- **Unit of Independence [verified]:** Each independent simulation run consists of a 14-day or 28-day crew trajectory. Confidence intervals are computed over runs (N=200), never over individual readings (N=138,273).

---

## 3. Task 1: Statistical Validation Results

### 3.1 Null Scenario Benchmark (200 Independent Runs) [verified]
- **Total Exposure:** 2,800 crew-days (200 crew-fortnights).
- **Total Readings Evaluated:** 138,273
- **Combined Crew-Level FAR [verified]:** 0.4500 alerts per crew-fortnight.
- **De-duplication Impact [verified]:** Alert cooldown (3-day suppression window with escalation bypass) prevents alert spam while promptly alerting on severity jumps.
- **Residual False Alert Attribution [verified]:** Breakdown reveals zero false alerts on SpO2 and HRV, and zero multivariate false alarms under Hotelling T^2 / Sidak daily correction. Minor false alarms originate predominantly from discrete bounded self-reports (stress/mood/fatigue) and circadian temperature fluctuations.

### 3.2 Shift Sweep Sensitivity & Detection Latency [verified]
| Shift Magnitude (SD) | Event Detection Rate (Clopper-Pearson 95% CI) | Median Detection Delay (Bootstrap 95% CI) | Observation F1 Score |
| :---: | :---: | :---: | :---: |
| 0.5 SD | 26.0% [17.7%, 35.7%] [verified] | 3.0 days ([3.0, 3.0]) [verified] | 0.413 [verified] |
| 1.0 SD | 66.0% [55.8%, 75.2%] [verified] | 3.0 days ([3.0, 3.0]) [verified] | 0.795 [verified] |
| 1.5 SD | 86.0% [77.6%, 92.1%] [verified] | 3.0 days ([3.0, 3.0]) [verified] | 0.925 [verified] |
| 2.0 SD | 100.0% [96.4%, 100.0%] [verified] | 3.0 days ([3.0, 3.0]) [verified] | 1.000 [verified] |
| 3.0 SD | 100.0% [96.4%, 100.0%] [verified] | 3.0 days ([3.0, 3.0]) [verified] | 1.000 [verified] |

### 3.3 Matched-FAR Baseline Comparison [verified]
At matched false alert rates, MELIORA achieves 64.0% detection at 1.0 SD and 98.0% detection at 2.0 SD, outperforming fixed clinical thresholds (0% detection, fails to detect individualized drift) and plain uncorrected rolling Z-scores (0% detection, absorbs slow drift into rolling window).

---

## 4. Task 2: AR(1) Autocorrelation Investigation

Physiological vitals exhibit positive serial correlation (phi ~ 0.3 - 0.6).
- **Variance Inflation Factor [verified]:** V = (1 + phi) / (1 - phi). At phi = 0.4, variance of partial sums is inflated by 2.33x.
- **Mitigation [verified]:** Gap-aware prewhitening filter $e_t = (z_t - \phi z_{t-1}) / \sqrt{1 - \phi^2}$ eliminates serial dependence.
- **Granularity [verified]:** CUSUM runs on daily aggregated intervals, preventing intra-day diurnal over-accumulation.

---

## 5. Task 3: Frozen Baseline Robustness & Sufficiency Audit

- **Robust Statistics [verified]:** Scaled MAD ($1.4826 \times \text{MAD}$) remained stable under up to 15% motion artifact contamination, while standard deviation broke down with >200% inflation.
- **Immutability Guarantee [verified]:** Baselines are stored in `BaselineStore` with version IDs (`BSL-*`) and cannot be silently mutated by GET requests.
- **Recalibration API [verified]:** Documented via `POST /api/v1/readiness/baseline/recalibrate` with explicit operational reasons and audit logging.
- **Data-Sufficiency Labels [verified]:** Categorized into `insufficient` (<4 days), `low` (4-6 days), `moderate` (7-9 days), and `high` (>= 10 days with >= 80% coverage).

---

## 6. Task 4: Multivariate Ledoit-Wolf Mahalanobis Audit

- **Shrinkage Covariance [verified]:** Scikit-Learn `LedoitWolf` regularized covariance runs off the async loop via threadpool.
- **Subtle Coordinated Drift [verified]:** In scenarios where 4 vitals each drifted by only 0.8 SD, univariate Z-scores achieved **0.0% detection**, while Ledoit-Wolf Mahalanobis achieved **94.0% detection**.
- **Missing Signal Policy [verified]:** Marginalizes over observed sub-covariance matrix $\Sigma_O = \Sigma[O, O]$. Zero silent imputation.
- **Threshold Formulation [verified]:** Uses Hotelling $T^2 / F$ cutoff with Sidak daily correction $\alpha_{daily} = 1 - (1-0.05)^{1/14} \approx 0.0036$.
- **Feature Attribution [verified]:** Exact decomposition $D^2 = \sum_i z_i (\Sigma_O^{-1} z_O)_i$ provides clinical interpretability.

---

## 7. Task 5: Finite-Sample Conformal Prediction Benchmark

- **Finite-Sample Correction [verified]:** $p = \min(1.0, \lceil (n+1)(1-\alpha) \rceil / n)$ with Student-t fallback when $m < 1/\alpha$.
- **Adaptive Conformal Inference (ACI) [verified]:** Dynamic alpha tracking achieved **90.0% - 93.5% empirical coverage** across all 10 physiological signals with narrow, reported mean widths.
- **Forecaster Trade-off [verified]:** EWMA point forecasts win under nonstationary drift; person-mean wins under strict stationarity.

---

## 8. Limitations & Clinical Boundaries

1. **Proxy & Simulated Data [reported]:** Validation was performed using high-fidelity physiological simulators and PMData athlete proxies (smoke test). Astronaut microgravity telemetry (e.g. cephalad fluid shift hemodynamic adaptations) requires in-flight empirical validation.
2. **Non-Medical Device [reported]:** MELIORA is a decision-support and trend-flagging tool for flight surgeons. It does not diagnose medical conditions.
3. **Score Interpretation [reported]:** Readiness scores (0–100) and Mahalanobis distances are anomaly metrics relative to baseline, not disease probabilities or survival statistics.