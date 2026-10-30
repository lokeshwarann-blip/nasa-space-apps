import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    DuplicateSubmissionError,
    InvalidUnitError,
    InvalidValueError,
    ResourceNotFoundError,
    UnsupportedMeasurementTypeError,
)
from src.models.telemetry import HealthMeasurement
from src.modules.audit.service import record_audit_event
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService, AuthorizationError
from src.modules.telemetry.registry import (
    MeasurementValidationError,
    measurement_registry,
)
from src.schemas.telemetry import (
    MeasurementCreateRequest,
    MeasurementResponse,
)


class TelemetryService:
    """Service handling physiological measurement ingestion, query, and invalidation."""

    @staticmethod
    def _map_measurement_to_response(m: HealthMeasurement) -> MeasurementResponse:
        """Helper to extract preserved original values from metadata and construct clean DTO."""
        ctx = m.context_metadata or {}
        orig_val = ctx.get("original_value")
        orig_unit = ctx.get("original_unit")
        conv_audit = ctx.get("conversion_audit")

        return MeasurementResponse(
            id=m.id,
            crew_member_id=m.crew_member_id,
            measurement_type=m.measurement_type,
            value_numeric=m.value_numeric,
            value_structured=m.value_structured,
            unit=m.unit,
            measured_at=m.measured_at,
            recorded_at=m.recorded_at,
            input_method=m.input_method,
            provenance=m.provenance,
            quality_status=m.quality_status,
            context_metadata=m.context_metadata,
            original_value=orig_val,
            original_unit=orig_unit,
            conversion_audit=conv_audit,
        )

    @classmethod
    async def ingest_measurement(
        cls,
        session: AsyncSession,
        payload: MeasurementCreateRequest,
        identity: AuthenticatedIdentity,
    ) -> MeasurementResponse:
        """Ingests a verified physiological measurement record."""
        # 1. Determine effective target crew member ID
        effective_crew_id: uuid.UUID
        if payload.crew_member_id is not None:
            effective_crew_id = payload.crew_member_id
        elif identity.crew_member_id:
            effective_crew_id = uuid.UUID(identity.crew_member_id)
        else:
            raise InvalidValueError("Target crew_member_id must be specified.")

        # 2. Enforce Object-Level Authorization
        await AuthService.enforce_crew_access(
            session=session,
            identity=identity,
            target_crew_member_id=effective_crew_id,
            action="INGEST_MEASUREMENT",
        )

        # 3. Registry validation & deterministic unit conversion
        defn = measurement_registry.get(payload.measurement_type)
        if defn is None:
            raise UnsupportedMeasurementTypeError(payload.measurement_type)

        if payload.unit not in defn.allowed_units:
            raise InvalidUnitError(
                unit=payload.unit,
                measurement_type=payload.measurement_type,
                allowed_units=list(defn.allowed_units),
            )

        try:
            (
                eff_numeric,
                eff_structured,
                eff_unit,
                conv_audit,
            ) = measurement_registry.validate_and_convert(
                measurement_type=payload.measurement_type,
                value_numeric=payload.value_numeric,
                value_structured=payload.value_structured,
                unit=payload.unit,
            )
        except MeasurementValidationError as err:
            raise InvalidValueError(str(err))

        # 4. Check for duplicate submissions
        dup_query = select(HealthMeasurement.id).where(
            HealthMeasurement.crew_member_id == effective_crew_id,
            HealthMeasurement.measurement_type == payload.measurement_type,
            HealthMeasurement.measured_at == payload.measured_at,
        )
        existing_dup = (await session.execute(dup_query)).scalar_one_or_none()
        if existing_dup is not None:
            raise DuplicateSubmissionError(
                f"Duplicate measurement for crew '{effective_crew_id}', "
                f"type '{payload.measurement_type}' at timestamp '{payload.measured_at.isoformat()}' already exists."
            )

        # 5. Preserve original representation and conversion audit in context
        ctx = dict(payload.context_metadata or {})
        ctx["original_value"] = payload.value_numeric
        ctx["original_unit"] = payload.unit
        if conv_audit:
            ctx["conversion_audit"] = {
                "original_value": conv_audit.original_value,
                "original_unit": conv_audit.original_unit,
                "converted_value": conv_audit.converted_value,
                "canonical_unit": conv_audit.canonical_unit,
                "conversion_formula": conv_audit.conversion_formula,
            }

        # 6. Construct and persist entity
        measurement = HealthMeasurement(
            id=uuid.uuid4(),
            crew_member_id=effective_crew_id,
            measurement_type=payload.measurement_type,
            value_numeric=eff_numeric,
            value_structured=eff_structured,
            unit=eff_unit,
            measured_at=payload.measured_at,
            recorded_at=datetime.now(timezone.utc),
            input_method=payload.input_method,
            provenance=payload.provenance,
            quality_status="VERIFIED",
            context_metadata=ctx,
        )
        session.add(measurement)
        await session.flush()

        # 7. Audit log (sanitized, zero medical payloads)
        await record_audit_event(
            session=session,
            actor=identity.username,
            action="INGEST_MEASUREMENT",
            resource_type="health_measurement",
            resource_id=str(measurement.id),
            metadata={
                "measurement_type": measurement.measurement_type,
                "unit": measurement.unit,
                "crew_member_id": str(effective_crew_id),
            },
        )

        return cls._map_measurement_to_response(measurement)

    @classmethod
    async def get_measurement_by_id(
        cls,
        session: AsyncSession,
        measurement_id: uuid.UUID,
        identity: AuthenticatedIdentity,
    ) -> MeasurementResponse:
        """Retrieves a single measurement with object-level authorization."""
        query = select(HealthMeasurement).where(HealthMeasurement.id == measurement_id)
        result = await session.execute(query)
        measurement = result.scalar_one_or_none()

        if measurement is None:
            raise ResourceNotFoundError("health_measurement", measurement_id)

        # Enforce authorization
        await AuthService.enforce_crew_access(
            session=session,
            identity=identity,
            target_crew_member_id=measurement.crew_member_id,
            action="READ_MEASUREMENT",
        )

        return cls._map_measurement_to_response(measurement)

    @classmethod
    async def list_measurements(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        crew_id: uuid.UUID | None = None,
        measurement_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MeasurementResponse], int]:
        """Lists measurements matching filters with deterministic ordering and authorization."""
        query = select(HealthMeasurement)
        count_query = select(func.count(HealthMeasurement.id))

        # Authorization scoping
        if identity.role == "CREW_MEMBER":
            user_crew = uuid.UUID(identity.crew_member_id) if identity.crew_member_id else None
            if not user_crew:
                raise AuthorizationError("Crew identity is not bound to a valid crew member.")
            if crew_id is not None and crew_id != user_crew:
                raise AuthorizationError("Crew members may only query their own measurements.")
            query = query.where(HealthMeasurement.crew_member_id == user_crew)
            count_query = count_query.where(HealthMeasurement.crew_member_id == user_crew)

        elif identity.role == "FLIGHT_SURGEON":
            assigned_uuids = [uuid.UUID(cid) for cid in identity.assigned_crew_ids]
            if not assigned_uuids:
                return [], 0
            if crew_id is not None:
                if crew_id not in assigned_uuids:
                    raise AuthorizationError("Flight surgeon not assigned to requested crew member.")
                query = query.where(HealthMeasurement.crew_member_id == crew_id)
                count_query = count_query.where(HealthMeasurement.crew_member_id == crew_id)
            else:
                query = query.where(HealthMeasurement.crew_member_id.in_(assigned_uuids))
                count_query = count_query.where(HealthMeasurement.crew_member_id.in_(assigned_uuids))

        elif identity.role == "ADMIN":
            assigned_uuids = [uuid.UUID(cid) for cid in identity.assigned_crew_ids]
            if not assigned_uuids:
                raise AuthorizationError("Admins cannot access clinical records without explicit assignment.")
            if crew_id is not None:
                if crew_id not in assigned_uuids:
                    raise AuthorizationError("Admin not assigned to requested crew member.")
                query = query.where(HealthMeasurement.crew_member_id == crew_id)
                count_query = count_query.where(HealthMeasurement.crew_member_id == crew_id)
            else:
                query = query.where(HealthMeasurement.crew_member_id.in_(assigned_uuids))
                count_query = count_query.where(HealthMeasurement.crew_member_id.in_(assigned_uuids))

        # Filter: type
        if measurement_type:
            query = query.where(HealthMeasurement.measurement_type == measurement_type)
            count_query = count_query.where(HealthMeasurement.measurement_type == measurement_type)

        # Filter: time range
        if start_time:
            query = query.where(HealthMeasurement.measured_at >= start_time)
            count_query = count_query.where(HealthMeasurement.measured_at >= start_time)
        if end_time:
            query = query.where(HealthMeasurement.measured_at <= end_time)
            count_query = count_query.where(HealthMeasurement.measured_at <= end_time)

        # Execute total count
        total = (await session.execute(count_query)).scalar() or 0

        # Deterministic ordering: latest measured_at first, then ID
        query = query.order_by(HealthMeasurement.measured_at.desc(), HealthMeasurement.id.desc())
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        measurements = result.scalars().all()

        items = [cls._map_measurement_to_response(m) for m in measurements]
        return items, total

    @classmethod
    async def invalidate_measurement(
        cls,
        session: AsyncSession,
        measurement_id: uuid.UUID,
        reason: str,
        identity: AuthenticatedIdentity,
    ) -> MeasurementResponse:
        """Marks a measurement as invalidated with full audit trail without deleting history."""
        query = select(HealthMeasurement).where(HealthMeasurement.id == measurement_id)
        measurement = (await session.execute(query)).scalar_one_or_none()

        if measurement is None:
            raise ResourceNotFoundError("health_measurement", measurement_id)

        # Authorization check
        await AuthService.enforce_crew_access(
            session=session,
            identity=identity,
            target_crew_member_id=measurement.crew_member_id,
            action="INVALIDATE_MEASUREMENT",
        )

        ctx = dict(measurement.context_metadata or {})
        ctx["invalidated"] = True
        ctx["invalidation_reason"] = reason
        ctx["invalidated_by"] = identity.username
        ctx["invalidated_at"] = datetime.now(timezone.utc).isoformat()

        measurement.quality_status = "INVALIDATED"
        measurement.context_metadata = ctx
        await session.flush()

        await record_audit_event(
            session=session,
            actor=identity.username,
            action="INVALIDATE_MEASUREMENT",
            resource_type="health_measurement",
            resource_id=str(measurement.id),
            metadata={
                "reason": reason,
                "crew_member_id": str(measurement.crew_member_id),
            },
        )

        return cls._map_measurement_to_response(measurement)

