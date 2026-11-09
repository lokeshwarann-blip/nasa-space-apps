"""Test fixtures and loader utilities for test crew data and health readings.

This module provides programmatic access to the mock test crew dataset and
simulated biometric readings. It is strictly intended for isolated local development,
unit tests, and integration test harnesses. It is never loaded into production environments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import uuid

_CURRENT_DIR = Path(__file__).resolve().parent
_CREW_FILE = _CURRENT_DIR / "crew_members.json"
_READINGS_FILE = _CURRENT_DIR / "health_readings.json"

# Standard test user credentials for local test authentication
TEST_USERS = [
    {
        "username": "crew_astra",
        "password": "Password123!",
        "role": "CREW_MEMBER",
        "crew_member_id": "c1111111-1111-4111-8111-111111111111",
        "assigned_crew_ids": [],
    },
    {
        "username": "crew_vanguard",
        "password": "Password123!",
        "role": "CREW_MEMBER",
        "crew_member_id": "c2222222-2222-4222-8222-222222222222",
        "assigned_crew_ids": [],
    },
    {
        "username": "crew_caduceus",
        "password": "Password123!",
        "role": "CREW_MEMBER",
        "crew_member_id": "c3333333-3333-4333-8333-333333333333",
        "assigned_crew_ids": [],
    },
    {
        "username": "flight_surgeon",
        "password": "Password123!",
        "role": "FLIGHT_SURGEON",
        "crew_member_id": None,
        "assigned_crew_ids": [
            "c1111111-1111-4111-8111-111111111111",
            "c2222222-2222-4222-8222-222222222222",
            "c3333333-3333-4333-8333-333333333333",
            "c4444444-4444-4444-8444-444444444444",
            "c5555555-5555-4555-8555-555555555555",
            "c6666666-6666-4666-8666-666666666666",
        ],
    },
    {
        "username": "admin",
        "password": "Admin123!",
        "role": "ADMIN",
        "crew_member_id": None,
        "assigned_crew_ids": [],
    },
]


def load_test_crew_data() -> list[dict[str, Any]]:
    """Loads raw test crew member dictionaries from crew_members.json."""
    with open(_CREW_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_test_crew_by_id(crew_id: str) -> dict[str, Any] | None:
    """Finds a test crew member record by pseudonymous crew identifier (e.g., 'CREW-001')."""
    records = load_test_crew_data()
    for record in records:
        if record["crew_id"] == crew_id:
            return record
    return None


def get_test_crew_by_uuid(member_uuid: str | uuid.UUID) -> dict[str, Any] | None:
    """Finds a test crew member record by UUID."""
    target_str = str(member_uuid)
    records = load_test_crew_data()
    for record in records:
        if record["id"] == target_str:
            return record
    return None


def get_active_test_crew() -> list[dict[str, Any]]:
    """Returns only active test crew members."""
    return [r for r in load_test_crew_data() if r.get("status") == "ACTIVE"]


def load_test_health_readings() -> list[dict[str, Any]]:
    """Loads physiological health readings from health_readings.json."""
    with open(_READINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_health_readings_by_crew_id(crew_id: str) -> list[dict[str, Any]]:
    """Filters health readings for a specific crew identifier (e.g., 'CREW-001')."""
    readings = load_test_health_readings()
    return [r for r in readings if r.get("crew_id") == crew_id]


def get_health_readings_by_type(measurement_type: str, crew_id: str | None = None) -> list[dict[str, Any]]:
    """Filters health readings by measurement type (e.g., 'heart_rate', 'spo2')."""
    readings = load_test_health_readings()
    result = [r for r in readings if r.get("measurement_type") == measurement_type]
    if crew_id is not None:
        result = [r for r in result if r.get("crew_id") == crew_id]
    return result


# Pre-cached quick reference mappings for test harnesses
TEST_CREW_1 = get_test_crew_by_id("CREW-001")
TEST_CREW_2 = get_test_crew_by_id("CREW-002")
TEST_CREW_3 = get_test_crew_by_id("CREW-003")
