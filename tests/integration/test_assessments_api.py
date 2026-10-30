import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_access_token
from src.modules.clinical.rules import (
    ClinicalRuleFinding,
    ClinicalRuleInterface,
    clinical_rule_registry,
)


# ==============================================================================
# Nonclinical Test Rules for Integration Testing
# ==============================================================================

class NonclinicalMockHrRule(ClinicalRuleInterface):
    """Test rule verifying elevated heart rate in test fixtures only."""
    rule_id = "TEST_RULE_HR_CAUTION_01"
    version = "1.0.0"
    title = "Test Heart Rate Elevated Trigger"
    description = "Nonclinical fixture rule to test finding generation."
    guidance_source = {
        "source_identifier": "TEST-GUIDANCE-3001",
        "title": "NASA Human-System Standard (Test Mock)",
        "publisher": "Test Flight Surgeon Office",
        "version": "Rev C",
        "document_url": "https://example.com/nasa-std-3001-test",
    }
    applicable_context = "MICROGRAVITY"
    approval_status = "APPROVED"
    effective_from = datetime(2025, 1, 1, tzinfo=timezone.utc)
    effective_to = datetime(2035, 1, 1, tzinfo=timezone.utc)
    target_measurement_types = ["heart_rate"]
    max_freshness_seconds = 7200.0  # 2 hours

    def evaluate(self, observations, context):
        obs = observations.get("heart_rate")
        if obs and obs.value_numeric and obs.value_numeric > 100.0:
            return ClinicalRuleFinding(
                indicator="heart_rate",
                observed_value=obs.value_numeric,
                unit=obs.unit,
                observed_at=obs.measured_at,
                severity="CAUTION",
                explanation=f"Observed heart rate {obs.value_numeric} bpm exceeds threshold (100 bpm).",
                rule_reference=self.guidance_source,
                limitations="Nonclinical test rule for unit/integration testing only; not a diagnosis.",
                next_step="Notify flight surgeon for routine telemetry review.",
            )
        return None


class NonclinicalFailingRule(ClinicalRuleInterface):
    """Test rule that raises an unexpected exception to verify safe failure behavior."""
    rule_id = "TEST_RULE_FAILING_01"
    version = "1.0.0"
    title = "Test Crash Rule"
    description = "Intentionally throws to verify failure handling."
    guidance_source = {"source_identifier": "FAIL-DOC"}
    applicable_context = "MICROGRAVITY"
    approval_status = "APPROVED"
    target_measurement_types = ["heart_rate"]

    def evaluate(self, observations, context):
        raise RuntimeError("Internal math matrix inversion singularity.")


@pytest.fixture(autouse=True)
def clean_rule_registry():
    """Ensure clinical rule registry is reset before and after every test."""
    clinical_rule_registry.clear()
    yield
    clinical_rule_registry.clear()


@pytest.fixture
def test_crew():
    return {
        "crew_1": uuid.uuid4(),
        "crew_2": uuid.uuid4(),
    }


@pytest.fixture
def crew_1_token(test_crew):
    return create_access_token(
        subject="astronaut_mark",
        role="CREW_MEMBER",
        crew_member_id=str(test_crew["crew_1"]),
    )


@pytest.fixture
def crew_2_token(test_crew):
    return create_access_token(
        subject="astronaut_lewis",
        role="CREW_MEMBER",
        crew_member_id=str(test_crew["crew_2"]),
    )


# ==============================================================================
# Clinical Assessment Tests
# ==============================================================================

def test_assessment_with_empty_registry(client: TestClient, test_crew, crew_1_token):
    """Verify system starts with empty registry and safely reports not_assessed."""
    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "operational_context": "MICROGRAVITY",
            "evaluation_window_hours": 24.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assessment_status"] == "not_assessed"
    assert "No active approved clinical rules" in data["status_reason"]
    assert len(data["findings"]) == 0


def test_assessment_with_missing_inputs(client: TestClient, test_crew, crew_1_token):
    """Verify missing required observation returns insufficient_evidence."""
    clinical_rule_registry.register(NonclinicalMockHrRule())

    # Request assessment with zero observations in DB
    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "operational_context": "MICROGRAVITY",
            "evaluation_window_hours": 24.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assessment_status"] == "insufficient_evidence"
    assert "heart_rate" in data["input_evaluation"]["missing_inputs"]
    assert len(data["findings"]) == 0


def test_assessment_with_stale_data(client: TestClient, test_crew, crew_1_token):
    """Verify observations older than rule max_freshness_seconds are flagged as stale."""
    clinical_rule_registry.register(NonclinicalMockHrRule())  # Max freshness = 2 hours

    # Ingest measurement from 5 hours ago (stale)
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 120.0,
            "unit": "bpm",
            "measured_at": stale_time,
        },
    )

    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "operational_context": "MICROGRAVITY",
            "evaluation_window_hours": 24.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assessment_status"] == "insufficient_evidence"
    assert "heart_rate" in data["input_evaluation"]["stale_inputs"]
    assert len(data["findings"]) == 0


def test_assessment_with_invalidated_data(client: TestClient, test_crew, crew_1_token):
    """Verify invalidated observations are flagged as invalid and excluded from evaluation."""
    clinical_rule_registry.register(NonclinicalMockHrRule())

    # Ingest and then invalidate
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    res_m = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 120.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )
    m_id = res_m.json()["id"]

    client.post(
        f"/api/v1/measurements/{m_id}/invalidate",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"reason": "Faulty lead wire"},
    )

    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assessment_status"] == "insufficient_evidence"
    assert "heart_rate" in data["input_evaluation"]["invalid_inputs"]


def test_assessment_nominal_assessed_no_findings(client: TestClient, test_crew, crew_1_token):
    """Verify all rules evaluate with zero findings triggers assessed_no_findings."""
    clinical_rule_registry.register(NonclinicalMockHrRule())

    # Ingest nominal HR (72.0 bpm, < 100.0)
    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    res_m = client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 72.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )
    m_id = res_m.json()["id"]

    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assessment_status"] == "assessed_no_findings"
    assert len(data["findings"]) == 0
    assert m_id in [str(uid) for uid in data["evaluated_measurement_ids"]]


def test_assessment_triggered_finding(client: TestClient, test_crew, crew_1_token):
    """Verify elevated HR triggers explainable finding with source attribution."""
    clinical_rule_registry.register(NonclinicalMockHrRule())

    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 125.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )

    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["findings"]) == 1
    finding = data["findings"][0]
    assert finding["indicator"] == "heart_rate"
    assert finding["observed_value"] == 125.0
    assert finding["severity"] == "CAUTION"
    assert "exceeds threshold" in finding["explanation"]
    assert finding["rule_reference"]["source_identifier"] == "TEST-GUIDANCE-3001"
    assert "not a diagnosis" in finding["limitations"]
    assert "Notify flight surgeon" in finding["next_step"]


def test_assessment_safe_failure_on_rule_exception(client: TestClient, test_crew, crew_1_token):
    """Verify rule execution failure records technical error and status=needs_review (not nominal!)."""
    clinical_rule_registry.register(NonclinicalFailingRule())

    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 75.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )

    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )
    assert response.status_code == 201
    data = response.json()
    # Must NOT report nominal!
    assert data["assessment_status"] == "needs_review"
    assert len(data["technical_errors"]) == 1
    assert data["technical_errors"][0]["rule_id"] == "TEST_RULE_FAILING_01"
    assert "singularity" in data["technical_errors"][0]["error"]


def test_assessment_reproducibility(client: TestClient, test_crew, crew_1_token):
    """Verify executing assessment twice on identical observations yields identical reproducibility hash."""
    clinical_rule_registry.register(NonclinicalMockHrRule())

    measured_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    client.post(
        "/api/v1/measurements",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={
            "crew_member_id": str(test_crew["crew_1"]),
            "measurement_type": "heart_rate",
            "value_numeric": 110.0,
            "unit": "bpm",
            "measured_at": measured_at,
        },
    )

    res1 = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )
    res2 = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )

    data1 = res1.json()
    data2 = res2.json()

    # Reproducibility hash must be identical
    assert data1["reproducibility_hash"] == data2["reproducibility_hash"]
    assert data1["assessment_status"] == data2["assessment_status"]
    assert len(data1["findings"]) == len(data2["findings"])


def test_assessment_retrieval_and_history(client: TestClient, test_crew, crew_1_token):
    """Verify GET /api/v1/assessments/{id} and GET /api/v1/assessments."""
    # Generate assessment
    create_res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
        json={"crew_member_id": str(test_crew["crew_1"])},
    )
    assert create_res.status_code == 201
    assessment_id = create_res.json()["id"]

    # Retrieve by ID
    get_res = client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == assessment_id

    # List assessments
    list_res = client.get(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


def test_assessment_cross_crew_access_rejected(client: TestClient, test_crew, crew_1_token, crew_2_token):
    """Verify crew member cannot request or view another crew member's clinical assessment."""
    # 1. Crew 2 creates assessment
    res_crew_2 = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {crew_2_token}"},
        json={"crew_member_id": str(test_crew["crew_2"])},
    )
    assert res_crew_2.status_code == 201
    c2_assessment_id = res_crew_2.json()["id"]

    # 2. Crew 1 attempts to retrieve Crew 2's assessment -> 403 Forbidden
    res_cross = client.get(
        f"/api/v1/assessments/{c2_assessment_id}",
        headers={"Authorization": f"Bearer {crew_1_token}"},
    )
    assert res_cross.status_code == 403
    assert res_cross.json()["error"]["code"] == "forbidden"

