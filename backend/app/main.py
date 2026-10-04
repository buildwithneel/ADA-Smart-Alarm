from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import (
    ContentLengthLimitMiddleware,
    RequestLoggingAndTracingMiddleware,
    SecurityHeadersMiddleware,
)
from app.models.base import Base
from app.services.event_handlers import init_domain_event_subscribers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle context manager for FastAPI.
    Initializes structured logging and ensures DB schema is prepared in dev mode.
    """
    setup_logging()
    init_domain_event_subscribers()
    if settings.ENVIRONMENT == "development":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ADA - Adaptive Dynamic Alarm backend service engine API.",
    version="0.1.0",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENABLE_DOCS else None,
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service diagnostic and infrastructure health checks",
        },
        {
            "name": "Users",
            "description": "User profile and travel preference management",
        },
        {
            "name": "Destinations",
            "description": "Saved destination addresses and geocoded locations",
        },
        {
            "name": "Alarms",
            "description": "Adaptive dynamic alarms and recurrence schedules",
        },
    ],
    lifespan=lifespan,
)

# Register RFC 7807 Error Handling
register_exception_handlers(app)

# Defensive Middlewares (ordered from outermost to innermost)
# 1. Enforce max request payload limit to defend against memory exhaustion DOS
app.add_middleware(ContentLengthLimitMiddleware)

# 2. Inject defensive HTTP response headers (CSP, HSTS, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Transparent response body compression for payloads > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. Distributed Request Tracing and Performance Logging Middleware
app.add_middleware(RequestLoggingAndTracingMiddleware)

# Configure CORS policies for frontend integrations
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Attach versioned API routing layers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    """Root discovery and health gateway endpoint."""
    return {
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.ENABLE_DOCS else "disabled",
        "redoc": "/redoc" if settings.ENABLE_DOCS else "disabled",
        "api_v1": settings.API_V1_STR,
        "status": "online",
    }


# Top-level health & liveness probes (standard cloud/Kubernetes entrypoints)
@app.get("/health/live", include_in_schema=False)
def top_level_liveness():
    from app.api.v1.endpoints.health import liveness_probe
    return liveness_probe()


@app.get("/health/ready", include_in_schema=False)
def top_level_readiness(db=None):
    from app.core.database import SessionLocal
    from app.api.v1.endpoints.health import readiness_probe
    db = SessionLocal()
    try:
        return readiness_probe(db)
    finally:
        db.close()


@app.get("/metrics", include_in_schema=False)
def top_level_metrics(format: str = "prometheus"):
    from app.api.v1.endpoints.health import get_metrics
    return get_metrics(format=format)


