
MELIORA brings astronaut health information into a centralized dashboard helping crew members and authorized medical personnel monitor health indicators and review available health trends.

The platform is designed around the needs of three user roles:

- **Crew Members:** Access their health information and monitor personal health indicators.
- **Flight Surgeons:** Review health information for assigned crew members.
- **Administrators:** Manage registered user accounts.

##  Key Features

- Health monitoring dashboard.
- Visualization of health indicators and historical trends.
- Role-based authentication and authorization.
- Crew-specific access controls.
- Flight surgeon dashboard for assigned crew members.
- Administrative user management.
- Backend API for health data and authentication.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Styling | CSS Modules |
| Charts | Recharts |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Authentication | JWT, Argon2id password hashing |

##  Project Structure

```text
nasa-space-apps/
│
├── backend/
│   ├── migrations/
│   └── src/
│       ├── api/
│       ├── core/
│       ├── models/
│       └── modules/
│
└── frontend/
    └── src/
        ├── app/
        │   ├── admin/
        │   ├── dashboard/
        │   ├── login/
        │   └── flight-sergeon/
        └── components/
```

##  Getting Started

### Prerequisites

- Python
- Node.js and npm
- PostgreSQL

### 1. Clone the repository

```bash
git clone https://github.com/srijonighosh04/nasa-space-apps.git
cd nasa-space-apps
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment.

**Windows:**
```powershell
.\venv\Scripts\Activate.ps1
```

Install the backend dependencies using the project's dependency file, configure the environment variables using the provided example configuration, and start the backend:

```bash
python -m uvicorn src.main:app --reload
```

Backend API documentation:

`http://localhost:8000/docs`

### 3. Frontend Setup

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

`http://localhost:3000`


