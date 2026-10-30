import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import InvalidValueError, ResourceNotFoundError
from src.models.wellness import SymptomCheckIn, WellnessCheckIn
from src.modules.audit.service import record_audit_event
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService, AuthorizationError
from src.schemas.wellness import CheckInCreateRequest, CheckInResponse


class CheckInService:
    """Service handling crew wellness and symptom self-report check-ins."""

    @staticmethod
    def _map_wellness_to_response(w: WellnessCheckIn) -> CheckInResponse:
        return CheckInResponse(
            id=w.id,
            check_in_type="WELLNESS",
            crew_member_id=w.crew_member_id,
            recorded_at=w.recorded_at,
            timestamp=w.measured_at,
            details={
                "sleep_duration_hours": w.sleep_duration_hours,
                "sleep_quality": w.sleep_quality,
                "mood": w.mood,
                "stress": w.stress,
                "fatigue": w.fatigue,
            },
            provenance=w.provenance,
        )

    @staticmethod
    def _map_symptom_to_response(s: SymptomCheckIn) -> CheckInResponse:
        return CheckInResponse(
            id=s.id,
            check_in_type="SYMPTOM",
            crew_member_id=s.crew_member_id,
            recorded_at=s.recorded_at,
            timestamp=s.onset_time,
            details={
                "symptom_identifiers": s.symptom_identifiers,
                "severity": s.severity,
                "controlled_notes": s.controlled_notes,
            },
            provenance=s.provenance,
        )

    @classmethod
    async def create_check_in(
        cls,
        session: AsyncSession,
        payload: CheckInCreateRequest,
        identity: AuthenticatedIdentity,
    ) -> CheckInResponse:
        """Processes and records a subjective wellness or symptom check-in."""
        effective_crew_id: uuid.UUID
        if payload.crew_member_id is not None:
            effective_crew_id = payload.crew_member_id
        elif identity.crew_member_id:
            effective_crew_id = uuid.UUID(identity.crew_member_id)
        else:
            raise InvalidValueError("Target crew_member_id must be specified.")

        await AuthService.enforce_crew_access(
            session=session,
            identity=identity,
            target_crew_member_id=effective_crew_id,
            action="CREATE_CHECK_IN",
        )

        now_utc = datetime.now(timezone.utc)

        if payload.check_in_type == "WELLNESS":
            wellness = WellnessCheckIn(
                id=uuid.uuid4(),
                crew_member_id=effective_crew_id,
                sleep_duration_hours=float(payload.sleep_duration_hours or 0.0),
                sleep_quality=int(payload.sleep_quality or 3),
                mood=int(payload.mood or 3),
                stress=int(payload.stress or 1),
                fatigue=int(payload.fatigue or 1),
                measured_at=payload.measured_at or now_utc,
                recorded_at=now_utc,
                provenance=payload.provenance,
            )
            session.add(wellness)
            await session.flush()

            await record_audit_event(
                session=session,
                actor=identity.username,
                action="CREATE_WELLNESS_CHECK_IN",
                resource_type="wellness_checkin",
                resource_id=str(wellness.id),
                metadata={"crew_member_id": str(effective_crew_id)},
            )
            return cls._map_wellness_to_response(wellness)

        else:
            symptom = SymptomCheckIn(
                id=uuid.uuid4(),
                crew_member_id=effective_crew_id,
                symptom_identifiers=payload.symptom_identifiers or [],
                severity=payload.severity or "MILD",
                onset_time=payload.onset_time or now_utc,
                recorded_at=now_utc,
                controlled_notes=payload.controlled_notes,
                provenance=payload.provenance,
            )
            session.add(symptom)
            await session.flush()

            await record_audit_event(
                session=session,
                actor=identity.username,
                action="CREATE_SYMPTOM_CHECK_IN",
                resource_type="symptom_checkin",
                resource_id=str(symptom.id),
                metadata={
                    "crew_member_id": str(effective_crew_id),
                    "severity": symptom.severity,
                },
            )
            return cls._map_symptom_to_response(symptom)

    @classmethod
    async def get_check_in_by_id(
        cls,
        session: AsyncSession,
        check_in_id: uuid.UUID,
        identity: AuthenticatedIdentity,
    ) -> CheckInResponse:
        """Retrieves a single check-in across wellness and symptom tables."""
        # 1. Check wellness table
        wellness_query = select(WellnessCheckIn).where(WellnessCheckIn.id == check_in_id)
        wellness = (await session.execute(wellness_query)).scalar_one_or_none()
        if wellness:
            await AuthService.enforce_crew_access(
                session=session,
                identity=identity,
                target_crew_member_id=wellness.crew_member_id,
                action="READ_WELLNESS_CHECK_IN",
            )
            return cls._map_wellness_to_response(wellness)

        # 2. Check symptom table
        symptom_query = select(SymptomCheckIn).where(SymptomCheckIn.id == check_in_id)
        symptom = (await session.execute(symptom_query)).scalar_one_or_none()
        if symptom:
            await AuthService.enforce_crew_access(
                session=session,
                identity=identity,
                target_crew_member_id=symptom.crew_member_id,
                action="READ_SYMPTOM_CHECK_IN",
            )
            return cls._map_symptom_to_response(symptom)

        raise ResourceNotFoundError("check_in", check_in_id)

    @classmethod
    async def list_check_ins(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        crew_id: uuid.UUID | None = None,
        check_in_type: Literal["WELLNESS", "SYMPTOM", "ALL"] = "ALL",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CheckInResponse], int]:
        """Lists check-ins with deterministic ordering and object-level scoping."""
        allowed_crew_ids: list[uuid.UUID] = []
        if identity.role == "CREW_MEMBER":
            user_crew = uuid.UUID(identity.crew_member_id) if identity.crew_member_id else None
            if not user_crew:
                raise AuthorizationError("Crew identity is not bound to a valid crew member.")
            if crew_id is not None and crew_id != user_crew:
                raise AuthorizationError("Crew members may only query their own check-ins.")
            allowed_crew_ids = [user_crew]

        elif identity.role == "FLIGHT_SURGEON":
            assigned_uuids = [uuid.UUID(cid) for cid in identity.assigned_crew_ids]
            if not assigned_uuids:
                return [], 0
            if crew_id is not None:
                if crew_id not in assigned_uuids:
                    raise AuthorizationError("Flight surgeon not assigned to requested crew member.")
                allowed_crew_ids = [crew_id]
            else:
                allowed_crew_ids = assigned_uuids

        elif identity.role == "ADMIN":
            assigned_uuids = [uuid.UUID(cid) for cid in identity.assigned_crew_ids]
            if not assigned_uuids:
                raise AuthorizationError("Admins cannot access check-in records without explicit assignment.")
            if crew_id is not None:
                if crew_id not in assigned_uuids:
                    raise AuthorizationError("Admin not assigned to requested crew member.")
                allowed_crew_ids = [crew_id]
            else:
                allowed_crew_ids = assigned_uuids

        results: list[CheckInResponse] = []

        # Query Wellness Check-ins
        if check_in_type in ("WELLNESS", "ALL"):
            wq = select(WellnessCheckIn).where(WellnessCheckIn.crew_member_id.in_(allowed_crew_ids))
            if start_time:
                wq = wq.where(WellnessCheckIn.measured_at >= start_time)
            if end_time:
                wq = wq.where(WellnessCheckIn.measured_at <= end_time)
            wellness_records = (await session.execute(wq)).scalars().all()
            results.extend([cls._map_wellness_to_response(w) for w in wellness_records])

        # Query Symptom Check-ins
        if check_in_type in ("SYMPTOM", "ALL"):
            sq = select(SymptomCheckIn).where(SymptomCheckIn.crew_member_id.in_(allowed_crew_ids))
            if start_time:
                sq = sq.where(SymptomCheckIn.onset_time >= start_time)
            if end_time:
                sq = sq.where(SymptomCheckIn.onset_time <= end_time)
            symptom_records = (await session.execute(sq)).scalars().all()
            results.extend([cls._map_symptom_to_response(s) for s in symptom_records])

        # Sort deterministically: timestamp desc, then ID desc
        results.sort(key=lambda r: (r.timestamp, str(r.id)), reverse=True)

        total = len(results)
        paged = results[offset : offset + limit]
        return paged, total

