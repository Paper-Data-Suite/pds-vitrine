"""Containment-safe Snapshot byte custody and guarded staging primitives."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final

from vitrine.models.common import (
    require_aware_datetime,
    require_identifier,
    require_positive_int,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.storage.paths import safe_vitrine_descendant

SNAPSHOT_PATH_POLICY_ID: Final[str] = "snapshot_path_v1"
SNAPSHOT_DIGEST_POLICY_ID: Final[str] = "snapshot_digest_v1"
SNAPSHOT_SERIES_LOCK_CONTRACT_VERSION: Final[str] = "snapshot_series_lock_v1"

SNAPSHOT_CUSTODY_CODES: Final[frozenset[str]] = frozenset(
    {
        "snapshot.path_invalid",
        "snapshot.path_collision",
        "snapshot.staging_conflict",
        "snapshot.staging_invalid",
        "snapshot.entry_write_failed",
        "snapshot.edition_conflict",
        "snapshot.edition_publish_failed",
        "snapshot.build_lock_conflict",
        "snapshot.build_lock_invalid",
        "snapshot.build_lock_missing",
        "snapshot.build_lock_write_failed",
    }
)


class SnapshotCustodyError(RuntimeError):
    """Expected Snapshot custody failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in SNAPSHOT_CUSTODY_CODES:
            raise ValueError(f"unsupported Snapshot custody code: {code}")
        self.code = code
        super().__init__(message)


def normalize_snapshot_relative_path(value: object) -> str:
    """Validate one audience/content relative path under the v0.2 path policy."""

    if not isinstance(value, str):
        raise SnapshotCustodyError("snapshot.path_invalid", "Snapshot path must be text.")
    text = unicodedata.normalize("NFC", value)
    if not text or text != text.strip() or "\x00" in text:
        raise SnapshotCustodyError(
            "snapshot.path_invalid",
            "Snapshot path must be nonempty, normalized text without surrounding whitespace.",
        )
    if "\\" in text or ":" in text:
        raise SnapshotCustodyError(
            "snapshot.path_invalid",
            "Snapshot path must use portable relative POSIX syntax.",
        )
    posix = PurePosixPath(text)
    windows = PureWindowsPath(text)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        raise SnapshotCustodyError("snapshot.path_invalid", "Snapshot path must be relative.")
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SnapshotCustodyError(
            "snapshot.path_invalid",
            "Snapshot path must not contain empty or traversal components.",
        )
    if any(unicodedata.normalize("NFC", part) != part for part in parts):
        raise SnapshotCustodyError(
            "snapshot.path_invalid", "Snapshot path components must be NFC-normalized."
        )
    return "/".join(parts)


def snapshot_path_collision_key(value: object) -> str:
    """Return the portable case/Unicode collision key for a relative path."""

    return normalize_snapshot_relative_path(value).casefold()


def validate_snapshot_path_inventory(paths: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(normalize_snapshot_relative_path(item) for item in paths)
    keys = tuple(snapshot_path_collision_key(item) for item in normalized)
    if len(set(keys)) != len(keys):
        raise SnapshotCustodyError(
            "snapshot.path_collision",
            "Snapshot path inventory contains a portable case/Unicode collision.",
        )
    return normalized


def snapshot_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "snapshots")


def snapshot_staging_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "snapshots/staging")


def snapshot_editions_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "snapshots/editions")


def snapshot_edition_root(
    root: str | Path, snapshot_series_id: str, edition_number: int
) -> Path:
    try:
        snapshot_series_id = require_identifier(snapshot_series_id, "snapshot_series_id")
        edition_number = require_positive_int(edition_number, "edition_number")
    except VitrineModelValidationError as error:
        raise SnapshotCustodyError(
            "snapshot.path_invalid", "Snapshot Edition identity is invalid."
        ) from error
    return safe_vitrine_descendant(
        root, f"snapshots/editions/{snapshot_series_id}/{edition_number}"
    )


def snapshot_exports_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "snapshots/exports")


def snapshot_locks_root(root: str | Path) -> Path:
    return safe_vitrine_descendant(root, "snapshots/.locks")



def snapshot_series_lock_path(root: str | Path, snapshot_series_id: str) -> Path:
    try:
        snapshot_series_id = require_identifier(
            snapshot_series_id, "snapshot_series_id"
        )
    except VitrineModelValidationError as error:
        raise SnapshotCustodyError(
            "snapshot.path_invalid", "Snapshot Series identity is invalid."
        ) from error
    return safe_vitrine_descendant(
        root, f"snapshots/.locks/{snapshot_series_id}.json"
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSeriesLockInspection:
    snapshot_series_id: str
    snapshot_build_attempt_id: str
    snapshot_build_plan_id: str
    acquired_at: datetime
    sha256: str
    relative_path: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "snapshot_series_id",
                require_identifier(self.snapshot_series_id, "snapshot_series_id"),
            )
            object.__setattr__(
                self,
                "snapshot_build_attempt_id",
                require_identifier(
                    self.snapshot_build_attempt_id, "snapshot_build_attempt_id"
                ),
            )
            object.__setattr__(
                self,
                "snapshot_build_plan_id",
                require_identifier(
                    self.snapshot_build_plan_id, "snapshot_build_plan_id"
                ),
            )
            object.__setattr__(
                self,
                "acquired_at",
                require_aware_datetime(self.acquired_at, "acquired_at"),
            )
        except VitrineModelValidationError as error:
            raise ValueError("Snapshot Series lock inspection is invalid.") from error
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.sha256)
        ):
            raise ValueError("Snapshot Series lock digest must be lowercase SHA-256.")
        if not isinstance(self.relative_path, str) or not self.relative_path:
            raise ValueError("Snapshot Series lock relative_path must be nonempty.")


def _series_lock_bytes(
    *,
    snapshot_series_id: str,
    snapshot_build_attempt_id: str,
    snapshot_build_plan_id: str,
    acquired_at: datetime,
) -> bytes:
    value = {
        "contract_version": SNAPSHOT_SERIES_LOCK_CONTRACT_VERSION,
        "snapshot_series_id": snapshot_series_id,
        "snapshot_build_attempt_id": snapshot_build_attempt_id,
        "snapshot_build_plan_id": snapshot_build_plan_id,
        "acquired_at": acquired_at.astimezone(timezone.utc).isoformat(),
    }
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _parse_series_lock(
    root: str | Path,
    snapshot_series_id: str,
    payload: bytes,
) -> SnapshotSeriesLockInspection:
    path = snapshot_series_lock_path(root, snapshot_series_id)
    try:
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict) or set(value) != {
            "contract_version",
            "snapshot_series_id",
            "snapshot_build_attempt_id",
            "snapshot_build_plan_id",
            "acquired_at",
        }:
            raise ValueError
        if value["contract_version"] != SNAPSHOT_SERIES_LOCK_CONTRACT_VERSION:
            raise ValueError
        if value["snapshot_series_id"] != snapshot_series_id:
            raise ValueError
        acquired_at = datetime.fromisoformat(str(value["acquired_at"]))
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise ValueError
        canonical = _series_lock_bytes(
            snapshot_series_id=snapshot_series_id,
            snapshot_build_attempt_id=str(value["snapshot_build_attempt_id"]),
            snapshot_build_plan_id=str(value["snapshot_build_plan_id"]),
            acquired_at=acquired_at,
        )
        if canonical != payload:
            raise ValueError
        relative = path.relative_to(snapshot_root(root)).as_posix()
        return SnapshotSeriesLockInspection(
            snapshot_series_id=snapshot_series_id,
            snapshot_build_attempt_id=str(value["snapshot_build_attempt_id"]),
            snapshot_build_plan_id=str(value["snapshot_build_plan_id"]),
            acquired_at=acquired_at,
            sha256=hashlib.sha256(payload).hexdigest(),
            relative_path=relative,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_invalid",
            "Snapshot Series build lock is malformed or noncanonical.",
        ) from error


def acquire_snapshot_series_lock(
    root: str | Path,
    *,
    snapshot_series_id: str,
    snapshot_build_attempt_id: str,
    snapshot_build_plan_id: str,
    acquired_at: datetime,
) -> SnapshotSeriesLockInspection:
    try:
        snapshot_series_id = require_identifier(
            snapshot_series_id, "snapshot_series_id"
        )
        snapshot_build_attempt_id = require_identifier(
            snapshot_build_attempt_id, "snapshot_build_attempt_id"
        )
        snapshot_build_plan_id = require_identifier(
            snapshot_build_plan_id, "snapshot_build_plan_id"
        )
        acquired_at = require_aware_datetime(acquired_at, "acquired_at")
    except VitrineModelValidationError as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_invalid",
            "Snapshot Series build lock request is invalid.",
        ) from error
    lock_root = snapshot_locks_root(root)
    try:
        if lock_root.exists():
            _require_plain_directory(lock_root)
        else:
            lock_root.mkdir(parents=True, exist_ok=False)
            _require_plain_directory(lock_root)
    except (OSError, SnapshotCustodyError) as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_write_failed",
            "Snapshot Series lock directory could not be established safely.",
        ) from error
    path = snapshot_series_lock_path(root, snapshot_series_id)
    payload = _series_lock_bytes(
        snapshot_series_id=snapshot_series_id,
        snapshot_build_attempt_id=snapshot_build_attempt_id,
        snapshot_build_plan_id=snapshot_build_plan_id,
        acquired_at=acquired_at,
    )
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_conflict",
            "Snapshot Series already has an exclusive build lock.",
        ) from error
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_write_failed",
            "Snapshot Series build lock could not be written durably.",
        ) from error
    return inspect_snapshot_series_lock(root, snapshot_series_id=snapshot_series_id)


def inspect_snapshot_series_lock(
    root: str | Path, *, snapshot_series_id: str
) -> SnapshotSeriesLockInspection:
    path = snapshot_series_lock_path(root, snapshot_series_id)
    try:
        if not path.exists():
            raise SnapshotCustodyError(
                "snapshot.build_lock_missing",
                "Snapshot Series build lock is not present.",
            )
        if _is_link_or_reparse(path) or not path.is_file():
            raise SnapshotCustodyError(
                "snapshot.build_lock_invalid",
                "Snapshot Series build lock is not a plain regular file.",
            )
        payload = path.read_bytes()
    except SnapshotCustodyError:
        raise
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_invalid",
            "Snapshot Series build lock could not be inspected.",
        ) from error
    return _parse_series_lock(root, snapshot_series_id, payload)


def release_snapshot_series_lock(
    root: str | Path,
    *,
    snapshot_series_id: str,
    snapshot_build_attempt_id: str,
    expected_sha256: str,
) -> None:
    inspection = inspect_snapshot_series_lock(
        root, snapshot_series_id=snapshot_series_id
    )
    if (
        inspection.snapshot_build_attempt_id != snapshot_build_attempt_id
        or inspection.sha256 != expected_sha256
    ):
        raise SnapshotCustodyError(
            "snapshot.build_lock_conflict",
            "Snapshot Series build lock changed or belongs to another Attempt.",
        )
    path = snapshot_series_lock_path(root, snapshot_series_id)
    try:
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise SnapshotCustodyError(
                "snapshot.build_lock_conflict",
                "Snapshot Series build lock changed immediately before release.",
            )
        path.unlink()
    except SnapshotCustodyError:
        raise
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.build_lock_write_failed",
            "Snapshot Series build lock could not be released.",
        ) from error

def snapshot_attempt_staging_root(root: str | Path, attempt_id: str) -> Path:
    try:
        attempt_id = require_identifier(attempt_id, "snapshot_build_attempt_id")
    except VitrineModelValidationError as error:
        raise SnapshotCustodyError(
            "snapshot.path_invalid", "Snapshot Attempt identity is invalid."
        ) from error
    return safe_vitrine_descendant(root, f"snapshots/staging/{attempt_id}")


def _is_link_or_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        raw_attributes = getattr(path.lstat(), "st_file_attributes", 0)
        attributes = raw_attributes if isinstance(raw_attributes, int) else 0
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot custody path could not be inspected."
        ) from error
    raw_reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    reparse_flag = raw_reparse_flag if isinstance(raw_reparse_flag, int) else 0
    return bool(reparse_flag and attributes & reparse_flag)


def _require_plain_directory(path: Path) -> None:
    if not path.exists() or not path.is_dir() or _is_link_or_reparse(path):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot custody directory must be an ordinary non-link directory.",
        )


def _safe_descendant(base: Path, relative_path: str) -> Path:
    normalized = normalize_snapshot_relative_path(relative_path)
    candidate = base.joinpath(*normalized.split("/"))
    try:
        candidate.relative_to(base)
    except ValueError as error:
        raise SnapshotCustodyError(
            "snapshot.path_invalid", "Snapshot path escaped its custody root."
        ) from error
    return candidate


def _ensure_plain_parent_chain(base: Path, target_parent: Path) -> None:
    _require_plain_directory(base)
    relative = target_parent.relative_to(base)
    current = base
    for part in relative.parts:
        current = current / part
        if current.exists():
            _require_plain_directory(current)
            continue
        try:
            current.mkdir()
        except OSError as error:
            raise SnapshotCustodyError(
                "snapshot.entry_write_failed",
                "Snapshot staging parent directory could not be created.",
            ) from error
        _require_plain_directory(current)


@dataclass(frozen=True, slots=True)
class SnapshotStagingArea:
    workspace_root: Path
    snapshot_build_attempt_id: str
    root: Path
    content_root: Path
    internal_root: Path

    def content_path(self, relative_path: str) -> Path:
        return _safe_descendant(self.content_root, relative_path)

    def internal_path(self, relative_path: str) -> Path:
        return _safe_descendant(self.internal_root, relative_path)


def create_snapshot_staging(
    root: str | Path, snapshot_build_attempt_id: str
) -> SnapshotStagingArea:
    """Create one exclusive noncanonical staging tree for an Attempt."""

    attempt_root = snapshot_attempt_staging_root(root, snapshot_build_attempt_id)
    staging_root = snapshot_staging_root(root)
    try:
        staging_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging root could not be created."
        ) from error
    _require_plain_directory(staging_root)
    if attempt_root.exists():
        raise SnapshotCustodyError(
            "snapshot.staging_conflict",
            "Snapshot Attempt staging already exists and will not be reused.",
        )
    try:
        attempt_root.mkdir()
        content_root = attempt_root / "content"
        internal_root = attempt_root / "internal"
        content_root.mkdir()
        internal_root.mkdir()
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging tree could not be created."
        ) from error
    for directory in (attempt_root, content_root, internal_root):
        _require_plain_directory(directory)
    return SnapshotStagingArea(
        workspace_root=Path(root).resolve(),
        snapshot_build_attempt_id=snapshot_build_attempt_id,
        root=attempt_root,
        content_root=content_root,
        internal_root=internal_root,
    )

def load_snapshot_staging(
    root: str | Path, snapshot_build_attempt_id: str
) -> SnapshotStagingArea:
    """Reopen one existing Attempt staging tree without creating or repairing it."""

    attempt_root = snapshot_attempt_staging_root(root, snapshot_build_attempt_id)
    content_root = attempt_root / "content"
    internal_root = attempt_root / "internal"
    for directory in (attempt_root, content_root, internal_root):
        _require_plain_directory(directory)
    try:
        names = {item.name for item in attempt_root.iterdir()}
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot staging tree could not be enumerated.",
        ) from error
    if names != {"content", "internal"}:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot staging root contains unexpected top-level content.",
        )
    return SnapshotStagingArea(
        workspace_root=Path(root).resolve(),
        snapshot_build_attempt_id=snapshot_build_attempt_id,
        root=attempt_root,
        content_root=content_root,
        internal_root=internal_root,
    )


def require_empty_snapshot_staging(staging: SnapshotStagingArea) -> None:
    """Reject implicit reuse of a staging tree with prior execution residue."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    for directory in (staging.content_root, staging.internal_root):
        _require_plain_directory(directory)
        try:
            if next(directory.iterdir(), None) is not None:
                raise SnapshotCustodyError(
                    "snapshot.staging_conflict",
                    "Snapshot Attempt staging contains prior execution residue.",
                )
        except SnapshotCustodyError:
            raise
        except OSError as error:
            raise SnapshotCustodyError(
                "snapshot.staging_invalid",
                "Snapshot staging content could not be inspected.",
            ) from error


def write_staging_bytes_exclusive(
    staging: SnapshotStagingArea,
    relative_path: str,
    payload: bytes,
) -> Path:
    """Write exact bytes once into staging and fsync the file before returning."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    if not isinstance(payload, bytes):
        raise SnapshotCustodyError(
            "snapshot.entry_write_failed", "Snapshot staged payload must be bytes."
        )
    _require_plain_directory(staging.content_root)
    target = staging.content_path(relative_path)
    _ensure_plain_parent_chain(staging.content_root, target.parent)
    if target.exists() or target.is_symlink():
        raise SnapshotCustodyError(
            "snapshot.staging_conflict", "Snapshot staged target already exists."
        )
    try:
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_conflict", "Snapshot staged target already exists."
        ) from error
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.entry_write_failed", "Snapshot staged bytes could not be written."
        ) from error
    if _is_link_or_reparse(target) or not target.is_file():
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot staged target must be an ordinary non-link file.",
        )
    return target


def read_staging_content_bytes(
    staging: SnapshotStagingArea, relative_path: str
) -> bytes:
    """Read exact staged content bytes after ordinary-file verification."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    _require_plain_directory(staging.content_root)
    target = staging.content_path(relative_path)
    if not target.exists() or _is_link_or_reparse(target) or not target.is_file():
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot staged content must be an ordinary non-link file.",
        )
    try:
        return target.read_bytes()
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staged content could not be read."
        ) from error


def staging_content_inventory(staging: SnapshotStagingArea) -> tuple[str, ...]:
    """Enumerate the exact ordinary-file inventory under staging/content."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    _require_plain_directory(staging.content_root)
    pending = [staging.content_root]
    files: list[str] = []
    while pending:
        current = pending.pop()
        _require_plain_directory(current)
        try:
            children = tuple(sorted(current.iterdir(), key=lambda item: item.name))
        except OSError as error:
            raise SnapshotCustodyError(
                "snapshot.staging_invalid",
                "Snapshot staged content inventory could not be enumerated.",
            ) from error
        for child in children:
            if _is_link_or_reparse(child):
                raise SnapshotCustodyError(
                    "snapshot.staging_invalid",
                    "Snapshot staged content inventory must not contain links or reparse points.",
                )
            if child.is_dir():
                pending.append(child)
                continue
            if not child.is_file():
                raise SnapshotCustodyError(
                    "snapshot.staging_invalid",
                    "Snapshot staged content inventory contains a nonregular object.",
                )
            relative = child.relative_to(staging.content_root).as_posix()
            files.append(normalize_snapshot_relative_path(relative))
    return tuple(sorted(files))


def write_staging_internal_bytes_exclusive(
    staging: SnapshotStagingArea, relative_path: str, payload: bytes
) -> Path:
    """Write one immutable internal Snapshot metadata file into staging."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    if not isinstance(payload, bytes):
        raise SnapshotCustodyError(
            "snapshot.entry_write_failed", "Snapshot internal payload must be bytes."
        )
    _require_plain_directory(staging.internal_root)
    target = staging.internal_path(relative_path)
    _ensure_plain_parent_chain(staging.internal_root, target.parent)
    if target.exists() or target.is_symlink():
        raise SnapshotCustodyError(
            "snapshot.staging_conflict", "Snapshot internal target already exists."
        )
    try:
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_conflict", "Snapshot internal target already exists."
        ) from error
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.entry_write_failed",
            "Snapshot internal bytes could not be written.",
        ) from error
    if _is_link_or_reparse(target) or not target.is_file():
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot internal target must be an ordinary non-link file.",
        )
    return target


def read_staging_internal_bytes(
    staging: SnapshotStagingArea, relative_path: str
) -> bytes:
    """Read exact staged internal metadata bytes."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    _require_plain_directory(staging.internal_root)
    target = staging.internal_path(relative_path)
    if not target.exists() or _is_link_or_reparse(target) or not target.is_file():
        raise SnapshotCustodyError(
            "snapshot.staging_invalid",
            "Snapshot internal metadata must be an ordinary non-link file.",
        )
    try:
        return target.read_bytes()
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot internal metadata could not be read."
        ) from error


def publish_snapshot_staging_as_edition(
    staging: SnapshotStagingArea,
    *,
    snapshot_series_id: str,
    edition_number: int,
) -> Path:
    """Move one verified staging tree into its immutable Edition custody path."""

    if not isinstance(staging, SnapshotStagingArea):
        raise SnapshotCustodyError(
            "snapshot.staging_invalid", "Snapshot staging area is invalid."
        )
    for directory in (staging.root, staging.content_root, staging.internal_root):
        _require_plain_directory(directory)
    target = snapshot_edition_root(
        staging.workspace_root, snapshot_series_id, edition_number
    )
    editions = snapshot_editions_root(staging.workspace_root)
    series_root = target.parent
    try:
        editions.mkdir(parents=True, exist_ok=True)
        _require_plain_directory(editions)
        series_root.mkdir(exist_ok=True)
        _require_plain_directory(series_root)
    except SnapshotCustodyError:
        raise
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.edition_publish_failed",
            "Snapshot Edition custody parent could not be created.",
        ) from error
    if target.exists() or target.is_symlink():
        raise SnapshotCustodyError(
            "snapshot.edition_conflict",
            "Snapshot Edition custody path already exists.",
        )
    try:
        os.replace(staging.root, target)
    except OSError as error:
        raise SnapshotCustodyError(
            "snapshot.edition_publish_failed",
            "Verified Snapshot staging could not be published as an Edition.",
        ) from error
    try:
        _require_plain_directory(target)
        _require_plain_directory(target / "content")
        _require_plain_directory(target / "internal")
    except SnapshotCustodyError as error:
        raise SnapshotCustodyError(
            "snapshot.edition_publish_failed",
            "Published Snapshot Edition custody failed final directory verification.",
        ) from error
    return target


__all__ = [
    "SNAPSHOT_DIGEST_POLICY_ID",
    "SNAPSHOT_PATH_POLICY_ID",
    "SNAPSHOT_SERIES_LOCK_CONTRACT_VERSION",
    "SnapshotCustodyError",
    "SnapshotSeriesLockInspection",
    "SnapshotStagingArea",
    "acquire_snapshot_series_lock",
    "create_snapshot_staging",
    "inspect_snapshot_series_lock",
    "load_snapshot_staging",
    "require_empty_snapshot_staging",
    "normalize_snapshot_relative_path",
    "publish_snapshot_staging_as_edition",
    "read_staging_content_bytes",
    "read_staging_internal_bytes",
    "snapshot_attempt_staging_root",
    "snapshot_edition_root",
    "snapshot_editions_root",
    "snapshot_exports_root",
    "snapshot_locks_root",
    "snapshot_path_collision_key",
    "release_snapshot_series_lock",
    "snapshot_root",
    "snapshot_series_lock_path",
    "snapshot_staging_root",
    "staging_content_inventory",
    "validate_snapshot_path_inventory",
    "write_staging_bytes_exclusive",
    "write_staging_internal_bytes_exclusive",
]
