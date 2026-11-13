import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging import get_request_id

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception for domain and business errors."""

    def __init__(
        self,
        message: str,
        code: str = "APPLICATION_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class DatabaseConnectionError(AppException):
    """Raised when the database connection or health check fails."""

    def __init__(self, message: str = "Database connection unavailable"):
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' was not found.",
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnsupportedMeasurementTypeError(AppException):
    """Raised when a submitted measurement type is not supported."""

    def __init__(self, measurement_type: str):
        super().__init__(
            message=f"Measurement type '{measurement_type}' is not supported.",
            code="unsupported_measurement_type",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidUnitError(AppException):
    """Raised when a submitted measurement unit is incompatible."""

    def __init__(self, unit: str, measurement_type: str, allowed_units: list[str]):
        super().__init__(
            message=f"Unit '{unit}' is invalid for measurement '{measurement_type}'. Allowed: {allowed_units}",
            code="invalid_unit",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidValueError(AppException):
    """Raised when a measurement value is non-finite, missing, or malformed."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="invalid_value",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidTimestampError(AppException):
    """Raised when a timestamp is non-UTC, in the future, or excessively stale."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="invalid_timestamp",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DuplicateSubmissionError(AppException):
    """Raised when an identical measurement has already been ingested."""

    def __init__(self, message: str = "Duplicate measurement already submitted."):
        super().__init__(
            message=message,
            code="duplicate_submission",
            status_code=status.HTTP_409_CONFLICT,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers centralized, consistent exception handlers with the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        req_id = get_request_id() or request.headers.get("X-Request-ID", "")
        logger.warning(f"Domain exception [{exc.code}]: {exc.message} (status: {exc.status_code})")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = get_request_id() or request.headers.get("X-Request-ID", "")
        # Sanitize errors to remove any internal memory representations
        sanitized_errors = []
        primary_code = "VALIDATION_ERROR"
        for err in exc.errors():
            msg = err.get("msg", "Validation error")
            loc = [str(x) for x in err.get("loc", [])]
            err_type = err.get("type", "value_error")
            loc_str = "".join(loc).lower()
            if "timestamp" in msg.lower() or "timestamp" in loc_str or "measured_at" in loc_str or "onset_time" in loc_str:
                primary_code = "invalid_timestamp"
            elif "finite" in msg.lower() or "nan" in msg.lower() or "numeric" in msg.lower():
                primary_code = "invalid_value"
            elif "unit" in loc_str:
                primary_code = "invalid_unit"
            sanitized_errors.append(
                {
                    "loc": loc,
                    "msg": msg,
                    "type": err_type,
                }
            )
        logger.info(f"Request validation failed: {len(sanitized_errors)} errors")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": primary_code,
                    "message": "Input validation failed. Please check the provided data.",
                    "details": sanitized_errors,
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        req_id = get_request_id() or request.headers.get("X-Request-ID", "")
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": str(exc.detail),
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = get_request_id() or request.headers.get("X-Request-ID", "")
        # Log full traceback internally with correlation ID, but never leak internals to client
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact system support.",
                    "request_id": req_id,
                }
            },
        )

