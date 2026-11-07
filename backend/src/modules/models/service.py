import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import select

from src.core.exceptions import AppException
from src.models.telemetry import HealthMeasurement
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.service import AuthService
from src.modules.models.base import (
    MANDATORY_MODEL_LIMITATIONS,
    AnalysisProviderInterface,
    AnalysisRequest,
    AnalysisResultDTO,
)


class AnalysisService:
    """Service managing optional, versioned analytical models and safety gating."""

    _providers: dict[str, AnalysisProviderInterface] = {}

    @classmethod
    def register_provider(cls, provider: AnalysisProviderInterface) -> None:
        """Registers an analytical model provider."""
        cls._providers[provider.provider_id.upper()] = provider

    @classmethod
    def unregister_provider(cls, provider_id: str) -> None:
        """Removes a model provider."""
        cls._providers.pop(provider_id.upper(), None)

    @classmethod
    def clear(cls) -> None:
        """Clears all registered model providers (test isolation)."""
        cls._providers.clear()

    @classmethod
    def list_providers(cls) -> list[dict[str, Any]]:
        """Lists registered analytical providers and enabled status."""
        return [
            {
                "provider_id": p.provider_id,
                "model_version": p.model_version,
                "is_enabled": getattr(p, "is_enabled", False),
                "capabilities": getattr(p, "capabilities", []),
            }
            for p in cls._providers.values()
        ]

    @classmethod
    async def run_analysis(
        cls,
        session: Any,
        request: AnalysisRequest,
        actor_identity: AuthenticatedIdentity,
    ) -> AnalysisResultDTO:
        """Executes an authorized analytical evaluation or safely reports unconfigured/disabled."""
        # 1. Enforce Object-Level Authorization on subject astronaut
        if actor_identity.role == "CREW_MEMBER":
            if actor_identity.crew_member_id is None or str(request.crew_member_id) != actor_identity.crew_member_id:
                raise AppException(
                    message="You do not have permission to execute analysis for another crew member.",
                    code="forbidden",
                    status_code=403,
                )
        elif actor_identity.role == "FLIGHT_SURGEON":
            await AuthService.enforce_crew_access(
                session=session,
                identity=actor_identity,
                target_crew_member_id=request.crew_member_id,
                action="ACCESS_HEALTH_RECORD",
            )

        provider = cls._providers.get(request.provider_id.upper())

        # 2. Safety Gate: Missing provider produces explicit not_configured result (NEVER fake predictions!)
        if provider is None:
            return AnalysisResultDTO(
                provider_id=request.provider_id,
                status="not_configured",
                message=f"Analysis provider '{request.provider_id}' is not configured on this deployment.",
                limitations=MANDATORY_MODEL_LIMITATIONS,
            )

        # 3. Safety Gate: Disabled provider returns explicit disabled result
        if not getattr(provider, "is_enabled", False):
            return AnalysisResultDTO(
                provider_id=request.provider_id,
                model_version=provider.model_version,
                status="disabled",
                message=f"Analysis provider '{request.provider_id}' is disabled by deployment safety policy.",
                limitations=MANDATORY_MODEL_LIMITATIONS,
            )

        # 4. Check capability support
        if request.capability not in provider.capabilities:
            raise AppException(
                message=f"Provider '{request.provider_id}' does not support requested capability '{request.capability}'. Supported: {provider.capabilities}",
                code="unsupported_capability",
                status_code=400,
            )

        # 5. Fetch verified, authorized observations within bounded time window
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=request.time_window_hours)

        stmt = select(HealthMeasurement).where(
            HealthMeasurement.crew_member_id == request.crew_member_id,
            HealthMeasurement.measurement_type.in_(request.measurement_types),
            HealthMeasurement.measured_at >= window_start,
        ).order_by(HealthMeasurement.measured_at.asc())

        result = await session.execute(stmt)
        observations = list(result.scalars().all())

        if not observations:
            return AnalysisResultDTO(
                provider_id=request.provider_id,
                model_version=provider.model_version,
                status="insufficient_data",
                message="No verified observations available within requested evaluation window.",
                limitations=MANDATORY_MODEL_LIMITATIONS,
            )

        # 6. Execute provider analysis
        context = {
            "crew_member_id": str(request.crew_member_id),
            "capability": request.capability,
            "window_start": window_start.isoformat(),
            "window_end": now.isoformat(),
        }

        try:
            analysis_dto = provider.analyze(observations=observations, context=context)
            # Ensure mandatory safety limitations cannot be removed or diluted by vendor provider
            analysis_dto.limitations = MANDATORY_MODEL_LIMITATIONS
            return analysis_dto
        except Exception as exc:
            raise AppException(
                message=f"Error occurred during analytical provider execution: {str(exc)}",
                code="provider_execution_error",
                status_code=500,
            )

