from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.check_ins import router as check_ins_router
from src.api.v1.health import router as health_router
from src.api.v1.measurements import router as measurements_router

# Root API v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Mount endpoints under /api/v1
api_v1_router.include_router(health_router, prefix="/health")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(measurements_router)
api_v1_router.include_router(check_ins_router)

# Dedicated health router for root /health probes (standard Kubernetes / Docker probes)
root_health_router = APIRouter(prefix="/health")
root_health_router.include_router(health_router)

