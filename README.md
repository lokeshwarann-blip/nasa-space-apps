# NASA Space Apps Challenge — Astronaut Health Monitoring Software Backend

High-performance, secure backend architecture designed to monitor astronaut physiological vitals, evaluate telemetry against verified aerospace clinical thresholds (e.g., NASA-STD-3001), and alert flight surgeons during spaceflight missions.

---

## 1. Architecture Overview

Built as a **modular monolith** adhering strictly to:
- **FastAPI** application factory (`src.main:create_app`)
- **Pydantic v2** strict typing and data validation
- **SQLAlchemy 2.0 (async)** with PostgreSQL and Alembic migrations
- **Decoupled Architecture**: Zero business or clinical logic in route handlers; all domain logic is isolated in services and deterministic rule engines.
- **Security & Privacy First**: Personal Health Information (PHI) protection, object-level RBAC, redacted logging, and no synthetic/fabricated medical records in production.

```
src/
├── main.py              # Application factory & ASGI entry point
├── api/                 # API routers, middleware, and versioned routes (/api/v1)
├── core/                # Core configurations, logging, exceptions, database session
└── schemas/             # Pydantic v2 validation models and response schemas
```

---

## 2. Environment Variables

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

---

## 3. Quickstart & Local Setup

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

## 4. API Documentation & Health Probes

* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) (available in `development` and `staging`)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Liveness Probe:** `GET /health/live`
  * Returns `200 OK` when the FastAPI application event loop is running.
* **Readiness Probe:** `GET /health/ready`
  * Checks backing PostgreSQL database connectivity. Returns `200 OK` when connected, or `503 Service Unavailable` if database is down.

---

## 5. Running Automated Tests

Run the test suite using `pytest`:

```bash
# Run all unit and integration tests
pytest

# Run with verbose output and coverage
pytest -v -s
```

The test suite covers:
- Configuration and typed environment validation.
- Structured logging, correlation ID (`X-Request-ID`) propagation, and sensitive key redaction.
- Liveness and readiness endpoints (including verified 503 behavior when database is unreachable).
- Centralized exception handling, sanitized 500 error responses, and 404/422 consistency.

---

## 6. Troubleshooting

* **Readiness probe returns 503 Service Unavailable:**  
  Verify PostgreSQL is running (`docker compose ps db`) and that the credentials in `.env` match the PostgreSQL container settings.
* **Secret key validation error on startup:**  
  `SECRET_KEY` must be at least 32 characters long. Update `SECRET_KEY` in `.env`.
* **Database port conflict:**  
  If port 5432 is already in use by a local PostgreSQL instance, change `POSTGRES_PORT` in `.env` and `docker-compose.yml`.

