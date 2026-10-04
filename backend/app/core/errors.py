import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("ada.errors")


class AppException(Exception):
    """Base application domain exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class NotFoundException(AppException):
    """Resource not found (404)."""

    def __init__(self, entity_name: str, identifier: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class EntityNotFoundException(NotFoundException):
    """Alias for backwards compatibility."""

    pass


class ConflictException(AppException):
    """Conflict with existing resource state (409)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class UnauthorizedException(AppException):
    """Unauthorized request (401)."""

    def __init__(self, message: str = "Authentication required."):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    """Forbidden request (403)."""

    def __init__(self, message: str = "Access forbidden."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class ValidationException(AppException):
    """Business rule or schema validation failure (422)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ProviderException(AppException):
    """External provider error or outage (502)."""

    def __init__(self, message: str, provider: str = "unknown", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="PROVIDER_ERROR",
            details={"provider": provider, **(details or {})},
        )


class RateLimitExceededException(AppException):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again shortly.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class NoRouteFoundException(AppException):
    """No route found between coordinates (404)."""

    def __init__(self, message: str = "No navigable route could be found between the specified origin and destination."):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NO_ROUTE_FOUND",
        )


class UnsupportedTravelModeException(AppException):
    """Travel mode is unsupported by the selected provider (400)."""

    def __init__(self, mode: str, provider: str):
        super().__init__(
            message=f"Travel mode '{mode}' is not supported by map provider '{provider}'.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="UNSUPPORTED_TRAVEL_MODE",
            details={"mode": mode, "provider": provider},
        )



def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers centralized exception handlers adhering to RFC 7807 Problem Details.
    Guarantees that raw database errors or stack traces are never exposed to clients,
    while attaching distributed tracing request_ids for fast SRE/developer correlation.
    """

    def _get_request_id(request: Request) -> Optional[str]:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(part) for part in err.get("loc", [])])
            errors.append({"field": loc, "message": err.get("msg")})

        req_id = _get_request_id(request)
        headers = {"X-Request-ID": req_id} if req_id else {}

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "type": "https://api.ada-alarm.com/errors/validation_error",
                "title": "VALIDATION_ERROR",
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "detail": "Request payload validation failed.",
                "instance": str(request.url.path),
                "request_id": req_id,
                "details": {"validation_errors": errors},
            },
            headers=headers,
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        req_id = _get_request_id(request)
        headers = {"X-Request-ID": req_id} if req_id else {}

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://api.ada-alarm.com/errors/{exc.error_code.lower()}",
                "title": exc.error_code,
                "status": exc.status_code,
                "detail": exc.message,
                "instance": str(request.url.path),
                "request_id": req_id,
                "details": exc.details,
            },
            headers=headers,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        req_id = _get_request_id(request)
        headers = {"X-Request-ID": req_id} if req_id else {}
        logger.error(f"Database IntegrityError on {request.url.path} [req_id={req_id}]: {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "type": "https://api.ada-alarm.com/errors/conflict",
                "title": "DATA_INTEGRITY_CONFLICT",
                "status": status.HTTP_409_CONFLICT,
                "detail": "The operation could not be completed due to a database integrity constraint conflict.",
                "instance": str(request.url.path),
                "request_id": req_id,
            },
            headers=headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        req_id = _get_request_id(request)
        headers = {"X-Request-ID": req_id} if req_id else {}
        logger.error(f"Database SQLAlchemyError on {request.url.path} [req_id={req_id}]: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "https://api.ada-alarm.com/errors/database_error",
                "title": "DATABASE_ERROR",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "detail": "A database error occurred while processing the request.",
                "instance": str(request.url.path),
                "request_id": req_id,
            },
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        req_id = _get_request_id(request)
        headers = {"X-Request-ID": req_id} if req_id else {}
        logger.error(
            f"Unhandled server exception on {request.url.path} [req_id={req_id}]: {exc}", exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "https://api.ada-alarm.com/errors/internal_server_error",
                "title": "INTERNAL_SERVER_ERROR",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "detail": "An unexpected server error occurred.",
                "instance": str(request.url.path),
                "request_id": req_id,
            },
            headers=headers,
        )
