from datetime import datetime, timedelta, timezone
import pytest

from src.models.telemetry import HealthMeasurement
from src.modules.clinical.rules import (
    ClinicalRuleFinding,
    ClinicalRuleInterface,
    ClinicalRuleRegistry,
)


class MockApprovedRule(ClinicalRuleInterface):
    """Nonclinical test rule for unit testing."""
    rule_id = "TEST_RULE_HR_HIGH_01"
    version = "1.0.0"
    title = "Test Elevated Heart Rate Observation"
    description = "Nonclinical test fixture to verify threshold triggering."
    guidance_source = {
        "source_identifier": "TEST-DOC-3001",
        "title": "Test Human Health Standard",
        "publisher": "Test Aerospace Panel",
        "version": "v1.0",
        "document_url": "https://example.com/test",
    }
    applicable_context = "MICROGRAVITY"
    approval_status = "APPROVED"
    effective_from = datetime(2025, 1, 1, tzinfo=timezone.utc)
    effective_to = datetime(2030, 1, 1, tzinfo=timezone.utc)
    target_measurement_types = ["heart_rate"]
    max_freshness_seconds = 3600.0  # 1 hour

    def evaluate(self, observations, context):
        obs = observations.get("heart_rate")
        if obs and obs.value_numeric and obs.value_numeric > 100.0:
            return ClinicalRuleFinding(
                indicator="heart_rate",
                observed_value=obs.value_numeric,
                unit=obs.unit,
                observed_at=obs.measured_at,
                severity="CAUTION",
                explanation=f"Observed heart rate {obs.value_numeric} bpm exceeds test baseline (100 bpm).",
                rule_reference=self.guidance_source,
                limitations="Nonclinical test rule for automated testing only; not a diagnosis.",
                next_step="Advise medical officer for routine assessment.",
            )
        return None


class MockDraftRule(ClinicalRuleInterface):
    """Unapproved draft rule."""
    rule_id = "TEST_RULE_DRAFT_01"
    version = "0.1.0"
    title = "Draft Rule"
    description = "Draft rule under review."
    guidance_source = {"source_identifier": "DRAFT-DOC"}
    applicable_context = "MICROGRAVITY"
    approval_status = "DRAFT"  # Must NOT be evaluated
    target_measurement_types = ["heart_rate"]

    def evaluate(self, observations, context):
        return None


class MockExpiredRule(ClinicalRuleInterface):
    """Expired clinical rule."""
    rule_id = "TEST_RULE_EXPIRED_01"
    version = "1.0.0"
    title = "Expired Standard"
    description = "Expired rule."
    guidance_source = {"source_identifier": "EXPIRED-DOC"}
    applicable_context = "MICROGRAVITY"
    approval_status = "APPROVED"
    effective_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
    effective_to = datetime(2021, 1, 1, tzinfo=timezone.utc)  # Expired
    target_measurement_types = ["heart_rate"]

    def evaluate(self, observations, context):
        return None


class MockEvaOnlyRule(ClinicalRuleInterface):
    """Context-specific rule for EVA only."""
    rule_id = "TEST_RULE_EVA_ONLY_01"
    version = "1.0.0"
    title = "EVA Heart Rate Check"
    description = "Context-specific."
    guidance_source = {"source_identifier": "EVA-DOC"}
    applicable_context = "EVA"
    approval_status = "APPROVED"
    target_measurement_types = ["heart_rate"]

    def evaluate(self, observations, context):
        return None


def test_registry_empty_initialization():
    """Verify registry starts empty per safety contract."""
    registry = ClinicalRuleRegistry()
    assert len(registry.get_all()) == 0
    assert len(registry.get_active_rules("MICROGRAVITY")) == 0


def test_registry_filters_unapproved_rules():
    """Verify draft and unapproved rules are strictly excluded from active execution."""
    registry = ClinicalRuleRegistry()
    registry.register(MockApprovedRule())
    registry.register(MockDraftRule())

    active = registry.get_active_rules("MICROGRAVITY")
    assert len(active) == 1
    assert active[0].rule_id == "TEST_RULE_HR_HIGH_01"


def test_registry_filters_expired_rules():
    """Verify rules past effective_to are excluded."""
    registry = ClinicalRuleRegistry()
    registry.register(MockApprovedRule())
    registry.register(MockExpiredRule())

    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    active = registry.get_active_rules("MICROGRAVITY", evaluation_time=now)
    assert len(active) == 1
    assert active[0].rule_id == "TEST_RULE_HR_HIGH_01"


def test_registry_filters_context_incompatible_rules():
    """Verify EVA-only rule is excluded when context is MICROGRAVITY."""
    registry = ClinicalRuleRegistry()
    registry.register(MockApprovedRule())
    registry.register(MockEvaOnlyRule())

    # In microgravity context -> only the microgravity rule is active
    micro_rules = registry.get_active_rules("MICROGRAVITY")
    assert len(micro_rules) == 1
    assert micro_rules[0].rule_id == "TEST_RULE_HR_HIGH_01"

    # In EVA context -> EVA-only rule is active
    eva_rules = registry.get_active_rules("EVA")
    assert len(eva_rules) == 1
    assert eva_rules[0].rule_id == "TEST_RULE_EVA_ONLY_01"


def test_rule_deterministic_evaluation():
    """Verify rule triggers finding on high value and None on nominal value."""
    rule = MockApprovedRule()
    obs_nominal = HealthMeasurement(
        measurement_type="heart_rate",
        value_numeric=75.0,
        unit="bpm",
        measured_at=datetime.now(timezone.utc),
    )
    obs_elevated = HealthMeasurement(
        measurement_type="heart_rate",
        value_numeric=125.0,
        unit="bpm",
        measured_at=datetime.now(timezone.utc),
    )

    # 1. Nominal -> no finding triggered
    finding_nom = rule.evaluate({"heart_rate": obs_nominal}, {})
    assert finding_nom is None

    # 2. Elevated -> finding triggered with explanation and limitations
    finding_high = rule.evaluate({"heart_rate": obs_elevated}, {})
    assert finding_high is not None
    assert finding_high.severity == "CAUTION"
    assert "exceeds test baseline" in finding_high.explanation
    assert finding_high.observed_value == 125.0
    assert "not a diagnosis" in finding_high.limitations
