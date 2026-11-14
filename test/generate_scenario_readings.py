"""
generate_scenario_readings.py - 14 days of SIMULATED crew readings with scripted stories, in the
same schema as test/health_readings.json (so test/seed_test_db.py can load it).

    python test/generate_scenario_readings.py                # 14 full days ending yesterday 21:00
    python test/generate_scenario_readings.py --end 2026-11-14T21:00:00   # pick the last reading (use 21:00)

Writes test/health_readings_scenario.json. Seed it with:  python test/seed_scenario.py --clean

Stories (all fictional, built from the README's resting ranges; NOT real astronaut data):
  CREW-001, 002, 006  stable
  CREW-003 Caduceus   deteriorates over the last 4 days: sleep down, stress/fatigue up, HR up, SpO2 down
  CREW-004 Kepler     solar particle event in the last 3 days: radiation spike, sleep and stress suffer
  CREW-005 Newton     slow fatigue drift (elevated monitoring)
"""
import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

DAYS = 14
VITAL_EVERY_H = 3
SENSOR_METHOD = "WEARABLE_SENSOR"      # known-valid value from your seed script
SELF_REPORT_METHOD = "MANUAL_ENTRY"      # self-report input method from HealthMeasurement model
NS = uuid.UUID("12345678-1234-5678-1234-567812345678")

CREW = {  # crew_id -> uuid (from the seed script) and baseline vitals (README ranges)
    "CREW-001": ("c1111111-1111-4111-8111-111111111111", dict(hr=62, sbp=114, dbp=72, spo2=98.4, temp=36.8)),
    "CREW-002": ("c2222222-2222-4222-8222-222222222222", dict(hr=64, sbp=116, dbp=74, spo2=98.2, temp=36.9)),
    "CREW-003": ("c3333333-3333-4333-8333-333333333333", dict(hr=61, sbp=112, dbp=71, spo2=98.6, temp=36.8)),
    "CREW-004": ("c4444444-4444-4444-8444-444444444444", dict(hr=58, sbp=112, dbp=72, spo2=98.8, temp=36.6)),
    "CREW-005": ("c5555555-5555-4555-8555-555555555555", dict(hr=70, sbp=124, dbp=80, spo2=97.5, temp=37.0)),
    "CREW-006": ("c6666666-6666-4666-8666-666666666666", dict(hr=64, sbp=120, dbp=78, spo2=98.2, temp=36.8)),
}
UNITS = {"heart_rate": "bpm", "blood_pressure_systolic": "mmHg", "blood_pressure_diastolic": "mmHg",
         "spo2": "%", "body_temperature": "degC", "sleep_duration": "hours", "stress": "score_1_5",
         "mood": "score_1_5", "fatigue": "score_1_5", "radiation_dose_rate": "uGy/h"}


def effects(crew_id: str, d: int) -> dict:
    """Additive story effects on day index d (0 = first day, DAYS-1 = last)."""
    e = {}
    if crew_id == "CREW-003":
        r = min(1.0, max(0, d - (DAYS - 5)) / 2)       # ramps in over the last 4 days
        e = dict(sleep_duration=-2.3 * r, stress=1.8 * r, fatigue=2.0 * r, mood=-1.3 * r,
                 heart_rate=9 * r, spo2=-2.2 * r, body_temperature=0.35 * r)
    elif crew_id == "CREW-004":
        spike = {DAYS - 3: 14, DAYS - 2: 28, DAYS - 1: 20}.get(d, 0)   # solar particle event, last 3 days
        e = dict(radiation_dose_rate=spike, sleep_duration=-1.4 if d >= DAYS - 2 else 0,
                 stress=1.6 if d >= DAYS - 2 else 0)
    elif crew_id == "CREW-005":
        k = max(0, d - 5)
        e = dict(fatigue=0.25 * k, sleep_duration=-0.18 * k, mood=-0.1 * k)
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", help="UTC end time, ISO format (default: now)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "health_readings_scenario.json"))
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    if a.end:
        end = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
    else:                                                    # last slot (21:00) of yesterday: whole days only
        end = datetime.now(timezone.utc).replace(hour=21, minute=0, second=0, microsecond=0) - timedelta(days=1)
    end = end.replace(minute=0, second=0, microsecond=0)
    end -= timedelta(hours=end.hour % VITAL_EVERY_H)
    start = (end - timedelta(days=DAYS - 1)).replace(hour=0)
    rng = np.random.default_rng(a.seed)
    out = []

    def add(crew_id, mtype, value, ts, method):
        cuuid = CREW[crew_id][0]
        iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append({
            "id": str(uuid.uuid5(NS, f"{crew_id}|{mtype}|{iso}")),   # stable ids: re-seeding is idempotent
            "crew_id": crew_id, "crew_member_id": cuuid, "measurement_type": mtype,
            "value_numeric": round(float(value), 2), "unit": UNITS[mtype],
            "measured_at": iso, "recorded_at": iso, "input_method": method,
            "provenance": {"source": "simulated_scenario"}, "quality_status": "VERIFIED",
            "context_metadata": {"scenario": True},
        })

    for crew_id, (_, b) in CREW.items():
        ts = start
        while ts <= end:
            d = (ts.date() - start.date()).days
            e = effects(crew_id, min(d, DAYS - 1))
            circ = -1.0 if 0 <= ts.hour < 6 else 0.0                 # lower at night
            add(crew_id, "heart_rate", rng.normal(b["hr"] + 6 * circ, 1.8) + e.get("heart_rate", 0), ts, SENSOR_METHOD)
            add(crew_id, "blood_pressure_systolic", rng.normal(b["sbp"], 2.0), ts, SENSOR_METHOD)
            add(crew_id, "blood_pressure_diastolic", rng.normal(b["dbp"], 1.5), ts, SENSOR_METHOD)
            add(crew_id, "spo2", min(100, rng.normal(b["spo2"], 0.3) + e.get("spo2", 0)), ts, SENSOR_METHOD)
            add(crew_id, "body_temperature", rng.normal(b["temp"] + 0.3 * circ, 0.12) + e.get("body_temperature", 0), ts, SENSOR_METHOD)
            if ts.hour == 6:                                          # nightly sleep, logged in the morning
                add(crew_id, "sleep_duration", np.clip(rng.normal(7.2, 0.4) + e.get("sleep_duration", 0), 3, 10), ts, SENSOR_METHOD)
                add(crew_id, "radiation_dose_rate", max(0.0, rng.normal(12.0, 1.0) + e.get("radiation_dose_rate", 0)), ts, SENSOR_METHOD)
            if ts.hour == 18:                                         # evening self-report (1-5 scale)
                for m, mu, sd in (("stress", 2.0, 0.6), ("mood", 4.0, 0.6), ("fatigue", 2.0, 0.6)):
                    v = np.clip(round(rng.normal(mu, sd) + e.get(m, 0)), 1, 5)
                    add(crew_id, m, v, ts, SELF_REPORT_METHOD)
            ts += timedelta(hours=VITAL_EVERY_H)

    Path(a.out).write_text(json.dumps(out, indent=2))
    print(f"Wrote {len(out)} readings for {len(CREW)} crew ({DAYS} days) to {a.out}")


if __name__ == "__main__":
    main()
