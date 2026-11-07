"""Unit tests for guidance registry models, schema validation, and rule activation guards."""
import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from src.models.clinical import GuidanceDocument, GuidanceSource
from src.modules.clinical.rules import (
    ClinicalRuleFinding,
    ClinicalRuleInterface,
    ClinicalRuleRegistry,
)
from src.modules.guidance.schemas import (
    VALID_STATUS_TRANSITIONS,
    GuidanceDocumentCreate,
    GuidanceReviewCreate,
    GuidanceSourceCreate,
)
from src.modules.guidance.service import GuidanceService


class MockTestRule(ClinicalRuleInterface):
    """Test rule for checking registry activation gating."""
    rule_id = "RULE-TEST-EVIDENCE-01"
    version = "1.0.0"
    title = "Test Heart Rate Elevated Rule"
    description = "Test rule verifying guidance approval gating."
    guidance_source = {"source": "NASA-STD-3001-TEST"}
    applicable_context = "MICROGRAVITY"
    target_measurement_types = ["heart_rate"]
    approval_status = "approved"
    guidance_approval_status = "approved"

    def evaluate(self, observations, context):
        return None


def test_status_transition_state_machine():
    """Validates the state machine transitions for the approval workflow."""
    assert "under_review" in VALID_STATUS_TRANSITIONS["draft"]
    assert "approved" not in VALID_STATUS_TRANSITIONS["draft"]  # Cannot skip review!

    assert "approved" in VALID_STATUS_TRANSITIONS["under_review"]
    assert "rejected" in VALID_STATUS_TRANSITIONS["under_review"]

    assert "retired" in VALID_STATUS_TRANSITIONS["approved"]
    assert "draft" in VALID_STATUS_TRANSITIONS["rejected"]


def test_guidance_document_schema_validation():
    """Validates that guidance type and approval status conform to strict enums."""
    # Valid educational guidance
    doc = GuidanceDocumentCreate(
        document_identifier="DOC-TEST-EDU-01",
        title="Microgravity Cardiovascular Adaptation",
        guidance_type="EDUCATIONAL",
        summary="Educational overview of cephalad fluid shift.",
        topic="Cardiovascular",
    )
    assert doc.guidance_type == "EDUCATIONAL"
    assert doc.approval_status == "draft"

    # Invalid guidance type rejected
    with pytest.raises(ValidationError):
        GuidanceDocumentCreate(
            document_identifier="DOC-TEST-INVALID-01",
            title="Invalid Type",
            guidance_type="PROPRIETARY_ALGORITHM",  # Not in allowed literals!
            summary="Invalid",
        )


def test_rule_activation_blocks_unapproved_rules():
    """Guarantees that unapproved clinical rules can never be activated."""
    registry = ClinicalRuleRegistry()
    rule = MockTestRule()
    rule.approval_status = "draft"
    registry.register(rule)

    active = registry.get_active_rules(context="MICROGRAVITY")
    assert len(active) == 0, "Draft rules must never be active!"

    rule.approval_status = "under_review"
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0

    rule.approval_status = "rejected"
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0

    rule.approval_status = "retired"
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0


def test_rule_activation_blocks_rules_with_unapproved_guidance():
    """Guarantees that even an approved rule CANNOT activate if backing guidance is unapproved or retired."""
    registry = ClinicalRuleRegistry()
    rule = MockTestRule()
    rule.approval_status = "approved"

    # Case 1: Backing guidance is draft
    rule.guidance_approval_status = "draft"
    registry.register(rule)
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0, "Rule with draft guidance cannot activate!"

    # Case 2: Backing guidance is under_review
    rule.guidance_approval_status = "under_review"
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0

    # Case 3: Backing guidance is retired
    rule.guidance_approval_status = "retired"
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0

    # Case 4: Backing guidance is rejected
    rule.guidance_approval_status = "rejected"
    assert len(registry.get_active_rules(context="MICROGRAVITY")) == 0

    # Case 5: Both rule and backing guidance are approved -> activated
    rule.guidance_approval_status = "approved"
    active = registry.get_active_rules(context="MICROGRAVITY")
    assert len(active) == 1
    assert active[0].rule_id == "RULE-TEST-EVIDENCE-01"


def test_metadata_redaction_for_crew_members():
    """Verifies that internal administrative and reviewer metadata is redacted for crew members."""
    now = datetime.now(timezone.utc)
    doc = GuidanceDocument(
        id=uuid.uuid4(),
        document_identifier="DOC-TEST-REDACT-01",
        title="Resting Heart Rate Clinical Standard",
        guidance_type="CLINICAL_RULE",
        summary="Summary of clinical standard.",
        approval_status="approved",
        version="1.0.0",
        created_at=now,
        updated_at=now,
        review_metadata={
            "internal_review_notes": "Clinical board meeting minutes item 4",
            "reviewer_user_id": "usr-surgeon-999",
        },
    )

    # Crew member serialization
    crew_dto = GuidanceService._serialize_document(doc, is_crew=True)
    assert crew_dto.review_metadata is None, "Administrative review metadata must be redacted for crew members!"

    # Flight surgeon serialization
    surgeon_dto = GuidanceService._serialize_document(doc, is_crew=False)
    assert surgeon_dto.review_metadata is not None
    assert surgeon_dto.review_metadata["internal_review_notes"] == "Clinical board meeting minutes item 4"
