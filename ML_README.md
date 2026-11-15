MELIORA: readiness model
This is the ML side of MELIORA. It takes a crew member's daily health readings and turns them into
one number, a readiness score from 0 to 100, plus a short forecast and an alert when something starts
drifting.

The part I care most about is that the score is relative to the person. A resting heart rate of 62 is fine
for one astronaut and a warning sign for another, so the model never compares anyone to a
population average. It compares each person to their own recent normal.
Why it works this way
Real astronaut health data is private, and what NASA publishes for this challenge is mostly articles,
not datasets. So there was nothing to train a population model on even if we wanted to. A personal
baseline fixes that: all you need is a few days of one person's data, and the model gets sharper the
longer a mission runs, which is also when it matters most.
What goes in
Everything lives in a single long-format table (HealthMeasurement), one row per reading:
- crew member: who the reading belongs to
- metric: e.g. resting heart rate, sleep duration, HRV
- value: the reading itself
- timestamp: when it was recorded
Long format means adding a new signal is a new metric value, not a schema change. That mattered
a lot when we were still deciding what to track halfway through the hackathon.

The model uses ten continuous signals:
- heart_rate — bpm; bidirectional; MIN_SD = 3; Cardiorespiratory
- blood_pressure_systolic — mmHg; bidirectional; MIN_SD = 4; Cardiorespiratory
- blood_pressure_diastolic — mmHg; bidirectional; MIN_SD = 3; Cardiorespiratory
- spo2 — %; higher is better; MIN_SD = 1.5; Cardiorespiratory
- hrv — ms; higher is better; MIN_SD = 8; Cardiorespiratory
- body_temperature — °C; bidirectional; MIN_SD = 0.2; Environmental/Systemic
- sleep_duration — hours; higher is better; MIN_SD = 0.6; Neurobehavioral
- fatigue — scale 1–5; lower is better; MIN_SD = 1.0; Neurobehavioral
- stress — scale 1–5; lower is better; MIN_SD = 1.0; Neurobehavioral
- mood — scale 1–5; higher is better; MIN_SD = 1.0; Neurobehavioral
Radiation dose rate (μGy/h) is tracked separately as an environmental timeline overlay. It is not
included in biological readiness scoring. Dose rate (μGy/h) is also kept distinct from dose-equivalent
units (Sv).
How the score is built
1. Baseline. For each person and metric, calibration uses 7–14 days of pre-mission or in-flight
   quarantine data to establish frozen personal medians and MAD-based spreads. The baseline is
   immutable during scoring. A 7-day analysis window is used, with at least 3 valid periods required.
2. Aggregation. Daily means are used for operational readiness triage; 3-hour aggregates support
   higher-frequency clinical review.
3. Deviation. For each signal, calculate a robust standardized deviation:
   Z = (x - center) / max(1.4826 × MAD, MIN_SD)
   Direction is then oriented so positive means improvement and negative means deterioration:
   bidirectional signals use -|Z|; higher-is-better signals use Z; lower-is-better signals use -Z.
4. Combine. Apply a 1-SD deadband: excess = max(0, -Z_oriented - 1.0).
   The current specification uses an equal-weight average across available signals; no separate
   per-signal weights are specified. The raw score is
   100 - 50 × average(excess), clipped to 0–100.
5. Smooth and categorize. Readiness is an EWMA of the raw score with α = 0.66, clipped to
   0–100. Categories are NOMINAL (≥85), WATCH (70–84.9), and CRITICAL (<70).
   An active drift alert caps the category at WATCH; a high-severity alert or multivariate drift can
   immediately cap it at CRITICAL.
6. Data-quality gate. More than 6 consecutive identical readings (flatline) or an impossible jump
   (for example, ΔHR >60 bpm) changes the data status to FAULTY_SENSOR or
   INSUFFICIENT_DATA, rather than treating the reading as a physiological change.
Forecast and drift alerts
The forecast uses Finite-Sample Adaptive Conformal Inference (ACI), with an EWMA update
(α = 0.40) to adapt the error quantile. The finite-sample empirical quantile uses
ceil((m + 1)(1 − α)) / m; when fewer than 10 calibration errors are available, a parametric
Student-t fallback is used. The forecast horizon is 24–48 hours (1–2 days). The reported empirical
prediction coverage in the evaluated runs is 90.0–93.5%; this is an observed result, not a guarantee
for every crew member or future mission.

Slow univariate drift is detected using a prewhitened innovation CUSUM:

e_t = (z_t − φ z_(t−1)) / sqrt(1 − φ²)

The detector resets across gaps greater than 1.5 days. Its reference value is k = 0.5 SD and its
threshold is h = 3.17 SD, calibrated on tuning seeds to target no more than 0.08 false alerts per
fortnight.

A second, multivariate detector uses Ledoit–Wolf covariance shrinkage and a Mahalanobis
distance / Hotelling T² statistic. Its threshold uses a finite-sample F-distribution cutoff, with a
daily Sidak family-wise correction of
α_daily = 1 − (1 − 0.05)^(1/14) ≈ 0.00366.
When signals are missing, the detector uses the observed sub-covariance
Σ_O = Σ[O,O]. Feature contributions are attributed additively as
D²_j = z_j (Σ_O⁻¹ z_O)_j.
Data
Simulated crew data. A 14-day scenario generator (seed_scenario.py) produces crew
members with a baseline period and then a planted decline, so we can check that the model
actually catches it.

PMData (CC BY 4.0), a public wellness dataset of real people's sleep, heart rate and activity
logs. We use it as a stand-in for real astronaut data, which is not available. It is a proxy, not the
same population, and the results should be read that way.
Running it
# fill a database with a demo scenario
python seed_scenario.py

# train the wellness model
python train_wellness_model.py
API endpoints, served by the FastAPI backend:
- GET /api/v1/readiness returns the score, forecast and alerts for one crew member
- GET /api/v1/readiness/overview returns the whole crew at a glance
Results
The following are held-out simulation validation results, not astronaut outcomes or PMData
training results. The evaluation used 200 independent trajectories and 1,400 scored monitoring
crew-days (207,537 physiological readings). Calibration days 0–6 were excluded from false-alert
rate calculations. Daily means included realistic intra-day autocorrelation (φ_intra = 0.75).

Nominal-condition false-alert rate
- Plain Z: 0.080 alerts per crew-fortnight; 95% Poisson CI = 0.035–0.158; 0.0057 alerts per crew-day
- Per-signal CUSUM: 0.050 alerts per crew-fortnight; 95% Poisson CI = 0.016–0.117; 0.0036 alerts per crew-day
- MELIORA Dual Fusion: 0.070 alerts per crew-fortnight; 95% Poisson CI = 0.028–0.144; 0.0050 alerts per crew-day
Detection on planted changes
- Single HR shift, 1 SD
  - Plain Z: 47.0% detection (95% CI 39.9–54.2); median delay 2.5 days
  - Per-signal CUSUM: 77.0% (70.5–82.6); median delay 4 days
  - MELIORA Dual Fusion: 77.5% (71.1–83.1); median delay 4 days
- Single HR shift, 2 SD
  - All three detectors: 100%; median delay 0 days for Z and 1 day for CUSUM/Fusion
- Four-vital shift, 0.5 SD
  - Plain Z: 17.5% (12.5–23.5); median delay 2 days
  - Per-signal CUSUM: 25.0% (19.2–31.6); median delay 5 days
  - MELIORA Dual Fusion: 69.5% (62.6–75.8); median delay 3 days
- Four-vital shift, 0.8 SD
  - Plain Z: 54.5% (47.3–61.5); median delay 2 days
  - Per-signal CUSUM: 87.5% (82.1–91.7); median delay 4 days
  - MELIORA Dual Fusion: 99.0% (96.4–99.9); median delay 1.5 days
- HR ramp, 1.5 SD
  - Plain Z: 80.0% (73.8–85.3); median delay 4 days
  - Per-signal CUSUM: 90.0% (85.0–93.8); median delay 5 days
  - MELIORA Dual Fusion: 88.5% (83.2–92.6); median delay 4 days
Dual Fusion was strongest on the tested multi-signal shifts, but it did not lead every scenario:
per-signal CUSUM performed better on the 1.5-SD HR ramp. These results describe the stated
simulation setup only. The PMData leave-one-person-out training/evaluation run has not been
completed, so no PMData model-performance result is claimed.
Limitations
Trained on simulated data and a civilian proxy dataset. It has never seen a real astronaut, and
we are not claiming it would transfer cleanly.

Needs a stretch of history before the baseline means anything. The first few days of a mission
give weak scores.

It flags that something has changed, not why. It is a prompt for the flight surgeon to look, not
a diagnosis.

Not a medical device.
Not done yet
- Full PMData training run and evaluation
- Heart-rate peaks during exercise as an extra signal
- Radiation exposure from NASA's DONKI space weather data
- Optional comparison against pretrained time-series models (Granite TTM, Chronos-2)
Author
Lekisha Anvi Balaji (@lekiii22): readiness model and the ML pipeline.