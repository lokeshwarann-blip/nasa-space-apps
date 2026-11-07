import uuid
from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity, require_roles
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.guidance.schemas import (
    GuidanceDocumentCreate,
    GuidanceDocumentListResponse,
    GuidanceDocumentResponse,
    GuidanceReviewCreate,
    GuidanceSourceCreate,
    GuidanceSourceListResponse,
    GuidanceSourceResponse,
    GuidanceSupersedeRequest,
)
from src.modules.guidance.service import GuidanceService

router = APIRouter(prefix="/guidance", tags=["Evidence & Guidance Registry"])


# ============================================================================
# Guidance Sources Endpoints (Registered before dynamic /{guidance_id} route)
# ============================================================================

@router.get(
    "/sources",
    response_model=GuidanceSourceListResponse,
    summary="List authoritative guidance sources",
    description="Retrieves registered standards (e.g. NASA-STD-3001). Redacts administrative reviewer metadata for crew members.",
)
async def list_sources(
    publisher: str | None = Query(None, description="Filter by publishing authority"),
    approval_status: str | None = Query(None, description="Filter by approval status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.list_sources(
        session=session,
        publisher=publisher,
        approval_status=approval_status,
        limit=limit,
        offset=offset,
        identity=identity,
    )


@router.post(
    "/sources",
    response_model=GuidanceSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new authoritative guidance source",
    description="Registers an official source document (e.g. NASA-STD-3001, HRP). Restricted to Flight Surgeons and Administrators.",
)
async def create_source(
    source_in: GuidanceSourceCreate,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.create_source(
        session=session,
        source_in=source_in,
        actor_identity=identity,
    )


@router.get(
    "/sources/{source_id}",
    response_model=GuidanceSourceResponse,
    summary="Get guidance source by ID",
    description="Retrieves a specific guidance source standard by unique UUID.",
)
async def get_source(
    source_id: uuid.UUID,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.get_source_by_id(
        session=session,
        source_id=source_id,
        identity=identity,
    )


# ============================================================================
# Guidance Documents Endpoints
# ============================================================================

@router.get(
    "",
    response_model=GuidanceDocumentListResponse,
    summary="List guidance documents",
    description="Query versioned guidance records separating educational material, operational instructions, and clinical rules.",
)
async def list_guidance(
    topic: str | None = Query(None, description="Filter by topic (e.g. Cardiovascular, Fatigue)"),
    indicator: str | None = Query(None, description="Filter by biomarker / indicator (e.g. heart_rate)"),
    hazard: str | None = Query(None, description="Filter by spaceflight hazard (e.g. MICROGRAVITY, RADIATION)"),
    mission_context: str | None = Query(None, description="Filter by mission context (e.g. TRANSIT, LEO, EVA)"),
    source: str | None = Query(None, description="Filter by source identifier or source UUID"),
    guidance_type: str | None = Query(None, description="EDUCATIONAL, OPERATIONAL_INSTRUCTION, or CLINICAL_RULE"),
    approval_status: str | None = Query(None, description="draft, under_review, approved, rejected, retired"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.list_guidance_documents(
        session=session,
        topic=topic,
        indicator=indicator,
        hazard=hazard,
        mission_context=mission_context,
        source=source,
        guidance_type=guidance_type,
        approval_status=approval_status,
        limit=limit,
        offset=offset,
        identity=identity,
    )


@router.post(
    "",
    response_model=GuidanceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest new guidance document",
    description="Ingests a new guidance document into the registry in draft status. Restricted to Flight Surgeons and Administrators.",
)
async def create_guidance(
    doc_in: GuidanceDocumentCreate,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.create_guidance_document(
        session=session,
        doc_in=doc_in,
        actor_identity=identity,
    )


@router.get(
    "/{guidance_id}",
    response_model=GuidanceDocumentResponse,
    summary="Get guidance document by ID",
    description="Retrieves a specific guidance document by ID with complete source links and audit review records.",
)
async def get_guidance(
    guidance_id: uuid.UUID,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.get_guidance_document(
        session=session,
        guidance_id=guidance_id,
        identity=identity,
    )


@router.post(
    "/{guidance_id}/reviews",
    response_model=GuidanceDocumentResponse,
    summary="Transition guidance approval status",
    description="Executes a medical/administrative approval workflow transition (e.g. draft -> under_review -> approved). Restricted to Flight Surgeons and Admins.",
)
async def review_guidance(
    guidance_id: uuid.UUID,
    review_in: GuidanceReviewCreate,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.transition_approval_status(
        session=session,
        guidance_id=guidance_id,
        review_in=review_in,
        actor_identity=identity,
    )


@router.post(
    "/{guidance_id}/supersede",
    response_model=GuidanceDocumentResponse,
    summary="Supersede guidance with a new version",
    description="Creates a new version of the guidance and marks the existing version as retired. Restricted to Flight Surgeons and Admins.",
)
async def supersede_guidance(
    guidance_id: uuid.UUID,
    req: GuidanceSupersedeRequest,
    identity: AuthenticatedIdentity = Depends(require_roles("FLIGHT_SURGEON", "ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await GuidanceService.supersede_guidance(
        session=session,
        guidance_id=guidance_id,
        req=req,
        actor_identity=identity,
    )

