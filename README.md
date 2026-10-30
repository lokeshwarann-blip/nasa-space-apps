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
* **Health Measurements:**
  * `POST /api/v1/measurements`: Ingest objective physiological measurements (heart rate, blood pressure, temperature, SpO₂, glucose). Explicitly converts units (e.g. °F to °C) and preserves original representation and sensor provenance.
  * `GET /api/v1/measurements`: Paginated and filtered query (`crew_id`, `measurement_type`, `start_time`, `end_time`, `limit`, `offset`) with deterministic ordering.
  * `GET /api/v1/measurements/{measurement_id}`: Single measurement record inspection.
  * `POST /api/v1/measurements/{measurement_id}/invalidate`: Marks measurement as invalidated with an auditable reason; preserves historical observation without deletion or rewriting.
* **Crew Check-Ins:**
  * `POST /api/v1/check-ins`: Submits subjective self-report check-ins (`WELLNESS` ratings 1-5 or `SYMPTOM` reports with controlled vocabulary).
  * `GET /api/v1/check-ins`: Paginated and filtered retrieval across check-in categories.
  * `GET /api/v1/check-ins/{check_in_id}`: Single check-in inspection.
* **Longitudinal Trends & Empirical Baselines:**
  * `GET /api/v1/trends/{measurement_type}`: Longitudinal trend series calculation over bounded windows with deterministic sample statistics (count, min, max, mean, median, sample standard deviation), temporal gap detection, data quality metrics, and outlier labeling.
  * `GET /api/v1/trends/{measurement_type}/summary`: Condensed statistical summary without raw observation points.
  * `GET /api/v1/baselines/{measurement_type}`: Empirical personal baseline calculated solely from actual historical observations (minimum 10 samples required; returns `baseline_status='UNAVAILABLE'` if insufficient; never substitutes population baselines or synthetic data).
* **Explainable Health Assessment Engine:**
  * `POST /api/v1/assessments`: Request an explainable clinical assessment evaluated strictly by versioned, approved deterministic rules. Verifies input data provenance, unit conformity, freshness, and temporal validity.
  * `GET /api/v1/assessments/{assessment_id}`: Retrieve a persisted assessment record with full explainability trace (triggered findings, rule versions, clinical rationale, cited guidelines, and SHA-256 input snapshot hash).
  * `GET /api/v1/assessments`: Paginated and filtered query of historical assessments (`crew_id`, `status`, `start_time`, `end_time`, `limit`, `offset`).
  * **Safety Guarantees**: Zero machine learning or generative AI for clinical decisions; production rule registry is empty by default until explicitly configured with approved rules; safe-failure transitions execution errors to `needs_review` rather than falsely declaring health nominal.
* **Evidence & Guidance Registry:**
  * `GET /api/v1/guidance`: Versioned guidance query with multi-parameter filtering (`topic`, `indicator`, `hazard`, `mission_context`, `source`, `guidance_type`, `approval_status`). Automatically filters non-approved content and redacts administrative review metadata for crew members.
  * `GET /api/v1/guidance/{guidance_id}`: Detailed guidance document retrieval with source attribution, limitations, intended use, and review records.
  * `GET /api/v1/guidance/sources`: List registered authoritative standards (e.g. NASA-STD-3001, HRP).
  * `POST /api/v1/guidance/sources`: Register a new authoritative guidance source (`FLIGHT_SURGEON` or `ADMIN`).
  * `POST /api/v1/guidance`: Ingest new guidance document with initial `draft` status (`FLIGHT_SURGEON` or `ADMIN`).
  * `POST /api/v1/guidance/{guidance_id}/reviews`: Transition guidance through auditable approval states (`draft` -> `under_review` -> `approved` / `rejected` -> `retired`).
  * `POST /api/v1/guidance/{guidance_id}/supersede`: Supersede guidance with a new version, automatically retiring the prior version and chaining provenance.
  * **Registry Separation**: Explicitly segregates `EDUCATIONAL` research material, `OPERATIONAL_INSTRUCTION` flight protocols, and `CLINICAL_RULE` decision thresholds. Unreviewed or retired guidance strictly cannot activate clinical rules in the assessment engine.
* **Wellness Tasks & Reminders:**
  * `GET /api/v1/tasks/definitions`: List reusable task blueprints and recurrence configurations.
  * `POST /api/v1/tasks/definitions`: Configure reusable task definition (`FLIGHT_SURGEON` or `ADMIN`).
  * `GET /api/v1/tasks`: List assigned task instances with due windows. Crew members view strictly their own tasks.
  * `POST /api/v1/tasks`: Schedule a task instance with bounded due window for an astronaut (`FLIGHT_SURGEON` or `ADMIN`).
  * `GET /api/v1/tasks/{task_id}`: Single task instance details and audit trail.
  * `POST /api/v1/tasks/{task_id}/complete`: Fulfill task instance idempotently, linking telemetry or check-in references.
  * `POST /api/v1/tasks/{task_id}/cancel`: Cancel task assignment with clinical justification (`FLIGHT_SURGEON` or `ADMIN`).
* **Clinical Alerts Lifecycle:**
  * `GET /api/v1/alerts`: Query clinical alerts filtered by crew member, status, priority, indicator, and event window.
  * `POST /api/v1/alerts`: Ingest/trigger alert instance with deterministic idempotency deduplication for repeated findings.
  * `GET /api/v1/alerts/{alert_id}`: Alert details with complete transition audit trail.
  * `POST /api/v1/alerts/{alert_id}/acknowledge`: Acknowledge open alert (assigned astronaut or medical officer).
  * `POST /api/v1/alerts/{alert_id}/assign`: Assign alert to designated medical reviewer (`FLIGHT_SURGEON` or `ADMIN`).
  * `POST /api/v1/alerts/{alert_id}/resolve`: Record clinical resolution with documented justification (`FLIGHT_SURGEON` or `ADMIN`).
  * `POST /api/v1/alerts/{alert_id}/dismiss`: Dismiss alert with auditable rationale (`FLIGHT_SURGEON` or `ADMIN`).
  * `POST /api/v1/alerts/{alert_id}/escalate`: Escalate alert to higher tier operational destinations, accurately recording `NO_DELIVERY_PROVIDER` without false confirmation.
  * **Safety Guarantees**: Delayed telemetry is explicitly flagged (`is_delayed=True`) and historical event time is preserved separately from alert creation time to avoid misclassifying delayed syncs as sudden acute emergencies.

---

## 6. Running Automated Tests

Run the test suite using `pytest`:

```bash
# Run all unit and integration tests
pytest

# Run with verbose output
pytest -v
```

The 129-test automated suite covers:
- Task definition recurrence configuration and bounded due window validation.
- Least-privilege authorization and BOLA prevention for task assignments and cancellations.
- Idempotent task completion without duplicate audit records.
- Clinical alert deduplication and idempotency key enforcement for repeated findings.
- Controlled alert lifecycle state transitions (`open` -> `acknowledged` -> `assigned` -> `resolved` / `dismissed`) and rejection of invalid jumps.
- Accurate reporting of unconfigured notification delivery providers (`NO_DELIVERY_PROVIDER`) upon alert escalation.
- Delayed-event handling distinguishing historical telemetry from acute emergencies.
- Evidence and guidance registry source provenance, document classification, and auditable approval workflows (`draft`, `under_review`, `approved`, `rejected`, `retired`).
- Strict separation of educational material from operational flight instructions and clinical rules.
- Role-based redaction of administrative reviewer metadata and restriction of draft/retired records from crew members.
- Guidance superseding and version deprecation chains.
- Gating and prevention of unapproved, under-review, or retired guidance from activating clinical rules.
- Deterministic, explainable clinical rule engine and registry validation.
- Assessment status transitions (`assessed_no_findings`, `partially_assessed`, `insufficient_evidence`, `needs_review`, `not_assessed`).
- Safe failure behavior ensuring rule execution runtime errors never silently report nominal health.
- Cryptographic reproducibility hashing (SHA-256) capturing input observation IDs and rule versions.
- Data freshness threshold enforcement and stale observation detection.
- Object-level authorization for assessment generation and retrieval (BOLA prevention).
- Longitudinal trend calculations and descriptive statistics (count, min, max, arithmetic mean, median, sample standard deviation).
- Data quality evaluation, observation freshness, and coverage gap detection.
- Statistical outlier detection labeled strictly as statistical observations (not medical diagnoses).
- Empirical personal baseline calculation with strict minimum sample requirements and `UNAVAILABLE` fallback.
- Ingestion of objective biometric measurements and subjective check-ins.
- Explicit unit conversions (e.g., Fahrenheit to Celsius) and provenance preservation.
- Acceptance of clinically concerning but physiologically valid values (e.g. tachycardia).
- Rejection of non-finite values (NaN/Infinity), unsupported types, and incompatible units.
- Timezone-aware UTC enforcement, clock skew future detection, and stale timestamp rejection.
- Duplicate submission detection with `409 Conflict`.
- Broken Object-Level Authorization (BOLA) prevention and cross-crew data inspection blocks.
- Pagination, time-range filtering, and deterministic ordering.
- Measurement invalidation workflows and audit trail preservation.
- Token signing, claims validation, expiration, and malformed token rejection.
- Password hashing with Argon2id and random salt generation.
- Role escalation prevention and object-level authorization.
- Request payload size limiter (HTTP 413).
- Typed measurement registry and database transaction isolation.
- Liveness and readiness health probes.
