#!/usr/bin/env python3
"""Execute and verify the representative improvement Portfolio vertical slice."""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.improvement_portfolio_fixture_support import (
    PORTFOLIO_ID,
    PROFILE_BINDING_ID,
    STUDENT,
    TEACHER,
    ImprovementPortfolioFixture,
    build_improvement_portfolio_fixture,
    fixed_clock,
)
from scripts.validate_snapshot_workflows import (
    EXPORT_CONFIGURATION_BYTES,
    REFLECTION_CONFIGURATION_BYTES,
    REFLECTION_RENDERER_CONTRACT,
    REFLECTION_RENDERER_ID,
    REFLECTION_RENDERER_VERSION,
    REFLECTION_TEMPLATE_BYTES,
    _digest,
    _FixtureAuthorityGate,
    _provider_registry,
    _ReflectionFixtureRenderer,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CandidateEvaluation,
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRevision,
    PortfolioSelection,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotEdition,
    SnapshotEntry,
    SnapshotEntryPlan,
    SnapshotExportArtifact,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeries,
    VitrineRecord,
)
from vitrine.snapshot_custody import SnapshotCustodyError, inspect_snapshot_series_lock
from vitrine.snapshot_distribution import (
    advance_snapshot_current_pointer,
    create_snapshot_directory_export,
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import SnapshotRendererRegistry
from vitrine.snapshot_services import (
    SnapshotAttemptExecutionResult,
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import load_current_records


class ImprovementValidationError(RuntimeError):
    """Privacy-minimal deterministic vertical-slice failure."""


EXPECTED_ENTRY_PATHS = (
    "baseline/argument.txt",
    "later/argument.txt",
    "later/student-feedback.txt",
    "reflection/student-comparison.md",
)


@dataclass(frozen=True, slots=True)
class ImmutableByteInventory:
    edition_identity: tuple[str, int]
    manifest_sha256: str
    logical_inventory_sha256: str
    entry_inventory: tuple[tuple[str, int, str], ...]
    seal_id: str
    export_artifact_id: str
    export_inventory_sha256: str
    edition_files: tuple[tuple[str, int, str], ...]
    export_files: tuple[tuple[str, int, str], ...]


@dataclass(frozen=True, slots=True)
class ImprovementValidationReport:
    subject_id: str
    profile_binding_id: str
    candidate_ids: tuple[str, ...]
    selection_ids: tuple[str, ...]
    arrangement_order: tuple[str, ...]
    reflection_id: str
    composition_revision: int
    snapshot_series_id: str
    build_request_id: str
    build_plan_id: str
    build_plan_fingerprint: str
    build_attempt_id: str
    edition_identity: tuple[str, int]
    seal_id: str
    manifest_sha256: str
    logical_inventory_sha256: str
    export_artifact_id: str
    export_inventory_sha256: str
    entry_inventory: tuple[tuple[str, int, str], ...]


def _records(setup: ImprovementPortfolioFixture) -> tuple[VitrineRecord, ...]:
    return load_current_records(setup.workspace)


def _candidate_for_selection(
    setup: ImprovementPortfolioFixture, selection: PortfolioSelection
) -> PortfolioCandidate:
    values = tuple(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioCandidate) and item.candidate_id == selection.candidate_id
    )
    if len(values) != 1:
        raise ImprovementValidationError("exact Selection Candidate did not resolve")
    return values[0]


def _evaluation_for_candidate(
    setup: ImprovementPortfolioFixture, candidate: PortfolioCandidate
) -> CandidateEvaluation:
    values = tuple(
        item
        for item in _records(setup)
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == candidate.candidate_evaluation_id
    )
    if len(values) != 1:
        raise ImprovementValidationError("exact Candidate Evaluation did not resolve")
    return values[0]


def _copied_entry(
    setup: ImprovementPortfolioFixture,
    *,
    source_record_id: str,
    entry_plan_id: str,
    position: int,
    ordinal: int,
    semantic_role: str,
    target_relative_path: str,
) -> SnapshotEntryPlan:
    selection = setup.selection(source_record_id)
    placement = setup.placement(source_record_id)
    candidate = _candidate_for_selection(setup, selection)
    evaluation = _evaluation_for_candidate(setup, candidate)
    artifact = candidate.source_endpoint.source_artifact
    if artifact is None or artifact.source_locator is None:
        raise ImprovementValidationError("copied Candidate lacks an exact source Artifact")
    content_class = (
        "student_work" if artifact.artifact_kind == "original_student_work" else "feedback"
    )
    return SnapshotEntryPlan(
        entry_plan_id=entry_plan_id,
        plan_position=position,
        section_id=placement.section_id,
        ordinal=ordinal,
        semantic_role=semantic_role,
        materialization_kind="copied_source",
        content_class=content_class,
        selection_id=selection.selection_id,
        placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            candidate.source_endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=target_relative_path,
        media_type=artifact.media_type,
    )


def _entry_plans(setup: ImprovementPortfolioFixture) -> tuple[SnapshotEntryPlan, ...]:
    reflection = setup.reflection
    return (
        _copied_entry(
            setup,
            source_record_id="baseline_argument",
            entry_plan_id="entry-plan-imp-baseline-work",
            position=1,
            ordinal=1,
            semantic_role="baseline_work",
            target_relative_path="baseline/argument.txt",
        ),
        _copied_entry(
            setup,
            source_record_id="revised_argument",
            entry_plan_id="entry-plan-imp-later-work",
            position=2,
            ordinal=1,
            semantic_role="later_work",
            target_relative_path="later/argument.txt",
        ),
        _copied_entry(
            setup,
            source_record_id="revised_feedback",
            entry_plan_id="entry-plan-imp-student-feedback",
            position=3,
            ordinal=2,
            semantic_role="student_feedback",
            target_relative_path="later/student-feedback.txt",
        ),
        SnapshotEntryPlan(
            entry_plan_id="entry-plan-imp-student-reflection",
            plan_position=4,
            section_id="reflection",
            ordinal=1,
            semantic_role="student_reflection",
            materialization_kind="generated_vitrine",
            content_class="reflection",
            target_relative_path="reflection/student-comparison.md",
            media_type="text/markdown",
            renderer_id=REFLECTION_RENDERER_ID,
            renderer_version=REFLECTION_RENDERER_VERSION,
            renderer_contract_version=REFLECTION_RENDERER_CONTRACT,
            renderer_configuration_digest=_digest(REFLECTION_CONFIGURATION_BYTES),
            renderer_template_digest=_digest(REFLECTION_TEMPLATE_BYTES),
            input_references=(
                SnapshotInputReference(
                    record_type="portfolio_reflection",
                    record_id=reflection.reflection_id,
                    record_revision=reflection.reflection_revision,
                ),
                SnapshotInputReference(
                    record_type="working_portfolio_composition_revision",
                    record_id=setup.composition.portfolio_id,
                    record_revision=setup.composition.composition_revision,
                ),
            ),
        ),
    )


def _start_pipeline(
    setup: ImprovementPortfolioFixture,
) -> tuple[SnapshotSeries, SnapshotBuildRequest, SnapshotBuildPlan, SnapshotBuildAttempt]:
    created = create_snapshot_series(
        setup.workspace,
        portfolio_id=PORTFOLIO_ID,
        audience_context_id=setup.audience.audience_context_id,
        snapshot_purpose="improvement",
        created_by=TEACHER,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    series = next(item for item in created.records if isinstance(item, SnapshotSeries))
    requested = request_snapshot_build(
        setup.workspace,
        snapshot_series_id=series.snapshot_series_id,
        composition_revision=setup.composition.composition_revision,
        requested_by=STUDENT,
        idempotency_key="representative-improvement-slice-v1",
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    request = next(item for item in requested.records if isinstance(item, SnapshotBuildRequest))
    entries = _entry_plans(setup)
    export = SnapshotExportPlan(
        export_plan_id="export-plan-imp-directory",
        export_format="directory_package",
        export_contract_version="1",
        included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
        excluded_entry_plan_ids=(),
        configuration_digest=_digest(EXPORT_CONFIGURATION_BYTES),
    )
    planned = plan_snapshot_build(
        setup.workspace,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=entries,
        export_plans=(export,),
        planned_by=TEACHER,
        acknowledged_obligation_codes=setup.inventory.unresolved_obligation_codes,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    plan = next(item for item in planned.records if isinstance(item, SnapshotBuildPlan))
    started = start_snapshot_build_attempt(
        setup.workspace,
        snapshot_build_plan_id=plan.snapshot_build_plan_id,
        started_by=TEACHER,
        expected_state_revision=setup.state_revision,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return series, request, plan, started.attempt


def _file_inventory(root: Path) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (
            path.relative_to(root).as_posix(),
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted((item for item in root.rglob("*") if item.is_file()))
    )


def _capture_inventory(
    setup: ImprovementPortfolioFixture,
    *,
    edition: SnapshotEdition,
    seal_id: str,
    manifest_sha256: str,
    logical_inventory_sha256: str,
    edition_path: Path,
    export: SnapshotExportArtifact,
    export_path: Path,
) -> ImmutableByteInventory:
    materializations = {
        item.materialization_id: item
        for item in _records(setup)
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition == edition.reference
    }
    entry_rows: list[tuple[str, int, str]] = []
    for item in _records(setup):
        if not isinstance(item, SnapshotEntry) or item.snapshot_edition != edition.reference:
            continue
        materialization = materializations[item.materialization_id]
        if materialization.byte_size is None or materialization.output_digest is None:
            raise ImprovementValidationError("Entry Materialization digest/size is absent")
        entry_rows.append(
            (item.relative_path, materialization.byte_size, materialization.output_digest.value)
        )
    entries = tuple(sorted(entry_rows))
    return ImmutableByteInventory(
        edition_identity=(edition.snapshot_series_id, edition.edition_number),
        manifest_sha256=manifest_sha256,
        logical_inventory_sha256=logical_inventory_sha256,
        entry_inventory=entries,
        seal_id=seal_id,
        export_artifact_id=export.snapshot_export_artifact_id,
        export_inventory_sha256=export.directory_inventory_digest.value,
        edition_files=_file_inventory(edition_path),
        export_files=_file_inventory(export_path),
    )


def _assert_curation(setup: ImprovementPortfolioFixture) -> tuple[str, ...]:
    records = _records(setup)
    if len(setup.publications) != 2 or len(setup.evaluations) != 3 or len(setup.candidates) != 3:
        raise ImprovementValidationError("Candidate discovery inventory is not exact")
    if any(isinstance(item, SnapshotEdition) for item in records):
        raise ImprovementValidationError("curation unexpectedly fabricated a Snapshot Edition")
    if len(setup.proposals) != 3 or len(setup.decisions) != 3 or len(setup.selections) != 3:
        raise ImprovementValidationError("explicit Selection workflow inventory is not exact")
    if any(item.decision != "accepted" for item in setup.decisions):
        raise ImprovementValidationError("a required Selection decision was not accepted")
    display_snapshots = tuple(
        item for item in records if isinstance(item, PortfolioSubjectDisplaySnapshot)
    )
    identity_decisions = tuple(
        item for item in records if isinstance(item, PortfolioSubjectIdentityDecision)
    )
    lifecycle = tuple(
        item for item in records if isinstance(item, PortfolioProfileLifecycleEvent)
    )
    bindings = tuple(
        item for item in records if isinstance(item, PortfolioProfileBinding)
    )
    if len(display_snapshots) != 2:
        raise ImprovementValidationError(
            "Subject services did not preserve two exact display snapshots"
        )
    if sorted(item.decision_type for item in identity_decisions) != [
        "confirm_link",
        "confirm_link",
        "create_subject",
    ]:
        raise ImprovementValidationError(
            "Subject services did not preserve exact identity decisions"
        )
    if len(lifecycle) != 1 or lifecycle[0].event_kind != "activated":
        raise ImprovementValidationError(
            "Profile service did not preserve exact activation history"
        )
    if len(bindings) != 1 or bindings[0].profile_binding_id != PROFILE_BINDING_ID:
        raise ImprovementValidationError(
            "Profile service did not preserve the exact active Binding"
        )
    profiles = tuple(
        item
        for item in records
        if isinstance(item, PortfolioProfileRevision)
        and item.reference == setup.composition.profile_revision
    )
    if len(profiles) != 1:
        raise ImprovementValidationError("exact improvement Profile did not resolve")
    profile = profiles[0]
    if tuple(item.section_id for item in profile.sections) != (
        "baseline",
        "later_work",
        "reflection",
    ):
        raise ImprovementValidationError(
            "improvement Profile does not preserve baseline/later/reflection sections"
        )
    reflection_section = profile.sections[2]
    if (
        reflection_section.reflection_requirement != "required"
        or reflection_section.minimum_placements != 0
        or reflection_section.maximum_placements != 0
    ):
        raise ImprovementValidationError(
            "reflection section does not preserve generated-Reflection semantics"
        )

    state = project_curation_state(records)
    baseline = state.current_arrangement(PORTFOLIO_ID, PROFILE_BINDING_ID, "baseline")
    later = state.current_arrangement(PORTFOLIO_ID, PROFILE_BINDING_ID, "later_work")
    expected_later = (
        setup.placement("revised_argument").placement_id,
        setup.placement("revised_feedback").placement_id,
    )
    if baseline is None or baseline.placement_ids != (setup.placements[0].placement_id,):
        raise ImprovementValidationError("baseline Arrangement is not exact")
    if later is None or later.placement_ids != expected_later:
        raise ImprovementValidationError("later-work Arrangement order is not exact")
    targets = setup.reflection.target_references
    if (
        setup.reflection.author != STUDENT
        or tuple(item.semantic_role for item in targets) != ("baseline", "later")
        or tuple(item.target_id for item in targets)
        != (
            setup.selection("baseline_argument").selection_id,
            setup.selection("revised_argument").selection_id,
        )
    ):
        raise ImprovementValidationError("student Reflection comparison target is not exact")
    if not any(
        item.record_kind == "reflection"
        and item.record_id == setup.reflection.reflection_id
        and item.revision == setup.reflection.reflection_revision
        for item in setup.inventory.included_curation_revisions
    ):
        raise ImprovementValidationError("Composition inventory did not freeze the Reflection")
    if setup.composition.selection_ids != tuple(item.selection_id for item in setup.selections):
        raise ImprovementValidationError("Composition did not freeze exact Selections")
    return expected_later


def validate() -> ImprovementValidationReport:
    with tempfile.TemporaryDirectory(prefix="vitrine-improvement-portfolio-") as raw:
        built = build_improvement_portfolio_fixture(Path(raw))
        if not isinstance(built, ImprovementPortfolioFixture):
            raise ImprovementValidationError("complete fixture did not return its runtime state")
        setup = built
        arrangement_order = _assert_curation(setup)
        series, request, plan, attempt = _start_pipeline(setup)
        execution = execute_snapshot_build_attempt(
            setup.workspace,
            snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision,
            authority_gate=_FixtureAuthorityGate(),
            source_providers=_provider_registry(plan.entry_plans, setup.source_root),
            renderers=SnapshotRendererRegistry(
                (_ReflectionFixtureRenderer(reflection=setup.reflection),)
            ),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
        _assert_materialization(setup, execution)
        sealed = seal_snapshot_build_attempt(
            setup.workspace,
            execution=execution,
            expected_state_revision=setup.state_revision,
            sealed_by=TEACHER,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
        if sealed.edition_path is None:
            raise ImprovementValidationError("sealed Edition path is absent")
        verification = verify_snapshot_edition(
            setup.workspace,
            snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            verified_at=fixed_clock(),
        )
        export_result = create_snapshot_directory_export(
            setup.workspace,
            snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            export_plan_id=plan.export_plans[0].export_plan_id,
            expected_state_revision=setup.state_revision,
            generated_at=fixed_clock(),
            artifact_id="export-artifact-imp-001",
        )
        export_verification = verify_snapshot_export(
            setup.workspace,
            snapshot_export_artifact_id=(
                export_result.export_artifact.snapshot_export_artifact_id
            ),
            verified_at=fixed_clock(),
        )
        if verification.manifest_digest != sealed.seal.manifest_digest:
            raise ImprovementValidationError("Manifest digest did not reproduce")
        if verification.logical_inventory_digest != sealed.seal.logical_inventory_digest:
            raise ImprovementValidationError("logical inventory digest did not reproduce")
        if (
            export_verification.directory_inventory_digest
            != export_result.export_artifact.directory_inventory_digest
        ):
            raise ImprovementValidationError("Export inventory digest did not reproduce")
        pointer = advance_snapshot_current_pointer(
            setup.workspace,
            snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            expected_state_revision=setup.state_revision,
            expected_pointer_revision=None,
            expected_current_edition=None,
            pointed_by=TEACHER,
            authority_reference="representative-local-build-authority",
            reason="Promote only after Edition and Export verification.",
            pointed_at=fixed_clock(),
            pointer_id="snapshot-current-pointer-imp-001",
        )
        before = _capture_inventory(
            setup,
            edition=sealed.edition,
            seal_id=sealed.seal.seal_id,
            manifest_sha256=sealed.seal.manifest_digest.value,
            logical_inventory_sha256=sealed.seal.logical_inventory_digest.value,
            edition_path=sealed.edition_path,
            export=export_result.export_artifact,
            export_path=export_result.export_path,
        )
        selected_candidate_id = setup.selection("revised_argument").candidate_id
        shutil.rmtree(setup.source_root)
        verify_snapshot_edition(
            setup.workspace,
            snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            verified_at=fixed_clock(),
        )
        verify_snapshot_export(
            setup.workspace,
            snapshot_export_artifact_id=(
                export_result.export_artifact.snapshot_export_artifact_id
            ),
            verified_at=fixed_clock(),
        )
        after = _capture_inventory(
            setup,
            edition=sealed.edition,
            seal_id=sealed.seal.seal_id,
            manifest_sha256=sealed.seal.manifest_digest.value,
            logical_inventory_sha256=sealed.seal.logical_inventory_digest.value,
            edition_path=sealed.edition_path,
            export=export_result.export_artifact,
            export_path=export_result.export_path,
        )
        if before != after:
            raise ImprovementValidationError("sealed/exported byte inventory changed after drift")
        if setup.selection("revised_argument").candidate_id != selected_candidate_id:
            raise ImprovementValidationError("source drift retargeted an immutable Selection")
        pointers = tuple(
            item for item in _records(setup) if isinstance(item, SnapshotCurrentPointerRevision)
        )
        if pointers != (pointer.pointer,):
            raise ImprovementValidationError("source drift advanced the current pointer")
        _assert_final_boundaries(setup, sealed.edition, export_result.export_artifact)
        report = ImprovementValidationReport(
            subject_id=sealed.edition.portfolio_subject_id,
            profile_binding_id=sealed.edition.profile_binding_id,
            candidate_ids=tuple(item.candidate_id for item in setup.candidates),
            selection_ids=tuple(item.selection_id for item in setup.selections),
            arrangement_order=arrangement_order,
            reflection_id=setup.reflection.reflection_id,
            composition_revision=setup.composition.composition_revision,
            snapshot_series_id=series.snapshot_series_id,
            build_request_id=request.snapshot_build_request_id,
            build_plan_id=plan.snapshot_build_plan_id,
            build_plan_fingerprint=plan.plan_fingerprint,
            build_attempt_id=attempt.snapshot_build_attempt_id,
            edition_identity=before.edition_identity,
            seal_id=before.seal_id,
            manifest_sha256=before.manifest_sha256,
            logical_inventory_sha256=before.logical_inventory_sha256,
            export_artifact_id=before.export_artifact_id,
            export_inventory_sha256=before.export_inventory_sha256,
            entry_inventory=before.entry_inventory,
        )
        _assert_report_contract(report)
        return report


def _assert_report_contract(report: ImprovementValidationReport) -> None:
    if len(report.candidate_ids) != 3 or len(report.selection_ids) != 3:
        raise ImprovementValidationError(
            "improvement report does not contain exactly three Candidates and Selections"
        )
    if tuple(item[0] for item in report.entry_inventory) != EXPECTED_ENTRY_PATHS:
        raise ImprovementValidationError(
            "improvement report Entry inventory paths are not exact"
        )
    if report.edition_identity[1] != 1:
        raise ImprovementValidationError("improvement report did not seal Edition 1")
    if any(
        len(value) != 64
        for value in (
            report.manifest_sha256,
            report.logical_inventory_sha256,
            report.export_inventory_sha256,
        )
    ):
        raise ImprovementValidationError(
            "improvement report contains an invalid SHA-256 digest"
        )


def _assert_materialization(
    setup: ImprovementPortfolioFixture, execution: SnapshotAttemptExecutionResult
) -> None:
    if tuple(item.disposition for item in execution.entries) != ("prepared_bytes",) * 4:
        raise ImprovementValidationError("all four planned Entries must materialize")
    if any(isinstance(item, SnapshotOmission) for item in _records(setup)):
        raise ImprovementValidationError("successful improvement slice created an Omission")


def _assert_final_boundaries(
    setup: ImprovementPortfolioFixture,
    edition: SnapshotEdition,
    export: SnapshotExportArtifact,
) -> None:
    records = _records(setup)
    editions = tuple(item for item in records if isinstance(item, SnapshotEdition))
    exports = tuple(item for item in records if isinstance(item, SnapshotExportArtifact))
    materializations = tuple(
        item
        for item in records
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition == edition.reference
    )
    entries = tuple(
        item
        for item in records
        if isinstance(item, SnapshotEntry) and item.snapshot_edition == edition.reference
    )
    if editions != (edition,) or exports != (export,):
        raise ImprovementValidationError("Edition/Export identity inventory is not exact")
    if len(materializations) != 4 or len(entries) != 4:
        raise ImprovementValidationError("four exact Materializations/Entries are required")
    try:
        inspect_snapshot_series_lock(setup.workspace, snapshot_series_id=edition.snapshot_series_id)
    except SnapshotCustodyError as error:
        if error.code != "snapshot.build_lock_missing":
            raise
    else:
        raise ImprovementValidationError("successful build left a Series lock")
    errors = tuple(
        item for item in inspect_snapshot_custody(setup.workspace).findings if item.severity == "error"
    )
    if errors:
        raise ImprovementValidationError("Snapshot custody audit contains unresolved errors")
    forbidden = (
        b"PRIVATE_TEACHER_NOTE",
        b"PRIVATE_FEEDBACK_SUMMARY",
        b"PRIVATE_QUILLAN_ROUTE",
        b"proficiency",
        b"mastery",
        b"recipient authorization",
    )
    export_root = setup.workspace / export.relative_path
    for path in export_root.rglob("*"):
        if path.is_file() and any(marker in path.read_bytes() for marker in forbidden):
            raise ImprovementValidationError("private or calculated content leaked into Export")
    if (export_root / "internal" / "manifest.json").exists():
        raise ImprovementValidationError("internal Snapshot Manifest leaked into Export")


def main() -> int:
    try:
        report = validate()
    except (OSError, RuntimeError, SnapshotCustodyError) as error:
        print(f"Improvement Portfolio validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "PASS executable improvement Portfolio: "
        f"3 Candidates, 3 Selections, 4 Entries, Edition {report.edition_identity[1]}, "
        "verified directory_package Export, exact pre/post-drift bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
