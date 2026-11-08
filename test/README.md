# Test Crew Dataset & Fixtures

This folder contains mock test crew data strictly for local development, integration test harnesses, and automated unit testing.

---

> [!IMPORTANT]
> **Privacy & Medical Data Policy:**  
> - **Synthetic / Non-PHI:** All records in this folder use pseudonymous identifiers (`CREW-001` through `CREW-006`) with fictional callsigns, roles, and baseline estimates.
> - **Zero Real Astronaut Data:** This data does not represent any real astronaut, NASA mission personnel, or private flight passenger.
> - **Isolation:** This data is strictly restricted to this `test/` directory and is never loaded into production databases, clinical rules, or deployment seeds.

---

## Files in this Directory

| File | Format | Description |
| :--- | :--- | :--- |
| `crew_members.json` | JSON | Complete structured test crew profiles conforming to `CrewMemberRead` / `CrewMemberCreate` schemas. |
| `crew_members.csv` | CSV | Tabular representation for spreadsheet inspection, statistical analysis, or bulk test imports. |
| `fixtures.py` | Python | Helper utilities (`load_test_crew_data()`, `get_test_crew_by_id()`, `get_active_test_crew()`) for test harnesses. |

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

## Programmatic Usage in Python

```python
from test.fixtures import load_test_crew_data, get_test_crew_by_id

# Load all records
crew_list = load_test_crew_data()
print(f"Loaded {len(crew_list)} test crew members.")

# Retrieve specific test subject
commander = get_test_crew_by_id("CREW-001")
print(commander["profile_metadata"]["callsign"])  # "Astra-Lead"
```
