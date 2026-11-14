import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class MeasurementValidationError(ValueError):
    """Raised when a health measurement fails type, unit, format, or bounds validation."""
    pass


@dataclass(frozen=True)
class ConversionAudit:
    """Auditable record of a deterministic unit conversion."""
    original_value: float
    original_unit: str
    converted_value: float
    canonical_unit: str
    conversion_formula: str


@dataclass
class MeasurementDefinition:
    """Specification of an indicator type within the typed measurement registry."""
    measurement_type: str
    canonical_unit: str
    allowed_units: set[str]
    is_numeric: bool = True
    min_value: float | None = None
    max_value: float | None = None
    # NOTE: Supporting a type does NOT imply a clinically validated threshold exists for it.
    has_clinical_threshold: bool = False
    converters: dict[str, Callable[[float], tuple[float, str]]] = field(default_factory=dict)


def _convert_degf_to_degc(degf: float) -> tuple[float, str]:
    """Explicit, deterministic conversion from Fahrenheit to Celsius."""
    degc = (degf - 32.0) * (5.0 / 9.0)
    return round(degc, 2), "(val - 32.0) * (5.0 / 9.0)"


def _convert_glucose_mmol_to_mgdl(mmol: float) -> tuple[float, str]:
    """Explicit, deterministic conversion from mmol/L to mg/dL for blood glucose."""
    mgdl = mmol * 18.0182
    return round(mgdl, 2), "val * 18.0182"


class MeasurementRegistry:
    """Registry maintaining supported biometric types, canonical units, and validation logic."""

    def __init__(self) -> None:
        self._definitions: dict[str, MeasurementDefinition] = {}
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Populates the initial approved set of aerospace indicator definitions."""
        self.register(
            MeasurementDefinition(
                measurement_type="heart_rate",
                canonical_unit="bpm",
                allowed_units={"bpm"},
                is_numeric=True,
                min_value=20.0,
                max_value=260.0,
                has_clinical_threshold=True,  # NASA-STD-3001 physiological range
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="blood_pressure_systolic",
                canonical_unit="mmHg",
                allowed_units={"mmHg"},
                is_numeric=True,
                min_value=40.0,
                max_value=280.0,
                has_clinical_threshold=True,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="blood_pressure_diastolic",
                canonical_unit="mmHg",
                allowed_units={"mmHg"},
                is_numeric=True,
                min_value=20.0,
                max_value=200.0,
                has_clinical_threshold=True,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="body_temperature",
                canonical_unit="degC",
                allowed_units={"degC", "degF"},
                is_numeric=True,
                min_value=30.0,
                max_value=45.0,
                has_clinical_threshold=True,
                converters={"degF": _convert_degf_to_degc},
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="spo2",
                canonical_unit="%",
                allowed_units={"%"},
                is_numeric=True,
                min_value=40.0,
                max_value=100.0,
                has_clinical_threshold=True,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="respiratory_rate",
                canonical_unit="breaths/min",
                allowed_units={"breaths/min"},
                is_numeric=True,
                min_value=3.0,
                max_value=60.0,
                has_clinical_threshold=True,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="blood_glucose",
                canonical_unit="mg/dL",
                allowed_units={"mg/dL", "mmol/L"},
                is_numeric=True,
                min_value=20.0,
                max_value=600.0,
                has_clinical_threshold=False,  # Supported type without endorsed aerospace threshold
                converters={"mmol/L": _convert_glucose_mmol_to_mgdl},
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="sleep_duration",
                canonical_unit="hours",
                allowed_units={"hours"},
                is_numeric=True,
                min_value=0.0,
                max_value=24.0,
                has_clinical_threshold=False,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="sleep_quality",
                canonical_unit="score_1_5",
                allowed_units={"score_1_5"},
                is_numeric=True,
                min_value=1.0,
                max_value=5.0,
                has_clinical_threshold=False,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="mood",
                canonical_unit="score_1_5",
                allowed_units={"score_1_5"},
                is_numeric=True,
                min_value=1.0,
                max_value=5.0,
                has_clinical_threshold=False,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="stress",
                canonical_unit="score_1_5",
                allowed_units={"score_1_5"},
                is_numeric=True,
                min_value=1.0,
                max_value=5.0,
                has_clinical_threshold=False,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="fatigue",
                canonical_unit="score_1_5",
                allowed_units={"score_1_5"},
                is_numeric=True,
                min_value=1.0,
                max_value=5.0,
                has_clinical_threshold=False,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="radiation_dose_rate",
                canonical_unit="uGy/h",
                allowed_units={"uGy/h"},
                is_numeric=True,
                min_value=0.0,
                max_value=1000.0,
                has_clinical_threshold=False,
            )
        )
        self.register(
            MeasurementDefinition(
                measurement_type="symptom_report",
                canonical_unit="structured",
                allowed_units={"structured"},
                is_numeric=False,
                has_clinical_threshold=False,
            )
        )

    def register(self, definition: MeasurementDefinition) -> None:
        """Registers a measurement indicator type."""
        self._definitions[definition.measurement_type] = definition

    def get(self, measurement_type: str) -> MeasurementDefinition | None:
        """Retrieves indicator definition by type name."""
        return self._definitions.get(measurement_type)

    def is_supported(self, measurement_type: str) -> bool:
        """Checks whether indicator type is supported."""
        return measurement_type in self._definitions

    def validate_and_convert(
        self,
        measurement_type: str,
        value_numeric: float | None,
        value_structured: dict[str, Any] | None,
        unit: str,
    ) -> tuple[float | None, dict[str, Any] | None, str, ConversionAudit | None]:
        """Validates input measurement against registry standards and performs explicit conversion if needed.
        
        Returns:
            Tuple of (effective_value_numeric, effective_value_structured, effective_unit, conversion_audit)
        """
        # 1. Type verification
        defn = self.get(measurement_type)
        if defn is None:
            raise MeasurementValidationError(
                f"Unsupported measurement type: '{measurement_type}'. Must be one of: {list(self._definitions.keys())}"
            )

        # 2. Unit verification
        if unit not in defn.allowed_units:
            raise MeasurementValidationError(
                f"Incompatible unit '{unit}' for measurement type '{measurement_type}'. "
                f"Allowed units: {list(defn.allowed_units)}"
            )

        # 3. Numeric validation
        conversion_audit: ConversionAudit | None = None
        effective_numeric: float | None = value_numeric
        effective_unit: str = unit

        if defn.is_numeric:
            if value_numeric is None:
                raise MeasurementValidationError(
                    f"Measurement type '{measurement_type}' requires a numeric value."
                )

            # Strict rejection of non-finite numbers (NaN, Infinity)
            if math.isnan(value_numeric) or math.isinf(value_numeric):
                raise MeasurementValidationError(
                    f"Non-finite numeric value '{value_numeric}' is not permitted."
                )

            # Explicit deterministic unit conversion if not in canonical unit
            if unit != defn.canonical_unit:
                if unit in defn.converters:
                    converted, formula = defn.converters[unit](value_numeric)
                    conversion_audit = ConversionAudit(
                        original_value=value_numeric,
                        original_unit=unit,
                        converted_value=converted,
                        canonical_unit=defn.canonical_unit,
                        conversion_formula=formula,
                    )
                    effective_numeric = converted
                    effective_unit = defn.canonical_unit
                else:
                    raise MeasurementValidationError(
                        f"No conversion available from '{unit}' to canonical '{defn.canonical_unit}'."
                    )

            # Range validation on canonical/converted numeric value
            if defn.min_value is not None and effective_numeric < defn.min_value:
                raise MeasurementValidationError(
                    f"Value {effective_numeric} {effective_unit} for '{measurement_type}' is below plausible physiological lower bound ({defn.min_value})."
                )
            if defn.max_value is not None and effective_numeric > defn.max_value:
                raise MeasurementValidationError(
                    f"Value {effective_numeric} {effective_unit} for '{measurement_type}' exceeds plausible physiological upper bound ({defn.max_value})."
                )

        else:
            # Structured validation
            if value_structured is None:
                raise MeasurementValidationError(
                    f"Measurement type '{measurement_type}' requires a structured JSON payload."
                )
            if not isinstance(value_structured, dict):
                raise MeasurementValidationError(
                    f"Structured payload for '{measurement_type}' must be a dictionary object."
                )

        return effective_numeric, value_structured, effective_unit, conversion_audit


# Global registry singleton
measurement_registry = MeasurementRegistry()

