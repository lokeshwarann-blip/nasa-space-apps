from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.modules.adapters.base import DevicePayloadEnvelope
from src.modules.adapters.registry import device_adapter_registry
from src.modules.adapters.service import DeviceIngestionService
from src.modules.auth.identity_provider import AuthenticatedIdentity

router = APIRouter(prefix="/devices", tags=["Sensor & External Device Adapters"])


@router.get(
    "/adapters",
    summary="List registered external device adapters",
    description="Retrieves list of registered vendor/hardware adapters and their connection status.",
)
async def list_device_adapters(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> Any:
    return {
        "adapters": device_adapter_registry.list_adapters(),
    }


@router.post(
    "/ingest",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest external device telemetry envelope",
    description="Authenticates incoming external hardware payload, parses canonical telemetry via registered adapter, and commits observations to database.",
)
async def ingest_device_payload(
    envelope: DevicePayloadEnvelope,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    records = await DeviceIngestionService.ingest_envelope(
        session=session,
        envelope=envelope,
        actor_identity=identity,
    )
    return {
        "provider_id": envelope.provider_id,
        "device_id": envelope.device_id,
        "event_id": envelope.event_id,
        "records_ingested": len(records),
        "records": records,
    }

