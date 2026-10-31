"""Unit tests for offline sync hashing, schemas, and boundary validations."""
import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from src.modules.sync.schemas import (
    SyncBatchRequest,
    SyncEventItem,
)
from src.modules.sync.service import compute_payload_hash


def test_payload_hash_determinism():
    """Verifies that canonical JSON hashing is key-order independent and deterministic."""
    payload_a = {
        "measurement_type": "heart_rate",
        "value": 78.5,
        "unit": "bpm",
        "context": {"posture": "sitting", "rested": True},
    }
    payload_b = {
        "unit": "bpm",
        "context": {"rested": True, "posture": "sitting"},
        "value": 78.5,
        "measurement_type": "heart_rate",
    }
    hash_a = compute_payload_hash(payload_a)
    hash_b = compute_payload_hash(payload_b)
    assert hash_a == hash_b, "Hash must be identical regardless of dictionary key order!"

    # Modifying a value changes the hash
    payload_c = {**payload_a, "value": 79.0}
    assert compute_payload_hash(payload_c) != hash_a


def test_sync_batch_bounded_limits():
    """Verifies that sync batches enforce minimum 1 and maximum 100 events."""
    now = datetime.now(timezone.utc)
    event = SyncEventItem(
        client_event_id=uuid.uuid4(),
        crew_member_id=uuid.uuid4(),
        event_type="MEASUREMENT",
        schema_version="1.0",
        client_event_at=now,
        measured_at=now,
        payload={"measurement_type": "heart_rate", "value": 72.0, "unit": "bpm"},
    )

    # Empty batch rejected
    with pytest.raises(ValidationError):
        SyncBatchRequest(
            batch_id="BATCH-001",
            client_sync_at=now,
            events=[],
        )

    # Valid batch within limits
    batch = SyncBatchRequest(
        batch_id="BATCH-001",
        client_sync_at=now,
        events=[event],
    )
    assert len(batch.events) == 1

    # Oversized batch (> 100 events) rejected
    with pytest.raises(ValidationError):
        SyncBatchRequest(
            batch_id="BATCH-OVERSIZED",
            client_sync_at=now,
            events=[event] * 101,
        )

