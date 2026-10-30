# NASA Space Apps Challenge — Astronaut Health Monitoring Software Backend

High-performance, secure backend architecture designed to monitor astronaut physiological vitals, evaluate telemetry against verified aerospace clinical thresholds (e.g., NASA-STD-3001), and alert flight surgeons during spaceflight missions.

---

> [!WARNING]
> **Regulatory Disclaimer:**  
> This software is an engineering prototype developed for the NASA Space Apps Challenge. It has not undergone clinical certification, FDA clearance, or NASA medical device flight readiness review. No claims of HIPAA compliance, HITECH certification, or aerospace flight surgeon replacement are made.

---

## 1. Architecture Overview

Built as a **modular monolith** adhering strictly to:
- **FastAPI** application factory (`src.main:create_app`)
- **Pydantic v2** strict typing, boundary validation, and UTC timezone enforcement
- **SQLAlchemy 2.0 (async)** with PostgreSQL and Alembic migrations
- **Decoupled Architecture**: Zero business or clinical logic in route handlers; all domain logic is isolated in services and deterministic rule engines.
- **Security & Privacy First**: Personal Health Information (PHI) protection, object-level RBAC, redacted logging, Argon2id password hashing, and no synthetic/fabricated medical records in production.

```
src/
├── main.py              # Application factory & ASGI entry point
├── api/                 # API routers, middleware, and versioned routes (/api/v1)
├── core/                # Core configurations, logging, exceptions, database session, security
├── models/              # SQLAlchemy 2.0 declarative database entities
├── modules/             # Domain modules: auth, audit, telemetry registry, clinical rules
└── schemas/             # Pydantic v2 validation models and response DTOs
```

---

## 2. Authentication & Authorization Model

### Logical Roles & Permission Scopes
* **Crew Member (`CREW_MEMBER`):**
  * Access restricted strictly to their personal health records, wellness reports, and assigned missions.
  * Attempting to query another astronaut's records (via guessed or supplied UUIDs) fails with `403 Forbidden` (Broken Object-Level Authorization / BOLA prevention).
* **Medical Reviewer / Flight Surgeon (`FLIGHT_SURGEON`):**
  * Access permitted only for crew members explicitly included within their authorized scope (`assigned_crew_ids`).
  * Attempting to inspect unassigned crew records returns `403 Forbidden`.
* **System Administrator (`ADMIN`):**
  * Manages accounts and system settings.
  * **Least-Privilege Enforcement:** Admins do *not* have automatic, unrestricted access to clinical health records unless explicitly assigned as a medical officer for that subject.

### Cryptographic Security Specifications
* **Token Standard:** RFC 7519 JSON Web Tokens signed with HMAC-SHA256 (`HS256`).
* **Claims Validated:** Cryptographic signature, expiration (`exp`), issuer (`iss`), audience (`aud`), subject (`sub`), and role (`role`).
* **Password Hashing:** Argon2id with unique random salting (OWASP recommended parameters).
* **Request Limits:** Payload size limiter rejects oversized bodies exceeding 1 MB (`HTTP 413 Content Too Large`).
* **Data Sanitization:** Strict audit logger redacting credentials, tokens, and raw medical telemetry before persisting audit events.

### Security Documentation & Policies
* [Security Architecture & Threat Model](docs/security_architecture.md)
* [Data Retention & Deletion Policy](docs/data_retention_policy.md)

---

## 3. Environment Variables

Copy `.env.example` to `.env` to configure local variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PROJECT_NAME` | Service name | `NASA Space Apps - Astronaut Health Monitor` |
| `ENVIRONMENT` | Environment (`development`, `staging`, `production`, `testing`) | `development` |
| `DEBUG` | Enable debug logs | `false` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `API_V1_PREFIX` | Versioned route prefix | `/api/v1` |
| `POSTGRES_SERVER` | PostgreSQL hostname | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `postgres` |
| `POSTGRES_DB` | PostgreSQL database name | `astronaut_health` |
| `SECRET_KEY` | Cryptographic secret for signing tokens (min 32 chars) | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token validity window | `60` |
| `JWT_ISSUER` | Expected JWT issuer claim | `nasa-space-apps-auth` |
| `JWT_AUDIENCE` | Expected JWT audience claim | `nasa-space-apps-api` |

---

## 4. Quickstart & Local Setup

### Prerequisites
- Python 3.12+
- Docker and Docker Compose (recommended for PostgreSQL)

### Option A: Local Python Virtual Environment

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

4. **Start PostgreSQL via Docker Compose:**
   ```bash
   docker compose up -d db
   ```

5. **Run the FastAPI development server:**
   ```bash
   python src/main.py
   # Or via uvicorn directly:
   uvicorn src.main:app --reload --port 8000
   ```

### Option B: Full Containerized Stack

```bash
docker compose up --build
```

The application runs as a secure, non-root user inside the container and will be accessible at `http://localhost:8000`.

---

## 5. API Endpoints & Health Probes

* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) (available in `development` and `staging`)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Liveness Probe:** `GET /health/live` (returns `200 OK` when process is running)
* **Readiness Probe:** `GET /health/ready` (probes PostgreSQL database connectivity)
* **Authentication:** `POST /api/v1/auth/token` (Argon2id credential verification and JWT issuance)
* **Identity Profile:** `GET /api/v1/auth/me` (returns verified claims and permissions)
* **Object Access Verification:** `GET /api/v1/auth/crew/{target_crew_member_id}/access-verification`

---

## 6. Running Automated Tests

Run the test suite using `pytest`:

```bash
# Run all unit and integration tests
pytest

# Run with verbose output
pytest -v
```

The 52-test automated suite covers:
- Token signing, claims validation, expiration, and malformed token rejection.
- Password hashing with Argon2id and random salt generation.
- Role escalation prevention and object-level authorization (BOLA prevention).
- Flight surgeon assigned scope verification and admin clinical record restrictions.
- Audit logging sanitization and redaction of credentials and medical observations.
- Request payload size limiter (HTTP 413).
- Typed measurement registry and explicit unit conversions.
- Database models, constraints, cascades, and rollback isolation.
- Liveness and readiness probes.
