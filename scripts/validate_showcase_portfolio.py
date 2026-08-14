#!/usr/bin/env python3
"""Execute and verify the representative showcase Portfolio vertical slice."""

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

from scripts.showcase_portfolio_fixture_support import (
    APPROVAL_REQUIREMENT_ID,
    ATTRIBUTION_TEXT,
    PORTFOLIO_ID,
    PROFILE_BINDING_ID,
    RATIONALE_TEXT,
    STUDENT,
    SUBJECT_ID,
    TEACHER,
    ShowcasePortfolioFixture,
    build_showcase_portfolio_fixture,
    fixed_clock,
)
from scripts.validate_snapshot_workflows import (
    EXPORT_CONFIGURATION_BYTES,
    _digest,
    _FixtureAuthorityGate,
    _provider_registry,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CandidateEvaluation,
    CurationAnnotation,
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRevision,
    PortfolioSelection,
    PortfolioSubjectClassLink,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEntry,
    SnapshotEntryPlan,
    SnapshotExportPlan,
    SnapshotInputReference,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeries,
    VitrineRecord,
)
from vitrine.snapshot_distribution import (
    create_snapshot_directory_export,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_materialization import (
    SnapshotMaterializationError,
    SnapshotRendererDescriptor,
    SnapshotRendererRegistry,
    SnapshotRenderRequest,
    SnapshotRenderResult,
)
from vitrine.snapshot_services import (
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import load_current_records

ATTRIBUTION_RENDERER_ID = "showcase_attribution_renderer"
RATIONALE_RENDERER_ID = "showcase_rationale_renderer"
INDEX_RENDERER_ID = "showcase_index_renderer"
RENDERER_VERSION = "1"
RENDERER_CONTRACT = "showcase_text_renderer_v1"
ATTRIBUTION_CONFIGURATION = b'{"format":"text","kind":"audience_safe_attribution"}\n'
ATTRIBUTION_TEMPLATE = b"{content}\n"
RATIONALE_CONFIGURATION = b'{"format":"markdown","kind":"curation_rationale"}\n'
RATIONALE_TEMPLATE = b"# Synthetic Showcase Rationale\n\n{content}\n"
INDEX_CONFIGURATION = b'{"format":"markdown","kind":"portfolio_index"}\n'
INDEX_TEMPLATE = (
    b"# Showcase Portfolio Index\n\nThis audience-safe index omits internal manifests, "
    b"private paths, and collaborator display names.\n"
)


class ShowcaseValidationError(RuntimeError):
    """Privacy-minimal deterministic vertical-slice failure."""


@dataclass(frozen=True, slots=True)
class ShowcaseValidationReport:
    subject_id: str
    profile_binding_id: str
    publication_ids: tuple[str, str]
    evaluation_inventory: tuple[tuple[str, str], ...]
    candidate_ids: tuple[str, ...]
    proposal_ids: tuple[str, ...]
    decision_ids: tuple[str, ...]
    selection_ids: tuple[str, ...]
    placement_ids: tuple[str, ...]
    arrangement_order: tuple[str, ...]
    annotation_revisions: tuple[tuple[str, int], tuple[str, int]]
    review_id: str
    composition_revision: int
    snapshot_series_id: str
    build_request_id: str
    build_plan_id: str
    plan_fingerprint: str
    build_attempt_id: str
    edition_identity: tuple[str, int]
    manifest_sha256: str
    logical_inventory_sha256: str
    export_artifact_id: str
    export_inventory_sha256: str
    entry_inventory: tuple[tuple[str, int, str], ...]


@dataclass
class _ShowcaseRenderer:
    annotation: CurationAnnotation | None
    descriptor: SnapshotRendererDescriptor
    content: bytes
    configuration: bytes
    template: bytes

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        annotation_refs = tuple(
            item for item in request.entry_plan.input_references
            if item.record_type == "curation_annotation"
        )
        if self.annotation is None:
            if annotation_refs:
                raise SnapshotMaterializationError(
                    "snapshot.render_failed", "Index renderer received annotation input.", stage="render"
                )
        elif annotation_refs != (
            SnapshotInputReference(
                record_type="curation_annotation",
                record_id=self.annotation.annotation_id,
                record_revision=self.annotation.annotation_revision,
            ),
        ):
            raise SnapshotMaterializationError(
                "snapshot.render_failed", "Renderer requires the exact frozen Annotation revision.", stage="render"
            )
        return SnapshotRenderResult(
            renderer_id=self.descriptor.renderer_id,
            renderer_version=self.descriptor.renderer_version,
            renderer_contract_version=self.descriptor.renderer_contract_version,
            content=self.content,
            media_type=request.entry_plan.media_type or "text/plain",
            configuration_digest=_digest(self.configuration),
            template_digest=_digest(self.template),
            language="en",
        )


def _records(setup: ShowcasePortfolioFixture) -> tuple[VitrineRecord, ...]:
    return load_current_records(setup.workspace)


def _candidate_for_selection(setup: ShowcasePortfolioFixture, selection: PortfolioSelection) -> PortfolioCandidate:
    values = tuple(item for item in _records(setup) if isinstance(item, PortfolioCandidate) and item.candidate_id == selection.candidate_id)
    if len(values) != 1:
        raise ShowcaseValidationError("exact Selection Candidate did not resolve")
    return values[0]


def _evaluation_for_candidate(setup: ShowcasePortfolioFixture, candidate: PortfolioCandidate) -> CandidateEvaluation:
    values = tuple(item for item in _records(setup) if isinstance(item, CandidateEvaluation) and item.candidate_evaluation_id == candidate.candidate_evaluation_id)
    if len(values) != 1:
        raise ShowcaseValidationError("exact Candidate Evaluation did not resolve")
    return values[0]


def _copied_entry(setup: ShowcasePortfolioFixture, *, source_id: str, entry_id: str, position: int, section: str, path: str, review: bool = False) -> SnapshotEntryPlan:
    selection = setup.selection(source_id)
    placement = setup.placement(source_id)
    candidate = _candidate_for_selection(setup, selection)
    evaluation = _evaluation_for_candidate(setup, candidate)
    artifact = candidate.source_endpoint.source_artifact
    if artifact is None or artifact.source_locator is None:
        raise ShowcaseValidationError("copied showcase Candidate lacks source Artifact")
    return SnapshotEntryPlan(
        entry_plan_id=entry_id, plan_position=position, section_id=section, ordinal=position,
        semantic_role="individual_work" if position == 1 else "collaborative_artifact",
        materialization_kind="copied_source", content_class="student_work",
        selection_id=selection.selection_id, placement_id=placement.placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_publication_id=candidate.source_endpoint.core_publication.publication_id,
        producer_module_id=candidate.source_endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=candidate.source_endpoint.producer_source.projection_contract_version,
        source_artifact=artifact, producer_source_digest_claim=artifact.source_digest,
        target_relative_path=path, media_type=artifact.media_type,
        required_review_ids=(setup.review.curation_review_decision_id,) if review else (),
    )


def _generated_entry(*, setup: ShowcasePortfolioFixture, annotation: CurationAnnotation | None, entry_id: str, position: int, section: str, role: str, content_class: str, path: str, media_type: str, renderer_id: str, configuration: bytes, template: bytes, review: bool = False) -> SnapshotEntryPlan:
    refs = []
    if annotation is not None:
        refs.append(SnapshotInputReference(record_type="curation_annotation", record_id=annotation.annotation_id, record_revision=annotation.annotation_revision))
    refs.append(SnapshotInputReference(record_type="working_portfolio_composition_revision", record_id=setup.composition.portfolio_id, record_revision=setup.composition.composition_revision))
    return SnapshotEntryPlan(
        entry_plan_id=entry_id, plan_position=position, section_id=section, ordinal=position,
        semantic_role=role, materialization_kind="generated_vitrine",
        content_class=content_class, target_relative_path=path, media_type=media_type,
        renderer_id=renderer_id, renderer_version=RENDERER_VERSION,
        renderer_contract_version=RENDERER_CONTRACT,
        renderer_configuration_digest=_digest(configuration),
        renderer_template_digest=_digest(template), input_references=tuple(refs),
        required_review_ids=(setup.review.curation_review_decision_id,) if review else (),
    )


def _entry_plans(setup: ShowcasePortfolioFixture) -> tuple[SnapshotEntryPlan, ...]:
    return (
        _copied_entry(setup, source_id="polished_literary_analysis", entry_id="entry-plan-show-polished", position=1, section="featured_work", path="01-polished-literary-analysis.txt"),
        _copied_entry(setup, source_id="concord-artifact-syn-001", entry_id="entry-plan-show-group", position=2, section="collaboration", path="02-group-water-quality-recommendation.txt", review=True),
        _generated_entry(setup=setup, annotation=setup.attribution, entry_id="entry-plan-show-attribution", position=3, section="collaboration", role="audience_safe_attribution", content_class="audience_safe_attribution", path="03-audience-safe-attribution.txt", media_type="text/plain", renderer_id=ATTRIBUTION_RENDERER_ID, configuration=ATTRIBUTION_CONFIGURATION, template=ATTRIBUTION_TEMPLATE, review=True),
        _generated_entry(setup=setup, annotation=setup.rationale, entry_id="entry-plan-show-rationale", position=4, section="showcase_context", role="curation_rationale", content_class="curation_rationale", path="04-curation-rationale.md", media_type="text/markdown", renderer_id=RATIONALE_RENDERER_ID, configuration=RATIONALE_CONFIGURATION, template=RATIONALE_TEMPLATE),
        _generated_entry(setup=setup, annotation=None, entry_id="entry-plan-show-index", position=5, section="showcase_context", role="portfolio_index", content_class="portfolio_index", path="05-index.md", media_type="text/markdown", renderer_id=INDEX_RENDERER_ID, configuration=INDEX_CONFIGURATION, template=INDEX_TEMPLATE),
    )


def _assert_projection_and_curation(setup: ShowcasePortfolioFixture) -> tuple[str, str]:
    records = _records(setup)
    links = tuple(item for item in records if isinstance(item, PortfolioSubjectClassLink))
    displays = tuple(item for item in records if isinstance(item, PortfolioSubjectDisplaySnapshot))
    decisions = tuple(item for item in records if isinstance(item, PortfolioSubjectIdentityDecision))
    lifecycle = tuple(item for item in records if isinstance(item, PortfolioProfileLifecycleEvent))
    bindings = tuple(item for item in records if isinstance(item, PortfolioProfileBinding))
    if len(links) != 1 or links[0].student_reference.student_id != "student-syn-001":
        raise ShowcaseValidationError("Subject class-qualified identity is not exact")
    if len(displays) != 1 or len(decisions) != 2:
        raise ShowcaseValidationError("Subject identity evidence inventory is not exact")
    if len(lifecycle) != 1 or lifecycle[0].event_kind != "activated" or len(bindings) != 1:
        raise ShowcaseValidationError("Profile activation or Binding is not exact")
    profile = next(item for item in records if isinstance(item, PortfolioProfileRevision) and item.portfolio_profile_id == "profile-showcase-rev-001")
    sections = {item.section_id: item for item in profile.sections}
    if sections["featured_work"].required_relationship_kinds != ("submission_subject",) or sections["collaboration"].required_relationship_kinds != ("documented_contributor",):
        raise ShowcaseValidationError("Profile relationship requirements are not exact")

    artifact_result = next(item for item in setup.projection_results if item.projected_source.projection_kind == "concord_fixture:artifact")
    relationships = artifact_result.projected_source.source_relationships
    subject_kinds = {item.relationship_kind for item in relationships if item.source_subject_kind == "core_student" and item.source_subject_id == "student-syn-001"}
    if not {"group_member", "artifact_subject", "documented_contributor"} <= subject_kinds or "artifact_author" in subject_kinds:
        raise ShowcaseValidationError("Concord Subject relationships were collapsed")
    group_kinds = {item.relationship_kind for item in relationships if item.source_subject_kind == "concord_group" and item.source_subject_id == "concord-group-syn-007"}
    if not {"artifact_author", "artifact_subject", "represented_group"} <= group_kinds:
        raise ShowcaseValidationError("collective Group relationships were not preserved")
    contribution = next(item for item in relationships if item.relationship_kind == "documented_contributor")
    if contribution.supporting_source_reference != "concord-contribution-syn-001":
        raise ShowcaseValidationError("documented contribution identity was not preserved")
    score_results = tuple(item for item in setup.projection_results if item.projected_source.projection_kind == "concord_fixture:score_summary")
    if len(score_results) != 2 or any(item.candidate is not None or item.evaluation.outcome != "unresolved" for item in score_results):
        raise ShowcaseValidationError("Group Score created a Candidate")
    for item in score_results:
        fields = {field.key: field.value for field in item.projected_source.display_snapshot.fields}
        if fields["target_kind"] != "concord_group" or item.projected_source.source_relationships[0].relationship_kind != "group_score_target":
            raise ShowcaseValidationError("Group Score target was substituted")
    deferred = next(item for item in score_results if dict((field.key, field.value) for field in item.projected_source.display_snapshot.fields)["disposition"] == "deferred")
    if any(field.key == "native_value" for field in deferred.projected_source.display_snapshot.fields):
        raise ShowcaseValidationError("deferred non-score acquired a value")

    polished = setup.candidate("polished_literary_analysis")
    group = setup.candidate("concord-artifact-syn-001")
    if polished.condition_state != "ready_for_consideration" or polished.eligible_section_ids != ("featured_work",):
        raise ShowcaseValidationError("polished Candidate eligibility is not exact")
    if group.condition_state != "collaborator_review_required" or group.eligible_section_ids != ("collaboration",):
        raise ShowcaseValidationError("collaborative Candidate condition/eligibility is not exact")
    if len(setup.proposals) != 2 or len(setup.decisions) != 2:
        raise ShowcaseValidationError("explicit Selection provenance is incomplete")
    group_decision = next(item for item in setup.decisions if item.selection_proposal_id == setup.proposals[1].selection_proposal_id)
    if group_decision.condition_codes != ("collaborator_review_required",):
        raise ShowcaseValidationError("collaborator condition was not acknowledged")
    if setup.review.approval_requirement_id != APPROVAL_REQUIREMENT_ID or setup.review.decision != "approved":
        raise ShowcaseValidationError("exact collaborator-treatment Review is absent")
    frozen = {(item.record_kind, item.record_id, item.revision) for item in setup.inventory.included_curation_revisions}
    if ("annotation", setup.attribution.annotation_id, 1) not in frozen or ("annotation", setup.rationale.annotation_id, 1) not in frozen:
        raise ShowcaseValidationError("Composition did not freeze exact Annotation revisions")
    if setup.inventory.applicable_review_decision_ids != (setup.review.curation_review_decision_id,):
        raise ShowcaseValidationError("Composition did not freeze exact Review")
    state = project_curation_state(records)
    featured = state.current_arrangement(PORTFOLIO_ID, PROFILE_BINDING_ID, "featured_work")
    collaboration = state.current_arrangement(PORTFOLIO_ID, PROFILE_BINDING_ID, "collaboration")
    if featured is None or collaboration is None:
        raise ShowcaseValidationError("current showcase Arrangements are absent")
    return featured.placement_ids[0], collaboration.placement_ids[0]


def _inventory(root: Path) -> tuple[tuple[str, int, str], ...]:
    return tuple((path.relative_to(root).as_posix(), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(item for item in root.rglob("*") if item.is_file()))


def validate() -> ShowcaseValidationReport:
    with tempfile.TemporaryDirectory(prefix="vitrine-showcase-portfolio-") as raw:
        built = build_showcase_portfolio_fixture(Path(raw))
        if not isinstance(built, ShowcasePortfolioFixture):
            raise ShowcaseValidationError("complete showcase fixture did not return runtime state")
        setup = built
        arrangement_order = _assert_projection_and_curation(setup)
        created = create_snapshot_series(
            setup.workspace, portfolio_id=PORTFOLIO_ID,
            audience_context_id=setup.audience.audience_context_id,
            snapshot_purpose="showcase", created_by=TEACHER,
            expected_state_revision=setup.state_revision, clock=fixed_clock, id_factory=setup.ids,
        )
        series = next(item for item in created.records if isinstance(item, SnapshotSeries))
        requested = request_snapshot_build(
            setup.workspace, snapshot_series_id=series.snapshot_series_id,
            composition_revision=setup.composition.composition_revision,
            requested_by=STUDENT, idempotency_key="representative-showcase-slice-v1",
            expected_state_revision=setup.state_revision, clock=fixed_clock, id_factory=setup.ids,
        )
        request = next(item for item in requested.records if isinstance(item, SnapshotBuildRequest))
        if request.curation_review_decision_ids != (setup.review.curation_review_decision_id,):
            raise ShowcaseValidationError("Build Request did not carry exact Review")
        entries = _entry_plans(setup)
        export_plan = SnapshotExportPlan(
            export_plan_id="export-plan-show-directory", export_format="directory_package",
            export_contract_version="1", included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
            excluded_entry_plan_ids=(), configuration_digest=_digest(EXPORT_CONFIGURATION_BYTES),
        )
        planned = plan_snapshot_build(
            setup.workspace, snapshot_build_request_id=request.snapshot_build_request_id,
            entry_plans=entries, export_plans=(export_plan,), planned_by=TEACHER,
            acknowledged_obligation_codes=setup.inventory.unresolved_obligation_codes,
            expected_state_revision=setup.state_revision, clock=fixed_clock, id_factory=setup.ids,
        )
        plan = next(item for item in planned.records if isinstance(item, SnapshotBuildPlan))
        started = start_snapshot_build_attempt(
            setup.workspace, snapshot_build_plan_id=plan.snapshot_build_plan_id,
            started_by=TEACHER, expected_state_revision=setup.state_revision,
            clock=fixed_clock, id_factory=setup.ids,
        )
        attempt = started.attempt
        renderers = SnapshotRendererRegistry((
            _ShowcaseRenderer(setup.attribution, SnapshotRendererDescriptor(renderer_id=ATTRIBUTION_RENDERER_ID, renderer_version=RENDERER_VERSION, renderer_contract_version=RENDERER_CONTRACT), (ATTRIBUTION_TEXT + "\n").encode(), ATTRIBUTION_CONFIGURATION, ATTRIBUTION_TEMPLATE),
            _ShowcaseRenderer(setup.rationale, SnapshotRendererDescriptor(renderer_id=RATIONALE_RENDERER_ID, renderer_version=RENDERER_VERSION, renderer_contract_version=RENDERER_CONTRACT), ("# Synthetic Showcase Rationale\n\n" + RATIONALE_TEXT + "\n").encode(), RATIONALE_CONFIGURATION, RATIONALE_TEMPLATE),
            _ShowcaseRenderer(None, SnapshotRendererDescriptor(renderer_id=INDEX_RENDERER_ID, renderer_version=RENDERER_VERSION, renderer_contract_version=RENDERER_CONTRACT), INDEX_TEMPLATE, INDEX_CONFIGURATION, INDEX_TEMPLATE),
        ))
        execution = execute_snapshot_build_attempt(
            setup.workspace, snapshot_build_attempt_id=attempt.snapshot_build_attempt_id,
            expected_state_revision=setup.state_revision, authority_gate=_FixtureAuthorityGate(),
            source_providers=_provider_registry(plan.entry_plans, setup.source_root),
            renderers=renderers, clock=fixed_clock, id_factory=setup.ids,
        )
        if tuple(item.disposition for item in execution.entries) != ("prepared_bytes",) * 5:
            raise ShowcaseValidationError("all five planned Entries must materialize")
        if any(isinstance(item, SnapshotOmission) for item in _records(setup)):
            raise ShowcaseValidationError("successful showcase slice created an Omission")
        sealed = seal_snapshot_build_attempt(
            setup.workspace, execution=execution, expected_state_revision=setup.state_revision,
            sealed_by=TEACHER, clock=fixed_clock, id_factory=setup.ids,
        )
        if sealed.edition_path is None:
            raise ShowcaseValidationError("sealed Edition path is absent")
        edition_verification = verify_snapshot_edition(
            setup.workspace, snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number, verified_at=fixed_clock(),
        )
        exported = create_snapshot_directory_export(
            setup.workspace, snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            export_plan_id=export_plan.export_plan_id,
            expected_state_revision=setup.state_revision, generated_at=fixed_clock(),
            artifact_id="export-artifact-show-001",
        )
        replay = create_snapshot_directory_export(
            setup.workspace, snapshot_series_id=series.snapshot_series_id,
            edition_number=sealed.edition.edition_number,
            export_plan_id=export_plan.export_plan_id,
            expected_state_revision=setup.state_revision, generated_at=fixed_clock(),
            artifact_id="export-artifact-show-001",
        )
        if replay.export_artifact != exported.export_artifact or _inventory(replay.export_path) != _inventory(exported.export_path):
            raise ShowcaseValidationError("exact Export replay did not reproduce")
        export_verification = verify_snapshot_export(
            setup.workspace,
            snapshot_export_artifact_id=exported.export_artifact.snapshot_export_artifact_id,
            verified_at=fixed_clock(),
        )
        if edition_verification.manifest_digest != sealed.seal.manifest_digest or edition_verification.logical_inventory_digest != sealed.seal.logical_inventory_digest:
            raise ShowcaseValidationError("Edition digests did not reproduce")
        if export_verification.directory_inventory_digest != exported.export_artifact.directory_inventory_digest:
            raise ShowcaseValidationError("Export inventory digest did not reproduce")
        expected = {
            "01-polished-literary-analysis.txt": (377, "5a86178f64b55c4774c919bf0c7c863e8c7d74268ec86ce6194fa22af519c575"),
            "02-group-water-quality-recommendation.txt": (322, "0b9ffbb18e44d698ffb51e8973bb3647df45995d815ba5dcea949a9dafe1cbc8"),
            "03-audience-safe-attribution.txt": (190, "1f51f05825c7907d4398c7807de97c1fd968cffe139f27c6d1b15e09f195d58e"),
        }
        inventory = _inventory(exported.export_path)
        for relative_path, size, digest in inventory:
            if relative_path in expected and (size, digest) != expected[relative_path]:
                raise ShowcaseValidationError("committed showcase byte fixture mismatch")
        if len(inventory) != 5:
            raise ShowcaseValidationError("Export does not contain exactly five files")
        forbidden = (
            b"collaborator-syn-001", b"collaborator-syn-002", b"PRIVATE_TEACHER_NOTE",
            b"PRIVATE_QUILLAN_ROUTE", b"secure_assessment", b"restricted_internal",
            b"recipient authorization", b"consent obtained",
        )
        for visible_path in exported.export_path.rglob("*"):
            if visible_path.is_file() and any(
                marker in visible_path.read_bytes() for marker in forbidden
            ):
                raise ShowcaseValidationError("private or authorization content leaked into Export")
        if (exported.export_path / "internal" / "manifest.json").exists():
            raise ShowcaseValidationError("internal Snapshot Manifest leaked into Export")
        snapshot_entries = tuple(item for item in _records(setup) if isinstance(item, SnapshotEntry) and item.snapshot_edition == sealed.edition.reference)
        if len(snapshot_entries) != 5 or any(item.content_class == "assessment_summary" for item in snapshot_entries):
            raise ShowcaseValidationError("showcase Edition Entry inventory is not exact")
        materializations = {item.materialization_id: item for item in _records(setup) if isinstance(item, SnapshotMaterializationRecord) and item.snapshot_edition == sealed.edition.reference}
        entry_rows: list[tuple[str, int, str]] = []
        for entry in snapshot_entries:
            materialization = materializations[entry.materialization_id]
            if materialization.byte_size is None or materialization.output_digest is None:
                raise ShowcaseValidationError("Entry digest or byte size is absent")
            entry_rows.append(
                (
                    entry.relative_path,
                    materialization.byte_size,
                    materialization.output_digest.value,
                )
            )
        entry_inventory = tuple(sorted(entry_rows))
        shutil.rmtree(setup.source_root)
        verify_snapshot_edition(setup.workspace, snapshot_series_id=series.snapshot_series_id, edition_number=sealed.edition.edition_number, verified_at=fixed_clock())
        verify_snapshot_export(setup.workspace, snapshot_export_artifact_id=exported.export_artifact.snapshot_export_artifact_id, verified_at=fixed_clock())
        return ShowcaseValidationReport(
            subject_id=SUBJECT_ID, profile_binding_id=PROFILE_BINDING_ID,
            publication_ids=setup.publications,
            evaluation_inventory=tuple((item.projected_source.producer_source.source_record_id, item.evaluation.outcome) for item in setup.projection_results),
            candidate_ids=tuple(item.candidate_id for item in setup.candidates),
            proposal_ids=tuple(item.selection_proposal_id for item in setup.proposals),
            decision_ids=tuple(item.selection_decision_id for item in setup.decisions),
            selection_ids=tuple(item.selection_id for item in setup.selections),
            placement_ids=tuple(item.placement_id for item in setup.placements),
            arrangement_order=arrangement_order,
            annotation_revisions=((setup.attribution.annotation_id, setup.attribution.annotation_revision), (setup.rationale.annotation_id, setup.rationale.annotation_revision)),
            review_id=setup.review.curation_review_decision_id,
            composition_revision=setup.composition.composition_revision,
            snapshot_series_id=series.snapshot_series_id,
            build_request_id=request.snapshot_build_request_id,
            build_plan_id=plan.snapshot_build_plan_id, plan_fingerprint=plan.plan_fingerprint,
            build_attempt_id=attempt.snapshot_build_attempt_id,
            edition_identity=(sealed.edition.snapshot_series_id, sealed.edition.edition_number),
            manifest_sha256=sealed.seal.manifest_digest.value,
            logical_inventory_sha256=sealed.seal.logical_inventory_digest.value,
            export_artifact_id=exported.export_artifact.snapshot_export_artifact_id,
            export_inventory_sha256=exported.export_artifact.directory_inventory_digest.value,
            entry_inventory=entry_inventory,
        )


def main() -> int:
    try:
        report = validate()
    except (OSError, RuntimeError) as error:
        print(f"Showcase Portfolio validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "PASS executable showcase Portfolio: 2 Candidates, 2 Selections, "
        f"5 Entries, Edition {report.edition_identity[1]}, verified reproducible directory_package Export"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
