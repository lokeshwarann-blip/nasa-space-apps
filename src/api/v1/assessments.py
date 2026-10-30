import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.clinical.schemas import (
    AssessmentListResponse,
    AssessmentRequest,
    AssessmentResponse,
)
from src.modules.clinical.service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Clinical Assessments"])


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Explainable Health Assessment",
    description=(
        "Executes a deterministic, rule-based clinical health assessment over verified historical observations. "
        "Strictly uses only approved, versioned clinical rules. Records input snapshots and reproducibility hashes. "
        "Distinguishes assessed_no_findings, partially_assessed, not_assessed, insufficient_evidence, and needs_review."
    ),
)
async def generate_health_assessment(
    payload: AssessmentRequest,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> AssessmentResponse:
    assessment = await AssessmentService.run_assessment(
        session=session,
        payload=payload,
        identity=identity,
    )
    await session.commit()
    return assessment


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Assessment by ID",
    description="Retrieves a saved explainable clinical assessment with traceable findings and input snapshot.",
)
async def get_assessment_by_id(
    assessment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> AssessmentResponse:
    return await AssessmentService.get_assessment_by_id(
        session=session,
        assessment_id=assessment_id,
        identity=identity,
    )


@router.get(
    "",
    response_model=AssessmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Historical Assessments",
    description="Retrieves chronological assessment history for authorized crew members.",
)
async def list_assessments(
    crew_id: uuid.UUID | None = Query(default=None, description="Optional target crew member UUID"),
    limit: int = Query(default=50, ge=1, le=100, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> AssessmentListResponse:
    items, total = await AssessmentService.list_assessments(
        session=session,
        identity=identity,
        crew_id=crew_id,
        limit=limit,
        offset=offset,
    )
    return AssessmentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )
