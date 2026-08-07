"""Immutable metadata models for Vitrine canonical storage."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from vitrine.models.common import SCHEMA_VERSION as RUNTIME_RECORD_SCHEMA_VERSION
from vitrine.models.common import (
    require_aware_datetime,
    require_identifier,
    require_sha256,
)
from vitrine.models.conversion import JsonValue
from vitrine.record_registry import descriptor_for_record_type

from .errors import VitrineStorageValidationError

if TYPE_CHECKING:
    from vitrine.models.graph import VitrineRecordGraph

VITRINE_STORAGE_SCHEMA_VERSION = "1"
VITRINE_CATALOG_SCHEMA_VERSION = 1
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise VitrineStorageValidationError(
            f"{name} must be a positive non-Boolean integer."
        )
    return value


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise VitrineStorageValidationError(
            f"{name} must be a lowercase SHA-256 digest."
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class VitrineStorageRecordKey:
    record_type: str
    identity_segments: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            descriptor = descriptor_for_record_type(self.record_type)
        except ValueError as error:
            raise VitrineStorageValidationError(str(error)) from error
        segments = tuple(self.identity_segments)
        if len(segments) != len(descriptor.identity_fields):
            raise VitrineStorageValidationError(
                f"{self.record_type} requires {len(descriptor.identity_fields)} "
                "identity segment(s)."
            )
        integer_fields = set(descriptor.integer_identity_fields)
        normalized: list[str] = []
        for field_name, segment in zip(descriptor.identity_fields, segments, strict=True):
            if not isinstance(segment, str):
                raise VitrineStorageValidationError(
                    f"identity segment {field_name} must be a string."
                )
            if field_name in integer_fields:
                if not segment.isdigit() or segment.startswith("0"):
                    raise VitrineStorageValidationError(
                        f"identity segment {field_name} must be canonical positive decimal text."
                    )
                _positive(int(segment), field_name)
                normalized.append(segment)
            else:
                try:
                    normalized.append(require_identifier(segment, field_name))
                except ValueError as error:
                    raise VitrineStorageValidationError(str(error)) from error
        object.__setattr__(self, "identity_segments", tuple(normalized))


@dataclass(frozen=True, slots=True)
class VitrineStoreMarker:
    schema_version: str = VITRINE_STORAGE_SCHEMA_VERSION
    record_type: Literal["vitrine_store"] = "vitrine_store"
    module_id: Literal["vitrine"] = "vitrine"
    runtime_record_schema_version: str = RUNTIME_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            self.schema_version != VITRINE_STORAGE_SCHEMA_VERSION
            or self.record_type != "vitrine_store"
            or self.module_id != "vitrine"
            or self.runtime_record_schema_version != RUNTIME_RECORD_SCHEMA_VERSION
        ):
            raise VitrineStorageValidationError("unsupported Vitrine store marker schema.")


@dataclass(frozen=True, slots=True)
class VitrineRecordRevision:
    key: VitrineStorageRecordKey
    storage_revision: int
    record_schema_version: str
    body: dict[str, JsonValue]
    schema_version: str = VITRINE_STORAGE_SCHEMA_VERSION
    record_type: Literal["vitrine_record_revision"] = "vitrine_record_revision"

    def __post_init__(self) -> None:
        if (
            self.schema_version != VITRINE_STORAGE_SCHEMA_VERSION
            or self.record_type != "vitrine_record_revision"
        ):
            raise VitrineStorageValidationError("unsupported record revision schema.")
        if not isinstance(self.key, VitrineStorageRecordKey):
            raise VitrineStorageValidationError("key must be VitrineStorageRecordKey.")
        _positive(self.storage_revision, "storage_revision")
        if self.record_schema_version != RUNTIME_RECORD_SCHEMA_VERSION:
            raise VitrineStorageValidationError("unsupported runtime record schema version.")
        if not isinstance(self.body, dict):
            raise VitrineStorageValidationError("body must be a JSON object.")


@dataclass(frozen=True, slots=True, order=True)
class VitrineRecordRevisionRef:
    key: VitrineStorageRecordKey
    storage_revision: int
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, VitrineStorageRecordKey):
            raise VitrineStorageValidationError("key must be VitrineStorageRecordKey.")
        _positive(self.storage_revision, "storage_revision")
        _digest(self.sha256, "sha256")


@dataclass(frozen=True, slots=True)
class VitrineStateRevision:
    state_revision: int
    previous_state_revision: int | None
    previous_state_sha256: str | None
    records: tuple[VitrineRecordRevisionRef, ...]
    schema_version: str = VITRINE_STORAGE_SCHEMA_VERSION
    record_type: Literal["vitrine_state_revision"] = "vitrine_state_revision"

    def __post_init__(self) -> None:
        revision = _positive(self.state_revision, "state_revision")
        if (
            self.schema_version != VITRINE_STORAGE_SCHEMA_VERSION
            or self.record_type != "vitrine_state_revision"
        ):
            raise VitrineStorageValidationError("unsupported state revision schema.")
        if revision == 1:
            if self.previous_state_revision is not None or self.previous_state_sha256 is not None:
                raise VitrineStorageValidationError(
                    "initial state revision must not have a predecessor."
                )
        else:
            if self.previous_state_revision != revision - 1:
                raise VitrineStorageValidationError(
                    "state predecessor revision must be contiguous."
                )
            _digest(self.previous_state_sha256, "previous_state_sha256")
        records = tuple(self.records)
        if tuple(sorted(records, key=lambda item: item.key)) != records:
            raise VitrineStorageValidationError(
                "state record references must be deterministically ordered."
            )
        keys = tuple(item.key for item in records)
        if len(keys) != len(set(keys)):
            raise VitrineStorageValidationError("state record keys must be unique.")
        object.__setattr__(self, "records", records)


@dataclass(frozen=True, slots=True)
class VitrineCurrentState:
    state_revision: int
    state_sha256: str
    schema_version: str = VITRINE_STORAGE_SCHEMA_VERSION
    record_type: Literal["vitrine_current_state"] = "vitrine_current_state"

    def __post_init__(self) -> None:
        _positive(self.state_revision, "state_revision")
        _digest(self.state_sha256, "state_sha256")
        if (
            self.schema_version != VITRINE_STORAGE_SCHEMA_VERSION
            or self.record_type != "vitrine_current_state"
        ):
            raise VitrineStorageValidationError("unsupported current-state schema.")


@dataclass(frozen=True, slots=True)
class VitrineStorageCommitResult:
    state_revision: int
    state_sha256: str
    created_record_revisions: tuple[VitrineRecordRevisionRef, ...]
    no_op: bool = False


@dataclass(frozen=True, slots=True)
class VitrineLoadedRecordGraph:
    graph: VitrineRecordGraph
    state_revision: int
    state_sha256: str


@dataclass(frozen=True, slots=True)
class VitrineLockInspection:
    relative_path: str
    byte_size: int
    sha256: str
    purpose: str | None
    expected_state_revision: int | None
    acquired_at: datetime | None

    def __post_init__(self) -> None:
        require_sha256(self.sha256, "sha256")
        if self.acquired_at is not None:
            require_aware_datetime(self.acquired_at, "acquired_at")


@dataclass(frozen=True, slots=True)
class StorageIssue:
    code: str
    message: str
    relative_path: str | None = None
    record_type: str | None = None
    logical_identity: tuple[str, ...] = field(default_factory=tuple)
    state_revision: int | None = None
