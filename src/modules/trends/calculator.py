import math
import uuid
from datetime import datetime, timezone
from src.modules.trends.schemas import (
    BaselineResponse,
    CoverageGap,
    SummaryStatistics,
)


def compute_statistics(values: list[float]) -> SummaryStatistics:
    """Computes deterministic descriptive statistics from actual numerical observations."""
    n = len(values)
    if n == 0:
        return SummaryStatistics(
            count=0,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            sample_std_dev=None,
            unavailable_reasons={
                "statistics": "No valid observations present in requested time window."
            },
        )

    # Clean finite check
    for v in values:
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"Non-finite numeric value encountered: {v}")

    minimum = round(float(min(values)), 3)
    maximum = round(float(max(values)), 3)
    mean = round(float(sum(values) / n), 3)

    sorted_vals = sorted(values)
    if n % 2 == 1:
        median = round(float(sorted_vals[n // 2]), 3)
    else:
        median = round(float((sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0), 3)

    unavailable: dict[str, str] = {}
    if n == 1:
        sample_std_dev = None
        unavailable["sample_std_dev"] = (
            "Sample standard deviation requires at least 2 observations (Bessel's correction N-1=0)."
        )
    else:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        sample_std_dev = round(float(math.sqrt(variance)), 3)

    return SummaryStatistics(
        count=n,
        minimum=minimum,
        maximum=maximum,
        mean=mean,
        median=median,
        sample_std_dev=sample_std_dev,
        calculation_method="EXACT_ARITHMETIC_DETERMINISTIC",
        unavailable_reasons=unavailable,
    )


def detect_coverage_gaps(
    timestamps: list[datetime],
    gap_threshold_seconds: float = 3600.0,
) -> list[CoverageGap]:
    """Identifies temporal gaps in observation coverage exceeding the configured threshold."""
    if len(timestamps) < 2:
        return []

    sorted_ts = sorted(timestamps)
    gaps: list[CoverageGap] = []

    for i in range(len(sorted_ts) - 1):
        t1 = sorted_ts[i]
        t2 = sorted_ts[i + 1]
        delta_sec = (t2 - t1).total_seconds()

        if delta_sec > gap_threshold_seconds:
            gaps.append(
                CoverageGap(
                    gap_start=t1,
                    gap_end=t2,
                    gap_duration_seconds=round(delta_sec, 1),
                    gap_duration_hours=round(delta_sec / 3600.0, 2),
                )
            )

    return gaps


def detect_statistical_outliers(
    values: list[float],
    std_threshold: float = 3.0,
) -> list[tuple[bool, str | None]]:
    """Identifies observations deviating significantly from sample mean.
    
    IMPORTANT: Results are explicitly designated as statistical observations,
    NOT medical diagnoses or clinical alerts.
    """
    n = len(values)
    if n < 4:
        # Insufficient sample for statistical deviation analysis
        return [(False, None) for _ in values]

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std_dev = math.sqrt(variance)

    if std_dev == 0.0:
        return [(False, None) for _ in values]

    results: list[tuple[bool, str | None]] = []
    for x in values:
        z = abs(x - mean) / std_dev
        if z >= std_threshold:
            note = (
                f"Statistical observation: z-score {z:.2f} exceeds {std_threshold:.1f} standard deviations "
                "(statistical deviation only; not a clinical diagnosis)"
            )
            results.append((True, note))
        else:
            results.append((False, None))

    return results


def calculate_personal_baseline(
    values: list[float],
    timestamps: list[datetime],
    crew_id: uuid.UUID,
    measurement_type: str,
    canonical_unit: str,
    min_sample_requirement: int = 10,
) -> BaselineResponse:
    """Calculates an individualized personal baseline from actual historical observations.
    
    DATA POLICY GUARANTEE:
    If observations are insufficient (< min_sample_requirement), returns baseline_status='UNAVAILABLE'.
    Never substitutes synthetic, population-average, or assumed healthy values.
    """
    n = len(values)
    if n < min_sample_requirement:
        return BaselineResponse(
            crew_member_id=crew_id,
            measurement_type=measurement_type,
            canonical_unit=canonical_unit,
            baseline_status="UNAVAILABLE",
            unavailable_reason=(
                f"Insufficient historical data to configure empirical personal baseline. "
                f"Requires at least {min_sample_requirement} verified observations, found {n}."
            ),
            observation_count=n,
        )

    mean = round(float(sum(values) / n), 3)
    sorted_vals = sorted(values)
    if n % 2 == 1:
        median = round(float(sorted_vals[n // 2]), 3)
    else:
        median = round(float((sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0), 3)

    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std_dev = round(float(math.sqrt(variance)), 3)

    sorted_ts = sorted(timestamps)
    window_start = sorted_ts[0]
    window_end = sorted_ts[-1]
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=timezone.utc)
    if window_end.tzinfo is None:
        window_end = window_end.replace(tzinfo=timezone.utc)

    return BaselineResponse(
        crew_member_id=crew_id,
        measurement_type=measurement_type,
        canonical_unit=canonical_unit,
        baseline_status="CONFIGURED",
        method="PERSONAL_EMPIRICAL_MEAN_2STD",
        method_version="1.0",
        calculated_at=datetime.now(timezone.utc),
        window_start=window_start,
        window_end=window_end,
        observation_count=n,
        baseline_values={
            "baseline_mean": mean,
            "baseline_median": median,
            "baseline_std_dev": std_dev,
            "nominal_range_lower": round(mean - (2.0 * std_dev), 3),
            "nominal_range_upper": round(mean + (2.0 * std_dev), 3),
        },
    )
