import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.database import check_db_connection
from src.schemas.health import LivenessResponse, ReadinessResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Liveness Probe",
    description="Returns 200 if the FastAPI application process is up and running.",
)
async def check_liveness() -> LivenessResponse:
    """Liveness probe to confirm application event loop is healthy."""
    return LivenessResponse(status="live")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_200_OK: {"model": ReadinessResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse},
    },
    summary="Dependency Readiness Probe",
    description=(
        "Verifies that required backing dependencies (PostgreSQL database) are reachable. "
        "Returns 503 if any required dependency fails."
    ),
)
async def check_readiness():
    """Readiness probe checking database connectivity without false positives."""
    settings = get_settings()
    is_db_connected = await check_db_connection()

    if is_db_connected:
        return ReadinessResponse(
            status="ready",
            database="connected",
            version=settings.VERSION,
        )

    # If the database cannot be reached, we MUST return 503 Service Unavailable
    logger.warning("Readiness check failed: Database connection unreachable.")
    unhealthy_payload = ReadinessResponse(
        status="unhealthy",
        database="disconnected",
        version=settings.VERSION,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=unhealthy_payload.model_dump(mode="json"),
    )

