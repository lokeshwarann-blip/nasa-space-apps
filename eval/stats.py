"""eval/stats.py - Rigorous statistical testing, exact confidence intervals, and FAR definitions.

Methodological Requirements:
1. Unit of independence is the simulation trajectory / crew-run, NOT individual readings.
2. FAR defined as: False Alerts per crew-member-fortnight (14 crew-days) and per crew-day.
3. For zero counts: Report exact Poisson / Clopper-Pearson upper bound ("FAR upper bound"), never as 0.
4. Exact Clopper-Pearson (Beta distribution) & Jeffreys intervals for proportions.
5. Exact Poisson CI for alert rates across total exposure.
6. Bootstrap CI for median detection delay (resampled over independent runs).
"""
import math
from typing import NamedTuple
import numpy as np
from scipy import stats


class ProportionCI(NamedTuple):
    point_est: float
    ci_lower: float
    ci_upper: float
    method: str


class RateCI(NamedTuple):
    rate_per_fortnight: float
    rate_per_day: float
    ci_lower_fortnight: float
    ci_upper_fortnight: float
    is_upper_bound_only: bool
    total_events: int
    exposure_days: float


def clopper_pearson_interval(k: int, n: int, confidence: float = 0.95) -> ProportionCI:
    """Exact Clopper-Pearson confidence interval for a binomial proportion via Beta distribution.
    
    Guaranteed conservative coverage: P(p in CI) >= 1 - alpha for all p.
    """
    if n <= 0:
        return ProportionCI(0.0, 0.0, 0.0, "clopper_pearson")
    alpha = 1.0 - confidence
    point = k / n
    lower = 0.0 if k == 0 else stats.beta.ppf(alpha / 2.0, k, n - k + 1)
    upper = 1.0 if k == n else stats.beta.ppf(1.0 - alpha / 2.0, k + 1, n - k)
    return ProportionCI(
        point_est=float(point),
        ci_lower=float(lower),
        ci_upper=float(upper),
        method="clopper_pearson"
    )


def jeffreys_interval(k: int, n: int, confidence: float = 0.95) -> ProportionCI:
    """Equal-tailed Jeffreys prior interval (Beta(0.5, 0.5)) for binomial proportion."""
    if n <= 0:
        return ProportionCI(0.0, 0.0, 0.0, "jeffreys")
    alpha = 1.0 - confidence
    point = k / n
    lower = 0.0 if k == 0 else stats.beta.ppf(alpha / 2.0, k + 0.5, n - k + 0.5)
    upper = 1.0 if k == n else stats.beta.ppf(1.0 - alpha / 2.0, k + 0.5, n - k + 0.5)
    return ProportionCI(
        point_est=float(point),
        ci_lower=float(lower),
        ci_upper=float(upper),
        method="jeffreys"
    )


def exact_poisson_rate_ci(
    total_events: int,
    exposure_days: float,
    confidence: float = 0.95,
    exposure_unit_days: float = 14.0
) -> RateCI:
    """Exact Poisson confidence interval for alert rates over known exposure.
    
    Exposure unit defaults to 14.0 days (1 crew-member-fortnight).
    When total_events == 0, provides the exact one-sided Poisson upper bound (rule-of-three counterpart).
    """
    if exposure_days <= 0:
        raise ValueError("exposure_days must be positive.")
    alpha = 1.0 - confidence
    scale = exposure_unit_days / exposure_days

    rate_per_day = total_events / exposure_days
    rate_per_fortnight = rate_per_day * exposure_unit_days

    if total_events == 0:
        # Exact upper limit: 0.5 * chi2(2, 1 - alpha)
        # For 95% one-sided (or 97.5% two-sided bound): chi2.ppf(0.975, 2) / 2 = ~3.6888
        upper_events = 0.5 * stats.chi2.ppf(1.0 - alpha / 2.0, 2)
        ci_upper = float(upper_events * scale)
        return RateCI(
            rate_per_fortnight=0.0,
            rate_per_day=0.0,
            ci_lower_fortnight=0.0,
            ci_upper_fortnight=ci_upper,
            is_upper_bound_only=True,
            total_events=0,
            exposure_days=exposure_days
        )

    # Exact Garwood / Chi-Square two-sided Poisson CI
    lower_events = 0.5 * stats.chi2.ppf(alpha / 2.0, 2 * total_events)
    upper_events = 0.5 * stats.chi2.ppf(1.0 - alpha / 2.0, 2 * (total_events + 1))

    return RateCI(
        rate_per_fortnight=float(rate_per_fortnight),
        rate_per_day=float(rate_per_day),
        ci_lower_fortnight=float(lower_events * scale),
        ci_upper_fortnight=float(upper_events * scale),
        is_upper_bound_only=False,
        total_events=total_events,
        exposure_days=exposure_days
    )


def bootstrap_median_ci(
    values: list[float] | np.ndarray,
    n_boot: int = 2000,
    confidence: float = 0.95,
    seed: int = 42
) -> tuple[float, float, float]:
    """Bootstrap confidence interval for median delay, resampling over simulation RUNS (not readings)."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return float("nan"), float("nan"), float("nan")
    if len(arr) == 1:
        return float(arr[0]), float(arr[0]), float(arr[0])

    rng = np.random.default_rng(seed)
    boot_medians = np.empty(n_boot)
    n = len(arr)
    for i in range(n_boot):
        sample = rng.choice(arr, size=n, replace=True)
        boot_medians[i] = np.median(sample)

    alpha = 1.0 - confidence
    low_pct = 100.0 * (alpha / 2.0)
    high_pct = 100.0 * (1.0 - alpha / 2.0)

    med = float(np.median(arr))
    ci_low = float(np.percentile(boot_medians, low_pct))
    ci_high = float(np.percentile(boot_medians, high_pct))
    return med, ci_low, ci_high


def compute_observation_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    """Computes observation-level classification metrics, clearly separated from event-level metrics."""
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)
    tp = int(np.sum((yt == 1) & (yp == 1)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    fn = int(np.sum((yt == 1) & (yp == 0)))
    tn = int(np.sum((yt == 0) & (yp == 0)))

    acc = (tp + tn) / max(1, len(yt))
    prec = tp / max(1, tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / max(1, tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec) / max(1e-9, prec + rec) if (prec + rec) > 0 else 0.0

    return {
        "obs_accuracy": round(float(acc), 4),
        "obs_precision": round(float(prec), 4),
        "obs_recall": round(float(rec), 4),
        "obs_f1": round(float(f1), 4),
        "obs_tp": tp, "obs_fp": fp, "obs_fn": fn, "obs_tn": tn,
    }
