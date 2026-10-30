import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

from src.models.telemetry import HealthMeasurement


class ClinicalRuleFinding(BaseModel):
    """Structured, source-attributed clinical rule finding with traceable rationale."""
    indicator: str
    observed_value: Any
    unit: str
    observed_at: datetime
    severity: Literal["NOMINAL", "CAUTION", "CRITICAL", "UNKNOWN"]
    explanation: str
    rule_reference: dict[str, Any]
    limitations: str
    next_step: str | None = None


class ClinicalRuleInterface(ABC):
    """Abstract interface for versioned, deterministic, explainable clinical rules."""

    rule_id: str
    version: str
    title: str
    description: str
    guidance_source: dict[str, str]
    guidance_document_id: str | None = None
    guidance_approval_status: str = "approved"
    applicable_context: str
    approval_status: str = "approved"  # approved, draft, under_review, rejected, retired
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    target_measurement_types: list[str] = []
    max_freshness_seconds: float | None = None

    @abstractmethod
    def evaluate(
        self,
        observations: dict[str, HealthMeasurement],
        context: dict[str, Any],
    ) -> ClinicalRuleFinding | None:
        """Evaluates verified observations against the rule.
        
        Returns:
            ClinicalRuleFinding if triggered, None if observation is nominal / untriggered.
        """
        pass


class ClinicalRuleRegistry:
    """Registry maintaining active approved clinical decision rules.
    
    POLICY COMPLIANCE GUARANTEE:
    Initialized as an empty registry. No synthetic rules or unverified clinical
    thresholds are pre-populated into production.
    """

    def __init__(self) -> None:
        self._rules: dict[str, ClinicalRuleInterface] = {}

    def register(self, rule: ClinicalRuleInterface) -> None:
        """Registers a versioned clinical decision rule."""
        self._rules[rule.rule_id] = rule

    def unregister(self, rule_id: str) -> None:
        """Removes a rule from the active registry."""
        self._rules.pop(rule_id, None)

    def clear(self) -> None:
        """Clears all rules (used for isolated test fixtures)."""
        self._rules.clear()

    def get_all(self) -> list[ClinicalRuleInterface]:
        """Returns all rules in registry regardless of status."""
        return list(self._rules.values())

    def get_active_rules(
        self,
        context: str,
        target_types: list[str] | None = None,
        evaluation_time: datetime | None = None,
    ) -> list[ClinicalRuleInterface]:
        """Filters rules ensuring ONLY explicitly approved, unexpired, context-compatible rules execute."""
        eval_time = evaluation_time or datetime.now(timezone.utc)
        active: list[ClinicalRuleInterface] = []

        for rule in self._rules.values():
            # 1. Rule approval check (must be explicitly 'approved' or 'APPROVED')
            status_str = str(getattr(rule, "approval_status", "")).strip().upper()
            if status_str != "APPROVED":
                continue

            # 2. Backing guidance approval check (unreviewed or retired guidance cannot trigger alert)
            guidance_status = str(getattr(rule, "guidance_approval_status", "approved")).strip().upper()
            if guidance_status != "APPROVED":
                continue

            # 3. Context compatibility
            if rule.applicable_context not in (context, "ANY"):
                continue

            # 4. Expiration / Effective date check
            if rule.effective_from and eval_time < rule.effective_from:
                continue
            if rule.effective_to and eval_time > rule.effective_to:
                continue

            # 5. Target measurement type filtering
            if target_types is not None:
                if not any(t in target_types for t in rule.target_measurement_types):
                    continue

            active.append(rule)

        return active


# Global registry singleton (initialized EMPTY per NASA Space Apps safety contract)
clinical_rule_registry = ClinicalRuleRegistry()

