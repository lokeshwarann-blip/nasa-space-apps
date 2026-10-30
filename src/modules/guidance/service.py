import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from src.models.clinical import GuidanceDocument, GuidanceReviewRecord, GuidanceSource
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.guidance.schemas import (
    VALID_STATUS_TRANSITIONS,
    GuidanceDocumentCreate,
    GuidanceDocumentListResponse,
    GuidanceDocumentResponse,
    GuidanceReviewCreate,
    GuidanceReviewRecordResponse,
    GuidanceSourceCreate,
    GuidanceSourceListResponse,
    GuidanceSourceResponse,
    GuidanceSupersedeRequest,
)


class GuidanceService:
    """Service handling authoritative guidance ingestion, query filtering, and auditable approval workflows."""

    @staticmethod
    async def create_source(
        session: Any,
        source_in: GuidanceSourceCreate,
        actor_identity: AuthenticatedIdentity,
    ) -> GuidanceSourceResponse:
        """Registers a new authoritative reference source (e.g. NASA-STD-3001)."""
        existing_stmt = select(GuidanceSource).where(
            GuidanceSource.source_identifier == source_in.source_identifier
        )
        existing = await session.scalar(existing_stmt)
        if existing is not None:
            raise AppException(
                message=f"Guidance source with identifier '{source_in.source_identifier}' already exists.",
                code="conflict",
                status_code=409,
            )

        source = GuidanceSource(
            source_identifier=source_in.source_identifier,
            title=source_in.title,
            publisher=source_in.publisher,
            document_url=source_in.document_url,
            version=source_in.version,
            review_state=source_in.review_state,
            approval_status=source_in.approval_status,
            publication_date=source_in.publication_date,
            access_date=source_in.access_date or datetime.now(timezone.utc),
            citation_reference=source_in.citation_reference,
            summary=source_in.summary,
            health_indicator=source_in.health_indicator,
            spaceflight_hazard=source_in.spaceflight_hazard,
            mission_context=source_in.mission_context,
            target_population=source_in.target_population,
            evidence_limitations=source_in.evidence_limitations,
            intended_use=source_in.intended_use,
            next_review_date=source_in.next_review_date,
            effective_from=source_in.effective_from,
            effective_to=source_in.effective_to,
            reviewer_metadata={
                "created_by_user": actor_identity.user_id,
                "created_by_role": actor_identity.role,
                **(source_in.reviewer_metadata or {}),
            },
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)
        return GuidanceSourceResponse.model_validate(source)

    @staticmethod
    async def list_sources(
        session: Any,
        publisher: str | None = None,
        approval_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity | None = None,
    ) -> GuidanceSourceListResponse:
        """Retrieves registered guidance sources with optional filtering and role-based metadata redaction."""
        stmt = select(GuidanceSource)
        count_stmt = select(func.count(GuidanceSource.id))

        if publisher:
            stmt = stmt.where(GuidanceSource.publisher.ilike(f"%{publisher}%"))
            count_stmt = count_stmt.where(GuidanceSource.publisher.ilike(f"%{publisher}%"))

        if approval_status:
            stmt = stmt.where(GuidanceSource.approval_status == approval_status.lower())
            count_stmt = count_stmt.where(GuidanceSource.approval_status == approval_status.lower())

        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(GuidanceSource.source_identifier.asc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        sources = result.scalars().all()

        is_crew = identity is not None and identity.role == "CREW_MEMBER"
        items: list[GuidanceSourceResponse] = []
        for src in sources:
            src_dto = GuidanceSourceResponse.model_validate(src)
            if is_crew:
                # Redact administrative reviewer metadata for crew members
                src_dto.reviewer_metadata = None
            items.append(src_dto)

        return GuidanceSourceListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_source_by_id(
        session: Any,
        source_id: uuid.UUID,
        identity: AuthenticatedIdentity | None = None,
    ) -> GuidanceSourceResponse:
        """Retrieves a single authoritative guidance source by ID."""
        stmt = select(GuidanceSource).where(GuidanceSource.id == source_id)
        source = await session.scalar(stmt)
        if source is None:
            raise AppException(
                message=f"Guidance source '{source_id}' not found.",
                code="not_found",
                status_code=404,
            )

        src_dto = GuidanceSourceResponse.model_validate(source)
        if identity is not None and identity.role == "CREW_MEMBER":
            src_dto.reviewer_metadata = None
        return src_dto

    @staticmethod
    async def create_guidance_document(
        session: Any,
        doc_in: GuidanceDocumentCreate,
        actor_identity: AuthenticatedIdentity,
    ) -> GuidanceDocumentResponse:
        """Ingests a new guidance document (begins in draft status)."""
        existing_stmt = select(GuidanceDocument).where(
            GuidanceDocument.document_identifier == doc_in.document_identifier
        )
        existing = await session.scalar(existing_stmt)
        if existing is not None:
            raise AppException(
                message=f"Guidance document with identifier '{doc_in.document_identifier}' already exists.",
                code="conflict",
                status_code=409,
            )

        if doc_in.guidance_source_id is not None:
            source_stmt = select(GuidanceSource).where(GuidanceSource.id == doc_in.guidance_source_id)
            source = await session.scalar(source_stmt)
            if source is None:
                raise AppException(
                    message=f"Referenced guidance source '{doc_in.guidance_source_id}' does not exist.",
                    code="not_found",
                    status_code=404,
                )

        doc = GuidanceDocument(
            document_identifier=doc_in.document_identifier,
            guidance_source_id=doc_in.guidance_source_id,
            title=doc_in.title,
            guidance_type=doc_in.guidance_type,
            summary=doc_in.summary,
            content=doc_in.content,
            citation_reference=doc_in.citation_reference,
            topic=doc_in.topic,
            health_indicator=doc_in.health_indicator,
            spaceflight_hazard=doc_in.spaceflight_hazard,
            mission_context=doc_in.mission_context,
            target_population=doc_in.target_population,
            evidence_limitations=doc_in.evidence_limitations,
            intended_use=doc_in.intended_use,
            approval_status=doc_in.approval_status,
            version=doc_in.version,
            effective_from=doc_in.effective_from,
            effective_to=doc_in.effective_to,
            next_review_date=doc_in.next_review_date,
            review_metadata={
                "created_by_user": actor_identity.user_id,
                "created_by_role": actor_identity.role,
                "initial_status": doc_in.approval_status,
            },
        )
        session.add(doc)
        await session.flush()

        # Record initial ingestion in audit review log
        initial_review = GuidanceReviewRecord(
            guidance_id=doc.id,
            reviewer_id=actor_identity.user_id,
            reviewer_role=actor_identity.role,
            previous_status="none",
            new_status=doc_in.approval_status,
            decision_rationale="Initial guidance document submission",
            reviewed_at=datetime.now(timezone.utc),
        )
        session.add(initial_review)

        await session.commit()
        return await GuidanceService.get_guidance_document(
            session=session, guidance_id=doc.id, identity=actor_identity
        )

    @staticmethod
    async def list_guidance_documents(
        session: Any,
        topic: str | None = None,
        indicator: str | None = None,
        hazard: str | None = None,
        mission_context: str | None = None,
        source: str | None = None,
        guidance_type: str | None = None,
        approval_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity | None = None,
    ) -> GuidanceDocumentListResponse:
        """Retrieves guidance documents with multi-parameter filtering, access control, and metadata redaction."""
        is_crew = identity is not None and identity.role == "CREW_MEMBER"

        if is_crew:
            # Crew members cannot request unapproved/draft/retired content
            if approval_status and approval_status.lower() != "approved":
                raise AppException(
                    message="Crew members are only authorized to view approved guidance.",
                    code="forbidden",
                    status_code=403,
                )
            effective_status = "approved"
        else:
            effective_status = approval_status.lower() if approval_status else None

        stmt = (
            select(GuidanceDocument)
            .options(
                selectinload(GuidanceDocument.guidance_source),
                selectinload(GuidanceDocument.review_records),
            )
        )
        count_stmt = select(func.count(GuidanceDocument.id))

        if effective_status:
            stmt = stmt.where(GuidanceDocument.approval_status == effective_status)
            count_stmt = count_stmt.where(GuidanceDocument.approval_status == effective_status)

        if topic:
            stmt = stmt.where(GuidanceDocument.topic.ilike(f"%{topic}%"))
            count_stmt = count_stmt.where(GuidanceDocument.topic.ilike(f"%{topic}%"))

        if indicator:
            stmt = stmt.where(GuidanceDocument.health_indicator == indicator.lower())
            count_stmt = count_stmt.where(GuidanceDocument.health_indicator == indicator.lower())

        if hazard:
            stmt = stmt.where(GuidanceDocument.spaceflight_hazard == hazard.upper())
            count_stmt = count_stmt.where(GuidanceDocument.spaceflight_hazard == hazard.upper())

        if mission_context:
            stmt = stmt.where(GuidanceDocument.mission_context == mission_context.upper())
            count_stmt = count_stmt.where(GuidanceDocument.mission_context == mission_context.upper())

        if guidance_type:
            stmt = stmt.where(GuidanceDocument.guidance_type == guidance_type.upper())
            count_stmt = count_stmt.where(GuidanceDocument.guidance_type == guidance_type.upper())

        if source:
            # Match by source_id UUID or source_identifier
            try:
                source_uuid = uuid.UUID(source)
                stmt = stmt.where(GuidanceDocument.guidance_source_id == source_uuid)
                count_stmt = count_stmt.where(GuidanceDocument.guidance_source_id == source_uuid)
            except ValueError:
                stmt = stmt.join(GuidanceSource).where(GuidanceSource.source_identifier == source)
                count_stmt = count_stmt.join(GuidanceSource).where(GuidanceSource.source_identifier == source)

        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(GuidanceDocument.created_at.desc(), GuidanceDocument.document_identifier.asc())
        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        docs = result.scalars().all()

        items: list[GuidanceDocumentResponse] = []
        for doc in docs:
            dto = GuidanceService._serialize_document(doc, is_crew=is_crew)
            items.append(dto)

        return GuidanceDocumentListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_guidance_document(
        session: Any,
        guidance_id: uuid.UUID,
        identity: AuthenticatedIdentity | None = None,
    ) -> GuidanceDocumentResponse:
        """Retrieves a single guidance document with complete source links and review audit history."""
        stmt = (
            select(GuidanceDocument)
            .where(GuidanceDocument.id == guidance_id)
            .options(
                selectinload(GuidanceDocument.guidance_source),
                selectinload(GuidanceDocument.review_records),
            )
        )
        doc = await session.scalar(stmt)
        if doc is None:
            raise AppException(
                message=f"Guidance document '{guidance_id}' not found.",
                code="not_found",
                status_code=404,
            )

        is_crew = identity is not None and identity.role == "CREW_MEMBER"
        if is_crew and doc.approval_status != "approved":
            raise AppException(
                message=f"Guidance document '{guidance_id}' not found.",
                code="not_found",
                status_code=404,
            )

        return GuidanceService._serialize_document(doc, is_crew=is_crew)

    @staticmethod
    async def transition_approval_status(
        session: Any,
        guidance_id: uuid.UUID,
        review_in: GuidanceReviewCreate,
        actor_identity: AuthenticatedIdentity,
    ) -> GuidanceDocumentResponse:
        """Transitions guidance through the approval workflow with medical/administrative audit records."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can execute guidance approval transitions.",
                code="forbidden",
                status_code=403,
            )

        stmt = (
            select(GuidanceDocument)
            .where(GuidanceDocument.id == guidance_id)
            .options(
                selectinload(GuidanceDocument.guidance_source),
                selectinload(GuidanceDocument.review_records),
                selectinload(GuidanceDocument.clinical_rules),
            )
        )
        doc = await session.scalar(stmt)
        if doc is None:
            raise AppException(
                message=f"Guidance document '{guidance_id}' not found.",
                code="not_found",
                status_code=404,
            )

        current_status = doc.approval_status.lower()
        target_status = review_in.new_status.lower()

        allowed_targets = VALID_STATUS_TRANSITIONS.get(current_status, [])
        if target_status not in allowed_targets:
            raise AppException(
                message=(
                    f"Invalid approval status transition from '{current_status}' to '{target_status}'. "
                    f"Permitted transitions from '{current_status}': {allowed_targets}"
                ),
                code="invalid_transition",
                status_code=400,
            )

        prev_status = doc.approval_status
        doc.approval_status = target_status

        if review_in.effective_from is not None:
            doc.effective_from = review_in.effective_from
        if review_in.effective_to is not None:
            doc.effective_to = review_in.effective_to
        if review_in.next_review_date is not None:
            doc.next_review_date = review_in.next_review_date

        doc.review_metadata = {
            **(doc.review_metadata or {}),
            "last_reviewed_by": actor_identity.user_id,
            "last_reviewed_role": actor_identity.role,
            "last_status_change": datetime.now(timezone.utc).isoformat(),
        }

        # Auditable review record
        record = GuidanceReviewRecord(
            guidance_id=doc.id,
            reviewer_id=actor_identity.user_id,
            reviewer_role=actor_identity.role,
            previous_status=prev_status,
            new_status=target_status,
            decision_rationale=review_in.decision_rationale,
            reviewed_at=datetime.now(timezone.utc),
            metadata_snapshot=review_in.metadata_snapshot,
        )
        session.add(record)

        # Safety Guard: If guidance is rejected or retired, deactivate all associated clinical rules
        if target_status in ("retired", "rejected"):
            for rule in doc.clinical_rules:
                rule.approval_status = target_status
                rule.review_state = target_status

        await session.commit()
        return await GuidanceService.get_guidance_document(
            session=session, guidance_id=doc.id, identity=actor_identity
        )

    @staticmethod
    async def supersede_guidance(
        session: Any,
        guidance_id: uuid.UUID,
        req: GuidanceSupersedeRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> GuidanceDocumentResponse:
        """Creates a new version of guidance and automatically marks the existing version as retired."""
        if actor_identity.role not in ("FLIGHT_SURGEON", "ADMIN"):
            raise AppException(
                message="Only Flight Surgeons and Administrators can supersede guidance.",
                code="forbidden",
                status_code=403,
            )

        stmt = select(GuidanceDocument).where(GuidanceDocument.id == guidance_id)
        current = await session.scalar(stmt)
        if current is None:
            raise AppException(
                message=f"Guidance document '{guidance_id}' not found.",
                code="not_found",
                status_code=404,
            )

        # Construct new document identifier for new version
        base_id = current.document_identifier.split("-V")[0]
        new_identifier = f"{base_id}-V{req.new_version}"

        new_doc = GuidanceDocument(
            document_identifier=new_identifier,
            guidance_source_id=current.guidance_source_id,
            title=req.title or current.title,
            guidance_type=current.guidance_type,
            summary=req.summary or current.summary,
            content=req.content or current.content,
            citation_reference=req.citation_reference or current.citation_reference,
            topic=current.topic,
            health_indicator=current.health_indicator,
            spaceflight_hazard=current.spaceflight_hazard,
            mission_context=current.mission_context,
            target_population=current.target_population,
            evidence_limitations=req.evidence_limitations or current.evidence_limitations,
            intended_use=req.intended_use or current.intended_use,
            approval_status="draft",  # New version must go through approval workflow
            version=req.new_version,
            review_metadata={
                "supersedes_guidance_id": str(current.id),
                "created_by_user": actor_identity.user_id,
                "created_by_role": actor_identity.role,
            },
        )
        session.add(new_doc)
        await session.flush()

        # Mark previous document as retired and link to replacement
        prev_status = current.approval_status
        current.approval_status = "retired"
        current.superseded_by_id = new_doc.id

        supersede_record = GuidanceReviewRecord(
            guidance_id=current.id,
            reviewer_id=actor_identity.user_id,
            reviewer_role=actor_identity.role,
            previous_status=prev_status,
            new_status="retired",
            decision_rationale=f"Superseded by new version {req.new_version} ({new_doc.document_identifier}): {req.decision_rationale}",
            reviewed_at=datetime.now(timezone.utc),
        )
        session.add(supersede_record)

        new_record = GuidanceReviewRecord(
            guidance_id=new_doc.id,
            reviewer_id=actor_identity.user_id,
            reviewer_role=actor_identity.role,
            previous_status="none",
            new_status="draft",
            decision_rationale=f"Created as version {req.new_version} superseding {current.document_identifier}: {req.decision_rationale}",
            reviewed_at=datetime.now(timezone.utc),
        )
        session.add(new_record)

        await session.commit()
        return await GuidanceService.get_guidance_document(
            session=session, guidance_id=new_doc.id, identity=actor_identity
        )

    @staticmethod
    def _serialize_document(doc: GuidanceDocument, is_crew: bool) -> GuidanceDocumentResponse:
        """Converts GuidanceDocument ORM entity to DTO with metadata redaction for crew members."""
        dto = GuidanceDocumentResponse.model_validate(doc)
        if is_crew:
            # Strip administrative metadata and internal reviewer identities for crew members
            dto.review_metadata = None
            if dto.guidance_source:
                dto.guidance_source.reviewer_metadata = None
            # Redact reviewer ID in review records
            redacted_records = []
            for rec in dto.review_records:
                rec_copy = GuidanceReviewRecordResponse.model_validate(rec)
                rec_copy.reviewer_id = None
                rec_copy.metadata_snapshot = None
                redacted_records.append(rec_copy)
            dto.review_records = redacted_records
        return dto

