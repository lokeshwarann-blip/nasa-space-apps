# Test Crew Dataset, Health Readings & Database Seeder

This folder contains mock test crew profiles, 48 hours of timestamped physiological health readings, and a one-command test database seeding script for local frontend and backend development.

---

> [!IMPORTANT]
> **Privacy & Medical Data Policy:**  
> - **Synthetic / Non-PHI:** All records in this folder use pseudonymous identifiers (`CREW-001` through `CREW-006`) with fictional callsigns, operational roles, and physiological estimates.
> - **Zero Real Astronaut Data:** This data does not represent any real astronaut, NASA flight personnel, or private passenger.
> - **Isolation:** This data is strictly restricted to this `test/` directory and is never loaded into production deployment seeds or clinical rule engines without explicit invocation of test seeders.

---

## Directory Contents

| File | Format | Description |
| :--- | :--- | :--- |
| `crew_members.json` | JSON | Complete structured test crew profiles conforming to `CrewMemberRead` / `CrewMemberCreate` schemas. |
| `crew_members.csv` | CSV | Tabular representation for spreadsheet inspection or bulk test imports. |
| `health_readings.json` | JSON | **480 timestamped physiological readings** (heart rate, blood pressure, SpO₂, body temp) across 48 hours. |
| `health_readings.csv` | CSV | Tabular format of the 480 physiological readings. |
| `fixtures.py` | Python | Helper utilities (`load_test_crew_data()`, `load_test_health_readings()`, `TEST_USERS`) for test harnesses. |
| `seed_test_db.py` | Python | Database seeding script to populate PostgreSQL with crew members, users, and readings. |

---

## Crew Roster Summary

| UUID | Crew ID | Callsign | Flight Role | Assigned Mission | Environment | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `c1111111-1111-4111-8111-111111111111` | `CREW-001` | Astra-Lead | COMMANDER | ARTEMIS-III | LUNAR_SURFACE | `ACTIVE` |
| `c2222222-2222-4222-8222-222222222222` | `CREW-002` | Vanguard | PILOT | ARTEMIS-III | LUNAR_SURFACE | `ACTIVE` |
| `c3333333-3333-4333-8333-333333333333` | `CREW-003` | Caduceus | MEDICAL_OFFICER | ARTEMIS-III | LUNAR_SURFACE | `ACTIVE` |
| `c4444444-4444-4444-8444-444444444444` | `CREW-004` | Kepler | MISSION_SPECIALIST | ARTEMIS-III | LUNAR_SURFACE | `ACTIVE` |
| `c5555555-5555-4555-8555-555555555555` | `CREW-005` | Newton | FLIGHT_ENGINEER | ISS-EXP-72 | MICROGRAVITY | `ACTIVE` |
| `c6666666-6666-4666-8666-666666666666` | `CREW-006` | Pioneer | MISSION_SPECIALIST | ARTEMIS-II | EARTH_1G | `RETIRED` |

---

## Physiological Readings Summary

Each crew member has **80 timestamped readings** spanning 48 hours (every 3 hours) across 5 indicators:
- **`heart_rate`** (`bpm`): Resting (58–70 bpm), operational (65–85 bpm), and exercise peaks (105–130 bpm).
- **`blood_pressure_systolic`** (`mmHg`): Resting 110–120 mmHg, exercise 130–140 mmHg.
- **`blood_pressure_diastolic`** (`mmHg`): Resting 70–78 mmHg, exercise 80–86 mmHg.
- **`spo2`** (`%`): 97.0%–99.5% oxygen saturation.
- **`body_temperature`** (`degC`): 36.5°C–37.4°C core temperature.

---

## How to Seed the Local Database

Ensure your local PostgreSQL instance or Docker container is running:
```bash
# Start PostgreSQL via Docker Compose:
docker compose up -d db

# Run the seed script:
python test/seed_test_db.py

# To reset and wipe existing test data before re-seeding:
python test/seed_test_db.py --clean
```

---

## Test User Accounts & Credentials

| Username | Password | Role | Assigned Scope | Dashboard Use Case |
| :--- | :--- | :--- | :--- | :--- |
| `crew_astra` | `Password123!` | `CREW_MEMBER` | `CREW-001` (`c1111111-...`) | Test personal astronaut dashboard |
| `crew_vanguard` | `Password123!` | `CREW_MEMBER` | `CREW-002` (`c2222222-...`) | Test multi-crew isolation & switching |
| `crew_caduceus` | `Password123!` | `CREW_MEMBER` | `CREW-003` (`c3333333-...`) | Test medical officer view |
| `flight_surgeon` | `Password123!` | `FLIGHT_SURGEON` | All 6 crew members | Test flight surgeon multi-crew telemetry |
| `admin` | `Admin123!` | `ADMIN` | System Configuration | Test administrative management |

---

## Connecting the Frontend Dashboard to the Backend APIs

### 1. Authenticate to obtain a JWT token
```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=crew_astra&password=Password123!
```

### 2. Verify current user profile
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### 3. Fetch physiological readings for charts
```http
GET /api/v1/measurements?crew_id=c1111111-1111-4111-8111-111111111111&measurement_type=heart_rate&limit=50
Authorization: Bearer <access_token>
```

### 4. Fetch computed longitudinal statistics & baselines
```http
GET /api/v1/trends/heart_rate?crew_id=c1111111-1111-4111-8111-111111111111
Authorization: Bearer <access_token>
```
Returns count, min, max, arithmetic mean, median, standard deviation, and data freshness metrics.
