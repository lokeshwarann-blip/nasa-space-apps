import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    InvalidValueError,
    ResourceNotFoundError,
)
from src.models.clinical import Assessment
from src.models.telemetry import HealthMeasurement
from src.modules.audit.service import record_audit_event
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService, AuthorizationError
from src.modules.clinical.rules import (
    ClinicalRuleFinding,
    clinical_rule_registry,
)
from src.modules.clinical.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    InputEvaluationSummary,
)


class AssessmentService:
    """Deterministic, explainable clinical assessment service."""

    ENGINE_VERSION = "engine-v1.0.0"
    RULESET_VERSION = "rules-2026.1"

    @classmethod
    def _calculate_reproducibility_hash(
        cls,
        evaluated_ids: list[uuid.UUID],
        rule_signatures: list[str],
        operational_context: str,
    ) -> str:
        """Computes a deterministic cryptographic hash of input observations and rule versions."""
        payload = {
            "evaluated_ids": sorted([str(uid) for uid in evaluated_ids]),
            "rule_signatures": sorted(rule_signatures),
            "context": operational_context,
            "engine": cls.ENGINE_VERSION,
        }
        raw_json = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_json).hexdigest()

    @classmethod
    async def run_assessment(
        cls,
        session: AsyncSession,
        payload: AssessmentRequest,
        identity: AuthenticatedIdentity,
    ) -> AssessmentResponse:
        """Executes a deterministic rule-based health assessment."""
        # 1. Resolve Target Crew Member
        effective_crew_id: uuid.UUID
        if identity.role == "CREW_MEMBER":
            if not identity.crew_member_id:
                raise AuthorizationError("Crew identity is not bound to a valid crew member.")
            user_crew = uuid.UUID(identity.crew_member_id)
            if payload.crew_member_id is not None and payload.crew_member_id != user_crew:
                raise AuthorizationError("Crew members may only request assessments for themselves.")
            effective_crew_id = user_crew
        else:
            if payload.crew_member_id is None:
                raise InvalidValueError("Target crew_member_id is required for medical reviewers.")
            if not AuthService.verify_object_level_crew_access(identity, payload.crew_member_id):
                raise AuthorizationError(
                    f"User '{identity.username}' is not authorized to assess crew member '{payload.crew_member_id}'."
                )
            effective_crew_id = payload.crew_member_id

        # 2. Time Window Bounds
        assessed_at = datetime.now(timezone.utc)
        window_start = assessed_at - timedelta(hours=payload.evaluation_window_hours)

        # 3. Retrieve Active Approved Clinical Rules
        active_rules = clinical_rule_registry.get_active_rules(
            context=payload.operational_context,
            target_types=payload.target_measurement_types,
            evaluation_time=assessed_at,
        )

        # 4. Handle Empty Registry (Mandated initial state)
        if not active_rules:
            input_summary = InputEvaluationSummary(
                available_inputs=[],
                missing_inputs=[],
                invalid_inputs=[],
                stale_inputs=[],
                out_of_scope_inputs=[],
            )
            rep_hash = cls._calculate_reproducibility_hash([], [], payload.operational_context)
            assessment_model = Assessment(
                id=uuid.uuid4(),
                subject_id=effective_crew_id,
                assessed_at=assessed_at,
                engine_version=cls.ENGINE_VERSION,
                ruleset_version=cls.RULESET_VERSION,
                assessment_status="not_assessed",
                findings={"findings": [], "reason": "No active approved clinical rules registered for this operational context."},
                input_measurement_ids=[],
                data_quality_info={"rules_registered": 0, "status": "not_assessed"},
            )
            session.add(assessment_model)
            await session.flush()

            await record_audit_event(
                session=session,
                actor=identity.username,
                action="GENERATE_ASSESSMENT",
                resource_type="assessment",
                resource_id=str(assessment_model.id),
                metadata={"status": "not_assessed", "reason": "empty_registry"},
            )

            return AssessmentResponse(
                id=assessment_model.id,
                crew_member_id=effective_crew_id,
                assessed_at=assessed_at,
                engine_version=cls.ENGINE_VERSION,
                ruleset_version=cls.RULESET_VERSION,
                assessment_status="not_assessed",
                status_reason="No active approved clinical rules are registered in the system for this operational context.",
                findings=[],
                input_evaluation=input_summary,
                evaluated_measurement_ids=[],
                data_quality_info={"rules_registered": 0},
                technical_errors=[],
                reproducibility_hash=rep_hash,
            )

        # 5. Query Observations for Evaluation Scope
        all_required_types = set()
        for rule in active_rules:
            all_required_types.update(rule.target_measurement_types)

        query = (
            select(HealthMeasurement)
            .where(
                HealthMeasurement.crew_member_id == effective_crew_id,
                HealthMeasurement.measured_at >= window_start,
                HealthMeasurement.measured_at <= assessed_at,
            )
            .order_by(HealthMeasurement.measured_at.desc(), HealthMeasurement.id.desc())
        )
        if all_required_types:
            query = query.where(HealthMeasurement.measurement_type.in_(all_required_types))

        result = await session.execute(query)
        measurements = result.scalars().all()

        # Group by type (keep latest observation per indicator)
        latest_valid_by_type: dict[str, HealthMeasurement] = {}
        invalid_types: set[str] = set()

        for m in measurements:
            m_ts = m.measured_at.replace(tzinfo=timezone.utc) if m.measured_at.tzinfo is None else m.measured_at
            m.measured_at = m_ts

            if m.quality_status == "INVALIDATED":
                invalid_types.add(m.measurement_type)
            elif m.measurement_type not in latest_valid_by_type:
                latest_valid_by_type[m.measurement_type] = m

        # Classify inputs
        available_inputs = list(latest_valid_by_type.keys())
        missing_inputs = [t for t in all_required_types if t not in latest_valid_by_type and t not in invalid_types]
        stale_inputs: list[str] = []

        # 6. Evaluate Active Approved Rules
        findings: list[ClinicalRuleFinding] = []
        technical_errors: list[dict[str, str]] = []
        evaluated_ids: set[uuid.UUID] = set()
        rule_signatures: list[str] = []
        rules_evaluated_count = 0

        for rule in active_rules:
            rule_sig = f"{rule.rule_id}:v{rule.version}"
            rule_signatures.append(rule_sig)

            # Check rule input completeness
            has_all_inputs = True
            for req_type in rule.target_measurement_types:
                if req_type not in latest_valid_by_type:
                    has_all_inputs = False
                    break
                # Freshness check
                obs = latest_valid_by_type[req_type]
                if rule.max_freshness_seconds is not None:
                    age_sec = (assessed_at - obs.measured_at).total_seconds()
                    if age_sec > rule.max_freshness_seconds:
                        if req_type not in stale_inputs:
                            stale_inputs.append(req_type)
                        has_all_inputs = False
                        break

            if not has_all_inputs:
                continue

            # Record measurement IDs used
            for req_type in rule.target_measurement_types:
                evaluated_ids.add(latest_valid_by_type[req_type].id)

            # Deterministic Execution with failure isolation
            try:
                finding = rule.evaluate(
                    observations=latest_valid_by_type,
                    context={"context": payload.operational_context, "assessed_at": assessed_at},
                )
                rules_evaluated_count += 1
                if finding:
                    findings.append(finding)
            except Exception as err:
                # Crucial safety mandate: rule execution error must NOT silently report nominal!
                technical_errors.append({
                    "rule_id": rule.rule_id,
                    "error": str(err),
                })

        # 7. Determine Assessment Status
        assessment_status: str
        status_reason: str

        if technical_errors:
            assessment_status = "needs_review"
            status_reason = f"Execution error in {len(technical_errors)} rule(s). Requires medical reviewer triage."
        elif rules_evaluated_count == 0:
            assessment_status = "insufficient_evidence"
            status_reason = "No applicable rules could be fully evaluated due to missing or stale required inputs."
        elif len(missing_inputs) > 0 or len(stale_inputs) > 0:
            assessment_status = "partially_assessed"
            if findings:
                status_reason = f"Partially assessed ({rules_evaluated_count}/{len(active_rules)} rules evaluated) with {len(findings)} finding(s)."
            else:
                status_reason = f"Partially assessed ({rules_evaluated_count}/{len(active_rules)} rules evaluated) with zero rule-triggered findings."
        elif not findings:
            assessment_status = "assessed_no_findings"
            status_reason = f"All {rules_evaluated_count} applicable approved rules evaluated with zero rule-triggered findings."
        else:
            assessment_status = "partially_assessed"
            status_reason = f"Assessment complete: {len(findings)} clinical finding(s) triggered."

        # 8. Compute Reproducibility Hash
        rep_hash = cls._calculate_reproducibility_hash(
            list(evaluated_ids),
            rule_signatures,
            payload.operational_context,
        )

        input_summary = InputEvaluationSummary(
            available_inputs=available_inputs,
            missing_inputs=missing_inputs,
            invalid_inputs=list(invalid_types),
            stale_inputs=stale_inputs,
            out_of_scope_inputs=[],
        )

        # 9. Persist Assessment Entity
        assessment_model = Assessment(
            id=uuid.uuid4(),
            subject_id=effective_crew_id,
            assessed_at=assessed_at,
            engine_version=cls.ENGINE_VERSION,
            ruleset_version=cls.RULESET_VERSION,
            assessment_status=assessment_status,
            findings={
                "status_reason": status_reason,
                "findings": [f.model_dump(mode="json") for f in findings],
                "technical_errors": technical_errors,
                "reproducibility_hash": rep_hash,
            },
            input_measurement_ids=[str(uid) for uid in evaluated_ids],
            data_quality_info=input_summary.model_dump(mode="json"),
        )
        session.add(assessment_model)
        await session.flush()

        await record_audit_event(
            session=session,
            actor=identity.username,
            action="GENERATE_ASSESSMENT",
            resource_type="assessment",
            resource_id=str(assessment_model.id),
            metadata={
                "status": assessment_status,
                "findings_count": len(findings),
                "rules_evaluated": rules_evaluated_count,
            },
        )

        return AssessmentResponse(
            id=assessment_model.id,
            crew_member_id=effective_crew_id,
            assessed_at=assessed_at,
            engine_version=cls.ENGINE_VERSION,
            ruleset_version=cls.RULESET_VERSION,
            assessment_status=assessment_status,  # type: ignore
            status_reason=status_reason,
            findings=findings,
            input_evaluation=input_summary,
            evaluated_measurement_ids=list(evaluated_ids),
            data_quality_info=input_summary.model_dump(mode="json"),
            technical_errors=technical_errors,
            reproducibility_hash=rep_hash,
        )

    @classmethod
    async def get_assessment_by_id(
        cls,
        session: AsyncSession,
        assessment_id: uuid.UUID,
        identity: AuthenticatedIdentity,
    ) -> AssessmentResponse:
        """Retrieves an existing saved assessment by ID with object-level authorization."""
        query = select(Assessment).where(Assessment.id == assessment_id)
        result = await session.execute(query)
        assessment = result.scalar_one_or_none()

        if assessment is None:
            raise ResourceNotFoundError("assessment", assessment_id)

        # Object-level authorization
        await AuthService.enforce_crew_access(
            session=session,
            identity=identity,
            target_crew_member_id=assessment.subject_id,
            action="READ_ASSESSMENT",
        )

        # Reconstruct response from stored JSON
        findings_json = assessment.findings or {}
        raw_findings = findings_json.get("findings", [])
        structured_findings = [ClinicalRuleFinding(**f) for f in raw_findings]
        data_quality = assessment.data_quality_info or {}
        input_eval = InputEvaluationSummary(
            available_inputs=data_quality.get("available_inputs", []),
            missing_inputs=data_quality.get("missing_inputs", []),
            invalid_inputs=data_quality.get("invalid_inputs", []),
            stale_inputs=data_quality.get("stale_inputs", []),
            out_of_scope_inputs=data_quality.get("out_of_scope_inputs", []),
        )

        assessed_ts = (
            assessment.assessed_at.replace(tzinfo=timezone.utc)
            if assessment.assessed_at.tzinfo is None
            else assessment.assessed_at
        )

        return AssessmentResponse(
            id=assessment.id,
            crew_member_id=assessment.subject_id,
            assessed_at=assessed_ts,
            engine_version=assessment.engine_version,
            ruleset_version=assessment.ruleset_version,
            assessment_status=assessment.assessment_status,  # type: ignore
            status_reason=findings_json.get("status_reason", ""),
            findings=structured_findings,
            input_evaluation=input_eval,
            evaluated_measurement_ids=[uuid.UUID(uid) for uid in assessment.input_measurement_ids],
            data_quality_info=data_quality,
            technical_errors=findings_json.get("technical_errors", []),
            reproducibility_hash=findings_json.get("reproducibility_hash", ""),
        )

    @classmethod
    async def list_assessments(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        crew_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AssessmentResponse], int]:
        """Lists historical assessments for authorized crew with deterministic ordering."""
        query = select(Assessment)
        count_query = select(func.count(Assessment.id))

        if identity.role == "CREW_MEMBER":
            user_crew = uuid.UUID(identity.crew_member_id) if identity.crew_member_id else None
            if not user_crew:
                raise AuthorizationError("Crew identity is not bound to a valid crew member.")
            if crew_id is not None and crew_id != user_crew:
                raise AuthorizationError("Crew members may only query their own assessments.")
            query = query.where(Assessment.subject_id == user_crew)
            count_query = count_query.where(Assessment.subject_id == user_crew)

        elif identity.role == "FLIGHT_SURGEON":
            assigned_uuids = [uuid.UUID(cid) for cid in identity.assigned_crew_ids]
            if not assigned_uuids:
                return [], 0
            if crew_id is not None:
                if crew_id not in assigned_uuids:
                    raise AuthorizationError("Flight surgeon not assigned to requested crew member.")
                query = query.where(Assessment.subject_id == crew_id)
                count_query = count_query.where(Assessment.subject_id == crew_id)
            else:
                query = query.where(Assessment.subject_id.in_(assigned_uuids))
                count_query = count_query.where(Assessment.subject_id.in_(assigned_uuids))

        elif identity.role == "ADMIN":
            assigned_uuids = [uuid.UUID(cid) for cid in identity.assigned_crew_ids]
            if not assigned_uuids:
                raise AuthorizationError("Admins cannot access clinical assessments without explicit assignment.")
            if crew_id is not None:
                if crew_id not in assigned_uuids:
                    raise AuthorizationError("Admin not assigned to requested crew member.")
                query = query.where(Assessment.subject_id == crew_id)
                count_query = count_query.where(Assessment.subject_id == crew_id)
            else:
                query = query.where(Assessment.subject_id.in_(assigned_uuids))
                count_query = count_query.where(Assessment.subject_id.in_(assigned_uuids))

        total = (await session.execute(count_query)).scalar() or 0

        query = query.order_by(Assessment.assessed_at.desc(), Assessment.id.desc()).limit(limit).offset(offset)
        records = (await session.execute(query)).scalars().all()

        responses = [
            await cls.get_assessment_by_id(session, r.id, identity)
            for r in records
        ]
        return responses, total
