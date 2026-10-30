"""Clinical alert lifecycle and deduplication module."""
from src.modules.alerts.schemas import (
    AlertAcknowledgeRequest,
    AlertAssignRequest,
    AlertCreate,
    AlertDismissRequest,
    AlertEscalateRequest,
    AlertInstanceListResponse,
    AlertInstanceResponse,
    AlertResolveRequest,
)
from src.modules.alerts.service import AlertService

__all__ = [
    "AlertService",
    "AlertCreate",
    "AlertInstanceResponse",
    "AlertInstanceListResponse",
    "AlertAcknowledgeRequest",
    "AlertAssignRequest",
    "AlertResolveRequest",
    "AlertDismissRequest",
    "AlertEscalateRequest",
]
