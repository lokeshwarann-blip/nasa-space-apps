import uuid
from datetime import timedelta
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from src.api.dependencies import require_roles
from src.core.security import create_access_token


def test_missing_token_returns_401(client: TestClient):
    """Verify accessing protected endpoint without Authorization header returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "unauthorized"


def test_expired_token_returns_401(client: TestClient):
    """Verify expired token returns 401 with unauthorized error code."""
    expired_token = create_access_token(
        subject="astronaut_01",
        role="CREW_MEMBER",
        expires_delta=timedelta(seconds=-10),
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "unauthorized"


def test_malformed_token_returns_401(client: TestClient):
    """Verify malformed/tampered token returns 401 with unauthorized error code."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "unauthorized"


def test_valid_token_returns_authenticated_identity(client: TestClient):
    """Verify valid token returns authenticated identity profile."""
    crew_uuid = str(uuid.uuid4())
    valid_token = create_access_token(
        subject="astro_watney",
        role="CREW_MEMBER",
        crew_member_id=crew_uuid,
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "astro_watney"
    assert data["role"] == "CREW_MEMBER"
    assert data["crew_member_id"] == crew_uuid


def test_role_escalation_prevented(app, client: TestClient):
    """Verify that a CREW_MEMBER role token cannot access ADMIN-restricted endpoints."""
    # Register an admin-only test endpoint
    @app.get("/api/v1/test-admin-only")
    def admin_endpoint(identity=Depends(require_roles("ADMIN"))):
        return {"status": "admin_granted"}

    crew_token = create_access_token(subject="astro_crew", role="CREW_MEMBER")
    response = client.get(
        "/api/v1/test-admin-only",
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "forbidden"


def test_cross_crew_bola_access_rejected(client: TestClient):
    """Verify Broken Object-Level Authorization (BOLA) is strictly prevented.
    
    A crew member must NOT be able to view another crew member's health record.
    """
    crew_1_id = uuid.uuid4()
    crew_2_id = uuid.uuid4()

    token_crew_1 = create_access_token(
        subject="astronaut_one",
        role="CREW_MEMBER",
        crew_member_id=str(crew_1_id),
    )

    # 1. Crew 1 accessing own resource -> 200 OK
    res_own = client.get(
        f"/api/v1/auth/crew/{crew_1_id}/access-verification",
        headers={"Authorization": f"Bearer {token_crew_1}"},
    )
    assert res_own.status_code == 200
    assert res_own.json()["status"] == "authorized"

    # 2. Crew 1 attempting to access Crew 2 resource -> 403 Forbidden
    res_cross = client.get(
        f"/api/v1/auth/crew/{crew_2_id}/access-verification",
        headers={"Authorization": f"Bearer {token_crew_1}"},
    )
    assert res_cross.status_code == 403
    assert res_cross.json()["error"]["code"] == "forbidden"


def test_flight_surgeon_scope_enforcement(client: TestClient):
    """Verify flight surgeon can only access assigned crew members."""
    assigned_crew = uuid.uuid4()
    unassigned_crew = uuid.uuid4()

    surgeon_token = create_access_token(
        subject="dr_stone",
        role="FLIGHT_SURGEON",
        assigned_crew_ids=[str(assigned_crew)],
    )

    # Assigned crew -> 200 OK
    res_assigned = client.get(
        f"/api/v1/auth/crew/{assigned_crew}/access-verification",
        headers={"Authorization": f"Bearer {surgeon_token}"},
    )
    assert res_assigned.status_code == 200

    # Unassigned crew -> 403 Forbidden
    res_unassigned = client.get(
        f"/api/v1/auth/crew/{unassigned_crew}/access-verification",
        headers={"Authorization": f"Bearer {surgeon_token}"},
    )
    assert res_unassigned.status_code == 403
    assert res_unassigned.json()["error"]["code"] == "forbidden"


def test_admin_denied_clinical_access_without_assignment(client: TestClient):
    """Verify administrator does NOT have automatic access to clinical crew records."""
    target_crew = uuid.uuid4()

    admin_token = create_access_token(
        subject="sysadmin",
        role="ADMIN",
        assigned_crew_ids=[],  # No explicit clinical assignment
    )

    response = client.get(
        f"/api/v1/auth/crew/{target_crew}/access-verification",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_request_size_limit_rejection(client: TestClient):
    """Verify requests with Content-Length exceeding configured max size are rejected with 413."""
    oversized_length = 2 * 1024 * 1024  # 2 MB (configured limit is 1 MB)
    response = client.post(
        "/api/v1/auth/token",
        headers={"Content-Length": str(oversized_length)},
        content=b"{}",
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

