from __future__ import annotations

import structlog
from fastapi import APIRouter

from app.config import get_settings
from app.db.session import check_database_connection
from app.models.schemas.responses.auth import HealthCheckDetail, HealthResponse

router = APIRouter()
log = structlog.get_logger(__name__)
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Returns system health status including database connectivity. "
        "No authentication required. Used by load balancers and Docker healthchecks."
    ),
    tags=["System"],
)
async def health_check() -> HealthResponse:
    db_healthy, db_latency = await check_database_connection()

    checks: dict[str, HealthCheckDetail] = {
        "database": HealthCheckDetail(
            status="ok" if db_healthy else "error",
            latency_ms=db_latency if db_healthy else None,
            error=None if db_healthy else "Database connection failed",
        ),
    }

    overall = "healthy" if db_healthy else "unhealthy"

    if overall != "healthy":
        log.warning("health.degraded", checks={k: v.model_dump() for k, v in checks.items()})

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        checks=checks,
    )