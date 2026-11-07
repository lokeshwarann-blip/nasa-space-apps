import json
import logging
from src.core.logging import JSONFormatter, get_request_id, set_request_id


def test_request_id_context():
    """Verify request ID is properly set and retrieved in context."""
    test_id = "test-uuid-1234-5678"
    set_request_id(test_id)
    assert get_request_id() == test_id


def test_json_formatter_redaction():
    """Verify that sensitive keys are redacted from structured log records."""
    set_request_id("req-abc-999")
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Telemetry ingestion event",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "status": "success",
        "astronaut_id": "ASTRO-101",
        "heart_rate": 78,
        "password": "super-secret-password",
        "token": "bearer-token-123",
    }

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert log_data["request_id"] == "req-abc-999"
    assert log_data["message"] == "Telemetry ingestion event"
    assert log_data["extra"]["astronaut_id"] == "ASTRO-101"
    assert log_data["extra"]["heart_rate"] == "[REDACTED]"
    assert log_data["extra"]["password"] == "[REDACTED]"
    assert log_data["extra"]["token"] == "[REDACTED]"

