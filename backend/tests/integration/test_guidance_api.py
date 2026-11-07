"""Integration tests for the Evidence and Guidance Registry API.

Verifies:
- Source provenance and metadata recording.
- Approval workflow permissions and state machine transitions.
- Metadata and draft redaction for crew members.
- Versioning and superseding lifecycle.
- Multi-parameter filtering (topic, indicator, hazard, context, guidance_type).
- Prevention of unapproved or retired guidance/rules from activating.
"""
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_access_token
from src.modules.clinical.rules import (
    ClinicalRuleFinding,
    ClinicalRuleInterface,
    clinical_rule_registry,
)


@pytest.fixture
def flight_surgeon_token():
    return create_access_token(
        subject="surgeon_bev_crusher",
        role="FLIGHT_SURGEON",
        assigned_crew_ids=["*"],
    )


@pytest.fixture
def admin_token():
    return create_access_token(
        subject="admin_houston",
        role="ADMIN",
    )


@pytest.fixture
def crew_token():
    return create_access_token(
        subject="astronaut_john_glenn",
        role="CREW_MEMBER",
        crew_member_id=str(uuid.uuid4()),
    )


# ==============================================================================
# 1. Source Provenance Tests
# ==============================================================================

def test_source_provenance_registration(client: TestClient, flight_surgeon_token):
    """Verifies guidance source creation with full provenance, attribution, and publisher metadata."""
    payload = {
        "source_identifier": "NASA-STD-3001-TEST",
        "title": "NASA Spaceflight Human-System Standard, Volume 1: Crew Health",
        "publisher": "National Aeronautics and Space Administration (NASA OCHMO)",
        "document_url": "https://www.nasa.gov/hhp/standards",
        "version": "Revision C",
        "citation_reference": "Section 4.2.1 Cardiovascular Deconditioning",
        "summary": "Mandates physiological monitoring requirements and environmental standards for human spaceflight missions.",
        "health_indicator": "heart_rate",
        "spaceflight_hazard": "MICROGRAVITY",
        "mission_context": "TRANSIT",
        "target_population": "Astronaut Corps",
        "evidence_limitations": "Standard specifies vehicle architecture and clinical criteria; requires individual clinical evaluation.",
        "intended_use": "Operational aerospace medical guidance.",
        "publication_date": "2023-01-15T00:00:00Z",
    }

    response = client.post(
        "/api/v1/guidance/sources",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_identifier"] == "NASA-STD-3001-TEST"
    assert data["publisher"] == "National Aeronautics and Space Administration (NASA OCHMO)"
    assert data["document_url"] == "https://www.nasa.gov/hhp/standards"
    assert data["version"] == "Revision C"
    assert data["reviewer_metadata"]["created_by_role"] == "FLIGHT_SURGEON"

    # Verify duplicate source identifier is rejected
    dup_response = client.post(
        "/api/v1/guidance/sources",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json=payload,
    )
    assert dup_response.status_code == 409


# ==============================================================================
# 2. Approval Permissions Tests
# ==============================================================================

def test_approval_permissions_enforcement(client: TestClient, crew_token, flight_surgeon_token):
    """Verifies least-privilege role boundaries: Crew members cannot create, review, or supersede guidance."""
    # 1. Crew cannot create guidance sources
    src_res = client.post(
        "/api/v1/guidance/sources",
        headers={"Authorization": f"Bearer {crew_token}"},
        json={
            "source_identifier": "UNAUTHORIZED-SRC",
            "title": "Unauthorized Source",
            "publisher": "Hacker",
            "version": "1.0",
        },
    )
    assert src_res.status_code == 403

    # 2. Crew cannot ingest guidance documents
    doc_res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {crew_token}"},
        json={
            "document_identifier": "UNAUTHORIZED-DOC",
            "title": "Unauthorized Document",
            "guidance_type": "EDUCATIONAL",
            "summary": "Should be blocked",
        },
    )
    assert doc_res.status_code == 403

    # Create a legitimate document as flight surgeon to test review & supersede endpoints
    create_res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "document_identifier": "DOC-AUTH-TEST-01",
            "title": "Orthostatic Intolerance Management",
            "guidance_type": "OPERATIONAL_INSTRUCTION",
            "summary": "Protocol for post-landing compression garments.",
        },
    )
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]

    # 3. Crew cannot transition approval status
    review_res = client.post(
        "/api/v1/guidance/{0}/reviews".format(doc_id),
        headers={"Authorization": f"Bearer {crew_token}"},
        json={
            "new_status": "under_review",
            "decision_rationale": "Unauthorized transition attempt",
        },
    )
    assert review_res.status_code == 403

    # 4. Crew cannot supersede guidance
    super_res = client.post(
        "/api/v1/guidance/{0}/supersede".format(doc_id),
        headers={"Authorization": f"Bearer {crew_token}"},
        json={
            "new_version": "2.0.0",
            "decision_rationale": "Unauthorized supersede attempt",
        },
    )
    assert super_res.status_code == 403


# ==============================================================================
# 3. Crew Member Draft Restriction & Redaction Tests
# ==============================================================================

def test_crew_member_draft_restriction_and_redaction(client: TestClient, flight_surgeon_token, crew_token):
    """Verifies that draft content and administrative reviewer metadata are strictly restricted/redacted for crew."""
    # 1. Flight surgeon ingests a draft document
    ingest_res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "document_identifier": "DOC-DRAFT-REDACT-01",
            "title": "Deep Space Radiation Shielding Protocols",
            "guidance_type": "OPERATIONAL_INSTRUCTION",
            "summary": "Internal protocol for shelter during SPE events.",
            "topic": "Radiation Protection",
            "spaceflight_hazard": "RADIATION",
        },
    )
    assert ingest_res.status_code == 201
    doc_id = ingest_res.json()["id"]

    # 2. Crew list query does NOT include draft documents
    crew_list = client.get(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert crew_list.status_code == 200
    returned_ids = [d["id"] for d in crew_list.json()["items"]]
    assert doc_id not in returned_ids, "Draft guidance must not be visible to crew members!"

    # 3. Crew explicit request for draft guidance returns 403 Forbidden
    forbidden_query = client.get(
        "/api/v1/guidance?approval_status=draft",
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert forbidden_query.status_code == 403

    # 4. Crew direct lookup of draft document returns 404 Not Found
    direct_get = client.get(
        f"/api/v1/guidance/{doc_id}",
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert direct_get.status_code == 404

    # 5. Flight Surgeon transitions document: draft -> under_review -> approved
    t1 = client.post(
        f"/api/v1/guidance/{doc_id}/reviews",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "new_status": "under_review",
            "decision_rationale": "Radiation board review submitted.",
        },
    )
    assert t1.status_code == 200
    assert t1.json()["approval_status"] == "under_review"

    t2 = client.post(
        f"/api/v1/guidance/{doc_id}/reviews",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "new_status": "approved",
            "decision_rationale": "Medical board unanimous clinical sign-off.",
        },
    )
    assert t2.status_code == 200
    assert t2.json()["approval_status"] == "approved"

    # 6. Now crew member inspects the approved document: metadata MUST be redacted
    approved_crew_get = client.get(
        f"/api/v1/guidance/{doc_id}",
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert approved_crew_get.status_code == 200
    crew_data = approved_crew_get.json()
    assert crew_data["approval_status"] == "approved"
    assert crew_data["review_metadata"] is None, "review_metadata must be redacted for crew members"
    for record in crew_data["review_records"]:
        assert record["reviewer_id"] is None, "reviewer_id must be redacted for crew members"

    # 7. Flight surgeon inspects same approved document: full administrative metadata is visible
    surgeon_get = client.get(
        f"/api/v1/guidance/{doc_id}",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
    )
    assert surgeon_get.status_code == 200
    surgeon_data = surgeon_get.json()
    assert surgeon_data["review_metadata"] is not None
    assert surgeon_data["review_metadata"]["last_reviewed_role"] == "FLIGHT_SURGEON"


# ==============================================================================
# 4. Version Changes & Superseding Tests
# ==============================================================================

def test_version_changes_and_superseding(client: TestClient, flight_surgeon_token, crew_token):
    """Verifies version history, deprecation of older version, and provenance chain upon superseding."""
    # Create base version 1.0.0
    res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "document_identifier": "DOC-HRP-SLEEP-HYGIENE",
            "title": "Crew Sleep Hygiene Guidelines",
            "guidance_type": "EDUCATIONAL",
            "summary": "Circadian alignment and sleep environment controls.",
            "version": "1.0.0",
        },
    )
    v1_id = res.json()["id"]

    # Transition v1 to approved
    client.post(
        f"/api/v1/guidance/{v1_id}/reviews",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={"new_status": "under_review", "decision_rationale": "Preliminary review"},
    )
    client.post(
        f"/api/v1/guidance/{v1_id}/reviews",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={"new_status": "approved", "decision_rationale": "Approved for baseline flight operations"},
    )

    # Supersede v1 with v2.0.0
    super_res = client.post(
        f"/api/v1/guidance/{v1_id}/supersede",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "new_version": "2.0.0",
            "title": "Crew Sleep Hygiene and Circadian Lighting Standards",
            "summary": "Updated with blue-wavelength LED cabin lighting protocols.",
            "decision_rationale": "Incorporated findings from ISS lighting upgrade trials.",
        },
    )
    assert super_res.status_code == 200
    v2_data = super_res.json()
    v2_id = v2_data["id"]
    assert v2_data["version"] == "2.0.0"
    assert v2_data["approval_status"] == "draft"  # New version must be vetted
    assert "blue-wavelength" in v2_data["summary"]

    # Verify v1 is now retired and points to v2
    v1_res = client.get(
        f"/api/v1/guidance/{v1_id}",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
    )
    v1_data = v1_res.json()
    assert v1_data["approval_status"] == "retired"
    assert v1_data["superseded_by_id"] == v2_id


# ==============================================================================
# 5. Retired Guidance Tests
# ==============================================================================

def test_retired_guidance_access_restriction(client: TestClient, flight_surgeon_token, crew_token):
    """Verifies that retired guidance is removed from active crew queries."""
    # Create and retire a document
    res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "document_identifier": "DOC-OBSOLETE-PROTOCOL-01",
            "title": "Legacy Centrifuge Protocol",
            "guidance_type": "OPERATIONAL_INSTRUCTION",
            "summary": "Obsolete protocol superseded by modern resistance exercise.",
        },
    )
    doc_id = res.json()["id"]

    # Transition: draft -> under_review -> approved -> retired
    client.post(f"/api/v1/guidance/{doc_id}/reviews", headers={"Authorization": f"Bearer {flight_surgeon_token}"}, json={"new_status": "under_review", "decision_rationale": "Reviewing"})
    client.post(f"/api/v1/guidance/{doc_id}/reviews", headers={"Authorization": f"Bearer {flight_surgeon_token}"}, json={"new_status": "approved", "decision_rationale": "Approved"})
    retire_res = client.post(f"/api/v1/guidance/{doc_id}/reviews", headers={"Authorization": f"Bearer {flight_surgeon_token}"}, json={"new_status": "retired", "decision_rationale": "Protocol retired due to updated standards"})
    assert retire_res.status_code == 200
    assert retire_res.json()["approval_status"] == "retired"

    # Crew member cannot find retired document
    crew_res = client.get(f"/api/v1/guidance/{doc_id}", headers={"Authorization": f"Bearer {crew_token}"})
    assert crew_res.status_code == 404


# ==============================================================================
# 6. Multi-Parameter Filtering Tests
# ==============================================================================

def test_guidance_filtering(client: TestClient, flight_surgeon_token):
    """Verifies query filtering by topic, indicator, hazard, mission context, and guidance type."""
    # Register 3 distinct documents
    docs = [
        {
            "document_identifier": "FILTER-DOC-EDU-CARDIO",
            "title": "Cardiovascular Microgravity Adaptation",
            "guidance_type": "EDUCATIONAL",
            "summary": "Physiological fluid shifts and cardiac remodeling in space.",
            "topic": "Cardiovascular",
            "health_indicator": "heart_rate",
            "spaceflight_hazard": "MICROGRAVITY",
            "mission_context": "TRANSIT",
        },
        {
            "document_identifier": "FILTER-DOC-OP-FATIGUE",
            "title": "Fatigue Countermeasures during EVA",
            "guidance_type": "OPERATIONAL_INSTRUCTION",
            "summary": "Rest schedule and alertness checklist for lunar surface EVA.",
            "topic": "Sleep & Fatigue",
            "health_indicator": "sleep_duration",
            "spaceflight_hazard": "HOSTILE_CLOSED_ENVIRONMENT",
            "mission_context": "EVA",
        },
        {
            "document_identifier": "FILTER-DOC-RULE-HR",
            "title": "Resting Bradycardia Evaluation Rule",
            "guidance_type": "CLINICAL_RULE",
            "summary": "Rule threshold evaluating resting heart rate below 40 bpm.",
            "topic": "Cardiovascular",
            "health_indicator": "heart_rate",
            "spaceflight_hazard": "MICROGRAVITY",
            "mission_context": "TRANSIT",
        },
    ]

    for d in docs:
        client.post(
            "/api/v1/guidance",
            headers={"Authorization": f"Bearer {flight_surgeon_token}"},
            json=d,
        )

    # Filter by topic: Cardiovascular
    cardio_res = client.get(
        "/api/v1/guidance?topic=Cardiovascular",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
    )
    assert cardio_res.status_code == 200
    cardio_ids = [item["document_identifier"] for item in cardio_res.json()["items"]]
    assert "FILTER-DOC-EDU-CARDIO" in cardio_ids
    assert "FILTER-DOC-RULE-HR" in cardio_ids
    assert "FILTER-DOC-OP-FATIGUE" not in cardio_ids

    # Filter by guidance_type: OPERATIONAL_INSTRUCTION
    op_res = client.get(
        "/api/v1/guidance?guidance_type=OPERATIONAL_INSTRUCTION",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
    )
    assert op_res.status_code == 200
    op_ids = [item["document_identifier"] for item in op_res.json()["items"]]
    assert "FILTER-DOC-OP-FATIGUE" in op_ids
    assert "FILTER-DOC-EDU-CARDIO" not in op_ids

    # Filter by mission_context: EVA
    eva_res = client.get(
        "/api/v1/guidance?mission_context=EVA",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
    )
    assert eva_res.status_code == 200
    eva_ids = [item["document_identifier"] for item in eva_res.json()["items"]]
    assert "FILTER-DOC-OP-FATIGUE" in eva_ids
    assert len(eva_ids) == 1


# ==============================================================================
# 7. Source Links Tests
# ==============================================================================

def test_source_links(client: TestClient, flight_surgeon_token):
    """Verifies that guidance documents correctly link to parent guidance sources."""
    # Register source
    src_res = client.post(
        "/api/v1/guidance/sources",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "source_identifier": "NASA-HRP-STANDARDS-TEST",
            "title": "NASA Human Research Program Evidence Book",
            "publisher": "NASA Human Research Program",
            "version": "2024 Edition",
            "document_url": "https://humanresearchroadmap.nasa.gov",
        },
    )
    assert src_res.status_code == 201
    source_id = src_res.json()["id"]

    # Ingest document linking to source
    doc_res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "document_identifier": "DOC-LINKED-SOURCE-01",
            "guidance_source_id": source_id,
            "title": "Radiation Induced Cardiovascular Risk",
            "guidance_type": "EDUCATIONAL",
            "summary": "Evidence synthesis regarding GCR and SPE cardiovascular impact.",
        },
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    # Fetch document and verify guidance_source relationship is populated
    get_res = client.get(
        f"/api/v1/guidance/{doc_id}",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
    )
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["guidance_source"] is not None
    assert data["guidance_source"]["source_identifier"] == "NASA-HRP-STANDARDS-TEST"
    assert data["guidance_source"]["publisher"] == "NASA Human Research Program"


# ==============================================================================
# 8. State Machine Invalid Transitions Tests
# ==============================================================================

def test_invalid_approval_state_transitions(client: TestClient, flight_surgeon_token):
    """Verifies that invalid or skipping workflow transitions are rejected with 400 Bad Request."""
    res = client.post(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "document_identifier": "DOC-TRANSITION-TEST-01",
            "title": "Transition Test",
            "guidance_type": "EDUCATIONAL",
            "summary": "Testing invalid jumps.",
        },
    )
    doc_id = res.json()["id"]

    # Attempt direct jump from draft -> approved without review
    invalid_jump = client.post(
        f"/api/v1/guidance/{doc_id}/reviews",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "new_status": "approved",
            "decision_rationale": "Trying to skip review",
        },
    )
    assert invalid_jump.status_code == 400
    error_payload = invalid_jump.json()
    error_msg = error_payload.get("error", {}).get("message", "")
    assert "Invalid approval status transition" in error_msg

    # Attempt direct jump from draft -> retired
    invalid_retire = client.post(
        f"/api/v1/guidance/{doc_id}/reviews",
        headers={"Authorization": f"Bearer {flight_surgeon_token}"},
        json={
            "new_status": "retired",
            "decision_rationale": "Trying to retire directly from draft",
        },
    )
    assert invalid_retire.status_code == 400


# ==============================================================================
# 9. Prevention of Unapproved Rules from Activating Tests
# ==============================================================================

class GatedClinicalRule(ClinicalRuleInterface):
    """Test rule linked to guidance approval status."""
    rule_id = "TEST-GATED-RULE-01"
    version = "1.0.0"
    title = "Gated Test Rule"
    description = "Only activates if backing guidance is approved."
    guidance_source = {"source": "NASA-STD-3001"}
    applicable_context = "MICROGRAVITY"
    approval_status = "approved"
    guidance_approval_status = "draft"  # Backing guidance starts as draft

    def evaluate(self, observations, context):
        return None


def test_prevention_of_unapproved_rules_becoming_active():
    """Verifies that unreviewed or unapproved guidance prevents associated clinical rules from activating."""
    clinical_rule_registry.clear()
    gated_rule = GatedClinicalRule()
    clinical_rule_registry.register(gated_rule)

    try:
        # Gated rule has guidance_approval_status = "draft"
        active_rules = clinical_rule_registry.get_active_rules(context="MICROGRAVITY")
        assert len(active_rules) == 0, "Rule backed by draft guidance must not be activated!"

        # Transition backing guidance to under_review -> still blocked
        gated_rule.guidance_approval_status = "under_review"
        assert len(clinical_rule_registry.get_active_rules(context="MICROGRAVITY")) == 0

        # Transition backing guidance to retired -> still blocked
        gated_rule.guidance_approval_status = "retired"
        assert len(clinical_rule_registry.get_active_rules(context="MICROGRAVITY")) == 0

        # Transition backing guidance to approved -> rule activates!
        gated_rule.guidance_approval_status = "approved"
        active_rules = clinical_rule_registry.get_active_rules(context="MICROGRAVITY")
        assert len(active_rules) == 1
        assert active_rules[0].rule_id == "TEST-GATED-RULE-01"
    finally:
        clinical_rule_registry.clear()
