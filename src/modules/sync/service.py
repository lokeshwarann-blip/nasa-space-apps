import hashlib
import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import AppException
from src.models.audit import AuditEvent
from src.models.crew import CrewMember
from src.models.sync import SyncEventRecord
from src.models.telemetry import HealthMeasurement
from src.models.wellness import SymptomCheckIn, WellnessCheckIn
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.sync.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncBatchSummary,
    SyncEventItem,
    SyncEventResult,
)
from src.modules.telemetry.registry import (
    MeasurementValidationError,
    measurement_registry,
)


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of canonicalized JSON payload."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class SyncService:
    """Reconciles offline telemetry and check-in event batches with database idempotency."""

    @staticmethod
    async def process_batch(
        session: Any,
        batch_req: SyncBatchRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> SyncBatchResponse:
        """Processes bounded batch of offline events with partial-success isolation and idempotency."""
        now = datetime.now(timezone.utc)
        results: list[SyncEventResult] = []
        accepted_count = 0
        duplicate_count = 0
        conflict_count = 0
        rejected_count = 0

        for item in batch_req.events:
            async with session.begin_nested():
                event_result = await SyncService._process_single_event(
                    session=session,
                    event=item,
                    actor_identity=actor_identity,
                    server_received_at=now,
                )
                results.append(event_result)

                if event_result.status == "accepted":
                    accepted_count += 1
                elif event_result.status == "duplicate":
                    duplicate_count += 1
                elif event_result.status == "conflict":
                    conflict_count += 1
                else:
                    rejected_count += 1

        # Commit all accepted and audit records from the batch
        await session.commit()

        summary = SyncBatchSummary(
            total_events=len(batch_req.events),
            accepted_count=accepted_count,
            duplicate_count=duplicate_count,
            conflict_count=conflict_count,
            rejected_count=rejected_count,
        )

        return SyncBatchResponse(
            batch_id=batch_req.batch_id,
            server_received_at=now,
            summary=summary,
            results=results,
        )

    @staticmethod
    async def _process_single_event(
        session: Any,
        event: SyncEventItem,
        actor_identity: AuthenticatedIdentity,
        server_received_at: datetime,
    ) -> SyncEventResult:
        """Processes a single event with strict validation, conflict detection, and idempotency."""
        payload_hash = compute_payload_hash(event.payload)

        # 1. Authorization check: Crew member can only sync their own data
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(event.crew_member_id) != actor_identity.crew_member_id:
                return SyncEventResult(
                    client_event_id=event.client_event_id,
                    status="rejected",
                    error_code="forbidden_crew_access",
                    message="Crew members are forbidden from submitting telemetry for other crew members.",
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            assigned = actor_identity.assigned_crew_ids or []
            if "*" not in assigned and str(event.crew_member_id) not in assigned:
                return SyncEventResult(
                    client_event_id=event.client_event_id,
                    status="rejected",
                    error_code="forbidden_crew_access",
                    message="Flight surgeon is not assigned to this crew member.",
                )

        # 2. Check for existing event record (IDEMPOTENCY & CONFLICT DETECTION)
        existing_stmt = select(SyncEventRecord).where(
            SyncEventRecord.client_event_id == event.client_event_id
        )
        existing = await session.scalar(existing_stmt)
        if existing is not None:
            # Case A: Same client_event_id AND same payload hash -> DUPLICATE (idempotent retry)
            if existing.payload_hash == payload_hash:
                return SyncEventResult(
                    client_event_id=event.client_event_id,
                    status="duplicate",
                    entity_id=existing.entity_id,
                    message="Event previously received and processed.",
                )
            # Case B: Same client_event_id BUT different payload hash -> CONFLICT
            # Record audit event without exposing PHI
            audit = AuditEvent(
                actor=actor_identity.user_id,
                action="SYNC_PAYLOAD_CONFLICT",
                resource_type="SYNC_EVENT",
                resource_id=str(event.client_event_id),
                occurred_at=server_received_at,
                metadata={
                    "crew_member_id": str(event.crew_member_id),
                    "event_type": event.event_type,
                    "reason": "Reuse of client_event_id with conflicting payload hash",
                },
            )
            session.add(audit)
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="conflict",
                error_code="sync_payload_conflict",
                message="Event UUID was previously submitted with a conflicting payload.",
            )

        # 3. Schema version validation
        if event.schema_version != "1.0":
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="rejected",
                error_code="unsupported_schema_version",
                message=f"Schema version '{event.schema_version}' is unsupported. Expected '1.0'.",
            )

        # 4. Clock-skew and future timestamp validation
        measured_utc = (
            event.measured_at.astimezone(timezone.utc)
            if event.measured_at.tzinfo
            else event.measured_at.replace(tzinfo=timezone.utc)
        )
        client_event_utc = (
            event.client_event_at.astimezone(timezone.utc)
            if event.client_event_at.tzinfo
            else event.client_event_at.replace(tzinfo=timezone.utc)
        )

        max_allowed_future = server_received_at + timedelta(minutes=15)
        if measured_utc > max_allowed_future:
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="rejected",
                error_code="invalid_future_timestamp",
                message="Observation measured_at cannot exceed server clock by more than 15 minutes.",
            )
        if client_event_utc > max_allowed_future:
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="rejected",
                error_code="invalid_future_timestamp",
                message="Client event timestamp cannot exceed server clock by more than 15 minutes.",
            )

        # 5. Verify crew member exists in database
        crew_stmt = select(CrewMember).where(CrewMember.id == event.crew_member_id)
        crew = await session.scalar(crew_stmt)
        if crew is None:
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="rejected",
                error_code="crew_member_not_found",
                message=f"Crew member '{event.crew_member_id}' not found.",
            )

        # 6. Domain-specific payload validation and entity creation
        created_entity_id: uuid.UUID | None = None
        try:
            if event.event_type == "MEASUREMENT":
                created_entity_id = await SyncService._ingest_measurement(
                    session=session,
                    event=event,
                    measured_utc=measured_utc,
                    client_event_utc=client_event_utc,
                )
            elif event.event_type == "WELLNESS_CHECK_IN":
                created_entity_id = await SyncService._ingest_wellness_checkin(
                    session=session,
                    event=event,
                    measured_utc=measured_utc,
                    client_event_utc=client_event_utc,
                )
            elif event.event_type == "SYMPTOM_CHECK_IN":
                created_entity_id = await SyncService._ingest_symptom_checkin(
                    session=session,
                    event=event,
                    measured_utc=measured_utc,
                    client_event_utc=client_event_utc,
                )
            else:
                return SyncEventResult(
                    client_event_id=event.client_event_id,
                    status="rejected",
                    error_code="unsupported_event_type",
                    message=f"Event type '{event.event_type}' is unsupported.",
                )
        except AppException as exc:
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="rejected",
                error_code=exc.code,
                message=exc.message,
            )
        except Exception as exc:
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="rejected",
                error_code="malformed_payload",
                message=str(exc),
            )

        # 7. Record sync event for idempotency
        sync_record = SyncEventRecord(
            client_event_id=event.client_event_id,
            crew_member_id=event.crew_member_id,
            event_type=event.event_type,
            schema_version=event.schema_version,
            client_event_at=client_event_utc,
            measured_at=measured_utc,
            server_received_at=server_received_at,
            payload_hash=payload_hash,
            sync_status="accepted",
            entity_id=created_entity_id,
        )
        try:
            session.add(sync_record)
            await session.flush()
        except IntegrityError:
            # Concurrent race condition: Another thread/request committed this event_id
            existing = await session.scalar(existing_stmt)
            if existing is not None and existing.payload_hash == payload_hash:
                return SyncEventResult(
                    client_event_id=event.client_event_id,
                    status="duplicate",
                    entity_id=existing.entity_id,
                    message="Event previously received and processed concurrently.",
                )
            return SyncEventResult(
                client_event_id=event.client_event_id,
                status="conflict",
                error_code="sync_payload_conflict",
                message="Event UUID was previously submitted with a conflicting payload.",
            )

        return SyncEventResult(
            client_event_id=event.client_event_id,
            status="accepted",
            entity_id=created_entity_id,
            message="Event successfully ingested.",
        )

    @staticmethod
    async def _ingest_measurement(
        session: Any,
        event: SyncEventItem,
        measured_utc: datetime,
        client_event_utc: datetime,
    ) -> uuid.UUID:
        """Validates telemetry spec and creates HealthMeasurement entity."""
        m_type = event.payload.get("measurement_type")
        if not m_type or not isinstance(m_type, str):
            raise AppException(
                message="Missing or invalid 'measurement_type' in payload.",
                code="missing_field",
                status_code=400,
            )

        defn = measurement_registry.get(m_type)
        if defn is None:
            raise AppException(
                message=f"Measurement type '{m_type}' is not registered in telemetry registry.",
                code="unsupported_measurement_type",
                status_code=400,
            )

        val = event.payload.get("value")
        if val is None or not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            raise AppException(
                message="Measurement 'value' must be a finite numeric float.",
                code="invalid_numeric_value",
                status_code=400,
            )

        unit = event.payload.get("unit")
        if not unit or not isinstance(unit, str):
            raise AppException(
                message="Missing or invalid 'unit' in measurement payload.",
                code="missing_unit",
                status_code=400,
            )

        if unit not in defn.allowed_units:
            raise AppException(
                message=f"Unit '{unit}' is incompatible with {m_type}. Supported units: {list(defn.allowed_units)}",
                code="incompatible_unit",
                status_code=400,
            )

        try:
            (
                eff_numeric,
                eff_structured,
                eff_unit,
                conv_audit,
            ) = measurement_registry.validate_and_convert(
                measurement_type=m_type,
                value_numeric=float(val),
                value_structured=event.payload.get("value_structured"),
                unit=unit,
            )
        except MeasurementValidationError as err:
            raise AppException(
                message=str(err),
                code="invalid_numeric_value",
                status_code=400,
            )

        measurement = HealthMeasurement(
            crew_member_id=event.crew_member_id,
            measurement_type=m_type,
            value_numeric=eff_numeric,
            unit=eff_unit,
            measured_at=measured_utc,
            recorded_at=client_event_utc,
            input_method=event.source.get("input_method", "WEARABLE_SENSOR"),
            provenance={
                **event.source,
                "sync_client_event_id": str(event.client_event_id),
                "original_value": val,
                "original_unit": unit,
            },
            quality_status=event.source.get("quality_status", "VERIFIED"),
            context_metadata=event.payload.get("context_metadata"),
        )
        session.add(measurement)
        await session.flush()
        return measurement.id

    @staticmethod
    async def _ingest_wellness_checkin(
        session: Any,
        event: SyncEventItem,
        measured_utc: datetime,
        client_event_utc: datetime,
    ) -> uuid.UUID:
        """Validates wellness self-report ranges and creates WellnessCheckIn entity."""
        payload = event.payload
        required_fields = ["sleep_duration_hours", "sleep_quality", "mood", "stress", "fatigue"]
        for f in required_fields:
            if f not in payload:
                raise AppException(
                    message=f"Missing required wellness field '{f}'.",
                    code="missing_field",
                    status_code=400,
                )

        try:
            sleep_hours = float(payload["sleep_duration_hours"])
            sleep_q = int(payload["sleep_quality"])
            mood = int(payload["mood"])
            stress = int(payload["stress"])
            fatigue = int(payload["fatigue"])
        except (ValueError, TypeError):
            raise AppException(
                message="Wellness ratings must be integers and sleep duration must be a number.",
                code="invalid_field_type",
                status_code=400,
            )

        if not (0.0 <= sleep_hours <= 24.0):
            raise AppException(
                message=f"sleep_duration_hours ({sleep_hours}) must be between 0.0 and 24.0.",
                code="out_of_range",
                status_code=400,
            )

        for name, val in [("sleep_quality", sleep_q), ("mood", mood), ("stress", stress), ("fatigue", fatigue)]:
            if not (1 <= val <= 5):
                raise AppException(
                    message=f"Wellness rating '{name}' ({val}) must be between 1 and 5.",
                    code="out_of_range",
                    status_code=400,
                )

        checkin = WellnessCheckIn(
            crew_member_id=event.crew_member_id,
            sleep_duration_hours=sleep_hours,
            sleep_quality=sleep_q,
            mood=mood,
            stress=stress,
            fatigue=fatigue,
            measured_at=measured_utc,
            recorded_at=client_event_utc,
            provenance={
                **event.source,
                "sync_client_event_id": str(event.client_event_id),
            },
        )
        session.add(checkin)
        await session.flush()
        return checkin.id

    @staticmethod
    async def _ingest_symptom_checkin(
        session: Any,
        event: SyncEventItem,
        measured_utc: datetime,
        client_event_utc: datetime,
    ) -> uuid.UUID:
        """Validates structured symptom fields and creates SymptomCheckIn entity."""
        payload = event.payload
        if "symptom_identifiers" not in payload or not isinstance(payload["symptom_identifiers"], list):
            raise AppException(
                message="'symptom_identifiers' must be a list of string identifiers.",
                code="invalid_symptom_identifiers",
                status_code=400,
            )
        if not payload["symptom_identifiers"]:
            raise AppException(
                message="'symptom_identifiers' list cannot be empty.",
                code="empty_symptom_identifiers",
                status_code=400,
            )

        severity = str(payload.get("severity", "")).upper()
        if severity not in ("MILD", "MODERATE", "SEVERE"):
            raise AppException(
                message=f"Symptom severity '{severity}' must be MILD, MODERATE, or SEVERE.",
                code="invalid_severity",
                status_code=400,
            )

        onset_str = payload.get("onset_time")
        if onset_str:
            try:
                onset_time = datetime.fromisoformat(onset_str)
                if onset_time.tzinfo is None:
                    onset_time = onset_time.replace(tzinfo=timezone.utc)
            except Exception:
                onset_time = measured_utc
        else:
            onset_time = measured_utc

        symptom = SymptomCheckIn(
            crew_member_id=event.crew_member_id,
            symptom_identifiers=payload["symptom_identifiers"],
            severity=severity,
            onset_time=onset_time,
            recorded_at=client_event_utc,
            controlled_notes=payload.get("notes"),
            provenance={
                **event.source,
                "sync_client_event_id": str(event.client_event_id),
            },
        )
        session.add(symptom)
        await session.flush()
        return symptom.id

    @staticmethod
    async def get_sync_record(
        session: Any,
        client_event_id: uuid.UUID,
        actor_identity: AuthenticatedIdentity,
    ) -> SyncEventRecord | None:
        """Retrieves sync record for status polling."""
        stmt = select(SyncEventRecord).where(SyncEventRecord.client_event_id == client_event_id)
        record = await session.scalar(stmt)
        if record is None:
            return None

        # Check access
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(record.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="You do not have permission to view this sync event.",
                    code="forbidden",
                    status_code=403,
                )
        return record
