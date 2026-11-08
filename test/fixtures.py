"""Test fixtures and loader utilities for test crew data.

This module provides programmatic access to the mock test crew dataset.
It is strictly intended for isolated local development, unit tests, and
integration test harnesses. It is never loaded into production environments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import uuid

_CURRENT_DIR = Path(__file__).resolve().parent
_DATA_FILE = _CURRENT_DIR / "crew_members.json"


def load_test_crew_data() -> list[dict[str, Any]]:
    """Loads raw test crew member dictionaries from crew_members.json."""
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
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


# Pre-cached quick reference mappings for test harnesses
TEST_CREW_1 = get_test_crew_by_id("CREW-001")
TEST_CREW_2 = get_test_crew_by_id("CREW-002")
TEST_CREW_3 = get_test_crew_by_id("CREW-003")
