from fastapi import APIRouter

from src.api.v1.health import router as health_router

# Root API v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Mount health checks under /api/v1/health
api_v1_router.include_router(health_router, prefix="/health")

# Dedicated health router for root /health probes (standard Kubernetes / Docker probes)
root_health_router = APIRouter(prefix="/health")
root_health_router.include_router(health_router)

