"""Custody, tamper, historical, and post-seal verification for issue #71 Slice 4B."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pds_core.routes import module_work_dir
from pds_core.routing_models import ModuleWorkRef

from vitrine.models import (
    ActorAttribution,
    SnapshotEdition,
    SnapshotExportArtifact,
    SnapshotMaterializationRecord,
    SnapshotSeal,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    advance_snapshot_current_pointer,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.storage import load_current_state, load_state_records

if TYPE_CHECKING:
    from scripts.live_installed_acceptance_portfolio import BuiltPortfolio
    from scripts.live_installed_acceptance_support import NOW, ProducerPublication
else:
    from live_installed_acceptance_portfolio import BuiltPortfolio
    from live_installed_acceptance_support import NOW, ProducerPublication

VERIFIER_REQUEST_CONTRACT = "vitrine_issue71_sealed_verifier_request_v1"


@dataclass(frozen=True, slots=True)
class CustodyVerificationSummary:
    tamper_failure_code: str
    tamper_failure_stage: str
    tampered_edition_preserved: bool
    historical_reload_exact: bool
    producer_source_roots_removed: int
    post_seal_edition_verified: bool
    post_seal_export_verified: bool
    verifier_workspace: Path
    verifier_request: Path


def _teacher_actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="issue71_teacher",
        owning_system="local",
        role_snapshot="teacher",
        display_label_snapshot="Synthetic Issue 71 Teacher",
    )


def _exact_one(values: tuple[object, ...], label: str) -> object:
    if len(values) != 1:
        raise RuntimeError(f"historical {label} did not resolve exactly once")
    return values[0]


def _verify_historical_state(workspace: Path, built: BuiltPortfolio) -> None:
    current = load_current_state(workspace)
    if current.state_revision <= built.state_revision:
        raise RuntimeError("historical reload target did not become historical")
    records = load_state_records(workspace, built.state_revision)
    edition = _exact_one(
        tuple(
            item
            for item in records
            if isinstance(item, SnapshotEdition)
            and item.snapshot_series_id == built.snapshot_series_id
            and item.edition_number == built.edition_number
        ),
        "Snapshot Edition",
    )
    assert isinstance(edition, SnapshotEdition)
    export = _exact_one(
        tuple(
            item
            for item in records
            if isinstance(item, SnapshotExportArtifact)
            and item.snapshot_export_artifact_id == built.snapshot_export_artifact_id
        ),
        "Snapshot Export",
    )
    assert isinstance(export, SnapshotExportArtifact)
    seal = _exact_one(
        tuple(
            item
            for item in records
            if isinstance(item, SnapshotSeal) and item.seal_id == edition.seal_id
        ),
        "Snapshot Seal",
    )
    assert isinstance(seal, SnapshotSeal)
    materializations = tuple(
        item
        for item in records
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition == edition.reference
    )
    counts = Counter(item.materialization_kind for item in materializations)
    if dict(sorted(counts.items())) != built.materialization_counts:
        raise RuntimeError("historical materialization inventory drifted")
    if (
        seal.manifest_digest.value != built.edition_manifest_sha256
        or seal.logical_inventory_digest.value
        != built.edition_logical_inventory_sha256
        or export.directory_inventory_digest.value
        != built.export_directory_inventory_sha256
        or export.snapshot_edition != edition.reference
    ):
        raise RuntimeError("historical Snapshot custody identity/digest drifted")


def _tamper_export(workspace: Path, work_root: Path, built: BuiltPortfolio) -> tuple[str, str]:
    tampered = work_root / "tampered-export-workspace"
    if tampered.exists():
        raise RuntimeError("tamper workspace must begin absent")
    shutil.copytree(workspace, tampered)
    verified = verify_snapshot_export(
        tampered,
        snapshot_export_artifact_id=built.snapshot_export_artifact_id,
    )
    if not verified.verified_file_paths:
        raise RuntimeError("Snapshot Export has no byte-bearing files to tamper")
    relative_export = built.export_path.relative_to(workspace)
    target = tampered / relative_export
    target = target.joinpath(*verified.verified_file_paths[0].split("/"))
    with target.open("ab") as handle:
        handle.write(b"\nISSUE71_TAMPER\n")
    try:
        verify_snapshot_export(
            tampered,
            snapshot_export_artifact_id=built.snapshot_export_artifact_id,
        )
    except SnapshotDistributionError as error:
        if error.code != "snapshot_distribution.verification_failed":
            raise RuntimeError("tampered Export failed with the wrong verifier code") from error
        verify_snapshot_edition(
            tampered,
            snapshot_series_id=built.snapshot_series_id,
            edition_number=built.edition_number,
        )
        return error.code, error.stage
    raise RuntimeError("tampered Snapshot Export unexpectedly verified")


def _remove_producer_sources(
    workspace: Path,
    publications: tuple[ProducerPublication, ...],
) -> int:
    removed = 0
    for publication in publications:
        root = module_work_dir(
            workspace,
            ModuleWorkRef(
                module_id=publication.module_id,
                class_id=publication.class_id,
                work_id=publication.work_id,
            ),
        )
        if not root.is_dir():
            raise RuntimeError("expected producer work root is unavailable before removal")
        shutil.rmtree(root)
        removed += 1
    if removed != 3:
        raise RuntimeError("producer source removal cardinality drifted")
    return removed


def _write_verifier_request(
    path: Path,
    *,
    built: BuiltPortfolio,
    current_state_revision: int,
) -> None:
    payload = {
        "contract_version": VERIFIER_REQUEST_CONTRACT,
        "snapshot_series_id": built.snapshot_series_id,
        "edition_number": built.edition_number,
        "snapshot_export_artifact_id": built.snapshot_export_artifact_id,
        "edition_manifest_sha256": built.edition_manifest_sha256,
        "edition_logical_inventory_sha256": built.edition_logical_inventory_sha256,
        "export_directory_inventory_sha256": built.export_directory_inventory_sha256,
        "historical_state_revision": built.state_revision,
        "current_state_revision": current_state_revision,
    }
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def run_custody_verification(
    workspace: Path,
    *,
    work_root: Path,
    publications: tuple[ProducerPublication, ...],
    built: BuiltPortfolio,
) -> CustodyVerificationSummary:
    """Exercise immutable custody after sealing without consulting producer readers."""

    verify_snapshot_edition(
        workspace,
        snapshot_series_id=built.snapshot_series_id,
        edition_number=built.edition_number,
    )
    verify_snapshot_export(
        workspace,
        snapshot_export_artifact_id=built.snapshot_export_artifact_id,
    )

    pointer = advance_snapshot_current_pointer(
        workspace,
        snapshot_series_id=built.snapshot_series_id,
        edition_number=built.edition_number,
        expected_state_revision=built.state_revision,
        expected_pointer_revision=None,
        expected_current_edition=None,
        pointed_by=_teacher_actor(),
        authority_reference="issue_71:synthetic_current_pointer",
        reason="Make the sealed/exported state an exact historical reload target.",
        pointed_at=NOW,
        pointer_id="issue71_snapshot_current_pointer",
    )
    if pointer.pointer.pointer_revision != 1:
        raise RuntimeError("Snapshot Current Pointer did not begin at revision 1")
    _verify_historical_state(workspace, built)

    tamper_code, tamper_stage = _tamper_export(workspace, work_root, built)

    verifier_workspace = work_root / "sealed-verifier-workspace"
    if verifier_workspace.exists():
        raise RuntimeError("sealed verifier workspace must begin absent")
    shutil.copytree(workspace, verifier_workspace)
    removed = _remove_producer_sources(verifier_workspace, publications)

    edition = verify_snapshot_edition(
        verifier_workspace,
        snapshot_series_id=built.snapshot_series_id,
        edition_number=built.edition_number,
    )
    export = verify_snapshot_export(
        verifier_workspace,
        snapshot_export_artifact_id=built.snapshot_export_artifact_id,
    )
    if (
        edition.manifest_digest.value != built.edition_manifest_sha256
        or edition.logical_inventory_digest.value
        != built.edition_logical_inventory_sha256
        or export.directory_inventory_digest.value
        != built.export_directory_inventory_sha256
    ):
        raise RuntimeError("post-seal verification digest drifted after producer removal")

    verifier_request = work_root / "sealed-verifier-request.json"
    _write_verifier_request(
        verifier_request,
        built=built,
        current_state_revision=pointer.state_revision,
    )
    return CustodyVerificationSummary(
        tamper_failure_code=tamper_code,
        tamper_failure_stage=tamper_stage,
        tampered_edition_preserved=True,
        historical_reload_exact=True,
        producer_source_roots_removed=removed,
        post_seal_edition_verified=True,
        post_seal_export_verified=True,
        verifier_workspace=verifier_workspace,
        verifier_request=verifier_request,
    )
