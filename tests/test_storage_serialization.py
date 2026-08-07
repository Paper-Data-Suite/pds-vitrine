from __future__ import annotations

import pytest

from vitrine.storage import VitrineCurrentState, VitrineStorageValidationError
from vitrine.storage.errors import VitrineStorageReadError
from vitrine.storage.serialization import (
    current_state_from_dict,
    current_state_to_dict,
    serialize_storage,
    strict_json_loads,
)


def test_storage_json_is_canonical_and_round_trips_exactly() -> None:
    current = VitrineCurrentState(3, "a" * 64)
    data = serialize_storage(current)
    assert data.endswith(b"\n")
    assert not data.endswith(b"\n\n")
    assert strict_json_loads(data) == current_state_to_dict(current)
    assert current_state_from_dict(strict_json_loads(data)) == current


def test_storage_decoder_rejects_duplicate_keys() -> None:
    with pytest.raises(VitrineStorageReadError):
        strict_json_loads(b'{"schema_version":"1","schema_version":"1"}\n')


def test_storage_metadata_rejects_unknown_fields() -> None:
    with pytest.raises(VitrineStorageValidationError):
        current_state_from_dict(
            {
                "schema_version": "1",
                "record_type": "vitrine_current_state",
                "state_revision": 1,
                "state_sha256": "a" * 64,
                "unexpected": True,
            }
        )
