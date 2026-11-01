import logging
import time
import uuid
from collections.abc import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.core.logging import get_request_id, set_request_id

logger = logging.getLogger("astronaut_health.access")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Generates or propagates X-Request-ID and tracks request duration safely."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        set_request_id(request_id)

        start_time = time.perf_counter()

        # Execute downstream handlers
        try:
            response = await call_next(request)
        except Exception:
            raise
        finally:
            process_time = (time.perf_counter() - start_time) * 1000.0

        # Propagate request ID in response header
        response.headers["X-Request-ID"] = request_id

        # Safe access logging: log method, sanitized path, status code, and latency
        # Do NOT log request bodies, query params with credentials, or authorization headers
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"{client_ip} - \"{request.method} {request.url.path}\" "
            f"{response.status_code} ({process_time:.2f}ms)"
        )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum request body payload size to prevent denial-of-service."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        content_length = request.headers.get("Content-Length")

        if content_length:
            try:
                length_int = int(content_length)
                if length_int > settings.MAX_REQUEST_BODY_SIZE_BYTES:
                    req_id = get_request_id()
                    logger.warning(
                        f"Request payload too large: {length_int} bytes "
                        f"(max {settings.MAX_REQUEST_BODY_SIZE_BYTES} bytes)"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body exceeds maximum allowed size of {settings.MAX_REQUEST_BODY_SIZE_BYTES} bytes.",
                                "request_id": req_id,
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
