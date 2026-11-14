# AUDIT.md: Statistical & Architectural Audit of MELIORA Readiness Engine

**Author / Role:** Model Lead, MELIORA Team (NASA Space Apps Challenge 2026)  
**Date:** November 14, 2026  
**Status:** Phase 0 Complete — Baseline Audit before Refactoring  

---

## 1. What is Currently Implemented

The current codebase (`backend/src/modules/readiness/` and `test/`) implements:

1. **Telemetry Ingestion & Pivoting (`from_measurements`, `to_series`):**
   - Ingests long-format `HealthMeasurement` rows (`crew_member_id`, `measurement_type`, `value_numeric`, `measured_at`, `quality_status`).
   - Filters rows by `quality_status` against `ok_status=("VERIFIED",)`.
   - Pivots rows into a wide table and resamples along regular frequency bins (`freq="1D"` or `"3h"`) via mean aggregation.

2. **Univariate Rolling Median/MAD Detector (`_signed_z`):**
   - Computes rolling median and rolling Median Absolute Deviation (MAD scaled by 1.4826) over a rolling window (default 7 periods).
   - Employs a guard gap (`guard = alert_n - 1`) to delay baseline adaptation so acute shifts do not immediately drag their own baseline.
   - Enforces a clinical noise floor (`MIN_SD`) to prevent sensor noise from dominating on saturated metrics (e.g., pulse oximetry $\text{SpO}_2 = 1.5\%$).
   - Flags an acute alert when $Z \le -2.0$ for `alert_n = 3` consecutive periods.

3. **Fast-Path Acute Multi-System Detector:**
   - Triggers an immediate critical alert if $Z \le -3.5$ on $\ge 2$ metrics in a single interval without waiting for $N$ consecutive periods.

4. **Early-Mission Anchor CUSUM Detector (`_detect_cusum_drift`):**
   - Freezes an early-mission anchor baseline from the first 5 days (`anchor_len = 5`).
   - Accumulates adverse deviations exceeding a slack threshold ($k = 0.5$) with decision limit $h = 3.0$ and minimum duration of 4 periods.
   - Designed to catch insidious, slow drifts (e.g., cumulative sleep debt or microgravity fluid shifts) that rolling baselines absorb.

5. **Incident Clustering (`_cluster_alerts`):**
   - Groups correlated individual alerts into composite clinical incidents (`cardiorespiratory`, `neurobehavioral`, `multi_system`) to reduce alert fatigue.

6. **Independent Environmental Hazard Evaluation (`_evaluate_environmental_hazards`):**
   - Separates environmental radiation dose rate ($\mu\text{Gy/h}$) from personal physiological scoring, treating space weather as an independent timeline overlay.

7. **Heuristic Readiness Score & Capping:**
   - Heuristic score: $100 - 50 \times \text{mean excess deviation}$, smoothed by EWMA ($\text{span}=2$).
   - Categorization: NOMINAL ($\ge 85$), WATCH ($70-84$), CRITICAL ($< 70$), with alert-severity capping (active watch alert caps status at WATCH; active high alert caps status at CRITICAL).

8. **EWMA Point Forecast & Empirical Interval (`_forecast`):**
   - 1-step ahead EWMA point forecast ($\alpha = 0.4$).
   - Uncertainty interval estimated using the 10th and 90th percentiles of in-sample 1-step prediction errors.

---

## 2. Assumptions Made by Each Detector

| Detector | Core Assumptions | Vulnerability / Failure Mode |
| :--- | :--- | :--- |
| **Rolling Median / MAD** | • Nominal state is locally stationary.<br>• Anomalies are acute and short-lived relative to window length.<br>• Observations are i.i.d. across intervals. | • A slow ramp or sustained plateau lasting longer than `window + guard` is absorbed into the rolling baseline, wiping out detection.<br>• Ignores temporal autocorrelation. |
| **Early-Mission Anchor CUSUM** | • First 5 days represent true, nominal homeostasis free of pathology or launch adaptation artifacts.<br>• Observations are i.i.d. Gaussian random variables with known fixed variance.<br>• Slack $k=0.5$ and decision limit $h=3.0$ provide adequate Average Run Length (ARL). | • **Critical flaw:** Under AR(1) autocorrelated noise ($\phi = 0.4$), the variance of the cumulative sum is inflated by factor $\frac{1+\phi}{1-\phi} = 2.33\times$. This caused FAR to spike to $0.320$ false alerts/crew-fortnight.<br>• If early mission data contains sensor drift or high noise, the frozen anchor is corrupted permanently. |
| **Acute Multi-System Fast Path** | • Extreme shifts ($Z \le -3.5$) on two metrics are independent events under the null hypothesis.<br>• Sensor dropouts or transient artifacts do not co-occur. | • Correlated physiological pairs (e.g., systolic BP and diastolic BP; HR and HRV) violate independence; an artifact affecting hemodynamics will trigger false alarms if not conditioned on correlation. |
| **EWMA Forecasting & Error Bands** | • Error distribution is stationary, homoscedastic, and symmetric across the horizon.<br>• In-sample residual percentiles generalize out-of-sample without finite-sample correction. | • Lacks finite-sample conformal correction ($q = \lceil (n+1)(1-\alpha) \rceil / n$).<br>• In-sample residual evaluation exhibits severe empirical undercoverage ($60-70\%$ coverage against $80\%$ target). |
| **Readiness Scoring** | • All physiological metrics are mutually independent and can be averaged linearly.<br>• 1 SD deviation in heart rate is clinically equivalent to 1 SD deviation in $\text{SpO}_2$. | • Ignores covariance structure between vitals.<br>• Does not differentiate between adaptive physiological compensation and pathological deconditioning. |

---

## 3. How Seeds Are Currently Used

In the existing benchmark script (`test/benchmark_readiness_model.py`):
- **Null scenarios:** `seed = 2000 + seed` for `seed in range(n_seeds)` (seeds 2000–2199).
- **Shift sweep:** `seed = 4000 + int(sd * 100) + rep` (seeds 4050–4499).
- **Noise ablation null:** `seed = 7000 + s` (seeds 7000–7049).
- **Noise ablation shift:** `seed = 8000 + s` (seeds 8000–8049).
- **Forecast backtest:** Single fixed seed `999`.

### Methodological Deficiencies:
1. **No Strict Separation of Tuning vs. Final Evaluation:**
   - Thresholds ($k=0.5, h=3.0, Z=-2.0$) were tuned or adjusted by viewing the benchmark results, creating risk of data snooping and overfitting to synthetic generator parameters.
2. **Deterministic Seed Addition vs. Formal Branching:**
   - Iterating seeds by adding small integers (`2000 + seed`) does not guarantee decorrelated RNG state streams compared to modern hierarchical splitting (e.g., `np.random.SeedSequence.spawn`).
3. **No Frozen Calibration Artifact:**
   - Hyperparameters are hard-coded in Python source rather than calibrated on an isolated tuning set, frozen to a versioned JSON config, and evaluated strictly once on held-out seeds.

---

## 4. Comprehensive Inventory of Statistical & Engineering Flaws

### Flaw 1: Unit of Independence & Confidence Interval Formulation
- In prior iterations, false alert counts were reported without defining the exact exposure denominator. In survival and alarm analysis, the unit of independence is the **simulation trajectory** (one crew member over a mission duration, e.g., 14 days), NOT the individual timestamp reading.
- Reporting "FAR = 0.0000" for 0 alerts in 200 runs violates statistical principles. With $N=200$ null runs and zero observed events, the Clopper-Pearson or Poisson upper bound is $\approx 3/N = 0.015$ (Rule of Three). It must be reported as a **one-sided upper confidence bound**, never as an absolute zero.

### Flaw 2: AR(1) Variance Inflation in CUSUM
- Autoregressive dependence induces long-memory random walks in cumulative sum charts. When $\phi = 0.4$, the effective sample size is reduced by a factor of $(1-\phi)/(1+\phi) = 0.429$, and the variance of partial sums is inflated by $2.33\times$.
- Without prewhitening ($e_t = x_t - \hat{\phi} x_{t-1}$) or an autocorrelation-corrected decision limit ($h \sqrt{\frac{1+\phi}{1-\phi}}$), standard CUSUM produces unacceptable false alert rates on real telemetry.

### Flaw 3: Absence of Multivariate Mahalanobis / LedoitWolf in Production Code
- Task 4 requests verification of Ledoit-Wolf shrinkage for multivariate anomaly detection. In the current repository, **no multivariate covariance detector exists in the live request path**. The model only runs isolated univariate z-scores followed by rule-based heuristic clustering.
- Subtle multivariate drifts—where 4 vitals each move by only $0.8\text{ SD}$ in a coordinated pathological pattern—are completely missed by univariate thresholds ($Z \le -2.0$), but would easily trigger a Mahalanobis distance alert.

### Flaw 4: Conformal Forecast Undercoverage
- The current interval calculation in `_forecast`:
  ```python
  lo, hi = np.percentile((s - level.shift(1)).dropna(), [10, 90])
  ```
  uses simple in-sample empirical percentiles.
- Under finite-sample theory, the conformal quantile for coverage $1-\alpha$ requires index $p = \lceil (n+1)(1-\alpha) \rceil / n$. For small samples ($n=7$ to $28$), using nominal $90\%$ quantile leads to systematic undercoverage ($60\%-70\%$).
- Furthermore, errors are not computed on a separate calibration split, violating conformal prediction exchangeability/split guarantees.

### Flaw 5: Ephemeral, Unfrozen Baseline Architecture
- In `backend/src/modules/readiness/model.py`, the baseline is computed dynamically on the fly on every HTTP request from whatever raw data happens to be returned by SQL.
- There is no persistent frozen baseline entity:
  - No baseline versioning (`version_id`, `created_at`).
  - No explicit recalibration procedure or audit trail.
  - No logging of calibration window boundaries, observation counts, or excluded corrupted packets.
  - No baseline confidence / data-sufficiency rating (`insufficient`, `low`, `moderate`, `high`).
  - If a patient starts deteriorating, querying the API over time can silently shift the baseline if the window slides, masking chronic illness.

### Flaw 6: Unhandled Missing Signals in Synchronized Feature Vectors
- When astronauts miss self-reports (mood, stress, fatigue) or wear sensors intermittently, long-format pivoting leaves `NaN`s in the feature vector.
- The system currently applies `mean(axis=1, skipna=True)` on excess deviations. If 8 out of 10 signals are missing, the score is calculated from the remaining 2 signals with equal visual confidence on the dashboard. There is no explicit data-sufficiency categorization or missing-signal marginalization policy.

### Flaw 7: Alert Fatigue from Repeated Alarms & Lack of Cooldown
- In a multi-day drift episode, an alert fires on day 8, day 9, day 10, day 11, etc.
- In naive counting, this counts as 4 separate alerts for a single underlying event, artificially inflating FAR and causing alert fatigue for flight surgeons. An alert cooldown / de-duplication mechanism is required.

---

## 5. Audit Action Plan & Transition to Implementation

With this audit established, the implementation proceeds through the following sequential tasks:

1. **Architecture & Configuration (`eval/config.py`, `eval/config.yaml`):**
   - Formalize disjoint seed sets: `TUNE_SEEDS`, `VALIDATION_SEEDS`, `FINAL_TEST_SEEDS`.
   - Assert disjointness in code with unit tests.
2. **Task 1: Rigorous Statistical Validation Engine:**
   - Establish unified FAR calculation (alerts per crew-fortnight with exposure in crew-days).
   - Implement exact Clopper-Pearson, Jeffreys, and exact Poisson confidence intervals.
   - Separate episode-level detection vs. observation-level metrics.
   - Implement alert cooldown and de-duplication.
3. **Task 2: Autocorrelation Mitigation for CUSUM & EWMA:**
   - Benchmark AR(1) across $\phi \in \{0, 0.2, 0.4, 0.6, 0.8\}$.
   - Implement prewhitened residual CUSUM and variance-inflated EWMA.
   - Calibrate on `TUNE_SEEDS` and evaluate on `FINAL_TEST_SEEDS`.
4. **Task 3: Production Frozen Baseline Entity & Recalibration API:**
   - Define baseline metadata model, robust statistics (median + MAD), and data-sufficiency confidence tiers.
   - Implement explicit recalibration service function and API endpoint with immutability guarantees.
5. **Task 4: Multivariate Ledoit-Wolf Mahalanobis Detector:**
   - Implement synchronized feature vector assembly with explicit sub-covariance marginalization (no imputation).
   - Standardize via frozen baseline and compute Ledoit-Wolf shrinkage covariance.
   - Calibrate empirical vs. Chi-square thresholds and compute feature-level squared distance decompositions.
6. **Task 5: Finite-Sample Conformal Prediction & Adaptive Horizons:**
   - Implement finite-sample corrected split conformal intervals and adaptive rolling conformal variants.
   - Eliminate temporal and participant leakage; benchmark against persistence and mean baselines.
7. **One-Command Reproduction & Deliverable Artifacts:**
   - Deliver `python -m eval.run_all --config eval/config.yaml` generating all CSVs, figures, `VALIDATION_REPORT.md`, and `JUDGE_SUMMARY.md`.
