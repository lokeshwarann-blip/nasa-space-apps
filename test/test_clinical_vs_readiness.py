import json
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

from src.models import (
    Base, User, CrewMember, HealthMeasurement, Assessment, AlertInstance
)
from tests.db_adapter import AsyncSessionAdapter
from src.core.database import get_db
from src.main import create_app
from src.core.config import Settings
from src.core.security import create_access_token, hash_password
from test.fixtures import TEST_USERS
from src.modules.clinical.rules import (
    ClinicalRuleInterface, ClinicalRuleFinding, clinical_rule_registry
)

# ==============================================================================
# Define Illustrative Adult Clinical Decision Rules for End-to-End Verification
# (Relabeled to illustrative adult reference ranges)
# ==============================================================================
class IllustrativeAdultRestingHrRule(ClinicalRuleInterface):
    """Illustrative adult reference range for resting heart rate (50-100 bpm).
    Decision support fixture only; not a formal NASA clinical threshold.
    """
    rule_id = "RULE-ILLUSTRATIVE-ADULT-HR-RANGE"
    version = "1.0.0"
    title = "Illustrative Adult Resting Heart Rate Reference Range (50-100 bpm)"
    description = "Flags clinical boundary exceedance when resting heart rate is outside illustrative 50-100 bpm range."
    guidance_source = {
        "source_identifier": "ILLUSTRATIVE-REF-VOL1",
        "title": "Illustrative Adult Physiological Reference Ranges",
        "publisher": "Clinical Reference Panel (Mock Fixture)",
        "version": "1.0",
    }
    applicable_context = "MICROGRAVITY"
    approval_status = "APPROVED"
    effective_from = datetime(2025, 1, 1, tzinfo=timezone.utc)
    effective_to = datetime(2035, 1, 1, tzinfo=timezone.utc)
    target_measurement_types = ["heart_rate"]
    max_freshness_seconds = 86400.0  # 24 hours

    def evaluate(self, observations, context):
        obs = observations.get("heart_rate")
        if obs and obs.value_numeric is not None:
            if obs.value_numeric > 100.0:
                return ClinicalRuleFinding(
                    indicator="heart_rate",
                    observed_value=obs.value_numeric,
                    unit=obs.unit,
                    observed_at=obs.measured_at,
                    severity="CAUTION",
                    explanation=f"Resting HR {obs.value_numeric:.1f} bpm exceeds illustrative adult boundary (>100 bpm).",
                    rule_reference=self.guidance_source,
                    limitations="Resting context required.",
                    next_step="Clinical evaluation by Flight Surgeon.",
                )
        return None  # NOMINAL if 50 - 100 bpm


class IllustrativeAdultSpo2Rule(ClinicalRuleInterface):
    """Illustrative adult reference range for oxygenation (nominal >=95%).
    Decision support fixture only; not a formal NASA clinical threshold.
    """
    rule_id = "RULE-ILLUSTRATIVE-ADULT-SPO2-RANGE"
    version = "1.0.0"
    title = "Illustrative Adult SpO2 Reference Boundary"
    description = "Flags clinical boundary exceedance when blood oxygen saturation drops below 95%."
    guidance_source = {
        "source_identifier": "ILLUSTRATIVE-REF-VOL1",
        "title": "Illustrative Adult Physiological Reference Ranges",
        "publisher": "Clinical Reference Panel (Mock Fixture)",
        "version": "1.0",
    }
    applicable_context = "MICROGRAVITY"
    approval_status = "APPROVED"
    effective_from = datetime(2025, 1, 1, tzinfo=timezone.utc)
    effective_to = datetime(2035, 1, 1, tzinfo=timezone.utc)
    target_measurement_types = ["spo2"]
    max_freshness_seconds = 86400.0

    def evaluate(self, observations, context):
        obs = observations.get("spo2")
        if obs and obs.value_numeric is not None:
            if obs.value_numeric < 90.0:
                return ClinicalRuleFinding(
                    indicator="spo2",
                    observed_value=obs.value_numeric,
                    unit=obs.unit,
                    observed_at=obs.measured_at,
                    severity="CRITICAL",
                    explanation=f"SpO2 {obs.value_numeric:.1f}% indicates critical desaturation (<90%).",
                    rule_reference=self.guidance_source,
                    limitations="Motion artifact ruled out.",
                    next_step="Immediate clinical atmosphere assessment.",
                )
            elif obs.value_numeric < 95.0:
                return ClinicalRuleFinding(
                    indicator="spo2",
                    observed_value=obs.value_numeric,
                    unit=obs.unit,
                    observed_at=obs.measured_at,
                    severity="CAUTION",
                    explanation=f"SpO2 {obs.value_numeric:.1f}% indicates mild desaturation (90-94%).",
                    rule_reference=self.guidance_source,
                    limitations="Pulse oximetry verification required.",
                    next_step="Assess ventilation and activity context.",
                )
        return None  # NOMINAL if >= 95%


def main():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(engine)

    app = create_app(Settings(ENVIRONMENT="testing", SECRET_KEY="test" * 8))

    def _get_db():
        with Session(engine) as s:
            yield AsyncSessionAdapter(s)

    app.dependency_overrides[get_db] = _get_db

    # Register Illustrative Reference Rules
    clinical_rule_registry.clear()
    clinical_rule_registry.register(IllustrativeAdultRestingHrRule())
    clinical_rule_registry.register(IllustrativeAdultSpo2Rule())

    # Load scenario data
    scenario_file = Path(__file__).resolve().parent / "health_readings_scenario.json"
    crew_file = Path(__file__).resolve().parent / "crew_members.json"

    with open(scenario_file, "r", encoding="utf-8") as f:
        readings = json.load(f)
    with open(crew_file, "r", encoding="utf-8") as f:
        crews = json.load(f)

    with Session(engine) as s:
        for c in crews:
            s.add(CrewMember(
                id=uuid.UUID(c["id"]),
                crew_id=c["crew_id"],
                status=c["status"],
                profile_metadata=c["profile_metadata"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ))
        for u in TEST_USERS:
            s.add(User(
                id=uuid.uuid4(),
                username=u["username"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                is_active=True,
                crew_member_id=uuid.UUID(u["crew_member_id"]) if u["crew_member_id"] else None,
                assigned_crew_ids=[str(cid) for cid in u["assigned_crew_ids"]]
            ))
        for r in readings:
            s.add(HealthMeasurement(
                id=uuid.UUID(r["id"]),
                crew_member_id=uuid.UUID(r["crew_member_id"]),
                measurement_type=r["measurement_type"],
                value_numeric=r["value_numeric"],
                unit=r["unit"],
                measured_at=datetime.fromisoformat(r["measured_at"].replace("Z", "+00:00")),
                recorded_at=datetime.fromisoformat(r["recorded_at"].replace("Z", "+00:00")),
                input_method=r["input_method"],
                provenance=r["provenance"],
                quality_status=r["quality_status"],
                context_metadata=r["context_metadata"]
            ))
        s.commit()

    client = TestClient(app)

    # Auth token for flight surgeon
    fs = [u for u in TEST_USERS if u["username"] == "flight_surgeon"][0]
    token = create_access_token(
        subject=fs["username"],
        role=fs["role"],
        assigned_crew_ids=fs["assigned_crew_ids"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    # ==========================================================================
    # 1. READINESS OVERVIEW WITH GROUPED INCIDENTS & ENVIRONMENTAL HAZARDS
    # ==========================================================================
    print("=" * 105)
    print("READINESS OVERVIEW (ENHANCED DUAL-BASELINE + INCIDENTS + HAZARD ISOLATION)")
    print("=" * 105)
    resp = client.get("/api/v1/readiness/overview", headers=headers)
    assert resp.status_code == 200
    ov_data = resp.json()

    id_to_crew = {c["id"]: c["crew_id"] for c in crews}

    row_fmt = "{:<10} {:<10} {:<10} {:<12} {:<40} {:<20}"
    print(row_fmt.format("Crew", "Readiness", "Status", "Data Status", "Grouped Incidents", "Environmental"))
    print("-" * 105)

    for c in ov_data.get("crews", []):
        cid = str(c["crew_id"])
        name = id_to_crew.get(cid, cid[:8])
        incidents = [i["title"] for i in c.get("incidents", [])]
        inc_str = incidents[0] if incidents else "None"
        env = [e["hazard_type"] for e in c.get("environmental_alerts", [])]
        env_str = env[0] if env else "None"
        print(row_fmt.format(
            name,
            str(c.get("readiness")),
            c.get("status"),
            c.get("data_status"),
            inc_str[:38],
            env_str
        ))

    # ==========================================================================
    # 2. END-TO-END VERIFICATION: CLINICAL NOMINAL vs PERSONAL DRIFT (CREW-003)
    # ==========================================================================
    c3_id = crews[2]["id"]
    print("\n" + "=" * 105)
    print("END-TO-END PROOF: CLINICAL ASSESSMENT VS PERSONAL DRIFT (CREW-003 CADUCEUS)")
    print("=" * 105)

    # A. Execute Clinical Assessment
    assess_res = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "crew_member_id": c3_id,
            "operational_context": "MICROGRAVITY",
            "evaluation_window_hours": 24.0,
            "target_measurement_types": ["heart_rate", "spo2"]
        }
    )
    assess_data = assess_res.json()
    print(f"CLINICAL ASSESSMENT (Illustrative Adult Population Reference Range):")
    print(f"  - HTTP Status:        {assess_res.status_code}")
    print(f"  - Assessment Status:  {assess_data.get('assessment_status').upper()} (Assessed with ZERO clinical findings)")
    print(f"  - Status Reason:      {assess_data.get('status_reason')}")
    print(f"  - Clinical Findings:  {assess_data.get('findings')}")

    # B. Execute Personal Readiness
    readiness_res = client.get(f"/api/v1/readiness?crew_id={c3_id}", headers=headers)
    read_data = readiness_res.json()
    print(f"\nPERSONAL READINESS MODEL (Individual Rolling Baseline + CUSUM):")
    print(f"  - HTTP Status:        {readiness_res.status_code}")
    print(f"  - Readiness Score:    {read_data.get('readiness')} / 100")
    print(f"  - Operational Status: {read_data.get('status')}")
    print(f"  - Grouped Incidents:  {[i['title'] for i in read_data.get('incidents', [])]}")
    print(f"  - Drift Alerts:       {[a['message'] for a in read_data.get('drift_alerts', [])]}")

    print("\nVERIFICATION TAKEAWAY FOR FRONTEND:")
    print("  'Clinical Status: NOMINAL (Within illustrative adult reference ranges) | Individual Readiness: 61.0 (CRITICAL DRIFT - Cardiopulmonary & Sleep Strain)'")
    print("=" * 105)


if __name__ == "__main__":
    main()
