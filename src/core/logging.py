import logging
import json
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Context variable to hold request/correlation ID across async tasks
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Sensitive key names to redact if encountered in extra dicts
SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "authorization",
    "jwt",
    "heart_rate",
    "blood_pressure",
    "spo2",
    "respiratory_rate",
    "core_temperature",
    "medical_notes",
    "clinical_note",
    "ecg",
    "biometric",
}


def get_request_id() -> str:
    """Retrieve current request ID from context."""
    return request_id_ctx.get()


def set_request_id(req_id: str) -> None:
    """Set current request ID in context."""
    request_id_ctx.set(req_id)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter that includes correlation IDs and redacts sensitive keys."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = get_request_id()
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": req_id if req_id else None,
        }

        # Include exception info if available
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include sanitized extra fields if present
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            sanitized: dict[str, Any] = {}
            for k, v in extra_fields.items():
                if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = v
            log_entry["extra"] = sanitized

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", environment: str = "development") -> logging.Logger:
    """Configures structured root logging based on runtime environment."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if environment in ("production", "staging"):
        handler.setFormatter(JSONFormatter())
    else:
        # Development human-readable formatting with request-id prefix
        class DevFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                req_id = get_request_id()
                req_prefix = f"[{req_id[:8]}] " if req_id else ""
                record.msg = f"{req_prefix}{record.msg}"
                return super().format(record)

        handler.setFormatter(
            DevFormatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
        )

    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return logging.getLogger("astronaut_health")

