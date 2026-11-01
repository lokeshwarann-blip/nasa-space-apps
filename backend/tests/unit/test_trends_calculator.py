import math
import uuid
from datetime import datetime, timedelta, timezone
import pytest

from src.modules.trends.calculator import (
    calculate_personal_baseline,
    compute_statistics,
    detect_coverage_gaps,
    detect_statistical_outliers,
)


def test_compute_statistics_empty():
    """Verify empty observation list returns count=0, None values, and explicit reason."""
    stats = compute_statistics([])
    assert stats.count == 0
    assert stats.minimum is None
    assert stats.maximum is None
    assert stats.mean is None
    assert stats.median is None
    assert stats.sample_std_dev is None
    assert "statistics" in stats.unavailable_reasons


def test_compute_statistics_single_observation():
    """Verify single observation calculates mean/median but marks std_dev unavailable."""
    stats = compute_statistics([72.5])
    assert stats.count == 1
    assert stats.minimum == 72.5
    assert stats.maximum == 72.5
    assert stats.mean == 72.5
    assert stats.median == 72.5
    assert stats.sample_std_dev is None
    assert "sample_std_dev" in stats.unavailable_reasons


def test_compute_statistics_multiple_observations():
    """Verify correct arithmetic statistics on known numerical inputs."""
    # Values: 70, 72, 74, 76, 78
    # Mean: 74.0, Median: 74.0, Min: 70.0, Max: 78.0
    # Variance = (16 + 4 + 0 + 4 + 16) / 4 = 10.0, StdDev = sqrt(10) ≈ 3.162
    values = [70.0, 72.0, 74.0, 76.0, 78.0]
    stats = compute_statistics(values)
    assert stats.count == 5
    assert stats.minimum == 70.0
    assert stats.maximum == 78.0
    assert stats.mean == 74.0
    assert stats.median == 74.0
    assert stats.sample_std_dev == pytest.approx(math.sqrt(10.0), 0.001)
    assert len(stats.unavailable_reasons) == 0


def test_compute_statistics_even_length_median():
    """Verify median calculation for even number of observations."""
    values = [60.0, 70.0, 80.0, 90.0]
    stats = compute_statistics(values)
    assert stats.median == 75.0


def test_detect_coverage_gaps():
    """Verify temporal gap detection flags intervals exceeding configured threshold."""
    base_time = datetime(2026, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
    # Timestamps with a 2-hour gap between t2 and t3
    timestamps = [
        base_time,
        base_time + timedelta(minutes=15),
        base_time + timedelta(minutes=30),
        base_time + timedelta(hours=2, minutes=30),  # 2h gap (> 1h threshold)
    ]

    gaps = detect_coverage_gaps(timestamps, gap_threshold_seconds=3600.0)
    assert len(gaps) == 1
    assert gaps[0].gap_start == timestamps[2]
    assert gaps[0].gap_end == timestamps[3]
    assert gaps[0].gap_duration_seconds == 7200.0
    assert gaps[0].gap_duration_hours == 2.0


def test_detect_statistical_outliers_labeling():
    """Verify outlier detection labels deviations as statistical observations, not diagnoses."""
    # 9 normal resting heart rate readings + 1 extreme statistical deviation
    values = [70.0, 71.0, 70.0, 72.0, 69.0, 71.0, 70.0, 72.0, 70.0, 150.0]
    outliers = detect_statistical_outliers(values, std_threshold=2.5)

    assert len(outliers) == 10
    # Last reading should be flagged as statistical outlier
    is_outlier, note = outliers[-1]
    assert is_outlier is True
    assert "Statistical observation" in note
    assert "not a clinical diagnosis" in note

    # First readings should not be outliers
    assert outliers[0][0] is False


def test_personal_baseline_insufficient_data():
    """Verify insufficient observation count returns baseline_status='UNAVAILABLE'."""
    crew_id = uuid.uuid4()
    values = [70.0, 72.0, 71.0, 69.0]  # Only 4 observations (< 10)
    timestamps = [datetime.now(timezone.utc) for _ in range(4)]

    baseline = calculate_personal_baseline(
        values=values,
        timestamps=timestamps,
        crew_id=crew_id,
        measurement_type="heart_rate",
        canonical_unit="bpm",
        min_sample_requirement=10,
    )
    assert baseline.baseline_status == "UNAVAILABLE"
    assert "Insufficient historical data" in baseline.unavailable_reason
    assert baseline.observation_count == 4
    assert baseline.baseline_values is None


def test_personal_baseline_configured_when_sufficient():
    """Verify empirical baseline is configured when minimum sample requirement is satisfied."""
    crew_id = uuid.uuid4()
    values = [68.0, 70.0, 72.0, 71.0, 69.0, 70.0, 72.0, 71.0, 68.0, 70.0, 71.0, 73.0]
    base_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    timestamps = [base_time + timedelta(hours=i) for i in range(len(values))]

    baseline = calculate_personal_baseline(
        values=values,
        timestamps=timestamps,
        crew_id=crew_id,
        measurement_type="heart_rate",
        canonical_unit="bpm",
        min_sample_requirement=10,
    )
    assert baseline.baseline_status == "CONFIGURED"
    assert baseline.method == "PERSONAL_EMPIRICAL_MEAN_2STD"
    assert baseline.observation_count == 12
    assert baseline.baseline_values is not None
    assert "baseline_mean" in baseline.baseline_values
    assert "baseline_median" in baseline.baseline_values
    assert "nominal_range_lower" in baseline.baseline_values
    assert "nominal_range_upper" in baseline.baseline_values

