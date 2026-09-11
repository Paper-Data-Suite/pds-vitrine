"""Validate Vitrine against opaque whole-workspace backup/restore relocation."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pds_core.module_operations import (
    ModuleAttentionReport,
    ModuleOperationsRequest,
    ModuleReadinessReport,
)

from scripts.curation_fixture_support import ACTOR, fixed_clock
from scripts.snapshot_fixture_support import (
    SnapshotFixtureWorkspace,
    build_snapshot_fixture_workspace,
)
from vitrine.models import (
    DigestReference,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotSeries,
)
from vitrine.operations_provider import (
    evaluate_vitrine_attention_for_core,
    evaluate_vitrine_readiness,
)
from vitrine.snapshot_distribution import (
    create_snapshot_directory_export,
    inspect_snapshot_attempt_recovery,
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
    SnapshotRendererRegistry,
    SnapshotSourceProviderDescriptor,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
    SnapshotSourceResult,
)
from vitrine.snapshot_services import (
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import (
    list_state_revisions,
    load_current_records,
    load_current_state,
    load_state_records,
    load_state_revision,
)
from vitrine.working_composition import prepare_working_composition


@dataclass(frozen=True, slots=True, order=True)
class _WorkspaceEntryDigest:
    relative_path: str
    kind: str
    byte_size: int | None
    sha256: str | None


@dataclass(frozen=True, slots=True)
class _PreparedAttempt:
    setup: SnapshotFixtureWorkspace
    plan: SnapshotBuildPlan
    attempt_id: str
    source_root: Path


class _AllowAuthority:
    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        del request
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="workspace_relocation_fixture_authority",
        )


class _SourceProvider:
    def __init__(self, root: Path, entry: SnapshotEntryPlan) -> None:
        if entry.producer_module_id is None:
            raise RuntimeError("copied Snapshot entry is missing producer_module_id")
        if entry.projection_kind is None:
            raise RuntimeError("copied Snapshot entry is missing projection_kind")
        if entry.projection_contract_version is None:
            raise RuntimeError(
                "copied Snapshot entry is missing projection_contract_version"
            )
        if entry.source_artifact is None:
            raise RuntimeError("copied Snapshot entry is missing source_artifact")
        self.root = root
        self.descriptor = SnapshotSourceProviderDescriptor(
            provider_id="workspace_relocation_source_provider",
            provider_version="1",
            producer_module_id=entry.producer_module_id,
            projection_kind=entry.projection_kind,
            projection_contract_version=entry.projection_contract_version,
            artifact_kind=entry.source_artifact.artifact_kind,
            representation_kind=entry.source_artifact.representation_kind,
        )

    def resolve(self, request: SnapshotSourceRequest) -> SnapshotSourceResult:
        artifact = request.entry_plan.source_artifact
        if artifact is None or artifact.source_locator is None:
            raise RuntimeError("copied Snapshot source locator is unavailable")
        if request.entry_plan.source_publication_id is None:
            raise RuntimeError("copied Snapshot publication identity is unavailable")
        return SnapshotSourceResult(
            provider_id=self.descriptor.provider_id,
            provider_version=self.descriptor.provider_version,
            source_publication_id=request.entry_plan.source_publication_id,
            source_artifact_id=artifact.artifact_id,
            source_root=self.root,
            source_relative_path=artifact.source_locator,
        )

    def confirm_stability(
        self, request: SnapshotSourceRequest, result: SnapshotSourceResult
    ) -> bool:
        del request, result
        return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _workspace_inventory(root: Path) -> tuple[_WorkspaceEntryDigest, ...]:
    entries: list[_WorkspaceEntryDigest] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise AssertionError(f"workspace contains unexpected symlink: {relative}")
        if path.is_dir():
            entries.append(
                _WorkspaceEntryDigest(
                    relative_path=relative,
                    kind="directory",
                    byte_size=None,
                    sha256=None,
                )
            )
            continue
        if not path.is_file():
            raise AssertionError(f"workspace contains unsupported entry: {relative}")
        entries.append(
            _WorkspaceEntryDigest(
                relative_path=relative,
                kind="file",
                byte_size=path.stat().st_size,
                sha256=_sha256(path),
            )
        )
    return tuple(entries)


def _source_entry(
    setup: SnapshotFixtureWorkspace,
    selection: PortfolioSelection,
    placement: PortfolioPlacement,
    position: int,
) -> SnapshotEntryPlan:
    candidate = next(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == selection.candidate_id
    )
    artifact = candidate.source_endpoint.source_artifact
    if artifact is None or artifact.source_locator is None:
        raise RuntimeError("fixture Candidate is missing its copied source artifact")
    content_class = {
        "original_student_work": "student_work",
        "rendered_feedback": "feedback",
        "assessment_summary": "assessment_summary",
        "collaborative_artifact": "student_work",
    }[artifact.artifact_kind]
    return SnapshotEntryPlan(
        entry_plan_id=f"relocation_entry_{placement.section_id}",
        plan_position=position,
        section_id=placement.section_id,
        ordinal=1,
        semantic_role="selected_work",
        materialization_kind="copied_source",
        content_class=content_class,
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            candidate.source_endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=f"{placement.section_id}/work-{position}.txt",
        media_type=artifact.media_type,
    )


def _prepare_attempt(base: Path) -> _PreparedAttempt:
    setup = build_snapshot_fixture_workspace(base / "fixture")
    series_result = create_snapshot_series(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        audience_context_id=setup.audience.audience_context_id,
        snapshot_purpose="improvement",
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    series = next(
        item for item in series_result.records if isinstance(item, SnapshotSeries)
    )
    request_result = request_snapshot_build(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=setup.composition.composition_revision,
        requested_by=ACTOR,
        idempotency_key="workspace-relocation-request",
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    request = next(
        item
        for item in request_result.records
        if isinstance(item, SnapshotBuildRequest)
    )
    entries = (
        _source_entry(
            setup,
            setup.baseline_selection,
            setup.baseline_placement,
            1,
        ),
        _source_entry(
            setup,
            setup.later_selection,
            setup.later_placement,
            2,
        ),
    )
    export = SnapshotExportPlan(
        export_plan_id="workspace_relocation_export_plan",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=DigestReference(value="a" * 64),
    )
    plan_result = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=ACTOR,
        acknowledged_obligation_codes=setup.inventory.unresolved_obligation_codes,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    plan = next(
        item for item in plan_result.records if isinstance(item, SnapshotBuildPlan)
    )
    started = start_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=ACTOR,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    source_root = (base / "producer-source").resolve()
    for entry in entries:
        artifact = entry.source_artifact
        if artifact is None or artifact.source_locator is None:
            raise RuntimeError("fixture copied source locator is unavailable")
        target = source_root.joinpath(*artifact.source_locator.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            f"opaque relocation bytes for {artifact.artifact_id}\n".encode("utf-8")
        )
    return _PreparedAttempt(
        setup=setup,
        plan=plan,
        attempt_id=started.attempt.snapshot_build_attempt_id,
        source_root=source_root,
    )


def _core_readiness(workspace: Path) -> ModuleReadinessReport:
    return evaluate_vitrine_readiness(
        ModuleOperationsRequest(
            workspace_root=workspace,
            active_school_year="2026-2027",
            class_id="english-10",
        )
    )


def _core_attention(workspace: Path) -> ModuleAttentionReport:
    return evaluate_vitrine_attention_for_core(
        ModuleOperationsRequest(
            workspace_root=workspace,
            active_school_year="2026-2027",
        )
    )


def _assert_raw_copy(source: Path, restored: Path) -> tuple[_WorkspaceEntryDigest, ...]:
    before = _workspace_inventory(source)
    shutil.copytree(source, restored)
    after = _workspace_inventory(restored)
    if after != before:
        raise AssertionError("restored workspace differs from source byte inventory")
    return before


def _validate_sealed_snapshot_relocation(base: Path) -> None:
    prepared = _prepare_attempt(base / "sealed")
    setup = prepared.setup
    provider = _SourceProvider(prepared.source_root, prepared.plan.entry_plans[0])
    executed = execute_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_attempt_id=prepared.attempt_id,
        expected_state_revision=setup.state_revision,
        authority_gate=_AllowAuthority(),
        source_providers=SnapshotSourceProviderRegistry((provider,)),
        renderers=SnapshotRendererRegistry(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    sealed = seal_snapshot_build_attempt(
        setup.workspace,
        execution=executed,
        expected_state_revision=setup.state_revision,
        sealed_by=ACTOR,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    if sealed.edition_path is None:
        raise AssertionError("fixture Snapshot Edition was not published")
    try:
        sealed.edition_path.relative_to(setup.workspace)
    except ValueError as error:
        raise AssertionError("Snapshot Edition escaped the shared workspace") from error

    exported = create_snapshot_directory_export(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        export_plan_id=prepared.plan.export_plans[0].export_plan_id,
        expected_state_revision=setup.state_revision,
        generated_at=fixed_clock(),
        artifact_id="workspace_relocation_export",
    )

    try:
        exported.export_path.relative_to(setup.workspace)
    except ValueError as error:
        raise AssertionError("Snapshot Export escaped the shared workspace") from error

    source_state = load_current_state(setup.workspace)
    source_records = load_current_records(setup.workspace)
    source_revision_numbers = list_state_revisions(setup.workspace)
    if not source_revision_numbers:
        raise AssertionError("fixture has no canonical Vitrine state revisions")
    historical_revision_number = source_revision_numbers[0]
    source_historical_revision = load_state_revision(
        setup.workspace, historical_revision_number
    )
    source_historical_records = load_state_records(
        setup.workspace, historical_revision_number
    )
    source_readiness = _core_readiness(setup.workspace)
    source_attention = _core_attention(setup.workspace)
    source_working = prepare_working_composition(setup.workspace, setup.portfolio_id)
    source_custody = inspect_snapshot_custody(setup.workspace)
    source_edition_verification = verify_snapshot_edition(
        setup.workspace,
        snapshot_series_id=sealed.edition.snapshot_series_id,
        edition_number=sealed.edition.edition_number,
        verified_at=fixed_clock(),
    )
    source_export_verification = verify_snapshot_export(
        setup.workspace,
        snapshot_export_artifact_id=(
            exported.export_artifact.snapshot_export_artifact_id
        ),
        verified_at=fixed_clock(),
    )
    if source_readiness.evaluation != "evaluated" or source_readiness.ready is not True:
        raise AssertionError("healthy source workspace did not evaluate ready")

    source_inventory = _workspace_inventory(setup.workspace)
    restored = base / "sealed-restored-workspace"
    copied_inventory = _assert_raw_copy(setup.workspace, restored)
    if copied_inventory != source_inventory:
        raise AssertionError("source workspace changed during relocation copy")

    shutil.rmtree(setup.workspace)
    shutil.rmtree(prepared.source_root)
    if setup.workspace.exists() or prepared.source_root.exists():
        raise AssertionError("source state still exists after relocation isolation")

    if load_current_state(restored) != source_state:
        raise AssertionError("restored canonical current-state identity changed")
    if load_current_records(restored) != source_records:
        raise AssertionError("restored canonical record projection changed")
    if list_state_revisions(restored) != source_revision_numbers:
        raise AssertionError("restored canonical state-revision inventory changed")
    if (
        load_state_revision(restored, historical_revision_number)
        != source_historical_revision
    ):
        raise AssertionError("restored historical state revision changed")
    if (
        load_state_records(restored, historical_revision_number)
        != source_historical_records
    ):
        raise AssertionError("restored historical record projection changed")
    if _core_readiness(restored) != source_readiness:
        raise AssertionError("restored Core readiness projection changed")
    if _core_attention(restored) != source_attention:
        raise AssertionError("restored Core attention projection changed")
    if prepare_working_composition(restored, setup.portfolio_id) != source_working:
        raise AssertionError("restored Working Composition projection changed")
    if inspect_snapshot_custody(restored) != source_custody:
        raise AssertionError("restored Snapshot custody projection changed")
    if (
        verify_snapshot_edition(
            restored,
            snapshot_series_id=sealed.edition.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            verified_at=fixed_clock(),
        )
        != source_edition_verification
    ):
        raise AssertionError("restored Snapshot Edition verification changed")
    if (
        verify_snapshot_export(
            restored,
            snapshot_export_artifact_id=(
                exported.export_artifact.snapshot_export_artifact_id
            ),
            verified_at=fixed_clock(),
        )
        != source_export_verification
    ):
        raise AssertionError("restored Snapshot Export verification changed")
    if _workspace_inventory(restored) != copied_inventory:
        raise AssertionError("restored workspace was mutated by read/verify workflows")


def _validate_recovery_state_relocation(base: Path) -> None:
    prepared = _prepare_attempt(base / "recovery")
    setup = prepared.setup
    residue = (
        setup.workspace
        / "vitrine"
        / "snapshots"
        / "staging"
        / prepared.attempt_id
        / "content"
        / "relocation-residue.bin"
    )
    residue.write_bytes(b"unresolved Snapshot recovery residue\n")

    source_recovery = inspect_snapshot_attempt_recovery(
        setup.workspace,
        snapshot_build_attempt_id=prepared.attempt_id,
    )
    if not source_recovery.recovery_required:
        raise AssertionError("fixture did not preserve unresolved Snapshot recovery")
    source_attention = _core_attention(setup.workspace)
    recovery_summaries = tuple(
        item
        for item in source_attention.summaries
        if item.code == "vitrine_snapshot_recovery_required"
    )
    if len(recovery_summaries) != 1 or recovery_summaries[0].count != 1:
        raise AssertionError("source attention did not expose Snapshot recovery")
    source_state = load_current_state(setup.workspace)

    restored = base / "recovery-restored-workspace"
    copied_inventory = _assert_raw_copy(setup.workspace, restored)
    shutil.rmtree(setup.workspace)
    shutil.rmtree(prepared.source_root)

    restored_recovery = inspect_snapshot_attempt_recovery(
        restored,
        snapshot_build_attempt_id=prepared.attempt_id,
    )
    if restored_recovery != source_recovery:
        raise AssertionError("restore altered unresolved Snapshot recovery state")
    if _core_attention(restored) != source_attention:
        raise AssertionError("restore altered unresolved Vitrine attention")
    if load_current_state(restored) != source_state:
        raise AssertionError("restore advanced or rewrote canonical state")
    if _workspace_inventory(restored) != copied_inventory:
        raise AssertionError("recovery inspection repaired or rewrote restored bytes")


def validate_workspace_relocation(base: Path) -> None:
    """Exercise sealed and unresolved Vitrine state after raw root relocation."""
    root = base.resolve()
    root.mkdir(parents=True, exist_ok=True)
    _validate_sealed_snapshot_relocation(root)
    _validate_recovery_state_relocation(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--work-root",
        type=Path,
        help="Optional empty parent used for validation work.",
    )
    args = parser.parse_args(argv)
    try:
        if args.work_root is not None:
            validate_workspace_relocation(args.work_root)
        else:
            with tempfile.TemporaryDirectory(
                prefix="vitrine-workspace-relocation-"
            ) as temporary:
                validate_workspace_relocation(Path(temporary))
    except (AssertionError, OSError, RuntimeError, ValueError) as error:
        print(
            f"Vitrine workspace relocation validation failed: {error}",
            file=sys.stderr,
        )
        return 1
    print("PASS opaque whole-workspace Vitrine relocation validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
