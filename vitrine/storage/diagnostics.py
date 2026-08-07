"""Read-only deterministic diagnostics for canonical Vitrine storage."""

from __future__ import annotations

from pathlib import Path

from .errors import (
    VitrineStorageGraphIntegrityError,
    VitrineStorageIntegrityError,
    VitrineStorageNotFoundError,
    VitrineStorageReadError,
)
from .models import StorageIssue
from .paths import write_lock_path
from .store import (
    list_record_keys,
    list_record_revisions,
    list_state_revisions,
    load_current_record_graph,
    load_store_marker,
)


def _classify(error: Exception) -> str:
    text = str(error).lower()
    if isinstance(error, VitrineStorageGraphIntegrityError):
        return "storage.graph.invalid"
    if isinstance(error, VitrineStorageNotFoundError):
        return "storage.object.missing"
    if "symlink" in text or "outside" in text:
        return "storage.path.unsafe"
    if "digest" in text:
        return "storage.state.digest_mismatch"
    if "orphan" in text:
        return "storage.state.orphan_history"
    if "noncontiguous" in text or "gap" in text:
        return "storage.state.history_gap"
    if "identity" in text or "canonical path" in text:
        return "storage.record.identity_mismatch"
    if "unexpected" in text:
        return "storage.path.unexpected_entry"
    if isinstance(error, VitrineStorageReadError):
        return "storage.object.malformed"
    if isinstance(error, VitrineStorageIntegrityError):
        return "storage.integrity.invalid"
    return "storage.audit.failed"


def audit_canonical_storage(root: str | Path) -> tuple[StorageIssue, ...]:
    """Audit canonical JSON without modifying storage or consulting derived state."""
    issues: list[StorageIssue] = []
    try:
        load_store_marker(root)
        for key in list_record_keys(root):
            list_record_revisions(root, key)
        list_state_revisions(root)
        load_current_record_graph(root)
    except Exception as error:
        issues.append(StorageIssue(code=_classify(error), message=str(error)))
        if isinstance(error, VitrineStorageGraphIntegrityError):
            for graph_issue in error.issues:
                issues.append(
                    StorageIssue(
                        code=f"storage.graph.{graph_issue.code}",
                        message=graph_issue.message,
                        record_type=graph_issue.record_type,
                        logical_identity=(graph_issue.record_id,)
                        if graph_issue.record_id is not None
                        else (),
                    )
                )
    lock = write_lock_path(root)
    try:
        if lock.exists() or lock.is_symlink():
            issues.append(
                StorageIssue(
                    code="storage.lock.present",
                    message="canonical write lock is present; ordinary writes must not proceed.",
                    relative_path="state/.locks/write.lock",
                )
            )
    except OSError:
        issues.append(
            StorageIssue(
                code="storage.lock.inspect_failed",
                message="canonical write lock presence could not be inspected.",
                relative_path="state/.locks/write.lock",
            )
        )
    return tuple(
        sorted(
            issues,
            key=lambda item: (
                item.code,
                item.relative_path or "",
                item.record_type or "",
                item.logical_identity,
                item.state_revision or 0,
                item.message,
            ),
        )
    )
