import math
import pytest

from src.modules.telemetry.registry import (
    MeasurementRegistry,
    MeasurementValidationError,
    measurement_registry,
)


def test_registry_supported_types():
    """Verify registry contains expected baseline types."""
    assert measurement_registry.is_supported("heart_rate")
    assert measurement_registry.is_supported("blood_pressure_systolic")
    assert measurement_registry.is_supported("blood_pressure_diastolic")
    assert measurement_registry.is_supported("body_temperature")
    assert measurement_registry.is_supported("spo2")
    assert measurement_registry.is_supported("respiratory_rate")
    assert measurement_registry.is_supported("blood_glucose")
    assert measurement_registry.is_supported("sleep_duration")
    assert measurement_registry.is_supported("symptom_report")


def test_registry_clinical_threshold_distinction():
    """Verify supporting a type does not imply a clinically validated threshold exists."""
    hr_defn = measurement_registry.get("heart_rate")
    glucose_defn = measurement_registry.get("blood_glucose")
    sleep_defn = measurement_registry.get("sleep_duration")

    assert hr_defn.has_clinical_threshold is True
    assert glucose_defn.has_clinical_threshold is False
    assert sleep_defn.has_clinical_threshold is False


def test_valid_numeric_measurement():
    """Verify valid numeric measurement is accepted unchanged."""
    val, struct, unit, audit = measurement_registry.validate_and_convert(
        measurement_type="heart_rate",
        value_numeric=72.0,
        value_structured=None,
        unit="bpm",
    )
    assert val == 72.0
    assert struct is None
    assert unit == "bpm"
    assert audit is None


def test_rejection_of_non_finite_values():
    """Verify NaN and Infinity are strictly rejected."""
    with pytest.raises(MeasurementValidationError) as exc:
        measurement_registry.validate_and_convert(
            measurement_type="heart_rate",
            value_numeric=float("nan"),
            value_structured=None,
            unit="bpm",
        )
    assert "Non-finite numeric value" in str(exc.value)

    with pytest.raises(MeasurementValidationError) as exc:
        measurement_registry.validate_and_convert(
            measurement_type="heart_rate",
            value_numeric=float("inf"),
            value_structured=None,
            unit="bpm",
        )
    assert "Non-finite numeric value" in str(exc.value)


def test_rejection_of_unsupported_type():
    """Verify submitting an unregistered type is rejected."""
    with pytest.raises(MeasurementValidationError) as exc:
        measurement_registry.validate_and_convert(
            measurement_type="telepathy_index",
            value_numeric=95.0,
            value_structured=None,
            unit="points",
        )
    assert "Unsupported measurement type" in str(exc.value)


def test_rejection_of_incompatible_unit():
    """Verify submitting an unapproved unit for a known type is rejected."""
    with pytest.raises(MeasurementValidationError) as exc:
        measurement_registry.validate_and_convert(
            measurement_type="heart_rate",
            value_numeric=72.0,
            value_structured=None,
            unit="degC",
        )
    assert "Incompatible unit" in str(exc.value)


def test_rejection_of_out_of_bounds_value():
    """Verify values outside physiological plausibility bounds are rejected."""
    with pytest.raises(MeasurementValidationError) as exc:
        measurement_registry.validate_and_convert(
            measurement_type="heart_rate",
            value_numeric=350.0,
            value_structured=None,
            unit="bpm",
        )
    assert "exceeds plausible physiological upper bound" in str(exc.value)


def test_explicit_deterministic_unit_conversion():
    """Verify explicit unit conversion produces exact canonical unit and conversion audit trail."""
    # Test temperature degF -> degC (98.6 degF -> 37.0 degC)
    val, struct, unit, audit = measurement_registry.validate_and_convert(
        measurement_type="body_temperature",
        value_numeric=98.6,
        value_structured=None,
        unit="degF",
    )
    assert val == 37.0
    assert unit == "degC"
    assert audit is not None
    assert audit.original_value == 98.6
    assert audit.original_unit == "degF"
    assert audit.converted_value == 37.0
    assert audit.canonical_unit == "degC"


def test_glucose_unit_conversion():
    """Verify blood glucose conversion from mmol/L to mg/dL."""
    val, struct, unit, audit = measurement_registry.validate_and_convert(
        measurement_type="blood_glucose",
        value_numeric=5.0,
        value_structured=None,
        unit="mmol/L",
    )
    # 5.0 * 18.0182 = 90.09 mg/dL
    assert val == 90.09
    assert unit == "mg/dL"
    assert audit is not None
    assert audit.original_unit == "mmol/L"
    assert audit.canonical_unit == "mg/dL"


def test_structured_measurement_validation():
    """Verify structured measurement types require dict payload."""
    val, struct, unit, audit = measurement_registry.validate_and_convert(
        measurement_type="symptom_report",
        value_numeric=None,
        value_structured={"symptom": "HEADACHE", "severity": "MILD"},
        unit="structured",
    )
    assert struct == {"symptom": "HEADACHE", "severity": "MILD"}
    assert unit == "structured"
    assert audit is None

    # Missing structured dict
    with pytest.raises(MeasurementValidationError) as exc:
        measurement_registry.validate_and_convert(
            measurement_type="symptom_report",
            value_numeric=None,
            value_structured=None,
            unit="structured",
        )
    assert "requires a structured JSON payload" in str(exc.value)

