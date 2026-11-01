from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.models.base import AnalysisRequest, AnalysisResultDTO
from src.modules.models.service import AnalysisService

router = APIRouter(prefix="/models", tags=["Future Analytical Models"])


@router.get(
    "/providers",
    summary="List analytical model providers",
    description="Retrieves registered analytical providers, model versions, and enabled safety state.",
)
async def list_model_providers(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> Any:
    return {
        "providers": AnalysisService.list_providers(),
    }


@router.post(
    "/analyze",
    response_model=AnalysisResultDTO,
    status_code=status.HTTP_200_OK,
    summary="Execute analytical model evaluation",
    description="Applies an optional versioned analytical provider to authorized observations. Disabled by default.",
)
async def analyze_telemetry(
    request: AnalysisRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await AnalysisService.run_analysis(
        session=session,
        request=request,
        actor_identity=identity,
    )

