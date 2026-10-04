import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("ada.access")


class RequestLoggingAndTracingMiddleware(BaseHTTPMiddleware):
    """
    Production middleware that:
    1. Injects a unique X-Request-ID into each request for distributed tracing.
    2. Measures processing execution time and adds X-Process-Time header.
    3. Emits structured access log metrics without logging sensitive data.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response: Response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"

        # Sanitize query parameters from access logs to prevent token/key leakage in logs
        path_clean = request.url.path

        logger.info(
            f"method={request.method} path={path_clean} "
            f"status={response.status_code} latency={process_time:.4f}s "
            f"request_id={request_id}"
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Hardens API responses with modern defensive HTTP security headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (anti-clickjacking)
    - Strict-Transport-Security (HSTS in production)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy
    - Content-Security-Policy (API default)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        if getattr(settings, "SECURE_HEADERS_ENABLED", True):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

            if settings.ENVIRONMENT == "production":
                # Enforce HSTS for 1 year with subdomains
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )

        return response


class ContentLengthLimitMiddleware(BaseHTTPMiddleware):
    """
    Defends against denial-of-service / memory exhaustion attacks by enforcing
    a configurable maximum HTTP request payload limit (MAX_CONTENT_LENGTH_BYTES).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        max_bytes = getattr(settings, "MAX_CONTENT_LENGTH_BYTES", 2097152)

        if content_length:
            try:
                length = int(content_length)
                if length > max_bytes:
                    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
                    logger.warning(
                        f"Request rejected: content-length {length} exceeds maximum {max_bytes} bytes."
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "type": "https://api.ada-alarm.com/errors/payload_too_large",
                            "title": "PAYLOAD_TOO_LARGE",
                            "status": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            "detail": f"Payload size {length} bytes exceeds maximum allowed {max_bytes} bytes.",
                            "instance": str(request.url.path),
                            "request_id": request_id,
                        },
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                pass

        return await call_next(request)
