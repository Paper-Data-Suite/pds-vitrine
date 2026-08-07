"""Disposable SQLite catalog rebuilt from canonical Vitrine JSON."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .errors import (
    VitrineCatalogBuildError,
    VitrineCatalogCompatibilityError,
    VitrineCatalogConflictError,
    VitrineCatalogIntegrityError,
    VitrineCatalogNotFoundError,
    VitrineCatalogSourceError,
    VitrineStorageError,
    VitrineStorageNotFoundError,
    VitrineStorageWriteError,
)
from .models import (
    VITRINE_CATALOG_SCHEMA_VERSION,
    VitrineLockInspection,
    VitrineStorageRecordKey,
)
from .paths import (
    catalog_lock_path,
    catalog_path,
    current_state_path,
    record_revision_path,
    state_revision_path,
    state_root,
    store_marker_path,
)
from .serialization import lock_json_bytes, strict_json_loads
from .store import (
    _fsync_directory_if_supported,
    _relative,
    _require_no_symlink_ancestors,
    list_record_keys,
    list_record_revisions,
    list_state_revisions,
    load_current_state,
    load_state_revision,
    load_store_marker,
    read_canonical_bytes,
    require_regular_nonsymlink_file,
)

CATALOG_APPLICATION_ID = 0x5654524E


@dataclass(frozen=True, slots=True)
class CatalogRecordRow:
    record_type: str
    identity_segments: tuple[str, ...]
    storage_revision: int
    sha256: str
    selected_state_revision: int | None
    is_current: bool


def canonical_source_inventory(
    root: str | Path,
) -> tuple[tuple[str, int, str], ...]:
    load_store_marker(root)
    load_current_state(root)
    paths: list[Path] = [store_marker_path(root)]
    for key in list_record_keys(root):
        for revision in list_record_revisions(root, key):
            paths.append(record_revision_path(root, key, revision))
    for revision in list_state_revisions(root):
        paths.append(state_revision_path(root, revision))
    paths.append(current_state_path(root))
    base = state_root(root)
    result: list[tuple[str, int, str]] = []
    for path in paths:
        data = read_canonical_bytes(root, path, missing=True)
        result.append(
            (
                path.relative_to(base).as_posix(),
                len(data),
                hashlib.sha256(data).hexdigest(),
            )
        )
    return tuple(sorted(result))


def source_inventory_digest(
    inventory: tuple[tuple[str, int, str], ...],
) -> str:
    digest = hashlib.sha256()
    for relative, size, sha in inventory:
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(sha))
    return digest.hexdigest()


def _identity_text(key: VitrineStorageRecordKey) -> str:
    return "/".join(key.identity_segments)


def _catalog_lock_bytes() -> bytes:
    return lock_json_bytes(
        lock_id=f"lock_{uuid.uuid4().hex}",
        purpose="catalog_rebuild",
        expected_state_revision=None,
        acquired_at=datetime.now(timezone.utc),
    )


def inspect_catalog_lock(root: str | Path) -> VitrineLockInspection:
    path = catalog_lock_path(root)
    data = read_canonical_bytes(root, path, missing=True)
    purpose: str | None = None
    acquired: datetime | None = None
    try:
        value = strict_json_loads(data)
        if isinstance(value, dict):
            raw_purpose = value.get("purpose")
            if isinstance(raw_purpose, str):
                purpose = raw_purpose
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
        sha256=hashlib.sha256(data).hexdigest(),
        purpose=purpose,
        expected_state_revision=None,
        acquired_at=acquired,
    )


def clear_catalog_lock(root: str | Path, *, expected_sha256: str) -> None:
    inspection = inspect_catalog_lock(root)
    if inspection.sha256 != expected_sha256:
        raise VitrineCatalogConflictError(
            "catalog lock changed since inspection; refusing to clear it."
        )
    path = catalog_lock_path(root)
    current = read_canonical_bytes(root, path, missing=True)
    if hashlib.sha256(current).hexdigest() != expected_sha256:
        raise VitrineCatalogConflictError(
            "catalog lock changed immediately before clearing."
        )
    try:
        path.unlink()
        _fsync_directory_if_supported(path.parent)
    except OSError as error:
        raise VitrineStorageWriteError("could not clear catalog lock.") from error


def rebuild_catalog(root: str | Path) -> Path:
    target = catalog_path(root)
    try:
        _require_no_symlink_ancestors(root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        _require_no_symlink_ancestors(root, target.parent)
    except VitrineStorageError:
        raise
    except OSError as error:
        raise VitrineCatalogBuildError(
            f"could not prepare derived catalog directory: {error}"
        ) from error

    lock = catalog_lock_path(root)
    lock.parent.mkdir(parents=True, exist_ok=True)
    acquired = False
    installed = False
    temporary: Path | None = None
    operation_error: Exception | None = None
    lock_cleanup_error: OSError | None = None
    result: Path | None = None

    try:
        try:
            with lock.open("xb") as output:
                acquired = True
                output.write(_catalog_lock_bytes())
                output.flush()
                os.fsync(output.fileno())
            _fsync_directory_if_supported(lock.parent)
        except FileExistsError as error:
            raise VitrineCatalogConflictError("catalog lock already exists.") from error

        before = canonical_source_inventory(root)
        source_digest = source_inventory_digest(before)
        current = load_current_state(root)
        keys = list_record_keys(root)
        state_revisions = list_state_revisions(root)

        selected: dict[tuple[str, str, int], list[int]] = {}
        for state_revision in state_revisions:
            state, _, _ = load_state_revision(root, state_revision)
            for reference in state.records:
                selection_key = (
                    reference.key.record_type,
                    _identity_text(reference.key),
                    reference.storage_revision,
                )
                selected.setdefault(selection_key, []).append(state_revision)

        fd, name = tempfile.mkstemp(
            prefix=".catalog.sqlite.", suffix=".tmp", dir=target.parent
        )
        os.close(fd)
        temporary = Path(name)
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript(
                f"""
                PRAGMA journal_mode=DELETE;
                PRAGMA application_id={CATALOG_APPLICATION_ID};
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE record_revisions (
                    record_type TEXT NOT NULL,
                    identity_text TEXT NOT NULL,
                    storage_revision INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    PRIMARY KEY(record_type, identity_text, storage_revision)
                );
                CREATE TABLE state_records (
                    state_revision INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    identity_text TEXT NOT NULL,
                    storage_revision INTEGER NOT NULL,
                    is_current INTEGER NOT NULL,
                    PRIMARY KEY(state_revision, record_type, identity_text)
                );
                CREATE INDEX state_records_identity
                    ON state_records(record_type, identity_text, storage_revision);
                """
            )
            revision_count = sum(len(list_record_revisions(root, key)) for key in keys)
            connection.executemany(
                "INSERT INTO metadata VALUES (?, ?)",
                (
                    ("schema_version", str(VITRINE_CATALOG_SCHEMA_VERSION)),
                    ("application_id", str(CATALOG_APPLICATION_ID)),
                    ("built_at_utc", datetime.now(timezone.utc).isoformat()),
                    ("source_digest", source_digest),
                    ("source_file_count", str(len(before))),
                    ("current_state_revision", str(current.state_revision)),
                    ("current_state_sha256", current.state_sha256),
                    ("record_identity_count", str(len(keys))),
                    ("record_revision_count", str(revision_count)),
                    ("state_revision_count", str(len(state_revisions))),
                ),
            )
            for key in keys:
                identity_text = _identity_text(key)
                for revision in list_record_revisions(root, key):
                    path = record_revision_path(root, key, revision)
                    data = read_canonical_bytes(root, path, missing=True)
                    sha = hashlib.sha256(data).hexdigest()
                    connection.execute(
                        "INSERT INTO record_revisions VALUES (?, ?, ?, ?, ?)",
                        (
                            key.record_type,
                            identity_text,
                            revision,
                            sha,
                            path.relative_to(state_root(root)).as_posix(),
                        ),
                    )
            for selection_key, states in selected.items():
                for state_revision in states:
                    connection.execute(
                        "INSERT INTO state_records VALUES (?, ?, ?, ?, ?)",
                        (
                            state_revision,
                            *selection_key,
                            int(state_revision == current.state_revision),
                        ),
                    )
            connection.commit()
            if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise VitrineCatalogIntegrityError(
                    "replacement catalog failed integrity_check."
                )
        finally:
            connection.close()

        after = canonical_source_inventory(root)
        if after != before:
            raise VitrineCatalogConflictError(
                "canonical source changed during catalog rebuild."
            )
        os.replace(temporary, target)
        temporary = None
        installed = True
        _fsync_directory_if_supported(target.parent)
        _open_verified(root).close()
        result = target
    except (VitrineCatalogConflictError, VitrineCatalogIntegrityError) as error:
        operation_error = error
    except Exception as error:
        operation_error = VitrineCatalogBuildError(f"catalog rebuild failed: {error}")

    if temporary is not None:
        try:
            temporary.unlink()
        except OSError as error:
            if operation_error is None:
                operation_error = VitrineCatalogBuildError(
                    "catalog rebuild failed and its temporary file remains."
                )
                operation_error.__cause__ = error

    if acquired:
        try:
            lock.unlink()
            _fsync_directory_if_supported(lock.parent)
        except OSError as error:
            lock_cleanup_error = error

    if lock_cleanup_error is not None:
        if installed:
            raise VitrineCatalogBuildError(
                "catalog was installed successfully, but catalog.lock could not be removed."
            ) from lock_cleanup_error
        raise VitrineCatalogBuildError(
            "catalog rebuild failed and catalog.lock could not be removed."
        ) from lock_cleanup_error
    if operation_error is not None:
        raise operation_error
    if result is None:
        raise VitrineCatalogBuildError("catalog rebuild produced no result.")
    return result


def _open_verified(root: str | Path) -> sqlite3.Connection:
    path = catalog_path(root)
    try:
        require_regular_nonsymlink_file(root, path, missing=True)
    except VitrineStorageNotFoundError as error:
        raise VitrineCatalogNotFoundError("catalog not found.") from error
    except VitrineStorageError as error:
        raise VitrineCatalogIntegrityError("catalog path is unsafe.") from error
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        metadata: dict[str, str] = {
            str(row[0]): str(row[1])
            for row in connection.execute("SELECT key, value FROM metadata")
        }
        if metadata.get("schema_version") != str(VITRINE_CATALOG_SCHEMA_VERSION):
            raise VitrineCatalogCompatibilityError("catalog schema is incompatible.")
        if connection.execute("PRAGMA application_id").fetchone() != (
            CATALOG_APPLICATION_ID,
        ):
            raise VitrineCatalogCompatibilityError(
                "catalog application identifier is incompatible."
            )
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise VitrineCatalogIntegrityError("catalog is corrupt.")
        inventory = canonical_source_inventory(root)
        if metadata.get("source_digest") != source_inventory_digest(inventory):
            raise VitrineCatalogSourceError(
                "catalog is stale relative to canonical storage."
            )
        current = load_current_state(root)
        if (
            metadata.get("current_state_revision") != str(current.state_revision)
            or metadata.get("current_state_sha256") != current.state_sha256
        ):
            raise VitrineCatalogSourceError(
                "catalog current-state metadata is stale."
            )
        return connection
    except (
        VitrineCatalogCompatibilityError,
        VitrineCatalogSourceError,
        VitrineCatalogIntegrityError,
    ):
        if connection is not None:
            connection.close()
        raise
    except sqlite3.Error as error:
        if connection is not None:
            connection.close()
        raise VitrineCatalogIntegrityError(f"catalog is corrupt: {error}") from error


def query_catalog_records(
    root: str | Path,
    *,
    state_revision: int | None = None,
    state: str = "all",
) -> tuple[CatalogRecordRow, ...]:
    if state not in {"all", "current", "historical"}:
        raise ValueError("state must be all, current, or historical.")
    if state_revision is not None and state != "all":
        raise ValueError("state filtering cannot be combined with state_revision.")
    connection = _open_verified(root)
    try:
        if state_revision is None:
            clause = {
                "all": "",
                "current": "WHERE EXISTS (SELECT 1 FROM state_records x "
                "WHERE x.record_type=r.record_type AND x.identity_text=r.identity_text "
                "AND x.storage_revision=r.storage_revision AND x.is_current=1)",
                "historical": "WHERE NOT EXISTS (SELECT 1 FROM state_records x "
                "WHERE x.record_type=r.record_type AND x.identity_text=r.identity_text "
                "AND x.storage_revision=r.storage_revision AND x.is_current=1)",
            }[state]
            sql = f"""SELECT r.record_type,r.identity_text,r.storage_revision,r.sha256,
                (SELECT MAX(x.state_revision) FROM state_records x
                 WHERE x.record_type=r.record_type AND x.identity_text=r.identity_text
                 AND x.storage_revision=r.storage_revision),
                EXISTS (SELECT 1 FROM state_records x
                 WHERE x.record_type=r.record_type AND x.identity_text=r.identity_text
                 AND x.storage_revision=r.storage_revision AND x.is_current=1)
                FROM record_revisions r {clause} ORDER BY 1,2,3"""
            params: tuple[object, ...] = ()
        else:
            if isinstance(state_revision, bool) or not isinstance(state_revision, int) or state_revision < 1:
                raise ValueError("state_revision must be a positive non-Boolean integer.")
            sql = """SELECT r.record_type,r.identity_text,r.storage_revision,r.sha256,
                s.state_revision,s.is_current FROM state_records s
                JOIN record_revisions r USING(record_type,identity_text,storage_revision)
                WHERE s.state_revision=? ORDER BY 1,2,3"""
            params = (state_revision,)
        rows: list[CatalogRecordRow] = []
        for row in connection.execute(sql, params):
            segments = tuple(str(row[1]).split("/"))
            rows.append(
                CatalogRecordRow(
                    str(row[0]),
                    segments,
                    int(row[2]),
                    str(row[3]),
                    int(row[4]) if row[4] is not None else None,
                    bool(row[5]),
                )
            )
        return tuple(rows)
    finally:
        connection.close()
