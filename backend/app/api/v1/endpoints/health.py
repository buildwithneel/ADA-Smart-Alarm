import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import engine
from app.core.redis import check_redis_health

router = APIRouter()
START_TIME = time.time()


@router.get("/health/live", summary="Liveness Probe", tags=["Health"])
def liveness_probe() -> dict:
    """Lightweight process liveness check for Kubernetes/Docker."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/ready", summary="Readiness Probe", tags=["Health"])
def readiness_probe(db: Session = Depends(get_db)) -> Response:
    """Readiness probe checking critical dependencies (PostgreSQL & Redis)."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    redis_ok = check_redis_health()

    if db_ok and redis_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "connected",
                "redis": "connected",
            },
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "unready",
            "database": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
        },
    )


@router.get("/health/deps", summary="Dependency Diagnostic Breakdown", tags=["Health"])
def dependency_health(db: Session = Depends(get_db)) -> dict:
    """Detailed health check of primary and upstream dependencies with measured latency."""
    # 1. DB
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        db_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = "healthy"
    except Exception as exc:
        db_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = f"unhealthy: {type(exc).__name__}"

    # 2. Redis
    t0 = time.perf_counter()
    redis_ok = check_redis_health()
    redis_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "status": "healthy" if db_status == "healthy" and redis_ok else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "dependencies": {
            "postgresql": {"status": db_status, "latency_ms": db_ms},
            "redis": {"status": "healthy" if redis_ok else "unhealthy", "latency_ms": redis_ms},
            "routing_provider": {"provider": settings.ROUTING_PROVIDER, "fallback": settings.ROUTING_FALLBACK_PROVIDER},
            "weather_provider": {"provider": settings.WEATHER_PROVIDER},
            "ai_provider": {"provider": settings.AI_PROVIDER, "model": settings.AI_MODEL_NAME},
        },
    }


@router.get("/health", summary="Service Health Check", tags=["Health"])
def check_health(db: Session = Depends(get_db)) -> dict:
    """Legacy backward-compatible health check."""
    db_healthy = False
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    redis_healthy = check_redis_health()
    is_overall_healthy = db_healthy and redis_healthy

    return {
        "status": "healthy" if is_overall_healthy else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_healthy else "disconnected",
        "redis": "connected" if redis_healthy else "disconnected",
    }


@router.get("/metrics", summary="Application Metrics", tags=["Health"])
def get_metrics(format: str = "prometheus") -> Response:
    """
    Exposes application and database pool telemetry in Prometheus text format (or JSON).
    No sensitive credentials or high-cardinality PII is exposed.
    """
    uptime = round(time.time() - START_TIME, 1)
    pool = engine.pool
    pool_size = pool.size()
    checked_in = pool.checkedin()
    checked_out = pool.checkedout()
    overflow = pool.overflow()

    if format == "json":
        return JSONResponse(
            content={
                "uptime_seconds": uptime,
                "db_pool": {
                    "size": pool_size,
                    "checked_in": checked_in,
                    "checked_out": checked_out,
                    "overflow": overflow,
                },
                "service": settings.PROJECT_NAME,
                "environment": settings.ENVIRONMENT,
            }
        )

    # Prometheus text format
    lines = [
        "# HELP ada_uptime_seconds Total runtime of the ADA backend service in seconds.",
        "# TYPE ada_uptime_seconds counter",
        f"ada_uptime_seconds {uptime}",
        "# HELP ada_db_pool_size Configured SQLAlchemy connection pool size.",
        "# TYPE ada_db_pool_size gauge",
        f"ada_db_pool_size {pool_size}",
        "# HELP ada_db_pool_checked_in Connections in the pool that are currently idle.",
        "# TYPE ada_db_pool_checked_in gauge",
        f"ada_db_pool_checked_in {checked_in}",
        "# HELP ada_db_pool_checked_out Connections currently checked out by active queries.",
        "# TYPE ada_db_pool_checked_out gauge",
        f"ada_db_pool_checked_out {checked_out}",
        "# HELP ada_db_pool_overflow Connection pool overflow count.",
        "# TYPE ada_db_pool_overflow gauge",
        f"ada_db_pool_overflow {overflow}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")

