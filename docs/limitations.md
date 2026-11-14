# Model Limitations, Assumptions & Data Disclaimers

## 1. Decision Support Only — Not a Medical Device
MELIORA is developed as an engineering prototype for decision support and trend anomaly detection. It is **not an approved diagnostic tool or medical device**. It is designed to flag subtle statistical patterns for review by an assigned flight surgeon, who remains the sole clinical authority.

---

## 2. Simulated Telemetry & Proxy Datasets
- **Zero Astronaut Datasets:** NASA's official public competition materials do not release operational in-flight crew medical telemetry due to crew privacy and medical confidentiality policies.
- **Simulated Mission Telemetry:** In-flight scenario datasets (14-day scenarios) are generated mathematically from published resting physiological baselines, scripted missions, and simulated sensor noise.
- **PMData Proxy Reality:** Open-source PMData (CC BY 4.0) consists of 16 free-living terrestrial athletes logging Fitbit telemetry and self-reported wellness surveys. It is an empirical proxy for the relationship between wearable telemetry and self-reported fatigue/mood; it does not reflect microgravity cephalad fluid shifts, spaceflight neuro-vestibular adaptation, or closed-habitat environmental stressors.

---

## 3. Empirical Detection Sensitivity & Latency Bounds
Based on systematic Monte Carlo sweeps ($N=100$ repetitions per level, Wilson 95% CI) evaluated in [docs/benchmarks/shift_sweep.md](file:///c:/Projects/nasa-space-apps/docs/benchmarks/shift_sweep.md):
- **Shifts $\le 0.5\ \text{SD}$ (Sub-Threshold):** Detection rate is $0.0\% - 3.0\%$. These deviations are within natural circadian and sensor noise envelopes and are intentionally filtered by the $1.0\ \text{SD}$ deadband.
- **Shifts of $1.0\ \text{SD}$ (Emergence Threshold):** Detected at **$89.0\%$** (Wilson 95% CI: $[81.4\%, 93.7\%]$) when cumulative drift tracking (CUSUM) is enabled. Under naive rolling medians, a sustained $1.0\ \text{SD}$ shift is absorbed and missed ($0.0\%$ detection).
- **Shifts of $1.5\ \text{SD}$:** Detected at **$100.0\%$** (Wilson 95% CI: $[96.3\%, 100.0\%]$) with a median latency of 3.0 days.
- **Shifts $\ge 2.0\ \text{SD}$ (Acute Shift):** Detected at **$100.0\%$** with a median latency of 3.0 days (required for the 3-interval confirmation filter). Extreme acute multi-system shifts ($Z \le -3.5$ on $\ge 2$ metrics) trigger the 0-latency emergency fast-path.

---

## 4. Operational Heuristics
- **Readiness Scoring Bands:** The operational triage thresholds (NOMINAL $\ge 85.0$, WATCH $70.0 - 84.9$, CRITICAL $< 70.0$) are heuristic engineering guidelines, not clinical triage boundaries.
- **Score Weighting:** The $1.0\ \text{SD}$ deadband and $50.0\ \text{pts} / \text{SD}$ slope assign equal weight across available verified signals. Individual astronauts may exhibit idiosyncratic sensitivities that require clinician calibration.
- **SpO2 Sensor Ceiling:** Pulse oximetry saturates at 98–100% in healthy subjects, with instrument noise of $\pm 2\%$. A noise floor of `MIN_SD = 1.5%` is enforced to prevent sub-clinical saturation fluctuations from tripping alerts.

---

## 5. Space Radiation Dosimetry
- **DONKI Event Notifications:** Space weather feeds (e.g. NASA DONKI) provide qualitative or observational timeline event alerts (flares, coronal mass ejections, solar energetic particle events), not direct cabin micro-dosimetry.
- **Absorbed Dose vs. Dose Equivalent:** Onboard sensors report physical absorbed dose rate in $\mu Gy/h$ ($1\ Gy = 1\ J/kg$). NASA Space Permissible Exposure Limits (SPEL) reference biological effective dose equivalent in Sieverts ($Sv$), requiring energy- and ion-specific Radiation Quality Factors $Q(LET)$ ($w_R \approx 1-2$ for protons, $w_R \approx 20$ for heavy galactic cosmic ray ions).
