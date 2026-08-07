"""Strict canonical JSON conversion for Vitrine storage metadata."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from vitrine.models.common import canonical_datetime_text, require_identifier
from vitrine.models.conversion import JsonValue
from vitrine.models.serialization import strict_json_loads as runtime_strict_json_loads

from .errors import VitrineStorageReadError, VitrineStorageValidationError
from .models import (
    VITRINE_STORAGE_SCHEMA_VERSION,
    VitrineCurrentState,
    VitrineRecordRevision,
    VitrineRecordRevisionRef,
    VitrineStateRevision,
    VitrineStorageRecordKey,
    VitrineStoreMarker,
)


def canonical_json_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise VitrineStorageValidationError(
            f"could not serialize storage JSON: {error}"
        ) from error


def strict_json_loads(data: bytes) -> object:
    try:
        return runtime_strict_json_loads(data)
    except Exception as error:
        raise VitrineStorageReadError(f"invalid storage JSON: {error}") from error


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VitrineStorageValidationError(f"{label} must be an object.")
    if any(not isinstance(key, str) for key in value):
        raise VitrineStorageValidationError(f"{label} keys must be strings.")
    return cast(Mapping[str, object], value)


def _keys(
    value: Mapping[str, object], label: str, expected: tuple[str, ...]
) -> None:
    actual = set(value)
    expected_set = set(expected)
    unknown = sorted(actual - expected_set)
    missing = sorted(expected_set - actual)
    if unknown:
        raise VitrineStorageValidationError(
            f"{label} contains unknown key(s): {', '.join(unknown)}."
        )
    if missing:
        raise VitrineStorageValidationError(
            f"{label} is missing key(s): {', '.join(missing)}."
        )


def key_to_dict(value: VitrineStorageRecordKey) -> dict[str, JsonValue]:
    return {
        "identity_segments": list(value.identity_segments),
        "record_type": value.record_type,
    }


def key_from_dict(value: object) -> VitrineStorageRecordKey:
    data = _mapping(value, "storage record key")
    _keys(data, "storage record key", ("record_type", "identity_segments"))
    record_type = data["record_type"]
    segments = data["identity_segments"]
    if not isinstance(record_type, str):
        raise VitrineStorageValidationError("storage record key record_type must be a string.")
    if not isinstance(segments, list) or any(not isinstance(item, str) for item in segments):
        raise VitrineStorageValidationError(
            "storage record key identity_segments must be an array of strings."
        )
    return VitrineStorageRecordKey(record_type, tuple(cast(list[str], segments)))


def ref_to_dict(value: VitrineRecordRevisionRef) -> dict[str, JsonValue]:
    return {
        "key": key_to_dict(value.key),
        "sha256": value.sha256,
        "storage_revision": value.storage_revision,
    }


def ref_from_dict(value: object) -> VitrineRecordRevisionRef:
    data = _mapping(value, "record revision reference")
    _keys(data, "record revision reference", ("key", "storage_revision", "sha256"))
    return VitrineRecordRevisionRef(
        key=key_from_dict(data["key"]),
        storage_revision=cast(int, data["storage_revision"]),
        sha256=cast(str, data["sha256"]),
    )


def store_marker_to_dict(value: VitrineStoreMarker) -> dict[str, JsonValue]:
    return {
        "module_id": value.module_id,
        "record_type": value.record_type,
        "runtime_record_schema_version": value.runtime_record_schema_version,
        "schema_version": value.schema_version,
    }


def store_marker_from_dict(value: object) -> VitrineStoreMarker:
    data = _mapping(value, "store marker")
    _keys(
        data,
        "store marker",
        ("schema_version", "record_type", "module_id", "runtime_record_schema_version"),
    )
    return VitrineStoreMarker(
        schema_version=cast(str, data["schema_version"]),
        record_type=cast(Any, data["record_type"]),
        module_id=cast(Any, data["module_id"]),
        runtime_record_schema_version=cast(str, data["runtime_record_schema_version"]),
    )


def record_revision_to_dict(value: VitrineRecordRevision) -> dict[str, JsonValue]:
    return {
        "body": value.body,
        "key": key_to_dict(value.key),
        "record_schema_version": value.record_schema_version,
        "record_type": value.record_type,
        "schema_version": value.schema_version,
        "storage_revision": value.storage_revision,
    }


def record_revision_from_dict(value: object) -> VitrineRecordRevision:
    data = _mapping(value, "record revision")
    _keys(
        data,
        "record revision",
        (
            "schema_version",
            "record_type",
            "key",
            "storage_revision",
            "record_schema_version",
            "body",
        ),
    )
    body = data["body"]
    if not isinstance(body, dict) or any(not isinstance(key, str) for key in body):
        raise VitrineStorageValidationError("record revision body must be a JSON object.")
    return VitrineRecordRevision(
        key=key_from_dict(data["key"]),
        storage_revision=cast(int, data["storage_revision"]),
        record_schema_version=cast(str, data["record_schema_version"]),
        body=cast(dict[str, JsonValue], body),
        schema_version=cast(str, data["schema_version"]),
        record_type=cast(Any, data["record_type"]),
    )


def state_revision_to_dict(value: VitrineStateRevision) -> dict[str, JsonValue]:
    return {
        "previous_state_revision": value.previous_state_revision,
        "previous_state_sha256": value.previous_state_sha256,
        "record_type": value.record_type,
        "records": [ref_to_dict(item) for item in value.records],
        "schema_version": value.schema_version,
        "state_revision": value.state_revision,
    }


def state_revision_from_dict(value: object) -> VitrineStateRevision:
    data = _mapping(value, "state revision")
    _keys(
        data,
        "state revision",
        (
            "schema_version",
            "record_type",
            "state_revision",
            "previous_state_revision",
            "previous_state_sha256",
            "records",
        ),
    )
    raw_records = data["records"]
    if not isinstance(raw_records, list):
        raise VitrineStorageValidationError("state revision records must be an array.")
    previous_revision = data["previous_state_revision"]
    previous_sha = data["previous_state_sha256"]
    if previous_revision is not None and (
        isinstance(previous_revision, bool) or not isinstance(previous_revision, int)
    ):
        raise VitrineStorageValidationError(
            "previous_state_revision must be an integer or null."
        )
    if previous_sha is not None and not isinstance(previous_sha, str):
        raise VitrineStorageValidationError(
            "previous_state_sha256 must be a string or null."
        )
    return VitrineStateRevision(
        state_revision=cast(int, data["state_revision"]),
        previous_state_revision=previous_revision,
        previous_state_sha256=previous_sha,
        records=tuple(ref_from_dict(item) for item in raw_records),
        schema_version=cast(str, data["schema_version"]),
        record_type=cast(Any, data["record_type"]),
    )


def current_state_to_dict(value: VitrineCurrentState) -> dict[str, JsonValue]:
    return {
        "record_type": value.record_type,
        "schema_version": value.schema_version,
        "state_revision": value.state_revision,
        "state_sha256": value.state_sha256,
    }


def current_state_from_dict(value: object) -> VitrineCurrentState:
    data = _mapping(value, "current state")
    _keys(
        data,
        "current state",
        ("schema_version", "record_type", "state_revision", "state_sha256"),
    )
    return VitrineCurrentState(
        state_revision=cast(int, data["state_revision"]),
        state_sha256=cast(str, data["state_sha256"]),
        schema_version=cast(str, data["schema_version"]),
        record_type=cast(Any, data["record_type"]),
    )


def lock_json_bytes(
    *,
    lock_id: str,
    purpose: str,
    expected_state_revision: int | None,
    acquired_at: datetime,
) -> bytes:
    return canonical_json_bytes(
        {
            "acquired_at": canonical_datetime_text(acquired_at),
            "expected_state_revision": expected_state_revision,
            "lock_id": require_identifier(lock_id, "lock_id"),
            "purpose": purpose,
            "record_type": "vitrine_storage_lock",
            "schema_version": VITRINE_STORAGE_SCHEMA_VERSION,
        }
    )


def serialize_storage(value: object) -> bytes:
    if isinstance(value, VitrineStoreMarker):
        return canonical_json_bytes(store_marker_to_dict(value))
    if isinstance(value, VitrineRecordRevision):
        return canonical_json_bytes(record_revision_to_dict(value))
    if isinstance(value, VitrineStateRevision):
        return canonical_json_bytes(state_revision_to_dict(value))
    if isinstance(value, VitrineCurrentState):
        return canonical_json_bytes(current_state_to_dict(value))
    raise VitrineStorageValidationError(
        f"unsupported storage value {type(value).__name__}."
    )
