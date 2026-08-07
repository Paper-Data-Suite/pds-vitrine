"""Deterministic containment-safe paths for workspace-scoped Vitrine storage."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from pds_core.workspace import resolve_workspace_root

from .errors import VitrineStorageValidationError
from .models import VitrineStorageRecordKey


def vitrine_root(root: str | Path) -> Path:
    return resolve_workspace_root(root) / "vitrine"


def safe_vitrine_descendant(root: str | Path, relative_path: str | Path) -> Path:
    if not isinstance(relative_path, (str, Path)):
        raise VitrineStorageValidationError("relative_path must be a string or Path.")
    text = str(relative_path)
    if text == "" or text != text.strip():
        raise VitrineStorageValidationError(
            "relative_path must be nonempty and have no surrounding whitespace."
        )
    if "\x00" in text:
        raise VitrineStorageValidationError("relative_path must not contain NUL.")
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        raise VitrineStorageValidationError("relative_path must be relative.")
    parts = text.replace("\\", "/").split("/")
    if any(part == "" for part in parts):
        raise VitrineStorageValidationError(
            "relative_path must not contain empty components."
        )
    if any(part in {".", ".."} for part in parts):
        raise VitrineStorageValidationError(
            "relative_path must not contain traversal components."
        )
    base = vitrine_root(root)
    result = base.joinpath(*parts)
    try:
        relative = result.relative_to(base)
    except ValueError as error:
        raise VitrineStorageValidationError(
            "relative_path must remain beneath the Vitrine root."
        ) from error
    if not relative.parts:
        raise VitrineStorageValidationError("relative_path must identify a descendant.")
    return result


def state_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state")


def store_marker_path(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state/store.json")


def records_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state/records")


def record_identity_path(root: str | Path, key: VitrineStorageRecordKey) -> Path:
    if not isinstance(key, VitrineStorageRecordKey):
        raise VitrineStorageValidationError("key must be VitrineStorageRecordKey.")
    relative = "/".join(("state", "records", key.record_type, *key.identity_segments))
    return safe_vitrine_descendant(root, relative)


def record_revisions_path(root: str | Path, key: VitrineStorageRecordKey) -> Path:
    return record_identity_path(root, key) / "revisions"


def record_revision_path(
    root: str | Path, key: VitrineStorageRecordKey, storage_revision: int
) -> Path:
    if isinstance(storage_revision, bool) or not isinstance(storage_revision, int) or storage_revision < 1:
        raise VitrineStorageValidationError(
            "storage_revision must be a positive non-Boolean integer."
        )
    return record_revisions_path(root, key) / f"{storage_revision}.json"


def state_revisions_path(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state/revisions")


def state_revision_path(root: str | Path, state_revision: int) -> Path:
    if isinstance(state_revision, bool) or not isinstance(state_revision, int) or state_revision < 1:
        raise VitrineStorageValidationError(
            "state_revision must be a positive non-Boolean integer."
        )
    return state_revisions_path(root) / f"{state_revision}.json"


def current_state_path(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state/current.json")


def derived_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state/derived")


def catalog_path(root: str | Path) -> Path:
    return derived_root(root) / "catalog.sqlite"


def locks_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "state/.locks")


def write_lock_path(root: str | Path) -> Path:
    return locks_root(root) / "write.lock"


def catalog_lock_path(root: str | Path) -> Path:
    return locks_root(root) / "catalog.lock"
