"""eval/config.py - Centralized configuration and disjoint seed ranges for MELIORA evaluation.

Ground Rule:
- TUNE_SEEDS: Exclusively used to calibrate thresholds, prewhitening filters, and conformal quantiles.
- VALIDATION_SEEDS: Used for model/detector hyperparameter selection (e.g. CUSUM vs EWMA parameters).
- FINAL_TEST_SEEDS: Evaluated strictly ONCE with frozen parameters. Never touched during tuning.
"""
from pathlib import Path
import sys
import yaml

# Root paths
EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FROZEN_THRESHOLDS_PATH = EVAL_DIR / "calibrated_thresholds_v1.json"
CONFIG_YAML_PATH = EVAL_DIR / "config.yaml"

# 1. Disjoint Seed Ranges (1,000 seeds each)
TUNE_SEEDS = list(range(10000, 11000))
VALIDATION_SEEDS = list(range(20000, 21000))
FINAL_TEST_SEEDS = list(range(30000, 31000))

# Enforce strict disjointness assertion in code
assert set(TUNE_SEEDS).isdisjoint(set(VALIDATION_SEEDS)), "Fatal: TUNE and VALIDATION seeds overlap!"
assert set(TUNE_SEEDS).isdisjoint(set(FINAL_TEST_SEEDS)), "Fatal: TUNE and FINAL_TEST seeds overlap!"
assert set(VALIDATION_SEEDS).isdisjoint(set(FINAL_TEST_SEEDS)), "Fatal: VALIDATION and FINAL_TEST seeds overlap!"

# 10 Physiological signals
TEN_SIGNALS = [
    "heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic",
    "body_temperature", "spo2", "sleep_duration", "hrv", "stress", "mood", "fatigue"
]

BASELINES = {
    "heart_rate": (62.0, 2.0),
    "blood_pressure_systolic": (114.0, 2.5),
    "blood_pressure_diastolic": (72.0, 2.0),
    "body_temperature": (36.8, 0.15),
    "spo2": (98.4, 0.3),
    "sleep_duration": (7.4, 0.4),
    "hrv": (65.0, 5.0),
    "stress": (2.0, 0.5),
    "mood": (4.0, 0.5),
    "fatigue": (2.0, 0.5),
}

# Clinical noise floor (MIN_SD)
MIN_SD = {
    "heart_rate": 3.0, "blood_pressure_systolic": 4.0, "blood_pressure_diastolic": 3.0,
    "spo2": 1.5, "body_temperature": 0.2, "sleep_duration": 0.6, "stress": 1.0, "mood": 1.0,
    "fatigue": 1.0, "hrv": 8.0,
}

# Metric directionality (+1 = higher is better, -1 = higher is worse, 0 = any deviation is worse)
DIRECTIONS = {
    "heart_rate": 0, "blood_pressure_systolic": 0, "blood_pressure_diastolic": 0,
    "body_temperature": 0, "spo2": 1,
    "sleep_duration": 1, "hrv": 1, "steps": 1, "exercise_minutes": 1, "mood": 1,
    "resting_hr": -1, "fatigue": -1, "stress": -1,
}

def log_environment_versions() -> dict[str, str]:
    """Capture environment package versions for reproducible evaluation auditing."""
    import numpy as np
    import scipy
    import pandas as pd
    import sklearn
    import matplotlib
    
    versions = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "sklearn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "pyyaml": yaml.__version__,
    }
    return versions

def load_yaml_config(path: Path | None = None) -> dict:
    target = path or CONFIG_YAML_PATH
    if target.exists():
        with open(target, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}
