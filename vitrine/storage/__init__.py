"""Canonical Vitrine storage and nonauthoritative derived catalog APIs."""

from collections.abc import Iterable
from pathlib import Path
from typing import cast

from vitrine.candidate_state import (
    collect_candidate_state_issues,
    project_candidate_state,
)
from vitrine.curation_state import (
    collect_curation_state_issues,
    project_curation_state,
)
from vitrine.models import VitrineRecord
from vitrine.snapshot_state import collect_snapshot_state_issues, project_snapshot_state

from .catalog import (
    CATALOG_APPLICATION_ID,
    CatalogRecordRow,
    canonical_source_inventory,
    clear_catalog_lock,
    inspect_catalog_lock,
    query_catalog_records,
    rebuild_catalog,
    source_inventory_digest,
)
from .diagnostics import audit_canonical_storage
from .errors import (
    VitrineCatalogBuildError,
    VitrineCatalogCompatibilityError,
    VitrineCatalogConflictError,
    VitrineCatalogError,
    VitrineCatalogIntegrityError,
    VitrineCatalogNotFoundError,
    VitrineCatalogSourceError,
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
    VITRINE_CATALOG_SCHEMA_VERSION,
    VITRINE_STORAGE_SCHEMA_VERSION,
    StorageIssue,
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
    catalog_lock_path,
    catalog_path,
    current_state_path,
    derived_root,
    locks_root,
    record_identity_path,
    record_revision_path,
    record_revisions_path,
    records_root,
    safe_vitrine_descendant,
    state_revision_path,
    state_revisions_path,
    state_root,
    store_marker_path,
    vitrine_root,
    write_lock_path,
)
from .serialization import current_state_from_dict
from .store import (
    _load_state_chain,
    _load_state_records,
    _parse,
    _sha,
    _validate_state_records,
    clear_write_lock,
    inspect_write_lock,
    key_for_record,
    list_record_keys,
    list_record_revisions,
    list_state_revisions,
    load_current_record,
    load_current_record_graph,
    load_current_records,
    load_current_state,
    load_record_revision,
    load_state_records,
    load_state_revision,
    load_store_marker,
)
from .store import commit_record_batch as _commit_record_batch


def load_current_records_with_state(
    root: str | Path,
) -> tuple[VitrineCurrentState, tuple[VitrineRecord, ...]]:
    """Load the exact current pointer and records with one validated state pass."""

    load_store_marker(root)
    raw, _ = _parse(
        root,
        current_state_path(root),
        current_state_from_dict,
        missing=True,
    )
    current = cast(VitrineCurrentState, raw)
    state, state_bytes = _load_state_chain(root, current.state_revision)
    if _sha(state_bytes) != current.state_sha256:
        raise VitrineStorageIntegrityError("current-state digest mismatch.")
    records = _load_state_records(root, state)
    _validate_state_records(
        records,
        message="persisted state graph is invalid.",
    )
    return current, records


def _commit_prevalidated_curation_batch(
    root: str | Path,
    records: Iterable[VitrineRecord],
    *,
    expected_state_revision: int,
) -> VitrineStorageCommitResult:
    """Commit an already curation-validated transition through canonical storage."""

    return _commit_record_batch(
        root,
        tuple(records),
        expected_state_revision=expected_state_revision,
    )


def _commit_prevalidated_snapshot_batch(
    root: str | Path,
    records: Iterable[VitrineRecord],
    *,
    expected_state_revision: int,
) -> VitrineStorageCommitResult:
    """Commit a transition already validated by Snapshot workflow services."""

    return _commit_record_batch(
        root,
        tuple(records),
        expected_state_revision=expected_state_revision,
    )


def commit_record_batch(
    root: str | Path,
    records: Iterable[VitrineRecord],
    *,
    expected_state_revision: int | None,
) -> VitrineStorageCommitResult:
    """Guard the public canonical commit boundary with workflow-state validation."""

    candidates = tuple(records)
    if expected_state_revision is None:
        combined = candidates
    else:
        try:
            combined = (*load_state_records(root, expected_state_revision), *candidates)
        except VitrineStorageNotFoundError:
            combined = candidates
    candidate_issues = collect_candidate_state_issues(
        project_candidate_state(combined)
    )
    if candidate_issues:
        raise VitrineStorageValidationError(
            f"candidate state is invalid ({candidate_issues[0].code})."
        )
    curation_issues = collect_curation_state_issues(
        project_curation_state(combined)
    )
    if curation_issues:
        raise VitrineStorageValidationError(
            f"curation state is invalid ({curation_issues[0].code})."
        )
    snapshot_issues = collect_snapshot_state_issues(project_snapshot_state(combined))
    if snapshot_issues:
        raise VitrineStorageValidationError(
            f"snapshot state is invalid ({snapshot_issues[0].code})."
        )
    return _commit_record_batch(
        root,
        candidates,
        expected_state_revision=expected_state_revision,
    )


__all__ = [
    "CATALOG_APPLICATION_ID",
    "CatalogRecordRow",
    "StorageIssue",
    "VITRINE_CATALOG_SCHEMA_VERSION",
    "VITRINE_STORAGE_SCHEMA_VERSION",
    "VitrineCatalogBuildError",
    "VitrineCatalogCompatibilityError",
    "VitrineCatalogConflictError",
    "VitrineCatalogError",
    "VitrineCatalogIntegrityError",
    "VitrineCatalogNotFoundError",
    "VitrineCatalogSourceError",
    "VitrineCurrentState",
    "VitrineLoadedRecordGraph",
    "VitrineLockInspection",
    "VitrineRecordRevision",
    "VitrineRecordRevisionRef",
    "VitrineStateRevision",
    "VitrineStorageCommitResult",
    "VitrineStorageConflictError",
    "VitrineStorageError",
    "VitrineStorageGraphIntegrityError",
    "VitrineStorageIntegrityError",
    "VitrineStorageNotFoundError",
    "VitrineStoragePartialSuccessError",
    "VitrineStorageReadError",
    "VitrineStorageRecordKey",
    "VitrineStorageValidationError",
    "VitrineStorageWriteError",
    "VitrineStoreMarker",
    "audit_canonical_storage",
    "canonical_source_inventory",
    "catalog_lock_path",
    "catalog_path",
    "clear_catalog_lock",
    "clear_write_lock",
    "commit_record_batch",
    "current_state_path",
    "derived_root",
    "inspect_catalog_lock",
    "inspect_write_lock",
    "key_for_record",
    "list_record_keys",
    "list_record_revisions",
    "list_state_revisions",
    "load_current_record",
    "load_current_record_graph",
    "load_current_records",
    "load_current_records_with_state",
    "load_current_state",
    "load_record_revision",
    "load_state_records",
    "load_state_revision",
    "load_store_marker",
    "locks_root",
    "query_catalog_records",
    "rebuild_catalog",
    "record_identity_path",
    "record_revision_path",
    "record_revisions_path",
    "records_root",
    "safe_vitrine_descendant",
    "source_inventory_digest",
    "state_revision_path",
    "state_revisions_path",
    "state_root",
    "store_marker_path",
    "vitrine_root",
    "write_lock_path",
]
