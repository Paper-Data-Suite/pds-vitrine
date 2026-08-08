"""Strict reads and guarded commits for canonical workspace-scoped Vitrine state."""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from pds_core.workspace import inspect_workspace_root, resolve_workspace_root

from vitrine.identity_state import (
    collect_identity_state_issues,
    project_identity_state,
)
from vitrine.models import (
    VitrineRecord,
    VitrineRecordGraph,
    collect_record_graph_issues,
    record_from_dict,
    record_to_dict,
)
from vitrine.profile_state import (
    collect_profile_state_issues,
    project_profile_state,
)
from vitrine.record_registry import (
    RECORD_DESCRIPTORS,
    descriptor_for_record,
    descriptor_for_record_type,
    identity_segments_for_record,
)

from .errors import (
    VitrineStorageConflictError,
    VitrineStorageError,
    VitrineStorageGraphIntegrityError,
    VitrineStorageIntegrityError,
    VitrineStorageNotFoundError,
    VitrineStoragePartialSuccessError,
    VitrineStorageReadError,
    VitrineStorageValidationError,
    VitrineStorageWriteError,
)
from .models import (
    VitrineCurrentState,
    VitrineLoadedRecordGraph,
    VitrineLockInspection,
    VitrineRecordRevision,
    VitrineRecordRevisionRef,
    VitrineStateRevision,
    VitrineStorageCommitResult,
    VitrineStorageRecordKey,
    VitrineStoreMarker,
)
from .paths import (
    current_state_path,
    locks_root,
    record_revision_path,
    record_revisions_path,
    records_root,
    state_revision_path,
    state_revisions_path,
    state_root,
    store_marker_path,
    vitrine_root,
    write_lock_path,
)
from .serialization import (
    current_state_from_dict,
    lock_json_bytes,
    record_revision_from_dict,
    serialize_storage,
    state_revision_from_dict,
    store_marker_from_dict,
    strict_json_loads,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative(root: str | Path, path: Path) -> str:
    try:
        return path.relative_to(vitrine_root(root)).as_posix()
    except ValueError:
        return path.name


def _require_no_symlink_ancestors(root: str | Path, path: Path) -> None:
    workspace = resolve_workspace_root(root)
    base = vitrine_root(workspace)
    try:
        path.relative_to(base)
    except ValueError as error:
        raise VitrineStorageIntegrityError(
            "canonical path is outside the Vitrine workspace namespace."
        ) from error
    current = path
    while True:
        try:
            if current.is_symlink():
                raise VitrineStorageIntegrityError(
                    f"canonical path traverses a symlink: {_relative(workspace, current)}"
                )
        except OSError as error:
            raise VitrineStorageReadError(
                f"could not inspect canonical path {_relative(workspace, current)}: {error}"
            ) from error
        if current == base:
            break
        current = current.parent


def require_regular_nonsymlink_file(
    root: str | Path,
    path: Path,
    *,
    missing: bool = False,
) -> None:
    _require_no_symlink_ancestors(root, path)
    try:
        if path.is_symlink() or not path.is_file():
            if not path.exists() and not path.is_symlink() and missing:
                raise VitrineStorageNotFoundError(
                    f"canonical object not found: {_relative(root, path)}"
                )
            raise VitrineStorageIntegrityError(
                "canonical path is not a regular non-symlink file: "
                f"{_relative(root, path)}"
            )
    except VitrineStorageNotFoundError:
        raise
    except OSError as error:
        raise VitrineStorageReadError(
            f"could not inspect canonical path {_relative(root, path)}: {error}"
        ) from error


def read_canonical_bytes(
    root: str | Path, path: Path, *, missing: bool = False
) -> bytes:
    require_regular_nonsymlink_file(root, path, missing=missing)
    try:
        return path.read_bytes()
    except FileNotFoundError as error:
        raise VitrineStorageNotFoundError(
            f"canonical object not found: {_relative(root, path)}"
        ) from error
    except OSError as error:
        raise VitrineStorageReadError(
            f"could not read {_relative(root, path)}: {error}"
        ) from error


def _parse(
    root: str | Path,
    path: Path,
    parser: Any,
    *,
    missing: bool = False,
) -> tuple[Any, bytes]:
    data = read_canonical_bytes(root, path, missing=missing)
    try:
        return parser(strict_json_loads(data)), data
    except (VitrineStorageError, ValueError, TypeError) as error:
        raise VitrineStorageReadError(
            f"invalid canonical object at {_relative(root, path)}: {error}"
        ) from error


def key_for_record(record: VitrineRecord) -> VitrineStorageRecordKey:
    descriptor = descriptor_for_record(record)
    return VitrineStorageRecordKey(
        descriptor.record_type,
        identity_segments_for_record(record),
    )


def load_store_marker(root: str | Path) -> VitrineStoreMarker:
    marker, _ = _parse(root, store_marker_path(root), store_marker_from_dict, missing=True)
    return cast(VitrineStoreMarker, marker)


def load_record_revision(
    root: str | Path,
    key: VitrineStorageRecordKey,
    storage_revision: int,
) -> tuple[VitrineRecord, VitrineRecordRevision]:
    path = record_revision_path(root, key, storage_revision)
    envelope_raw, _ = _parse(root, path, record_revision_from_dict, missing=True)
    envelope = cast(VitrineRecordRevision, envelope_raw)
    if envelope.key != key or envelope.storage_revision != storage_revision:
        raise VitrineStorageIntegrityError(
            "record envelope identity disagrees with its canonical path."
        )
    try:
        record = record_from_dict(envelope.body)
        expected_key = key_for_record(record)
    except (ValueError, TypeError) as error:
        raise VitrineStorageIntegrityError(
            f"record body is invalid for {key.record_type}."
        ) from error
    if expected_key != key or record_to_dict(record) != envelope.body:
        raise VitrineStorageIntegrityError(
            "record body identity or exact round trip disagrees with its envelope."
        )
    if getattr(record, "schema_version", None) != envelope.record_schema_version:
        raise VitrineStorageIntegrityError(
            "record body schema version disagrees with its envelope."
        )
    return record, envelope


def _visible(root: str | Path, path: Path, description: str) -> tuple[Path, ...]:
    try:
        _require_no_symlink_ancestors(root, path)
        entries = tuple(path.iterdir())
    except FileNotFoundError:
        return ()
    except OSError as error:
        raise VitrineStorageReadError(
            f"could not enumerate {description} {_relative(root, path)}: {error}"
        ) from error
    return tuple(
        sorted((item for item in entries if not item.name.startswith(".")), key=lambda p: p.name)
    )


def list_record_revisions(
    root: str | Path, key: VitrineStorageRecordKey
) -> tuple[int, ...]:
    result: list[int] = []
    for path in _visible(root, record_revisions_path(root, key), "record revisions"):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix != ".json"
            or not path.stem.isdigit()
            or path.stem.startswith("0")
        ):
            raise VitrineStorageIntegrityError(
                f"unexpected record revision entry: {_relative(root, path)}"
            )
        revision = int(path.stem)
        load_record_revision(root, key, revision)
        result.append(revision)
    return tuple(sorted(result))


def _walk_record_identity_dirs(
    root: str | Path,
    record_type: str,
    current: Path,
    depth: int,
    segments: tuple[str, ...],
) -> list[VitrineStorageRecordKey]:
    descriptor = descriptor_for_record_type(record_type)
    if depth == len(descriptor.identity_fields):
        children = _visible(root, current, "record identity")
        if tuple(item.name for item in children) != ("revisions",):
            raise VitrineStorageIntegrityError(
                f"unexpected record identity contents: {_relative(root, current)}"
            )
        key = VitrineStorageRecordKey(record_type, segments)
        revisions = list_record_revisions(root, key)
        if not revisions:
            raise VitrineStorageIntegrityError(
                f"record identity has no revisions: {_relative(root, current)}"
            )
        return [key]

    result: list[VitrineStorageRecordKey] = []
    for child in _visible(root, current, "record identity segment"):
        if child.is_symlink() or not child.is_dir():
            raise VitrineStorageIntegrityError(
                f"unexpected record identity entry: {_relative(root, child)}"
            )
        result.extend(
            _walk_record_identity_dirs(
                root,
                record_type,
                child,
                depth + 1,
                (*segments, child.name),
            )
        )
    return result


def list_record_keys(root: str | Path) -> tuple[VitrineStorageRecordKey, ...]:
    result: list[VitrineStorageRecordKey] = []
    for type_path in _visible(root, records_root(root), "record types"):
        if type_path.is_symlink() or not type_path.is_dir():
            raise VitrineStorageIntegrityError(
                f"unexpected record-type entry: {_relative(root, type_path)}"
            )
        try:
            descriptor_for_record_type(type_path.name)
        except ValueError as error:
            raise VitrineStorageIntegrityError(
                f"unexpected record type directory: {type_path.name}"
            ) from error
        result.extend(
            _walk_record_identity_dirs(root, type_path.name, type_path, 0, ())
        )
    return tuple(sorted(result))


def _graph_descriptors() -> tuple[Any, ...]:
    return tuple(
        descriptor
        for descriptor in RECORD_DESCRIPTORS
        if descriptor.graph_collection is not None
    )


def _records_to_graph(records: Iterable[VitrineRecord]) -> VitrineRecordGraph:
    descriptors = _graph_descriptors()
    collections: dict[str, list[VitrineRecord]] = {
        cast(str, descriptor.graph_collection): [] for descriptor in descriptors
    }
    for record in records:
        descriptor = descriptor_for_record(record)
        if descriptor.graph_collection is None:
            continue
        collections[descriptor.graph_collection].append(record)
    kwargs = {
        cast(str, descriptor.graph_collection): tuple(
            sorted(
                collections[cast(str, descriptor.graph_collection)],
                key=lambda item: identity_segments_for_record(item),
            )
        )
        for descriptor in descriptors
    }
    return VitrineRecordGraph(**cast(Any, kwargs))


def _records_by_key(
    graph: VitrineRecordGraph,
) -> dict[VitrineStorageRecordKey, VitrineRecord]:
    return {
        key_for_record(record): record
        for descriptor in _graph_descriptors()
        for record in getattr(graph, cast(str, descriptor.graph_collection))
    }


def _records_by_key_from_records(
    records: Iterable[VitrineRecord],
) -> dict[VitrineStorageRecordKey, VitrineRecord]:
    return {key_for_record(record): record for record in records}


def _validate_state_records(
    records: Iterable[VitrineRecord],
    *,
    message: str,
) -> VitrineRecordGraph:
    values = tuple(records)
    graph = _records_to_graph(values)
    graph_issues = collect_record_graph_issues(graph)
    if graph_issues:
        raise VitrineStorageGraphIntegrityError(message, issues=graph_issues)
    identity_state = project_identity_state(values)
    identity_issues = tuple(
        issue
        for issue in collect_identity_state_issues(identity_state)
        if issue.code != "identity.duplicate_active_association"
    )
    if identity_issues:
        raise VitrineStorageGraphIntegrityError(
            "persisted Portfolio Subject identity state is invalid.",
            issues=identity_issues,
        )
    profile_state = project_profile_state(values)
    profile_issues = collect_profile_state_issues(profile_state)
    if profile_issues:
        raise VitrineStorageGraphIntegrityError(
            "persisted Portfolio Profile state is invalid.",
            issues=profile_issues,
        )
    return graph


def _load_state_envelope(
    root: str | Path, state_revision: int
) -> tuple[VitrineStateRevision, bytes]:
    raw, data = _parse(
        root,
        state_revision_path(root, state_revision),
        state_revision_from_dict,
        missing=True,
    )
    value = cast(VitrineStateRevision, raw)
    if value.state_revision != state_revision:
        raise VitrineStorageIntegrityError(
            "state revision identity disagrees with its canonical path."
        )
    return value, data


def _load_state_chain(
    root: str | Path, state_revision: int
) -> tuple[VitrineStateRevision, bytes]:
    target, target_bytes = _load_state_envelope(root, state_revision)
    child = target
    child_refs = {item.key: item for item in child.records}
    for expected in range(state_revision - 1, 0, -1):
        predecessor, predecessor_bytes = _load_state_envelope(root, expected)
        if child.previous_state_revision != expected:
            raise VitrineStorageIntegrityError("state predecessor revision mismatch.")
        if child.previous_state_sha256 != _sha(predecessor_bytes):
            raise VitrineStorageIntegrityError("state predecessor digest mismatch.")
        predecessor_refs = {item.key: item for item in predecessor.records}
        if not set(predecessor_refs).issubset(child_refs):
            raise VitrineStorageIntegrityError(
                "accepted state history removed a previously selected record key."
            )
        for key, reference in predecessor_refs.items():
            if child_refs[key] != reference:
                raise VitrineStorageIntegrityError(
                    "accepted state history replaced a previously selected record revision."
                )
        child = predecessor
        child_refs = predecessor_refs
    return target, target_bytes


def _load_state_records(
    root: str | Path, state: VitrineStateRevision
) -> tuple[VitrineRecord, ...]:
    records: list[VitrineRecord] = []
    for reference in state.records:
        path = record_revision_path(
            root, reference.key, reference.storage_revision
        )
        if _sha(read_canonical_bytes(root, path, missing=True)) != reference.sha256:
            raise VitrineStorageIntegrityError(
                "record revision digest mismatch for "
                f"{reference.key.record_type}:"
                f"{'/'.join(reference.key.identity_segments)}."
            )
        record, _ = load_record_revision(
            root, reference.key, reference.storage_revision
        )
        records.append(record)
    return tuple(records)


def load_state_records(
    root: str | Path, state_revision: int
) -> tuple[VitrineRecord, ...]:
    """Load every canonical record selected by one exact state revision."""
    state, _ = _load_state_chain(root, state_revision)
    records = _load_state_records(root, state)
    _validate_state_records(
        records,
        message="persisted state graph is invalid.",
    )
    return records


def load_state_revision(
    root: str | Path, state_revision: int
) -> tuple[VitrineStateRevision, str, VitrineRecordGraph]:
    value, data = _load_state_chain(root, state_revision)
    records = _load_state_records(root, value)
    graph = _validate_state_records(
        records,
        message="persisted state graph is invalid.",
    )
    return value, _sha(data), graph


def list_state_revisions(root: str | Path) -> tuple[int, ...]:
    result: list[int] = []
    for path in _visible(root, state_revisions_path(root), "state revisions"):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix != ".json"
            or not path.stem.isdigit()
            or path.stem.startswith("0")
        ):
            raise VitrineStorageIntegrityError(
                f"unexpected state revision entry: {_relative(root, path)}"
            )
        revision = int(path.stem)
        load_state_revision(root, revision)
        result.append(revision)
    return tuple(sorted(result))


def load_current_state(root: str | Path) -> VitrineCurrentState:
    raw, _ = _parse(root, current_state_path(root), current_state_from_dict, missing=True)
    current = cast(VitrineCurrentState, raw)
    _, digest, _ = load_state_revision(root, current.state_revision)
    if digest != current.state_sha256:
        raise VitrineStorageIntegrityError("current-state digest mismatch.")
    return current


def load_current_record_graph(root: str | Path) -> VitrineLoadedRecordGraph:
    load_store_marker(root)
    current = load_current_state(root)
    _, digest, graph = load_state_revision(root, current.state_revision)
    if digest != current.state_sha256:
        raise VitrineStorageIntegrityError("current-state digest mismatch.")
    return VitrineLoadedRecordGraph(graph, current.state_revision, digest)


def load_current_records(root: str | Path) -> tuple[VitrineRecord, ...]:
    """Load every canonical record selected by current.json."""
    load_store_marker(root)
    current = load_current_state(root)
    return load_state_records(root, current.state_revision)


def load_current_record(
    root: str | Path, key: VitrineStorageRecordKey
) -> tuple[VitrineRecord, VitrineRecordRevision]:
    current = load_current_state(root)
    state, _, _ = load_state_revision(root, current.state_revision)
    reference = next((item for item in state.records if item.key == key), None)
    if reference is None:
        raise VitrineStorageNotFoundError(
            f"record is not selected by current state: {key.record_type}:"
            f"{'/'.join(key.identity_segments)}"
        )
    return load_record_revision(root, key, reference.storage_revision)


def _validate_canonical_write_history(
    root: str | Path,
    current_state: VitrineStateRevision | None,
) -> None:
    state_revisions = list_state_revisions(root)
    record_keys = list_record_keys(root)
    marker_exists = store_marker_path(root).exists()
    current_exists = current_state_path(root).exists()

    if current_state is None:
        if marker_exists or current_exists or state_revisions or record_keys:
            raise VitrineStorageIntegrityError(
                "orphan or contradictory canonical history blocks initial creation."
            )
        return

    if not marker_exists or not current_exists:
        raise VitrineStorageIntegrityError(
            "store marker/current pointer presence is contradictory."
        )
    load_store_marker(root)
    expected_states = tuple(range(1, current_state.state_revision + 1))
    if state_revisions != expected_states:
        raise VitrineStorageIntegrityError(
            "state history is noncontiguous or contains orphan revisions."
        )
    selected = {item.key: item for item in current_state.records}
    if record_keys != tuple(sorted(selected)):
        raise VitrineStorageIntegrityError(
            "canonical record identities disagree with current state."
        )
    for key in record_keys:
        revisions = list_record_revisions(root, key)
        if revisions != (1,):
            raise VitrineStorageIntegrityError(
                "current storage schema permits exactly one storage revision per "
                f"semantic key; found {revisions!r} for {key.record_type}:"
                f"{'/'.join(key.identity_segments)}."
            )
        if selected[key].storage_revision != 1:
            raise VitrineStorageIntegrityError(
                "current state selects an unsupported storage revision."
            )


def _fsync_directory_if_supported(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive(root: str | Path, path: Path, data: bytes) -> None:
    created = False
    file_synced = False
    try:
        _require_no_symlink_ancestors(root, path)
        with path.open("xb") as target:
            created = True
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
            file_synced = True
        _fsync_directory_if_supported(path.parent)
    except FileExistsError as error:
        raise VitrineStorageConflictError(
            f"immutable canonical file already exists: {_relative(root, path)}"
        ) from error
    except OSError as error:
        if created and not file_synced:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                raise VitrineStoragePartialSuccessError(
                    "exclusive write failed and the partial file could not be removed.",
                    durable_paths=(_relative(root, path),),
                    pointer_published=False,
                    state_revision=None,
                    state_sha256=None,
                ) from cleanup_error
        if created and file_synced:
            raise VitrineStoragePartialSuccessError(
                "canonical bytes were synchronized but directory durability could not be confirmed.",
                durable_paths=(_relative(root, path),),
                pointer_published=False,
                state_revision=None,
                state_sha256=None,
            ) from error
        raise VitrineStorageWriteError(
            f"could not write {_relative(root, path)}: {error}"
        ) from error


def _publish(root: str | Path, path: Path, data: bytes) -> None:
    temporary: Path | None = None
    try:
        _require_no_symlink_ancestors(root, path)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=".current.json.",
            suffix=".tmp",
        ) as target:
            temporary = Path(target.name)
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        temporary = None
    except OSError as error:
        raise VitrineStorageWriteError(
            f"could not atomically publish {_relative(root, path)}: {error}"
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def _require_safe_storage_directories(root: str | Path) -> None:
    workspace = resolve_workspace_root(root)
    owned = (
        vitrine_root(workspace),
        state_root(workspace),
        records_root(workspace),
        state_revisions_path(workspace),
        locks_root(workspace),
    )
    for path in owned:
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            raise VitrineStorageIntegrityError(
                f"canonical storage directory is unsafe: {_relative(workspace, path)}"
            )
        _require_no_symlink_ancestors(workspace, path)


def _ensure_write_directories(root: str | Path) -> None:
    _require_safe_storage_directories(root)
    for path in (
        vitrine_root(root),
        state_root(root),
        records_root(root),
        state_revisions_path(root),
        locks_root(root),
    ):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise VitrineStorageWriteError(
                f"could not create canonical directory {_relative(root, path)}: {error}"
            ) from error
    _require_safe_storage_directories(root)


def _lock_bytes(expected_state_revision: int | None, purpose: str) -> bytes:
    return lock_json_bytes(
        lock_id=f"lock_{uuid.uuid4().hex}",
        purpose=purpose,
        expected_state_revision=expected_state_revision,
        acquired_at=datetime.now(timezone.utc),
    )


def inspect_write_lock(root: str | Path) -> VitrineLockInspection:
    path = write_lock_path(root)
    data = read_canonical_bytes(root, path, missing=True)
    purpose: str | None = None
    expected: int | None = None
    acquired: datetime | None = None
    try:
        value = strict_json_loads(data)
        if isinstance(value, dict):
            raw_purpose = value.get("purpose")
            if isinstance(raw_purpose, str):
                purpose = raw_purpose
            raw_expected = value.get("expected_state_revision")
            if raw_expected is None or (
                isinstance(raw_expected, int) and not isinstance(raw_expected, bool)
            ):
                expected = raw_expected
            raw_acquired = value.get("acquired_at")
            if isinstance(raw_acquired, str):
                parsed = datetime.fromisoformat(raw_acquired)
                if parsed.tzinfo is not None and parsed.utcoffset() is not None:
                    acquired = parsed
    except Exception:
        pass
    return VitrineLockInspection(
        relative_path=_relative(root, path),
        byte_size=len(data),
        sha256=_sha(data),
        purpose=purpose,
        expected_state_revision=expected,
        acquired_at=acquired,
    )


def clear_write_lock(root: str | Path, *, expected_sha256: str) -> None:
    inspection = inspect_write_lock(root)
    if inspection.sha256 != expected_sha256:
        raise VitrineStorageConflictError(
            "write lock changed since inspection; refusing to clear it."
        )
    path = write_lock_path(root)
    current = read_canonical_bytes(root, path, missing=True)
    if _sha(current) != expected_sha256:
        raise VitrineStorageConflictError(
            "write lock changed immediately before clearing."
        )
    try:
        path.unlink()
        _fsync_directory_if_supported(path.parent)
    except OSError as error:
        raise VitrineStorageWriteError("could not clear write lock.") from error


def _validate_candidate_records(
    records: Iterable[VitrineRecord],
) -> VitrineRecordGraph:
    return _validate_state_records(
        records,
        message="candidate graph is invalid.",
    )


def commit_record_batch(
    root: str | Path,
    records: Iterable[VitrineRecord],
    *,
    expected_state_revision: int | None,
) -> VitrineStorageCommitResult:
    candidates = tuple(records)
    if not candidates:
        raise VitrineStorageValidationError("records must contain at least one record.")
    if expected_state_revision is not None and (
        isinstance(expected_state_revision, bool)
        or not isinstance(expected_state_revision, int)
        or expected_state_revision < 1
    ):
        raise VitrineStorageValidationError(
            "expected_state_revision must be a positive non-Boolean integer or null."
        )

    candidate_map: dict[VitrineStorageRecordKey, VitrineRecord] = {}
    for record in candidates:
        try:
            key = key_for_record(record)
        except ValueError as error:
            raise VitrineStorageValidationError(str(error)) from error
        if key in candidate_map:
            raise VitrineStorageValidationError(
                "duplicate candidate logical identity: "
                f"{key.record_type}:{'/'.join(key.identity_segments)}."
            )
        candidate_map[key] = record

    status = inspect_workspace_root(root)
    if not status.exists or not status.is_dir or not status.is_writable:
        raise VitrineStorageWriteError("an existing writable Core workspace is required.")
    workspace = status.root
    _ensure_write_directories(workspace)

    lock = write_lock_path(workspace)
    acquired = False
    pointer_published = False
    published_revision: int | None = None
    published_sha: str | None = None
    durable: list[str] = []
    result: VitrineStorageCommitResult | None = None
    operation_error: Exception | None = None
    lock_cleanup_error: OSError | None = None

    class _CommitComplete(Exception):
        pass

    try:
        try:
            with lock.open("xb") as target:
                acquired = True
                target.write(_lock_bytes(expected_state_revision, "canonical_commit"))
                target.flush()
                os.fsync(target.fileno())
            _fsync_directory_if_supported(lock.parent)
        except FileExistsError as error:
            raise VitrineStorageConflictError("Vitrine write lock already exists.") from error
        except OSError as error:
            raise VitrineStorageWriteError(
                f"could not durably acquire Vitrine write lock: {error}"
            ) from error

        marker_exists = store_marker_path(workspace).exists()
        current_exists = current_state_path(workspace).exists()
        if marker_exists != current_exists:
            raise VitrineStorageIntegrityError(
                "store marker/current pointer presence is contradictory."
            )

        if current_exists:
            if expected_state_revision is None:
                raise VitrineStorageConflictError(
                    "initial commit requested for an existing Vitrine store."
                )
            loaded = load_current_record_graph(workspace)
            current_revision = loaded.state_revision
            if current_revision != expected_state_revision:
                raise VitrineStorageConflictError(
                    f"expected state {expected_state_revision}, found {current_revision}."
                )
            current_state, _, _ = load_state_revision(workspace, current_revision)
            _validate_canonical_write_history(workspace, current_state)
            current_records = load_state_records(workspace, current_revision)
            all_records = _records_by_key_from_records(current_records)
            selected = {item.key: item for item in current_state.records}
        else:
            if expected_state_revision is not None:
                raise VitrineStorageConflictError(
                    "no current state exists for the expected revision."
                )
            _validate_canonical_write_history(workspace, None)
            current_revision = 0
            all_records = {}
            selected = {}

        new_records: list[tuple[VitrineStorageRecordKey, VitrineRecord]] = []
        for key, record in sorted(candidate_map.items()):
            existing = all_records.get(key)
            if existing is not None:
                if record_to_dict(existing) != record_to_dict(record):
                    raise VitrineStorageConflictError(
                        "immutable semantic record already exists with different content: "
                        f"{key.record_type}:{'/'.join(key.identity_segments)}."
                    )
                continue
            new_records.append((key, record))
            all_records[key] = record

        _validate_candidate_records(all_records.values())

        if not new_records and current_revision:
            current = load_current_state(workspace)
            result = VitrineStorageCommitResult(
                current.state_revision,
                current.state_sha256,
                (),
                True,
            )
            raise _CommitComplete

        if not marker_exists:
            marker = VitrineStoreMarker()
            path = store_marker_path(workspace)
            _write_exclusive(workspace, path, serialize_storage(marker))
            durable.append(_relative(workspace, path))

        new_refs = dict(selected)
        created_refs: list[VitrineRecordRevisionRef] = []
        for key, record in new_records:
            revision = 1
            path = record_revision_path(workspace, key, revision)
            if path.exists() or record_revisions_path(workspace, key).exists():
                raise VitrineStorageIntegrityError(
                    "orphan/colliding record history blocks commit: "
                    f"{key.record_type}:{'/'.join(key.identity_segments)}."
                )
            try:
                path.parent.mkdir(parents=True, exist_ok=False)
            except FileExistsError as error:
                raise VitrineStorageIntegrityError(
                    "record revision directory unexpectedly exists."
                ) from error
            except OSError as error:
                raise VitrineStorageWriteError(
                    f"could not create record revision directory: {error}"
                ) from error
            _require_no_symlink_ancestors(workspace, path.parent)
            body = record_to_dict(record)
            envelope = VitrineRecordRevision(
                key=key,
                storage_revision=revision,
                record_schema_version=cast(str, body["schema_version"]),
                body=body,
            )
            data = serialize_storage(envelope)
            _write_exclusive(workspace, path, data)
            durable.append(_relative(workspace, path))
            persisted, persisted_envelope = load_record_revision(
                workspace, key, revision
            )
            if record_to_dict(persisted) != body or persisted_envelope != envelope:
                raise VitrineStorageIntegrityError(
                    "newly written record revision failed exact verification."
                )
            reference = VitrineRecordRevisionRef(key, revision, _sha(data))
            new_refs[key] = reference
            created_refs.append(reference)

        next_revision = current_revision + 1
        state_path = state_revision_path(workspace, next_revision)
        if state_path.exists():
            raise VitrineStorageIntegrityError(
                "orphan/colliding state revision blocks commit."
            )
        previous_digest: str | None = None
        if current_revision:
            _, previous_digest, _ = load_state_revision(workspace, current_revision)
        state = VitrineStateRevision(
            state_revision=next_revision,
            previous_state_revision=current_revision or None,
            previous_state_sha256=previous_digest,
            records=tuple(sorted(new_refs.values(), key=lambda item: item.key)),
        )
        state_data = serialize_storage(state)
        _write_exclusive(workspace, state_path, state_data)
        durable.append(_relative(workspace, state_path))
        verified_state, verified_digest, _ = load_state_revision(
            workspace, next_revision
        )
        verified_records = load_state_records(workspace, next_revision)
        if (
            verified_state != state
            or verified_digest != _sha(state_data)
            or _records_by_key_from_records(verified_records)
            != _records_by_key_from_records(all_records.values())
        ):
            raise VitrineStorageIntegrityError(
                "newly written state revision failed exact verification."
            )

        pointer = VitrineCurrentState(next_revision, _sha(state_data))
        current_path = current_state_path(workspace)
        _publish(workspace, current_path, serialize_storage(pointer))
        pointer_published = True
        published_revision = next_revision
        published_sha = pointer.state_sha256
        durable.append(_relative(workspace, current_path))
        _fsync_directory_if_supported(current_path.parent)

        load_current_record_graph(workspace)
        verified_records = load_current_records(workspace)
        if _records_by_key_from_records(verified_records) != (
            _records_by_key_from_records(all_records.values())
        ):
            raise VitrineStorageIntegrityError(
                "published state differs from validated candidate state."
            )
        result = VitrineStorageCommitResult(
            next_revision,
            pointer.state_sha256,
            tuple(created_refs),
            False,
        )
    except _CommitComplete:
        pass
    except Exception as error:
        operation_error = error

    if acquired:
        try:
            lock.unlink()
            _fsync_directory_if_supported(lock.parent)
        except OSError as error:
            lock_cleanup_error = error

    reported = list(durable)
    if isinstance(operation_error, VitrineStoragePartialSuccessError):
        reported.extend(operation_error.durable_paths)
    if lock_cleanup_error is not None:
        reported.append(_relative(workspace, lock))
    durable_paths = tuple(dict.fromkeys(reported))

    if operation_error is not None:
        if pointer_published:
            raise VitrineStoragePartialSuccessError(
                "canonical current state was published, but final verification failed.",
                durable_paths=durable_paths,
                pointer_published=True,
                state_revision=published_revision,
                state_sha256=published_sha,
            ) from operation_error
        if durable_paths:
            message = (
                str(operation_error)
                if isinstance(operation_error, VitrineStoragePartialSuccessError)
                else "commit stopped after canonical files may have become durable; "
                "current pointer was not advanced."
            )
            raise VitrineStoragePartialSuccessError(
                message,
                durable_paths=durable_paths,
                pointer_published=False,
                state_revision=None,
                state_sha256=None,
            ) from operation_error
        raise operation_error

    if lock_cleanup_error is not None:
        raise VitrineStoragePartialSuccessError(
            "storage operation succeeded, but write.lock could not be removed.",
            durable_paths=durable_paths,
            pointer_published=pointer_published,
            state_revision=published_revision,
            state_sha256=published_sha,
        ) from lock_cleanup_error

    if result is None:
        raise VitrineStorageWriteError("storage operation produced no result.")
    return result
