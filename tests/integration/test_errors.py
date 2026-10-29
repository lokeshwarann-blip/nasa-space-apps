from fastapi.testclient import TestClient

from src.core.exceptions import AppException


def test_404_not_found_standard_error(client: TestClient):
    """Verify 404 responses follow the standardized error schema."""
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]
    assert response.headers.get("X-Request-ID") == data["error"]["request_id"]


def test_custom_app_exception(app, client: TestClient):
    """Verify custom domain exceptions return expected code, message, and status."""
    @app.get("/api/v1/test-custom-error")
    def custom_error_route():
        raise AppException(
            message="Test domain validation failure",
            code="DOMAIN_RULE_VIOLATION",
            status_code=400,
            details={"field": "astronaut_id"},
        )

    response = client.get("/api/v1/test-custom-error")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "DOMAIN_RULE_VIOLATION"
    assert data["error"]["message"] == "Test domain validation failure"
    assert data["error"]["details"] == {"field": "astronaut_id"}
    assert "request_id" in data["error"]


def test_unhandled_exception_sanitized_500(app):
    """Verify unhandled exceptions return 500 without leaking stack traces or internal details."""
    @app.get("/api/v1/test-unhandled-crash")
    def crash_route():
        raise RuntimeError("Internal secret database password leak in trace")

    # Starlette TestClient re-raises server exceptions by default; set raise_server_exceptions=False to test 500 response
    unhandled_client = TestClient(app, raise_server_exceptions=False)
    response = unhandled_client.get("/api/v1/test-unhandled-crash")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Make sure raw exception message was NOT leaked
    assert "password" not in data["error"]["message"]
    assert data["error"]["message"] == "An unexpected error occurred. Please contact system support."
    assert "request_id" in data["error"]

