# NASA Space Apps Challenge — Astronaut Health Monitoring System

Autonomous, secure, and resilient health monitoring platform designed to support astronauts during long-duration spaceflight missions and assist terrestrial flight surgeons.

---

> [!WARNING]
> **Regulatory Notice & Challenge Disclaimer:**  
> This software is an engineering submission developed for the NASA Space Apps Challenge hackathon. It has not undergone clinical certification, FDA clearance, or NASA medical flight readiness review. It does not replace the clinical judgment of an aerospace flight surgeon.

---

## 1. Repository Layout

The repository is organized into distinct domain modules to support multi-service fullstack development:

```
nasa-space-apps/
├── backend/                      # Complete FastAPI backend application
│   ├── src/                      # Application source code (modular monolith)
│   │   ├── api/                  # 12 versioned v1 domain routers & health probes
│   │   ├── core/                 # Config, async database, logging, auth & security
│   │   ├── models/               # 19 SQLAlchemy 2.0 declarative database entities
│   │   ├── modules/              # Domain services, deterministic rules, & sync engine
│   │   └── schemas/              # Pydantic v2 strict data transfer schemas
│   ├── tests/                    # 150 automated unit & integration tests
│   ├── migrations/               # Alembic PostgreSQL schema migration chain
│   ├── docs/                     # Architectural specifications & clinical contracts
│   │   ├── security_architecture.md    # Threat model, PHI protection, & least privilege
│   │   ├── data_retention_policy.md    # Audit trails & retention windows
│   │   ├── offline_sync_architecture.md # Store-and-forward batch reconciliation
│   │   └── data_intake_contract.md     # Ground-truth criteria & IRB requirements
│   ├── Dockerfile                # Production multi-stage container (non-root appuser)
│   ├── requirements.txt          # Production pinned Python dependencies
│   ├── requirements-dev.txt      # Testing and development dependencies
│   ├── alembic.ini               # Database migration configuration
│   ├── pyproject.toml            # Backend build & pytest configuration
│   └── README.md                 # Detailed backend technical manual & API reference
│
├── docker-compose.yml            # Multi-container orchestration (PostgreSQL 16 + API)
├── pyproject.toml                # Root pytest delegation configuration
├── .gitignore                    # Git ignore rules
└── README.md                     # Root project documentation
```

For complete technical specifications of the backend, including the **50 API endpoints**, authentication models, and deterministic assessment rules, refer to [backend/README.md](backend/README.md).

---

## 2. Quickstart & Deployment

### Option A: Run the Entire Stack via Docker Compose (Recommended)

To launch the backend API and a managed PostgreSQL 16 database with healthchecks:

```bash
docker compose up --build -d
```

The service will start and expose:
- **API Root / Health:** `http://localhost:8000/health/live`
- **Interactive Swagger UI:** `http://localhost:8000/docs`
- **ReDoc Specification:** `http://localhost:8000/redoc`

To shut down:
```bash
docker compose down
```

---

### Option B: Local Backend Development

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server:**
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

---

## 3. Running Automated Tests

The test suite contains **150 automated tests** covering unit logic, rule determinism, BOLA security boundaries, and end-to-end API endpoints.

You can execute tests either from the project root or from inside `backend/`:

```bash
# From project root:
pytest

# Or from inside backend:
cd backend
pytest -v
```

---

## 4. Key Architectural Guarantees

- **Personal Health Information (PHI) Protection:** Astronaut vitals are isolated with object-level authorization (BOLA prevention). Administrators cannot view clinical records without explicit assignment.
- **Store-and-Forward Offline Resilience:** Intermittent spaceflight connectivity (loss-of-signal / LOS) is accommodated through a bounded, idempotent batch synchronization engine.
- **Deterministic & Explainable Assessments:** Health evaluations are performed strictly by versioned, approved deterministic rules (citing standards like NASA-STD-3001). Machine learning models are never used to make automated clinical decisions without review.
- **Provider-Neutral Sensor Adapters:** External telemetry is normalized and unit-converted into canonical records while tracking complete device provenance.
