import uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.wellness.service import CheckInService
from src.schemas.wellness import (
    CheckInCreateRequest,
    CheckInListResponse,
    CheckInResponse,
)

router = APIRouter(prefix="/check-ins", tags=["Crew Check-Ins"])


@router.post(
    "",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Crew Check-In",
    description="Submits a subjective self-report check-in (Wellness or Symptom report).",
)
async def submit_crew_check_in(
    payload: CheckInCreateRequest,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> CheckInResponse:
    check_in = await CheckInService.create_check_in(
        session=session,
        payload=payload,
        identity=identity,
    )
    await session.commit()
    return check_in


@router.get(
    "",
    response_model=CheckInListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Crew Check-Ins",
    description="Queries check-ins matching optional filters with deterministic ordering and object-level scoping.",
)
async def list_crew_check_ins(
    crew_id: uuid.UUID | None = Query(default=None, description="Optional target crew member UUID"),
    check_in_type: Literal["WELLNESS", "SYMPTOM", "ALL"] = Query(default="ALL", description="Filter by check-in type"),
    start_time: datetime | None = Query(default=None, description="Filter records timestamped on or after UTC"),
    end_time: datetime | None = Query(default=None, description="Filter records timestamped on or before UTC"),
    limit: int = Query(default=50, ge=1, le=100, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset"),
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> CheckInListResponse:
    items, total = await CheckInService.list_check_ins(
        session=session,
        identity=identity,
        crew_id=crew_id,
        check_in_type=check_in_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return CheckInListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.get(
    "/{check_in_id}",
    response_model=CheckInResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Check-In by ID",
    description="Retrieves a specific wellness or symptom check-in by ID with authorization verification.",
)
async def get_check_in_by_id(
    check_in_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> CheckInResponse:
    return await CheckInService.get_check_in_by_id(
        session=session,
        check_in_id=check_in_id,
        identity=identity,
    )

