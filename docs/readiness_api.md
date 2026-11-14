# Crew Readiness API Reference

## Endpoints

- `GET /api/v1/readiness`: Detailed readiness assessment, 1-step forecast, drift alerts, and grouped incident patterns for a specific crew member.
- `GET /api/v1/readiness/overview`: Multi-crew overview cards for flight surgeons (no series history payload).

---

## Field Semantics & Schema Changes

> [!IMPORTANT]
> **Semantic Clarification on `status` vs `data_status` vs `readiness_category`:**
> In earlier versions, `status` reported `"OK"` solely to indicate that the database returned $\ge 10$ verified observations. This created a visual contradiction when an astronaut had a low readiness score and active alerts while displaying `"status": "OK"`.
> 
> The schema now cleanly separates pipeline sufficiency from clinical decision-support status:
> - **`data_status`**: Pipeline health. Either `"COMPLETE"` ($\ge 10$ observations) or `"INSUFFICIENT_DATA"` ($< 10$ observations).
> - **`readiness_category`**: Heuristic operational triage category:
>   - `"NOMINAL"`: Score $\ge 85.0$ and no active alerts.
>   - `"WATCH"`: Score $70.0 - 84.9$ or presence of a cumulative/sub-acute alert.
>   - `"CRITICAL"`: Score $< 70.0$ or presence of multiple acute alerts.
> - **`status`**: Primary operational status aligned directly with `readiness_category`. An active alert caps the status at `WATCH` or `CRITICAL` so that status and alerts never contradict each other.

---

## Score Calculation & Weight Derivation

The 0–100 readiness score is derived from excess normalized deviation against the astronaut's own recent rolling baseline:

$$\text{Score} = \max\left(0, \min\left(100, 100 - 50 \times \overline{\text{excess\_deviation}}\right)\right)$$

Where:
- $\text{excess\_deviation}_m = \max\left(0, -oriented\_z_m - 1.0\right)$
- **Deadband ($1.0\ \text{SD}$):** Fluctuations within $1.0\ \text{SD}$ of own baseline carry $0$ penalty, accommodating standard circadian and biological rhythmicity.
- **Slope ($50\ \text{pts} / \text{SD}$):** Each $1.0\ \text{SD}$ of average excess deviation across indicators reduces the overall readiness score by 50 points. An astronaut whose indicators are on average $2.0\ \text{SD}$ worse than baseline receives a score of $50$.
- **Equal Weighting:** Indicators are weighted equally across all verified physiological signals present in the evaluation window.
- **Heuristic Bands:** 
  - $\ge 85.0$: NOMINAL (average excess deviation $< 0.3\ \text{SD}$)
  - $70.0 - 84.9$: WATCH (average excess deviation $0.3 - 0.6\ \text{SD}$)
  - $< 70.0$: CRITICAL (average excess deviation $> 0.6\ \text{SD}$)

---

## Example Response (`GET /api/v1/readiness?crew_id=c3333333-3333-4333-8333-333333333333`)

```json
{
  "crew_id": "c3333333-3333-4333-8333-333333333333",
  "status": "CRITICAL",
  "data_status": "COMPLETE",
  "readiness_category": "CRITICAL",
  "readiness": 61.0,
  "readiness_series": [
    {"t": "2026-11-07T00:00:00Z", "score": 98.8},
    {"t": "2026-11-08T00:00:00Z", "score": 98.8},
    {"t": "2026-11-09T00:00:00Z", "score": 98.4},
    {"t": "2026-11-10T00:00:00Z", "score": 91.2},
    {"t": "2026-11-11T00:00:00Z", "score": 77.4},
    {"t": "2026-11-12T00:00:00Z", "score": 67.2},
    {"t": "2026-11-13T00:00:00Z", "score": 61.0}
  ],
  "forecast": {
    "heart_rate": {"next": 67.47, "lo": 66.15, "hi": 72.56},
    "spo2": {"next": 96.76, "lo": 95.61, "hi": 96.83},
    "sleep_duration": {"next": 5.44, "lo": 4.31, "hi": 5.67},
    "fatigue": {"next": 3.48, "lo": 3.11, "hi": 4.73}
  },
  "drift_alerts": [
    {
      "metric": "heart_rate",
      "direction": "high",
      "severity": "high",
      "message": "heart_rate high vs own baseline for 3 readings in a row (~3.2 SD)"
    },
    {
      "metric": "sleep_duration",
      "direction": "low",
      "severity": "high",
      "message": "sleep_duration low vs own baseline for 3 readings in a row (~2.9 SD)"
    },
    {
      "metric": "fatigue",
      "direction": "high",
      "severity": "watch",
      "message": "fatigue cumulative elevated drift vs mission reference over 5 intervals (current 4.0 vs ref 2.0)"
    }
  ],
  "incidents": [
    {
      "incident_id": "INC-MULTI-9B7C12",
      "severity": "high",
      "title": "Multi-System Strain: Combined Cardiopulmonary & Neurobehavioral Degradation",
      "metrics_involved": ["heart_rate", "sleep_duration", "fatigue"],
      "summary": "Concurrent acute drift across 3 vital indicators (heart_rate, sleep_duration, fatigue). Recommends flight surgeon clinical review."
    }
  ],
  "environmental_alerts": [],
  "observations_used": 630,
  "disclaimer": "Decision support only. Flags trends for review by a flight surgeon; not a diagnosis."
}
```
