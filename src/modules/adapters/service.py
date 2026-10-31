import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select

from src.core.exceptions import AppException
from src.models.crew import CrewMember
from src.models.telemetry import HealthMeasurement
from src.modules.adapters.base import DevicePayloadEnvelope
from src.modules.adapters.registry import device_adapter_registry
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService
from src.modules.telemetry.registry import (
    MeasurementValidationError,
    measurement_registry,
)


class DeviceIngestionService:
    """Ingests, authenticates, and normalizes external health-device telemetry."""

    @staticmethod
    async def ingest_envelope(
        session: Any,
        envelope: DevicePayloadEnvelope,
        actor_identity: AuthenticatedIdentity,
    ) -> list[dict[str, Any]]:
        """Processes an incoming external device telemetry payload."""
        # 1. Enforce Object-Level Access Control for crew member
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(envelope.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="Crew members are forbidden from submitting telemetry for other astronauts.",
                    code="forbidden",
                    status_code=403,
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            await AuthService.enforce_crew_access(
                session=session,
                identity=actor_identity,
                target_crew_member_id=envelope.crew_member_id,
                action="INGEST_MEASUREMENT",
            )

        # 2. Check provider adapter availability
        adapter = device_adapter_registry.get(envelope.provider_id)
        if adapter is None:
            raise AppException(
                message=f"Device provider '{envelope.provider_id}' is not registered or supported.",
                code="unsupported_provider",
                status_code=400,
            )

        # 3. Validate device credentials
        if not adapter.validate_credentials(envelope.credentials):
            raise AppException(
                message=f"Authentication failed for device provider '{envelope.provider_id}'. Missing or invalid credentials.",
                code="invalid_credentials",
                status_code=401,
            )

        # 4. Verify subject crew member exists in database
        crew_stmt = select(CrewMember).where(CrewMember.id == envelope.crew_member_id)
        crew = await session.scalar(crew_stmt)
        if crew is None:
            raise AppException(
                message=f"Crew member '{envelope.crew_member_id}' not found.",
                code="not_found",
                status_code=404,
            )

        # 5. Deduplication check: verify event_id has not already been ingested for this device
        existing_stmt = select(HealthMeasurement).where(
            HealthMeasurement.crew_member_id == envelope.crew_member_id,
            HealthMeasurement.provenance["device_event_id"].as_string() == envelope.event_id,
        )
        existing = await session.scalar(existing_stmt)
        if existing is not None:
            # Idempotently return existing record details without inserting duplicate
            return [{
                "id": str(existing.id),
                "measurement_type": existing.measurement_type,
                "value_numeric": existing.value_numeric,
                "unit": existing.unit,
                "measured_at": existing.measured_at.isoformat(),
                "status": "duplicate",
            }]

        # 6. Parse and validate device payload via provider adapter
        try:
            canonical_items = adapter.parse_and_validate(envelope)
        except Exception as exc:
            raise AppException(
                message=f"Adapter payload parsing error for '{envelope.provider_id}': {str(exc)}",
                code="adapter_parse_error",
                status_code=400,
            )

        if not canonical_items:
            raise AppException(
                message=f"Device payload from '{envelope.provider_id}' contained no valid observations.",
                code="empty_device_payload",
                status_code=400,
            )

        now = datetime.now(timezone.utc)
        created_records: list[dict[str, Any]] = []

        # 7. Normalize, convert, and persist each canonical observation
        for item in canonical_items:
            defn = measurement_registry.get(item.measurement_type)
            if defn is None:
                raise AppException(
                    message=f"Measurement type '{item.measurement_type}' is not registered in telemetry registry.",
                    code="unsupported_measurement_type",
                    status_code=400,
                )

            if item.unit not in defn.allowed_units:
                raise AppException(
                    message=f"Unit '{item.unit}' is not supported for '{item.measurement_type}'. Allowed: {list(defn.allowed_units)}",
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
                    measurement_type=item.measurement_type,
                    value_numeric=item.value_numeric,
                    value_structured=None,
                    unit=item.unit,
                )
            except MeasurementValidationError as err:
                raise AppException(
                    message=str(err),
                    code="invalid_numeric_value",
                    status_code=400,
                )

            # Sanitize provenance: strip credentials and vendor authorization tokens
            sanitized_provenance = {
                "provider_id": envelope.provider_id,
                "device_id": envelope.device_id,
                "device_event_id": envelope.event_id,
                "adapter_version": adapter.version,
                "transmitted_at": envelope.transmitted_at.isoformat(),
                "original_value": item.value_numeric,
                "original_unit": item.unit,
            }

            measurement = HealthMeasurement(
                crew_member_id=envelope.crew_member_id,
                measurement_type=item.measurement_type,
                value_numeric=eff_numeric,
                unit=eff_unit,
                measured_at=item.measured_at,
                recorded_at=now,
                input_method="CLINICAL_DEVICE",
                provenance=sanitized_provenance,
                quality_status=item.quality_status,
                context_metadata=item.context_metadata,
            )
            session.add(measurement)
            await session.flush()

            created_records.append({
                "id": str(measurement.id),
                "measurement_type": measurement.measurement_type,
                "value_numeric": measurement.value_numeric,
                "unit": measurement.unit,
                "measured_at": measurement.measured_at.isoformat(),
                "status": "ingested",
            })

        await session.commit()
        return created_records

