"""Producer-independent Snapshot export, verification, pointer, and recovery services."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from vitrine.models import (
    ActorAttribution,
    DigestReference,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildFinding,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotEdition,
    SnapshotEditionBuildProvenance,
    SnapshotEntry,
    SnapshotEntryOutcome,
    SnapshotExportArtifact,
    SnapshotManifest,
    SnapshotMaterializationProvenance,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
    VitrineRecord,
)
from vitrine.models.common import (
    require_aware_datetime,
    require_identifier,
    require_positive_int,
    require_text,
)
from vitrine.models.conversion import JsonValue
from vitrine.models.errors import VitrineModelValidationError
from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    inspect_snapshot_series_lock,
    normalize_snapshot_relative_path,
    release_snapshot_series_lock,
    snapshot_attempt_staging_root,
    snapshot_edition_root,
    snapshot_editions_root,
    snapshot_exports_root,
    snapshot_locks_root,
    snapshot_staging_root,
)
from vitrine.snapshot_sealing import (
    canonical_snapshot_json_bytes,
    snapshot_digest,
    snapshot_logical_inventory_digest,
)
from vitrine.snapshot_state import collect_snapshot_state_issues, project_snapshot_state
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageError,
    VitrineStorageNotFoundError,
    VitrineStoragePartialSuccessError,
    _commit_prevalidated_snapshot_batch,
    load_current_records_with_state,
)

SNAPSHOT_DIRECTORY_PACKAGER_ID: Final[str] = "vitrine_directory_packager"
SNAPSHOT_DIRECTORY_PACKAGER_VERSION: Final[str] = "1"
SNAPSHOT_DIRECTORY_INVENTORY_CONTRACT_VERSION: Final[str] = (
    "vitrine_directory_inventory_v1"
)

SNAPSHOT_DISTRIBUTION_CODES: Final[frozenset[str]] = frozenset(
    {
        "snapshot_distribution.invalid_request",
        "snapshot_distribution.context_not_found",
        "snapshot_distribution.state_conflict",
        "snapshot_distribution.state_invalid",
        "snapshot_distribution.durability_uncertain",
        "snapshot_distribution.edition_not_found",
        "snapshot_distribution.edition_unpublished",
        "snapshot_distribution.verification_failed",
        "snapshot_distribution.export_plan_not_found",
        "snapshot_distribution.export_conflict",
        "snapshot_distribution.export_failed",
        "snapshot_distribution.export_not_found",
        "snapshot_distribution.pointer_conflict",
        "snapshot_distribution.recovery_conflict",
        "snapshot_distribution.recovery_unsafe",
    }
)


SNAPSHOT_CUSTODY_FINDING_CODES: Final[frozenset[str]] = frozenset(
    {
        "snapshot.custody.incomplete_attempt",
        "snapshot.custody.failed_attempt",
        "snapshot.custody.orphan_staging",
        "snapshot.custody.build_lock_present",
        "snapshot.custody.ambiguous_edition_target",
        "snapshot.custody.canonical_edition_missing_custody",
        "snapshot.custody.custody_edition_missing_canonical_state",
        "snapshot.custody.corrupted_entry",
        "snapshot.custody.corrupted_manifest",
        "snapshot.custody.orphan_export",
        "snapshot.custody.corrupted_export",
        "snapshot.custody.durability_uncertainty",
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotCustodyFinding:
    code: str
    severity: str
    subject_kind: str
    subject_id: str
    summary: str

    def __post_init__(self) -> None:
        if self.code not in SNAPSHOT_CUSTODY_FINDING_CODES:
            raise ValueError("unsupported Snapshot custody finding code.")
        if self.severity not in {"info", "warning", "error"}:
            raise ValueError("unsupported Snapshot custody finding severity.")
        require_text(self.subject_kind, "subject_kind", maximum=64)
        require_text(self.subject_id, "subject_id", maximum=500)
        require_text(self.summary, "summary", maximum=1000)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotCustodyAudit:
    canonical_state_revision: int
    findings: tuple[SnapshotCustodyFinding, ...]

    def __post_init__(self) -> None:
        require_positive_int(self.canonical_state_revision, "canonical_state_revision")
        object.__setattr__(self, "findings", tuple(self.findings))
        if any(not isinstance(item, SnapshotCustodyFinding) for item in self.findings):
            raise ValueError("findings must contain SnapshotCustodyFinding values.")


class SnapshotDistributionError(RuntimeError):
    """Expected distribution/recovery failure with stable machine-readable metadata."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in SNAPSHOT_DISTRIBUTION_CODES:
            raise ValueError(f"unsupported Snapshot distribution code: {code}")
        self.code = code
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class _Loaded:
    records: tuple[VitrineRecord, ...]
    state_revision: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEditionVerification:
    snapshot_series_id: str
    edition_number: int
    manifest_digest: DigestReference
    logical_inventory_digest: DigestReference
    verified_entry_ids: tuple[str, ...]
    verified_at: datetime

    def __post_init__(self) -> None:
        require_identifier(self.snapshot_series_id, "snapshot_series_id")
        require_positive_int(self.edition_number, "edition_number")
        if not isinstance(self.manifest_digest, DigestReference):
            raise ValueError("manifest_digest must be DigestReference.")
        if not isinstance(self.logical_inventory_digest, DigestReference):
            raise ValueError("logical_inventory_digest must be DigestReference.")
        object.__setattr__(self, "verified_entry_ids", tuple(self.verified_entry_ids))
        require_aware_datetime(self.verified_at, "verified_at")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotExportResult:
    state_revision: int
    export_artifact: SnapshotExportArtifact
    export_path: Path

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        if not isinstance(self.export_artifact, SnapshotExportArtifact):
            raise ValueError("export_artifact must be SnapshotExportArtifact.")
        if not isinstance(self.export_path, Path):
            raise ValueError("export_path must be pathlib.Path.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotExportVerification:
    snapshot_export_artifact_id: str
    snapshot_series_id: str
    edition_number: int
    directory_inventory_digest: DigestReference
    verified_file_paths: tuple[str, ...]
    verified_at: datetime

    def __post_init__(self) -> None:
        require_identifier(
            self.snapshot_export_artifact_id, "snapshot_export_artifact_id"
        )
        require_identifier(self.snapshot_series_id, "snapshot_series_id")
        require_positive_int(self.edition_number, "edition_number")
        if not isinstance(self.directory_inventory_digest, DigestReference):
            raise ValueError(
                "directory_inventory_digest must be DigestReference."
            )
        object.__setattr__(
            self, "verified_file_paths", tuple(self.verified_file_paths)
        )
        require_aware_datetime(self.verified_at, "verified_at")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotPointerResult:
    state_revision: int
    pointer: SnapshotCurrentPointerRevision

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        if not isinstance(self.pointer, SnapshotCurrentPointerRevision):
            raise ValueError("pointer must be SnapshotCurrentPointerRevision.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotAttemptRecoveryInspection:
    snapshot_build_attempt_id: str
    canonical_state_revision: int
    terminal_result_id: str | None
    staging_exists: bool
    staging_has_residue: bool
    build_lock_present: bool
    build_lock_matches_attempt: bool
    build_lock_sha256: str | None
    sealed_edition_numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        require_identifier(self.snapshot_build_attempt_id, "snapshot_build_attempt_id")
        require_positive_int(self.canonical_state_revision, "canonical_state_revision")
        object.__setattr__(self, "sealed_edition_numbers", tuple(self.sealed_edition_numbers))

    @property
    def recovery_required(self) -> bool:
        return self.terminal_result_id is None


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotRecoveryResult:
    state_revision: int
    attempt_result: SnapshotBuildAttemptResult

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        if not isinstance(self.attempt_result, SnapshotBuildAttemptResult):
            raise ValueError("attempt_result must be SnapshotBuildAttemptResult.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _load(root: str | Path, expected_state_revision: int | None = None) -> _Loaded:
    try:
        current, records = load_current_records_with_state(root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.context_not_found",
            "Vitrine canonical Snapshot state is unavailable.",
            stage="load",
        ) from error
    if (
        expected_state_revision is not None
        and current.state_revision != expected_state_revision
    ):
        raise SnapshotDistributionError(
            "snapshot_distribution.state_conflict",
            "Vitrine canonical state changed before the Snapshot distribution operation.",
            stage="concurrency",
        )
    return _Loaded(records=records, state_revision=current.state_revision)


def _commit(
    root: str | Path,
    records: tuple[VitrineRecord, ...],
    *,
    loaded: _Loaded,
) -> int:
    combined = (*loaded.records, *records)
    issues = collect_snapshot_state_issues(project_snapshot_state(combined))
    if issues:
        raise SnapshotDistributionError(
            "snapshot_distribution.state_invalid",
            f"Snapshot transition is invalid ({issues[0].code}).",
            stage="validation",
        )
    try:
        result = _commit_prevalidated_snapshot_batch(
            root,
            records,
            expected_state_revision=loaded.state_revision,
        )
    except VitrineStoragePartialSuccessError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.durability_uncertain",
            "Snapshot distribution persistence has uncertain durability.",
            stage="durability",
        ) from error
    except VitrineStorageConflictError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.state_conflict",
            "Vitrine canonical state changed before the Snapshot distribution commit.",
            stage="concurrency",
        ) from error
    except VitrineStorageError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.context_not_found",
            "Snapshot distribution persistence failed.",
            stage="persistence",
        ) from error
    return result.state_revision


def _edition(
    records: tuple[VitrineRecord, ...], snapshot_series_id: str, edition_number: int
) -> SnapshotEdition:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotEdition)
        and item.snapshot_series_id == snapshot_series_id
        and item.edition_number == edition_number
    )
    if len(values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.edition_not_found",
            "Snapshot Edition does not resolve uniquely.",
            stage="edition",
        )
    return values[0]


def _plain(path: Path) -> bool:
    try:
        if path.is_symlink():
            return False
        attrs_raw = getattr(path.lstat(), "st_file_attributes", 0)
        attrs = attrs_raw if isinstance(attrs_raw, int) else 0
        flag_raw = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        flag = flag_raw if isinstance(flag_raw, int) else 0
        return not bool(flag and attrs & flag)
    except OSError:
        return False


def _require_plain_dir(path: Path, message: str) -> None:
    if not path.exists() or not path.is_dir() or not _plain(path):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed", message, stage="custody"
        )


def _read_plain_file(path: Path, *, stage: str = "verification") -> bytes:
    if not path.exists() or not path.is_file() or not _plain(path):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot custody contains a missing, linked, reparse, or nonregular file.",
            stage=stage,
        )
    try:
        return path.read_bytes()
    except OSError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot custody file could not be read.",
            stage=stage,
        ) from error


def _content_inventory(content_root: Path) -> tuple[str, ...]:
    _require_plain_dir(
        content_root, "Snapshot Edition content custody is unavailable or unsafe."
    )
    pending = [content_root]
    result: list[str] = []
    while pending:
        current = pending.pop()
        _require_plain_dir(
            current, "Snapshot Edition content custody contains an unsafe directory."
        )
        try:
            children = tuple(sorted(current.iterdir(), key=lambda item: item.name))
        except OSError as error:
            raise SnapshotDistributionError(
                "snapshot_distribution.verification_failed",
                "Snapshot Edition content inventory could not be enumerated.",
                stage="verification",
            ) from error
        for child in children:
            if not _plain(child):
                raise SnapshotDistributionError(
                    "snapshot_distribution.verification_failed",
                    "Snapshot Edition content inventory contains a link or reparse point.",
                    stage="verification",
                )
            if child.is_dir():
                pending.append(child)
            elif child.is_file():
                result.append(
                    normalize_snapshot_relative_path(
                        child.relative_to(content_root).as_posix()
                    )
                )
            else:
                raise SnapshotDistributionError(
                    "snapshot_distribution.verification_failed",
                    "Snapshot Edition content inventory contains a nonregular object.",
                    stage="verification",
                )
    return tuple(sorted(result))


def _canonical_manifest_value(payload: bytes) -> dict[str, JsonValue]:
    try:
        raw = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal manifest is not valid UTF-8 JSON.",
            stage="verification",
        ) from error
    if not isinstance(raw, dict):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal manifest must be a JSON object.",
            stage="verification",
        )
    # Canonical serialization also rejects NaN/infinity.
    try:
        canonical = canonical_snapshot_json_bytes(raw)
    except (TypeError, ValueError) as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal manifest is outside the canonical JSON contract.",
            stage="verification",
        ) from error
    if canonical != payload:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal manifest bytes are not canonical.",
            stage="verification",
        )
    return raw


def verify_snapshot_edition(
    root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    verified_at: datetime | None = None,
) -> SnapshotEditionVerification:
    """Verify a historical sealed Edition without consulting any producer."""

    try:
        snapshot_series_id = require_identifier(
            snapshot_series_id, "snapshot_series_id"
        )
        edition_number = require_positive_int(edition_number, "edition_number")
        checked_at = require_aware_datetime(
            verified_at or _now(), "verified_at"
        ).astimezone(timezone.utc)
    except VitrineModelValidationError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.invalid_request",
            "Snapshot Edition verification request is invalid.",
            stage="verification",
        ) from error

    loaded = _load(root)
    state_issues = collect_snapshot_state_issues(project_snapshot_state(loaded.records))
    if state_issues:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            f"Canonical Snapshot provenance/state is invalid ({state_issues[0].code}).",
            stage="verification",
        )
    edition = _edition(loaded.records, snapshot_series_id, edition_number)
    manifest_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotManifest) and item.manifest_id == edition.manifest_id
    )
    seal_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotSeal) and item.seal_id == edition.seal_id
    )
    if len(manifest_values) != 1 or len(seal_values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition canonical Manifest or Seal is missing.",
            stage="verification",
        )
    manifest_record = manifest_values[0]
    seal = seal_values[0]
    build_provenance_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotEditionBuildProvenance)
        and item.snapshot_edition == edition.reference
    )
    if len(build_provenance_values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition must have exactly one complete build-provenance record.",
            stage="verification",
        )
    build_provenance = build_provenance_values[0]
    request_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildRequest)
        and item.snapshot_build_request_id
        == build_provenance.snapshot_build_request_id
    )
    plan_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id == build_provenance.snapshot_build_plan_id
    )
    attempt_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_attempt_id
        == build_provenance.snapshot_build_attempt_id
    )
    result_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_result_id
        == build_provenance.snapshot_build_attempt_result_id
    )
    if not all(
        len(values) == 1
        for values in (request_values, plan_values, attempt_values, result_values)
    ):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition build-provenance workflow chain is incomplete.",
            stage="verification",
        )
    request = request_values[0]
    plan = plan_values[0]
    attempt = attempt_values[0]
    result = result_values[0]
    if (
        plan.snapshot_build_request_id != request.snapshot_build_request_id
        or attempt.snapshot_build_plan_id != plan.snapshot_build_plan_id
        or result.snapshot_build_attempt_id != attempt.snapshot_build_attempt_id
        or result.sealed_snapshot_edition != edition.reference
        or plan.snapshot_series_id != edition.snapshot_series_id
        or plan.portfolio_id != edition.portfolio_id
        or plan.profile_binding_id != edition.profile_binding_id
        or plan.profile_revision != edition.profile_revision
        or plan.composition_revision != edition.composition_revision
        or plan.audience_context_id != edition.audience_context_id
    ):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition build provenance does not reproduce its exact workflow/context.",
            stage="verification",
        )
    edition_root = snapshot_edition_root(root, snapshot_series_id, edition_number)
    content_root = edition_root / "content"
    internal_root = edition_root / "internal"
    if not edition_root.exists():
        raise SnapshotDistributionError(
            "snapshot_distribution.edition_unpublished",
            "Snapshot Edition is sealed canonically but is not present in Edition custody.",
            stage="verification",
        )
    _require_plain_dir(edition_root, "Snapshot Edition custody root is unsafe.")
    _require_plain_dir(content_root, "Snapshot Edition content custody is unsafe.")
    _require_plain_dir(internal_root, "Snapshot Edition internal custody is unsafe.")
    try:
        internal_names = tuple(sorted(item.name for item in internal_root.iterdir()))
    except OSError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition internal inventory could not be enumerated.",
            stage="verification",
        ) from error
    if internal_names != ("manifest.json",):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition internal inventory must contain exactly manifest.json.",
            stage="verification",
        )
    manifest_bytes = _read_plain_file(internal_root / "manifest.json")
    manifest_value = _canonical_manifest_value(manifest_bytes)
    actual_manifest_digest = snapshot_digest(manifest_bytes)
    if actual_manifest_digest != seal.manifest_digest:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal Manifest digest does not match the canonical Seal.",
            stage="verification",
        )
    logical = manifest_value.get("logical_inventory")
    if not isinstance(logical, dict):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal Manifest has no logical inventory object.",
            stage="verification",
        )
    try:
        logical_digest = snapshot_logical_inventory_digest(logical)
    except (TypeError, ValueError) as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot logical inventory is outside the canonical digest contract.",
            stage="verification",
        ) from error
    if logical_digest != seal.logical_inventory_digest:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot logical inventory digest does not match the canonical Seal.",
            stage="verification",
        )
    edition_value = manifest_value.get("snapshot_edition")
    if edition_value != {
        "snapshot_series_id": snapshot_series_id,
        "edition_number": edition_number,
    }:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal Manifest Edition identity does not match canonical state.",
            stage="verification",
        )
    if (
        manifest_value.get("snapshot_manifest_id") != manifest_record.manifest_id
        or manifest_value.get("snapshot_seal_id") != seal.seal_id
    ):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal Manifest canonical identities do not match Edition state.",
            stage="verification",
        )
    entries = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotEntry) and item.snapshot_edition == edition.reference
    )
    materializations = {
        item.materialization_id: item
        for item in loaded.records
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition == edition.reference
    }
    materialization_provenance = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotMaterializationProvenance)
        and item.snapshot_edition == edition.reference
    )
    provenance_counts = {materialization_id: 0 for materialization_id in materializations}
    for provenance in materialization_provenance:
        if provenance.materialization_id not in provenance_counts:
            raise SnapshotDistributionError(
                "snapshot_distribution.verification_failed",
                "Snapshot Materialization provenance references foreign Edition state.",
                stage="verification",
            )
        provenance_counts[provenance.materialization_id] += 1
        if provenance.verification_result != "verified":
            raise SnapshotDistributionError(
                "snapshot_distribution.verification_failed",
                "Snapshot Materialization provenance is not verified.",
                stage="verification",
            )
    if any(count != 1 for count in provenance_counts.values()):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Every Snapshot Materialization must have exactly one provenance record.",
            stage="verification",
        )
    omissions = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotOmission)
        and item.snapshot_edition == edition.reference
    )
    if tuple(sorted(manifest_record.omission_ids)) != tuple(
        sorted(item.snapshot_omission_id for item in omissions)
    ):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot canonical Manifest Omission inventory is inconsistent.",
            stage="verification",
        )
    expected_paths = tuple(sorted(item.relative_path for item in entries))
    if _content_inventory(content_root) != expected_paths:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Edition byte inventory does not match canonical Entry records.",
            stage="verification",
        )
    for entry in entries:
        materialization = materializations.get(entry.materialization_id)
        if materialization is None or materialization.output_digest is None:
            raise SnapshotDistributionError(
                "snapshot_distribution.verification_failed",
                "Snapshot Entry lacks byte-bearing canonical Materialization state.",
                stage="verification",
            )
        payload = _read_plain_file(
            content_root.joinpath(*entry.relative_path.split("/"))
        )
        if (
            snapshot_digest(payload) != materialization.output_digest
            or len(payload) != materialization.byte_size
        ):
            raise SnapshotDistributionError(
                "snapshot_distribution.verification_failed",
                "Snapshot Edition Entry bytes do not match canonical Materialization digest/size.",
                stage="verification",
            )
    if tuple(sorted(manifest_record.entry_ids)) != tuple(
        sorted(item.snapshot_entry_id for item in entries)
    ):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot canonical Manifest Entry inventory is inconsistent.",
            stage="verification",
        )
    return SnapshotEditionVerification(
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
        manifest_digest=actual_manifest_digest,
        logical_inventory_digest=logical_digest,
        verified_entry_ids=tuple(sorted(item.snapshot_entry_id for item in entries)),
        verified_at=checked_at,
    )


def _directory_inventory_value(
    root: Path, relative_paths: tuple[str, ...]
) -> dict[str, JsonValue]:
    files: list[JsonValue] = []
    for relative_path in tuple(sorted(relative_paths)):
        payload = _read_plain_file(
            root.joinpath(*relative_path.split("/")), stage="export"
        )
        files.append(
            {
                "relative_path": relative_path,
                "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return {
        "contract_version": SNAPSHOT_DIRECTORY_INVENTORY_CONTRACT_VERSION,
        "files": files,
    }



def verify_snapshot_export(
    root: str | Path,
    *,
    snapshot_export_artifact_id: str,
    verified_at: datetime | None = None,
) -> SnapshotExportVerification:
    """Verify one persisted directory Export without consulting a producer."""

    try:
        snapshot_export_artifact_id = require_identifier(
            snapshot_export_artifact_id, "snapshot_export_artifact_id"
        )
        checked_at = require_aware_datetime(
            verified_at or _now(), "verified_at"
        ).astimezone(timezone.utc)
    except VitrineModelValidationError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.invalid_request",
            "Snapshot Export verification request is invalid.",
            stage="export_verification",
        ) from error
    loaded = _load(root)
    values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotExportArtifact)
        and item.snapshot_export_artifact_id == snapshot_export_artifact_id
    )
    if len(values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_not_found",
            "Snapshot Export Artifact does not resolve uniquely.",
            stage="export_verification",
        )
    artifact = values[0]
    if artifact.export_format != "directory_package":
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Export format is unsupported by the v0.2 verifier.",
            stage="export_verification",
        )
    verify_snapshot_edition(
        root,
        snapshot_series_id=artifact.snapshot_edition.snapshot_series_id,
        edition_number=artifact.snapshot_edition.edition_number,
        verified_at=checked_at,
    )
    entries = {
        item.snapshot_entry_id: item
        for item in loaded.records
        if isinstance(item, SnapshotEntry)
        and item.snapshot_edition == artifact.snapshot_edition
    }
    included = tuple(
        entries[item] for item in artifact.included_entry_ids if item in entries
    )
    if len(included) != len(artifact.included_entry_ids):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Export references missing canonical Entries.",
            stage="export_verification",
        )
    excluded = tuple(
        item.snapshot_entry_id
        for item in entries.values()
        if item.snapshot_entry_id not in set(artifact.included_entry_ids)
    )
    if tuple(sorted(excluded)) != tuple(sorted(artifact.excluded_entry_ids)):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Export included/excluded Entry partition is inconsistent.",
            stage="export_verification",
        )
    export_root = (
        snapshot_exports_root(root)
        / artifact.snapshot_edition.snapshot_series_id
        / str(artifact.snapshot_edition.edition_number)
        / artifact.snapshot_export_artifact_id
    )
    expected_relative = (
        f"snapshots/exports/{artifact.snapshot_edition.snapshot_series_id}/"
        f"{artifact.snapshot_edition.edition_number}/"
        f"{artifact.snapshot_export_artifact_id}"
    )
    if artifact.relative_path != expected_relative:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Export Artifact custody path is inconsistent.",
            stage="export_verification",
        )
    expected_paths = tuple(sorted(item.relative_path for item in included))
    if _content_inventory(export_root) != expected_paths:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Export directory contains missing, unexpected, or unsafe files.",
            stage="export_verification",
        )
    inventory = _directory_inventory_value(export_root, expected_paths)
    digest = snapshot_digest(canonical_snapshot_json_bytes(inventory))
    if digest != artifact.directory_inventory_digest:
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot Export directory inventory digest does not match canonical state.",
            stage="export_verification",
        )
    return SnapshotExportVerification(
        snapshot_export_artifact_id=artifact.snapshot_export_artifact_id,
        snapshot_series_id=artifact.snapshot_edition.snapshot_series_id,
        edition_number=artifact.snapshot_edition.edition_number,
        directory_inventory_digest=digest,
        verified_file_paths=expected_paths,
        verified_at=checked_at,
    )

def create_snapshot_directory_export(
    root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    export_plan_id: str,
    expected_state_revision: int,
    predecessor_export_artifact_id: str | None = None,
    generated_at: datetime | None = None,
    artifact_id: str | None = None,
) -> SnapshotExportResult:
    """Create and persist one independently verified directory-package Export Artifact."""

    try:
        snapshot_series_id = require_identifier(
            snapshot_series_id, "snapshot_series_id"
        )
        edition_number = require_positive_int(edition_number, "edition_number")
        export_plan_id = require_identifier(export_plan_id, "export_plan_id")
        artifact_identity = require_identifier(
            artifact_id or _id("snapshot_export"), "snapshot_export_artifact_id"
        )
        generated = require_aware_datetime(
            generated_at or _now(), "generated_at"
        ).astimezone(timezone.utc)
        if predecessor_export_artifact_id is not None:
            predecessor_export_artifact_id = require_identifier(
                predecessor_export_artifact_id, "predecessor_export_artifact_id"
            )
    except VitrineModelValidationError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.invalid_request",
            "Snapshot directory Export request is invalid.",
            stage="export",
        ) from error

    loaded = _load(root, expected_state_revision)
    edition = _edition(loaded.records, snapshot_series_id, edition_number)
    verify_snapshot_edition(
        root,
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
        verified_at=generated,
    )
    provenance_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotEditionBuildProvenance)
        and item.snapshot_edition == edition.reference
    )
    if len(provenance_values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_plan_not_found",
            "Snapshot Edition build provenance does not resolve uniquely.",
            stage="export",
        )
    plan_id = provenance_values[0].snapshot_build_plan_id
    plan_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id == plan_id
    )
    if len(plan_values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_plan_not_found",
            "Snapshot Build Plan does not resolve uniquely for the sealed Edition.",
            stage="export",
        )
    plan = plan_values[0]
    export_plans = tuple(
        item for item in plan.export_plans if item.export_plan_id == export_plan_id
    )
    if len(export_plans) != 1 or export_plans[0].export_format != "directory_package":
        raise SnapshotDistributionError(
            "snapshot_distribution.export_plan_not_found",
            "Requested directory Export Plan does not resolve uniquely.",
            stage="export",
        )
    export_plan = export_plans[0]

    edition_entries = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotEntry) and item.snapshot_edition == edition.reference
    )
    edition_entry_by_id = {item.snapshot_entry_id: item for item in edition_entries}
    manifest_bytes = _read_plain_file(
        snapshot_edition_root(root, snapshot_series_id, edition_number)
        / "internal"
        / "manifest.json"
    )
    manifest_value = _canonical_manifest_value(manifest_bytes)
    manifest_entries = manifest_value.get("entries")
    if not isinstance(manifest_entries, list):
        raise SnapshotDistributionError(
            "snapshot_distribution.verification_failed",
            "Snapshot internal Manifest has no Entry-plan mapping.",
            stage="export",
        )
    entry_id_by_plan: dict[str, str] = {}
    for item in manifest_entries:
        if not isinstance(item, dict):
            continue
        plan_entry_id = item.get("entry_plan_id")
        snapshot_entry_id = item.get("snapshot_entry_id")
        if isinstance(plan_entry_id, str) and isinstance(snapshot_entry_id, str):
            entry_id_by_plan[plan_entry_id] = snapshot_entry_id
    included_entry_ids = tuple(
        entry_id_by_plan[item]
        for item in export_plan.included_entry_plan_ids
        if item in entry_id_by_plan
    )
    included_set = set(included_entry_ids)
    excluded_entry_ids = tuple(
        item.snapshot_entry_id
        for item in edition_entries
        if item.snapshot_entry_id not in included_set
    )
    if not included_entry_ids:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_plan_not_found",
            "Directory Export Plan does not include any byte-bearing Snapshot Entries.",
            stage="export",
        )

    exact_existing = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotExportArtifact)
        and item.snapshot_edition == edition.reference
        and item.export_format == "directory_package"
        and item.export_contract_version == export_plan.export_contract_version
        and item.included_entry_ids == included_entry_ids
        and tuple(sorted(item.excluded_entry_ids))
        == tuple(sorted(excluded_entry_ids))
        and item.packager_id == SNAPSHOT_DIRECTORY_PACKAGER_ID
        and item.packager_version == SNAPSHOT_DIRECTORY_PACKAGER_VERSION
        and item.configuration_digest == export_plan.configuration_digest
        and item.predecessor_export_artifact_id
        == predecessor_export_artifact_id
    )
    if len(exact_existing) > 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_conflict",
            "More than one immutable Export Artifact represents the same exact Export Plan.",
            stage="export",
        )
    if exact_existing:
        existing = exact_existing[0]
        verify_snapshot_export(
            root,
            snapshot_export_artifact_id=existing.snapshot_export_artifact_id,
            verified_at=generated,
        )
        existing_path = (
            snapshot_exports_root(root)
            / existing.snapshot_edition.snapshot_series_id
            / str(existing.snapshot_edition.edition_number)
            / existing.snapshot_export_artifact_id
        )
        return SnapshotExportResult(
            state_revision=loaded.state_revision,
            export_artifact=existing,
            export_path=existing_path,
        )

    exports_root = snapshot_exports_root(root)
    final_root = exports_root / snapshot_series_id / str(edition_number) / artifact_identity
    temporary_root = (
        exports_root
        / snapshot_series_id
        / str(edition_number)
        / f".{artifact_identity}.staging"
    )
    edition_content = (
        snapshot_edition_root(root, snapshot_series_id, edition_number) / "content"
    )
    try:
        final_root.parent.mkdir(parents=True, exist_ok=True)
        if final_root.exists() or temporary_root.exists():
            raise SnapshotDistributionError(
                "snapshot_distribution.export_conflict",
                "Snapshot Export custody identity already exists or has unresolved staging.",
                stage="export",
            )
        temporary_root.mkdir()
        for entry_id in included_entry_ids:
            entry = edition_entry_by_id[entry_id]
            source = edition_content.joinpath(*entry.relative_path.split("/"))
            payload = _read_plain_file(source, stage="export")
            target = temporary_root.joinpath(*entry.relative_path.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if _read_plain_file(target, stage="export") != payload:
                raise SnapshotDistributionError(
                    "snapshot_distribution.export_failed",
                    "Snapshot Export copied bytes failed exact re-read verification.",
                    stage="export",
                )
        relative_paths = tuple(
            edition_entry_by_id[item].relative_path for item in included_entry_ids
        )
        if _content_inventory(temporary_root) != tuple(sorted(relative_paths)):
            raise SnapshotDistributionError(
                "snapshot_distribution.export_failed",
                "Snapshot directory Export staging contains an unexpected file inventory.",
                stage="export",
            )
        inventory = _directory_inventory_value(temporary_root, relative_paths)
        inventory_digest = snapshot_digest(canonical_snapshot_json_bytes(inventory))
        os.replace(temporary_root, final_root)
    except SnapshotDistributionError:
        raise
    except OSError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_failed",
            "Snapshot directory Export Artifact could not be published.",
            stage="export",
        ) from error

    # Verify final directory bytes independently after publication.
    final_relative_paths = tuple(
        edition_entry_by_id[item].relative_path for item in included_entry_ids
    )
    if _content_inventory(final_root) != tuple(sorted(final_relative_paths)):
        raise SnapshotDistributionError(
            "snapshot_distribution.export_failed",
            "Published Snapshot directory Export contains an unexpected file inventory.",
            stage="export",
        )
    final_inventory = _directory_inventory_value(
        final_root,
        final_relative_paths,
    )
    final_digest = snapshot_digest(canonical_snapshot_json_bytes(final_inventory))
    if final_digest != inventory_digest:
        raise SnapshotDistributionError(
            "snapshot_distribution.export_failed",
            "Published Snapshot directory Export inventory digest changed.",
            stage="export",
        )

    relative_path = (
        f"snapshots/exports/{snapshot_series_id}/{edition_number}/{artifact_identity}"
    )
    artifact = SnapshotExportArtifact(
        snapshot_export_artifact_id=artifact_identity,
        snapshot_edition=edition.reference,
        export_format="directory_package",
        export_contract_version=export_plan.export_contract_version,
        included_entry_ids=included_entry_ids,
        excluded_entry_ids=excluded_entry_ids,
        packager_id=SNAPSHOT_DIRECTORY_PACKAGER_ID,
        packager_version=SNAPSHOT_DIRECTORY_PACKAGER_VERSION,
        configuration_digest=export_plan.configuration_digest,
        generated_at=generated,
        relative_path=relative_path,
        directory_inventory_digest=inventory_digest,
        validation_result="verified",
        predecessor_export_artifact_id=predecessor_export_artifact_id,
    )
    try:
        state_revision = _commit(root, (artifact,), loaded=loaded)
    except Exception:
        # Export bytes may already be durable even if canonical persistence fails.
        # Preserve them for explicit inspection/recovery rather than deleting history.
        raise
    return SnapshotExportResult(
        state_revision=state_revision,
        export_artifact=artifact,
        export_path=final_root,
    )


def advance_snapshot_current_pointer(
    root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    expected_state_revision: int,
    expected_pointer_revision: int | None,
    expected_current_edition: int | None,
    pointed_by: ActorAttribution,
    authority_reference: str,
    reason: str,
    pointed_at: datetime | None = None,
    pointer_id: str | None = None,
) -> SnapshotPointerResult:
    """Advance one Series Current Pointer with explicit predecessor expectations."""

    try:
        snapshot_series_id = require_identifier(
            snapshot_series_id, "snapshot_series_id"
        )
        edition_number = require_positive_int(edition_number, "edition_number")
        authority_reference = require_text(
            authority_reference, "authority_reference", maximum=500
        )
        reason = require_text(reason, "reason", maximum=1000)
        when = require_aware_datetime(
            pointed_at or _now(), "pointed_at"
        ).astimezone(timezone.utc)
        if not isinstance(pointed_by, ActorAttribution):
            raise VitrineModelValidationError(
                "pointed_by must be ActorAttribution."
            )
        if expected_pointer_revision is not None:
            expected_pointer_revision = require_positive_int(
                expected_pointer_revision, "expected_pointer_revision"
            )
        if expected_current_edition is not None:
            expected_current_edition = require_positive_int(
                expected_current_edition, "expected_current_edition"
            )
    except VitrineModelValidationError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.invalid_request",
            "Snapshot Current Pointer request is invalid.",
            stage="pointer",
        ) from error

    loaded = _load(root, expected_state_revision)
    _edition(loaded.records, snapshot_series_id, edition_number)
    pointers = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotCurrentPointerRevision)
        and item.snapshot_series_id == snapshot_series_id
    )
    predecessor_keys = {
        (item.snapshot_current_pointer_id, item.predecessor_pointer_revision)
        for item in pointers
        if item.predecessor_pointer_revision is not None
    }
    heads = tuple(
        item
        for item in pointers
        if (item.snapshot_current_pointer_id, item.pointer_revision)
        not in predecessor_keys
    )
    if len(heads) > 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.pointer_conflict",
            "Snapshot Series has multiple Current Pointer heads.",
            stage="pointer",
        )
    head = heads[0] if heads else None
    if head is None:
        if expected_pointer_revision is not None or expected_current_edition is not None:
            raise SnapshotDistributionError(
                "snapshot_distribution.pointer_conflict",
                "Snapshot Current Pointer does not yet exist.",
                stage="pointer",
            )
        current_pointer_id = require_identifier(
            pointer_id or _id("snapshot_current_pointer"),
            "snapshot_current_pointer_id",
        )
        revision = 1
        predecessor_revision = None
    else:
        if (
            expected_pointer_revision != head.pointer_revision
            or expected_current_edition != head.edition_number
        ):
            raise SnapshotDistributionError(
                "snapshot_distribution.pointer_conflict",
                "Snapshot Current Pointer changed from the caller's expected predecessor.",
                stage="pointer",
            )
        if edition_number <= head.edition_number:
            raise SnapshotDistributionError(
                "snapshot_distribution.pointer_conflict",
                "Snapshot Current Pointer may only advance to a newer Edition.",
                stage="pointer",
            )
        current_pointer_id = head.snapshot_current_pointer_id
        revision = head.pointer_revision + 1
        predecessor_revision = head.pointer_revision
    pointer = SnapshotCurrentPointerRevision(
        snapshot_current_pointer_id=current_pointer_id,
        pointer_revision=revision,
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
        pointed_at=when,
        pointed_by=pointed_by,
        authority_reference=authority_reference,
        reason=reason,
        predecessor_pointer_revision=predecessor_revision,
    )
    state_revision = _commit(root, (pointer,), loaded=loaded)
    return SnapshotPointerResult(state_revision=state_revision, pointer=pointer)


def _attempt(
    records: tuple[VitrineRecord, ...], snapshot_build_attempt_id: str
) -> SnapshotBuildAttempt:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildAttempt)
        and item.snapshot_build_attempt_id == snapshot_build_attempt_id
    )
    if len(values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.context_not_found",
            "Snapshot Build Attempt does not resolve uniquely.",
            stage="recovery",
        )
    return values[0]


def _attempt_result(
    records: tuple[VitrineRecord, ...], snapshot_build_attempt_id: str
) -> SnapshotBuildAttemptResult | None:
    values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotBuildAttemptResult)
        and item.snapshot_build_attempt_id == snapshot_build_attempt_id
    )
    if len(values) > 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.recovery_conflict",
            "Snapshot Build Attempt has multiple terminal Results.",
            stage="recovery",
        )
    return values[0] if values else None



def _staging_manifest_path(root: str | Path, attempt_id: str) -> Path:
    return snapshot_attempt_staging_root(root, attempt_id) / "internal" / "manifest.json"


def _canonical_edition_identity(value: object) -> tuple[str, int] | None:
    if not isinstance(value, dict):
        return None
    series_id = value.get("snapshot_series_id")
    edition_number = value.get("edition_number")
    if (
        not isinstance(series_id, str)
        or not series_id
        or isinstance(edition_number, bool)
        or not isinstance(edition_number, int)
        or edition_number < 1
    ):
        return None
    return series_id, edition_number


def _manifest_is_verified_for_edition(
    root: str | Path,
    *,
    edition: SnapshotEdition,
    records: tuple[VitrineRecord, ...],
) -> bool:
    seal_values = tuple(
        item
        for item in records
        if isinstance(item, SnapshotSeal) and item.seal_id == edition.seal_id
    )
    if len(seal_values) != 1:
        return False
    seal = seal_values[0]
    path = (
        snapshot_edition_root(
            root, edition.snapshot_series_id, edition.edition_number
        )
        / "internal"
        / "manifest.json"
    )
    try:
        payload = _read_plain_file(path)
        value = _canonical_manifest_value(payload)
        logical = value.get("logical_inventory")
        if not isinstance(logical, dict):
            return False
        return (
            snapshot_digest(payload) == seal.manifest_digest
            and snapshot_logical_inventory_digest(logical)
            == seal.logical_inventory_digest
            and _canonical_edition_identity(value.get("snapshot_edition"))
            == (edition.snapshot_series_id, edition.edition_number)
        )
    except (SnapshotDistributionError, TypeError, ValueError):
        return False


def inspect_snapshot_custody(root: str | Path) -> SnapshotCustodyAudit:
    """Return privacy-minimal diagnostics without adopting, deleting, or repairing state."""

    loaded = _load(root)
    findings: list[SnapshotCustodyFinding] = []
    attempts = {
        item.snapshot_build_attempt_id: item
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttempt)
    }
    results = {
        item.snapshot_build_attempt_id: item
        for item in loaded.records
        if isinstance(item, SnapshotBuildAttemptResult)
    }
    plans = {
        item.snapshot_build_plan_id: item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
    }
    editions = {
        (item.snapshot_series_id, item.edition_number): item
        for item in loaded.records
        if isinstance(item, SnapshotEdition)
    }
    exports = {
        item.snapshot_export_artifact_id: item
        for item in loaded.records
        if isinstance(item, SnapshotExportArtifact)
    }

    for attempt_id, attempt in sorted(attempts.items()):
        result = results.get(attempt_id)
        if result is None:
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.incomplete_attempt",
                    severity="warning",
                    subject_kind="snapshot_build_attempt",
                    subject_id=attempt_id,
                    summary="Snapshot Build Attempt has no terminal Result.",
                )
            )
        elif result.terminal_outcome == "failed":
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.failed_attempt",
                    severity="info",
                    subject_kind="snapshot_build_attempt",
                    subject_id=attempt_id,
                    summary="Snapshot Build Attempt is terminally failed and retained as history.",
                )
            )
        elif result.terminal_outcome == "durability_uncertain":
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.durability_uncertainty",
                    severity="error",
                    subject_kind="snapshot_build_attempt",
                    subject_id=attempt_id,
                    summary="Snapshot Build Attempt records explicit durability uncertainty.",
                )
            )
        staging_manifest = _staging_manifest_path(root, attempt_id)
        if result is None and staging_manifest.exists():
            findings.extend(
                (
                    SnapshotCustodyFinding(
                        code="snapshot.custody.ambiguous_edition_target",
                        severity="error",
                        subject_kind="snapshot_build_attempt",
                        subject_id=attempt_id,
                        summary="Incomplete Attempt staging contains sealing metadata and requires explicit recovery.",
                    ),
                    SnapshotCustodyFinding(
                        code="snapshot.custody.durability_uncertainty",
                        severity="error",
                        subject_kind="snapshot_build_attempt",
                        subject_id=attempt_id,
                        summary="Allocated sealing metadata exists without a terminal Attempt Result.",
                    ),
                )
            )
        plan = plans.get(attempt.snapshot_build_plan_id)
        if plan is not None:
            try:
                lock = inspect_snapshot_series_lock(
                    root, snapshot_series_id=plan.snapshot_series_id
                )
            except SnapshotCustodyError as error:
                if error.code != "snapshot.build_lock_missing":
                    findings.append(
                        SnapshotCustodyFinding(
                            code="snapshot.custody.build_lock_present",
                            severity="error",
                            subject_kind="snapshot_series",
                            subject_id=plan.snapshot_series_id,
                            summary="Snapshot Series build lock exists but could not be validated.",
                        )
                    )
            else:
                if lock.snapshot_build_attempt_id == attempt_id:
                    findings.append(
                        SnapshotCustodyFinding(
                            code="snapshot.custody.build_lock_present",
                            severity="warning",
                            subject_kind="snapshot_series",
                            subject_id=plan.snapshot_series_id,
                            summary="Snapshot Series has an explicit build lock for this Attempt.",
                        )
                    )

    staging_root = snapshot_staging_root(root)
    if staging_root.exists() and staging_root.is_dir() and _plain(staging_root):
        try:
            staging_children = tuple(staging_root.iterdir())
        except OSError:
            staging_children = ()
        for child in staging_children:
            if child.name not in attempts:
                findings.append(
                    SnapshotCustodyFinding(
                        code="snapshot.custody.orphan_staging",
                        severity="warning",
                        subject_kind="snapshot_staging",
                        subject_id=child.name,
                        summary="Snapshot staging custody has no canonical Build Attempt.",
                    )
                )

    locks_root = snapshot_locks_root(root)
    if locks_root.exists() and locks_root.is_dir() and _plain(locks_root):
        known_locked_series = {
            plans[item.snapshot_build_plan_id].snapshot_series_id
            for item in attempts.values()
            if item.snapshot_build_plan_id in plans
        }
        try:
            lock_children = tuple(locks_root.iterdir())
        except OSError:
            lock_children = ()
        for child in lock_children:
            if child.suffix == ".json" and child.stem not in known_locked_series:
                findings.append(
                    SnapshotCustodyFinding(
                        code="snapshot.custody.build_lock_present",
                        severity="warning",
                        subject_kind="snapshot_series",
                        subject_id=child.stem,
                        summary="Snapshot Series lock has no matching canonical Build Attempt context.",
                    )
                )

    for identity, edition in sorted(editions.items()):
        edition_path = snapshot_edition_root(root, *identity)
        subject = f"{identity[0]}:{identity[1]}"
        if not edition_path.exists():
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.canonical_edition_missing_custody",
                    severity="error",
                    subject_kind="snapshot_edition",
                    subject_id=subject,
                    summary="Canonical Snapshot Edition has no immutable Edition custody directory.",
                )
            )
            continue
        if not _manifest_is_verified_for_edition(
            root, edition=edition, records=loaded.records
        ):
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.corrupted_manifest",
                    severity="error",
                    subject_kind="snapshot_edition",
                    subject_id=subject,
                    summary="Snapshot Edition internal Manifest does not reproduce its canonical Seal.",
                )
            )
            continue
        try:
            verify_snapshot_edition(
                root,
                snapshot_series_id=identity[0],
                edition_number=identity[1],
            )
        except SnapshotDistributionError:
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.corrupted_entry",
                    severity="error",
                    subject_kind="snapshot_edition",
                    subject_id=subject,
                    summary="Snapshot Edition Entry custody does not reproduce canonical Materialization state.",
                )
            )

    editions_root = snapshot_editions_root(root)
    if editions_root.exists() and editions_root.is_dir() and _plain(editions_root):
        try:
            series_dirs = tuple(editions_root.iterdir())
        except OSError:
            series_dirs = ()
        for series_dir in series_dirs:
            if not series_dir.is_dir() or not _plain(series_dir):
                findings.append(
                    SnapshotCustodyFinding(
                        code="snapshot.custody.ambiguous_edition_target",
                        severity="error",
                        subject_kind="snapshot_edition_custody",
                        subject_id=series_dir.name,
                        summary="Snapshot Edition custody contains an unsafe or ambiguous Series target.",
                    )
                )
                continue
            try:
                edition_dirs = tuple(series_dir.iterdir())
            except OSError:
                edition_dirs = ()
            for edition_dir in edition_dirs:
                try:
                    number = int(edition_dir.name)
                except ValueError:
                    number = 0
                identity = (series_dir.name, number)
                if number < 1 or not edition_dir.is_dir() or not _plain(edition_dir):
                    findings.append(
                        SnapshotCustodyFinding(
                            code="snapshot.custody.ambiguous_edition_target",
                            severity="error",
                            subject_kind="snapshot_edition_custody",
                            subject_id=f"{series_dir.name}:{edition_dir.name}",
                            summary="Snapshot Edition custody target has an invalid identity or filesystem type.",
                        )
                    )
                elif identity not in editions:
                    findings.append(
                        SnapshotCustodyFinding(
                            code="snapshot.custody.custody_edition_missing_canonical_state",
                            severity="error",
                            subject_kind="snapshot_edition",
                            subject_id=f"{identity[0]}:{identity[1]}",
                            summary="Immutable Edition custody has no canonical Snapshot Edition record.",
                        )
                    )

    for export_id, artifact in sorted(exports.items()):
        try:
            verify_snapshot_export(
                root, snapshot_export_artifact_id=export_id
            )
        except SnapshotDistributionError:
            findings.append(
                SnapshotCustodyFinding(
                    code="snapshot.custody.corrupted_export",
                    severity="error",
                    subject_kind="snapshot_export_artifact",
                    subject_id=export_id,
                    summary="Snapshot Export custody does not reproduce its canonical inventory digest.",
                )
            )

    export_root = snapshot_exports_root(root)
    if export_root.exists() and export_root.is_dir() and _plain(export_root):
        expected_paths = {
            (
                artifact.snapshot_edition.snapshot_series_id,
                artifact.snapshot_edition.edition_number,
                artifact.snapshot_export_artifact_id,
            )
            for artifact in exports.values()
        }
        try:
            series_dirs = tuple(export_root.iterdir())
        except OSError:
            series_dirs = ()
        for series_dir in series_dirs:
            if not series_dir.is_dir() or not _plain(series_dir):
                continue
            try:
                edition_dirs = tuple(series_dir.iterdir())
            except OSError:
                edition_dirs = ()
            for edition_dir in edition_dirs:
                try:
                    number = int(edition_dir.name)
                except ValueError:
                    number = 0
                if number < 1 or not edition_dir.is_dir() or not _plain(edition_dir):
                    continue
                try:
                    artifact_dirs = tuple(edition_dir.iterdir())
                except OSError:
                    artifact_dirs = ()
                for artifact_dir in artifact_dirs:
                    export_identity = (
                        series_dir.name,
                        number,
                        artifact_dir.name,
                    )
                    if export_identity not in expected_paths:
                        findings.append(
                            SnapshotCustodyFinding(
                                code="snapshot.custody.orphan_export",
                                severity="warning",
                                subject_kind="snapshot_export_custody",
                                subject_id=(
                                    f"{export_identity[0]}:"
                                    f"{export_identity[1]}:"
                                    f"{export_identity[2]}"
                                ),
                                summary="Snapshot Export custody has no canonical Export Artifact record.",
                            )
                        )

    findings.sort(key=lambda item: (item.code, item.subject_kind, item.subject_id))
    return SnapshotCustodyAudit(
        canonical_state_revision=loaded.state_revision,
        findings=tuple(findings),
    )

def _sealed_editions_for_attempt(
    root: str | Path,
    records: tuple[VitrineRecord, ...],
    snapshot_build_attempt_id: str,
) -> tuple[int, ...]:
    editions = tuple(item for item in records if isinstance(item, SnapshotEdition))
    by_identity = {
        (item.snapshot_series_id, item.edition_number): item for item in editions
    }
    found: set[int] = set()
    for edition in editions:
        manifest_path = (
            snapshot_edition_root(
                root, edition.snapshot_series_id, edition.edition_number
            )
            / "internal"
            / "manifest.json"
        )
        if not manifest_path.exists():
            continue
        try:
            value = _canonical_manifest_value(_read_plain_file(manifest_path))
        except SnapshotDistributionError:
            continue
        if value.get("snapshot_build_attempt_id") == snapshot_build_attempt_id:
            found.add(edition.edition_number)

    # If Edition publication failed after the canonical seal commit, the verified
    # internal manifest remains in Attempt staging. Recognize that canonical
    # Edition identity so explicit recovery cannot misclassify sealed work.
    staging_manifest = (
        snapshot_attempt_staging_root(root, snapshot_build_attempt_id)
        / "internal"
        / "manifest.json"
    )
    if staging_manifest.exists():
        try:
            value = _canonical_manifest_value(_read_plain_file(staging_manifest))
        except SnapshotDistributionError:
            value = {}
        edition_value = value.get("snapshot_edition")
        if (
            value.get("snapshot_build_attempt_id") == snapshot_build_attempt_id
            and isinstance(edition_value, dict)
        ):
            series_id = edition_value.get("snapshot_series_id")
            edition_number = edition_value.get("edition_number")
            if (
                isinstance(series_id, str)
                and isinstance(edition_number, int)
                and not isinstance(edition_number, bool)
                and (series_id, edition_number) in by_identity
            ):
                found.add(edition_number)
    return tuple(sorted(found))


def inspect_snapshot_attempt_recovery(
    root: str | Path,
    *,
    snapshot_build_attempt_id: str,
) -> SnapshotAttemptRecoveryInspection:
    """Inspect unresolved Attempt state without clearing locks or deleting custody."""

    try:
        snapshot_build_attempt_id = require_identifier(
            snapshot_build_attempt_id, "snapshot_build_attempt_id"
        )
    except VitrineModelValidationError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.invalid_request",
            "Snapshot recovery inspection request is invalid.",
            stage="recovery",
        ) from error
    loaded = _load(root)
    _attempt(loaded.records, snapshot_build_attempt_id)
    result = _attempt_result(loaded.records, snapshot_build_attempt_id)
    staging = snapshot_attempt_staging_root(root, snapshot_build_attempt_id)
    staging_exists = staging.exists()
    residue = False
    if staging_exists:
        if not staging.is_dir() or not _plain(staging):
            residue = True
        else:
            try:
                residue = any(staging.rglob("*"))
            except OSError:
                residue = True
    sealed_editions = _sealed_editions_for_attempt(
        root, loaded.records, snapshot_build_attempt_id
    )
    plan_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id
        == _attempt(loaded.records, snapshot_build_attempt_id).snapshot_build_plan_id
    )
    build_lock_present = False
    build_lock_matches_attempt = False
    build_lock_sha256: str | None = None
    if len(plan_values) == 1:
        try:
            lock = inspect_snapshot_series_lock(
                root, snapshot_series_id=plan_values[0].snapshot_series_id
            )
            build_lock_present = True
            build_lock_matches_attempt = (
                lock.snapshot_build_attempt_id == snapshot_build_attempt_id
                and lock.snapshot_build_plan_id == plan_values[0].snapshot_build_plan_id
            )
            build_lock_sha256 = lock.sha256
        except SnapshotCustodyError as error:
            if error.code != "snapshot.build_lock_missing":
                build_lock_present = True
    return SnapshotAttemptRecoveryInspection(
        snapshot_build_attempt_id=snapshot_build_attempt_id,
        canonical_state_revision=loaded.state_revision,
        terminal_result_id=(
            None if result is None else result.snapshot_build_attempt_result_id
        ),
        staging_exists=staging_exists,
        staging_has_residue=residue,
        build_lock_present=build_lock_present,
        build_lock_matches_attempt=build_lock_matches_attempt,
        build_lock_sha256=build_lock_sha256,
        sealed_edition_numbers=sealed_editions,
    )


def abandon_snapshot_build_attempt_after_recovery(
    root: str | Path,
    *,
    snapshot_build_attempt_id: str,
    expected_state_revision: int,
    recovered_by: ActorAttribution,
    authority_reference: str,
    reason: str,
    completed_at: datetime | None = None,
    result_id: str | None = None,
) -> SnapshotRecoveryResult:
    """Explicitly abandon one unresolved unsealed Attempt; staging is preserved."""

    try:
        snapshot_build_attempt_id = require_identifier(
            snapshot_build_attempt_id, "snapshot_build_attempt_id"
        )
        authority_reference = require_text(
            authority_reference, "authority_reference", maximum=500
        )
        reason = require_text(reason, "reason", maximum=1000)
        when = require_aware_datetime(
            completed_at or _now(), "completed_at"
        ).astimezone(timezone.utc)
        if not isinstance(recovered_by, ActorAttribution):
            raise VitrineModelValidationError(
                "recovered_by must be ActorAttribution."
            )
    except VitrineModelValidationError as error:
        raise SnapshotDistributionError(
            "snapshot_distribution.invalid_request",
            "Snapshot recovery abandonment request is invalid.",
            stage="recovery",
        ) from error

    loaded = _load(root, expected_state_revision)
    attempt = _attempt(loaded.records, snapshot_build_attempt_id)
    if _attempt_result(loaded.records, snapshot_build_attempt_id) is not None:
        raise SnapshotDistributionError(
            "snapshot_distribution.recovery_conflict",
            "Snapshot Build Attempt is already terminal.",
            stage="recovery",
        )
    if _sealed_editions_for_attempt(root, loaded.records, snapshot_build_attempt_id):
        raise SnapshotDistributionError(
            "snapshot_distribution.recovery_unsafe",
            "A sealed Edition is associated with this Attempt; it must not be abandoned.",
            stage="recovery",
        )
    # Internal manifest creation occurs only after Edition identity allocation and
    # complete pre-seal verification. If it exists without visible sealed state,
    # durability is ambiguous and the identity must remain quarantined.
    if _staging_manifest_path(root, snapshot_build_attempt_id).exists():
        raise SnapshotDistributionError(
            "snapshot_distribution.recovery_unsafe",
            "Attempt staging contains allocated sealing metadata; abandonment could reuse an uncertain Edition identity.",
            stage="recovery",
        )
    plan_values = tuple(
        item
        for item in loaded.records
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id == attempt.snapshot_build_plan_id
    )
    if len(plan_values) != 1:
        raise SnapshotDistributionError(
            "snapshot_distribution.context_not_found",
            "Snapshot Build Plan does not resolve for recovery.",
            stage="recovery",
        )
    plan = plan_values[0]
    finding = SnapshotBuildFinding(
        code="snapshot.explicit_recovery_abandonment",
        severity="warning",
        blocking=False,
        summary=(
            "Snapshot Build Attempt was explicitly abandoned after operator "
            "inspection; any staging residue was preserved for diagnostics."
        ),
    )
    outcomes = tuple(
        SnapshotEntryOutcome(
            entry_plan_id=item.entry_plan_id,
            disposition=(
                "reference_only"
                if item.materialization_kind == "reference_only"
                and item.permitted_omission_reason is None
                else "failed_blocking"
            ),
            finding_codes=(
                ()
                if item.materialization_kind == "reference_only"
                and item.permitted_omission_reason is None
                else (finding.code,)
            ),
        )
        for item in plan.entry_plans
    )
    cleanup_findings: tuple[SnapshotBuildFinding, ...] = ()
    try:
        lock = inspect_snapshot_series_lock(
            root, snapshot_series_id=plan.snapshot_series_id
        )
        if (
            lock.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
            and lock.snapshot_build_plan_id == plan.snapshot_build_plan_id
        ):
            release_snapshot_series_lock(
                root,
                snapshot_series_id=plan.snapshot_series_id,
                snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
                expected_sha256=lock.sha256,
            )
        else:
            cleanup_findings = (
                SnapshotBuildFinding(
                    code="snapshot.build_lock_conflict",
                    severity="warning",
                    blocking=False,
                    summary="A different Snapshot Series build lock was preserved.",
                ),
            )
    except SnapshotCustodyError as error:
        if error.code != "snapshot.build_lock_missing":
            cleanup_findings = (
                SnapshotBuildFinding(
                    code=error.code,
                    severity="warning",
                    blocking=False,
                    summary="Snapshot Series build lock remains for explicit recovery.",
                ),
            )
    terminal = SnapshotBuildAttemptResult(
        snapshot_build_attempt_result_id=require_identifier(
            result_id or _id("snapshot_attempt_result"),
            "snapshot_build_attempt_result_id",
        ),
        snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
        completed_at=when,
        terminal_outcome="abandoned_after_explicit_recovery",
        entry_outcomes=outcomes,
        findings=(finding,),
        cleanup_findings=cleanup_findings,
    )
    state_revision = _commit(root, (terminal,), loaded=loaded)
    return SnapshotRecoveryResult(
        state_revision=state_revision, attempt_result=terminal
    )


__all__ = [
    "SNAPSHOT_DIRECTORY_INVENTORY_CONTRACT_VERSION",
    "SNAPSHOT_DIRECTORY_PACKAGER_ID",
    "SNAPSHOT_DIRECTORY_PACKAGER_VERSION",
    "SNAPSHOT_DISTRIBUTION_CODES",
    "SNAPSHOT_CUSTODY_FINDING_CODES",
    "SnapshotAttemptRecoveryInspection",
    "SnapshotCustodyAudit",
    "SnapshotCustodyFinding",
    "SnapshotDistributionError",
    "SnapshotEditionVerification",
    "SnapshotExportResult",
    "SnapshotExportVerification",
    "SnapshotPointerResult",
    "SnapshotRecoveryResult",
    "abandon_snapshot_build_attempt_after_recovery",
    "advance_snapshot_current_pointer",
    "create_snapshot_directory_export",
    "inspect_snapshot_attempt_recovery",
    "inspect_snapshot_custody",
    "verify_snapshot_edition",
    "verify_snapshot_export",
]
