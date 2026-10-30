import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity
from src.core.database import get_db
from src.core.exceptions import AppException
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.sync.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncEventResult,
)
from src.modules.sync.service import SyncService

router = APIRouter(prefix="/sync", tags=["Offline Synchronization & Ingestion"])


@router.post(
    "",
    response_model=SyncBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize bounded batch of offline events",
    description="Ingests bounded batches (1-100) of biometric measurements and check-ins recorded offline. Provides database-enforced idempotency, partial batch success, and conflict detection.",
)
async def sync_batch(
    batch_req: SyncBatchRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    return await SyncService.process_batch(
        session=session,
        batch_req=batch_req,
        actor_identity=identity,
    )


@router.get(
    "/status/{client_event_id}",
    response_model=SyncEventResult,
    summary="Get sync status for client event UUID",
    description="Polls the synchronization and reconciliation outcome of a specific client event UUID.",
)
async def get_sync_status(
    client_event_id: uuid.UUID,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> Any:
    record = await SyncService.get_sync_record(
        session=session,
        client_event_id=client_event_id,
        actor_identity=identity,
    )
    if record is None:
        raise AppException(
            message=f"Sync record for client event '{client_event_id}' not found.",
            code="not_found",
            status_code=404,
        )

    return SyncEventResult(
        client_event_id=record.client_event_id,
        status=record.sync_status,
        entity_id=record.entity_id,
        error_code=record.error_code,
        message=record.error_message,
    )
