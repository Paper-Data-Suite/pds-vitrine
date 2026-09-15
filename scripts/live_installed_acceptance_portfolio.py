"""Explicit curation and authorized Current Portfolio build for issue #71 Slice 3.

This installed-only helper consumes the live Candidates persisted by Slice 2. It
selects exact source identities (never score/latest/best heuristics), freezes the
Starter Improvement Portfolio, and exercises Vitrine's production Current
Portfolio build path with separate curation, source-read, Artifact-read, and
Snapshot-build authorization gates.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from live_installed_acceptance_support import (
    MAIN_STUDENT_ID,
    NOW,
    DeterministicIds,
    LivePortfolioContext,
    ProducerPublication,
)

from vitrine.concord_artifact_context import (
    build_canonical_concord_artifact_source_context_resolver,
)
from vitrine.concord_artifact_source import (
    ConcordArtifactAuthorizationDecision,
    ConcordArtifactAuthorizationRequest,
    build_concord_artifact_source_provider,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
    create_reflection,
    create_working_composition,
    place_selection,
    review_curation_target,
    select_candidate_directly,
)
from vitrine.curation_state import project_curation_state
from vitrine.current_portfolio_build import prepare_current_portfolio_build
from vitrine.current_portfolio_execution import execute_prepared_current_portfolio_build
from vitrine.models import (
    ActorAttribution,
    CurationReviewDecision,
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioReflection,
    PortfolioSelection,
    SnapshotMaterializationRecord,
    WorkingPortfolioCompositionRevision,
)
from vitrine.producer_reader_services import (
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationRequest,
)
from vitrine.quillan_artifact_context import (
    build_canonical_quillan_artifact_source_context_resolver,
)
from vitrine.quillan_artifact_source import (
    QuillanArtifactAuthorizationDecision,
    QuillanArtifactAuthorizationRequest,
    build_quillan_artifact_source_providers,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
    SnapshotSourceProviderRegistry,
)
from vitrine.storage import load_current_records, load_current_state


@dataclass(frozen=True, slots=True)
class CuratedPortfolio:
    selection_ids: tuple[str, ...]
    placement_ids: tuple[str, ...]
    reflection_id: str
    review_id: str
    composition_revision: int


@dataclass(frozen=True, slots=True)
class BuiltPortfolio:
    snapshot_series_id: str
    edition_number: int
    materialization_counts: dict[str, int]
    copied_artifact_kinds: tuple[str, ...]
    curation_authorization_requests: int
    snapshot_source_read_requests: int
    quillan_artifact_authorization_requests: int
    concord_artifact_authorization_requests: int
    snapshot_build_authorization_requests: int


def _teacher_actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="issue71_teacher",
        owning_system="local",
        role_snapshot="teacher",
        display_label_snapshot="Synthetic Issue 71 Teacher",
    )


def _student_actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="core_student",
        actor_id=MAIN_STUDENT_ID,
        owning_system="core",
        role_snapshot="student",
        display_label_snapshot="Synthetic Issue 71 Learner",
    )


class ExactCurationGate:
    def __init__(self, portfolio: LivePortfolioContext) -> None:
        self.portfolio = portfolio
        self.requests: list[CurationAuthorityRequest] = []

    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        self.requests.append(request)
        allowed = (
            request.portfolio_id == self.portfolio.portfolio_id
            and request.portfolio_subject_id == self.portfolio.portfolio_subject_id
            and request.profile_binding_id == self.portfolio.profile_binding_id
            and request.profile_revision_id == "vitrine_starter_improvement"
            and request.profile_revision_number == 1
        )
        acknowledged = (
            (request.candidate_condition_state,)
            if allowed
            and request.candidate_condition_state not in {None, "ready_for_consideration"}
            else ()
        )
        return CurationAuthorityDecision(
            outcome="allowed" if allowed else "denied",
            authority_reference=("issue_71:synthetic_curation" if allowed else None),
            reason_codes=("issue_71:exact_scope",) if allowed else (),
            acknowledged_condition_codes=acknowledged,
        )


class ExactSnapshotSourceReadGate:
    def __init__(self, publication_ids: set[str]) -> None:
        self.publication_ids = frozenset(publication_ids)
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        allowed = (
            request.publication_id in self.publication_ids
            and request.operation
            in {"snapshot_quillan_source_read", "snapshot_concord_source_read"}
            and request.purpose == "build_snapshot"
        )
        return SourceReadAuthorizationDecision(
            outcome="allowed" if allowed else "denied",
            reason_codes=("issue_71:exact_snapshot_source",) if allowed else (),
        )


class ExactQuillanArtifactGate:
    def __init__(self) -> None:
        self.requests: list[QuillanArtifactAuthorizationRequest] = []

    def authorize(
        self, request: QuillanArtifactAuthorizationRequest
    ) -> QuillanArtifactAuthorizationDecision:
        self.requests.append(request)
        allowed = (
            request.operation == "read_quillan_artifact"
            and request.purpose == "build_snapshot"
            and request.artifact_kind in {"student_work", "feedback_pdf"}
        )
        return QuillanArtifactAuthorizationDecision(
            outcome="allowed" if allowed else "denied",
            authority_reference=("issue_71:quillan_artifact" if allowed else None),
            reason_codes=("issue_71:exact_artifact",) if allowed else (),
        )


class ExactConcordArtifactGate:
    def __init__(self) -> None:
        self.requests: list[ConcordArtifactAuthorizationRequest] = []

    def authorize(
        self, request: ConcordArtifactAuthorizationRequest
    ) -> ConcordArtifactAuthorizationDecision:
        self.requests.append(request)
        allowed = (
            request.operation == "read_concord_artifact"
            and request.purpose == "build_snapshot"
            and request.evidence_kind in {"artifact_instance", "artifact_page"}
        )
        return ConcordArtifactAuthorizationDecision(
            outcome="allowed" if allowed else "denied",
            authority_reference=("issue_71:concord_artifact" if allowed else None),
            reason_codes=("issue_71:exact_artifact",) if allowed else (),
        )


class ExactSnapshotBuildGate:
    def __init__(self, portfolio: LivePortfolioContext) -> None:
        self.portfolio = portfolio
        self.requests: list[SnapshotBuildAuthorityRequest] = []

    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        self.requests.append(request)
        allowed = (
            request.operation == "build_snapshot"
            and request.portfolio_id == self.portfolio.portfolio_id
            and request.portfolio_subject_id == self.portfolio.portfolio_subject_id
            and request.profile_binding_id == self.portfolio.profile_binding_id
        )
        return SnapshotBuildAuthorityDecision(
            outcome="allowed" if allowed else "denied",
            authority_reference=("issue_71:snapshot_build" if allowed else None),
            reason_codes=("issue_71:exact_snapshot",) if allowed else (),
        )


def _candidate_matches(
    candidate: PortfolioCandidate,
    *,
    producer: str,
    artifact_kind: str,
    representation_kind: str | None = None,
    native_revision: int | None = None,
) -> bool:
    endpoint = candidate.source_endpoint
    artifact = endpoint.source_artifact
    source = endpoint.producer_source
    return (
        source.producer_module_id == producer
        and artifact is not None
        and artifact.artifact_kind == artifact_kind
        and (representation_kind is None or artifact.representation_kind == representation_kind)
        and (native_revision is None or source.native_revision == native_revision)
    )


def _one_candidate(workspace: Path, **criteria: object) -> PortfolioCandidate:
    records = load_current_records(workspace)
    matches = tuple(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
        and _candidate_matches(item, **criteria)  # type: ignore[arg-type]
    )
    if len(matches) != 1:
        raise RuntimeError("explicit Candidate identity did not resolve exactly once")
    return matches[0]


def _arrangement_pointer_revision(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    section_id: str,
) -> int | None:
    state = project_curation_state(load_current_records(workspace))
    heads = state.arrangement_pointer_heads(
        portfolio.portfolio_id,
        portfolio.profile_binding_id,
        section_id,
    )
    if not heads:
        return None
    if len(heads) != 1:
        raise RuntimeError("section Arrangement pointer is conflicted")
    return heads[0].pointer_revision


def _record(result: object, record_type: type[object]) -> object:
    records = tuple(getattr(result, "records"))
    matches = tuple(item for item in records if isinstance(item, record_type))
    if len(matches) != 1:
        raise RuntimeError("curation mutation returned an unexpected record shape")
    return matches[0]


def _select_and_place(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    candidate: PortfolioCandidate,
    section_id: str,
    requirement_ids: tuple[str, ...],
    gate: ExactCurationGate,
    ids: DeterministicIds,
) -> tuple[PortfolioSelection, PortfolioPlacement]:
    selected = select_candidate_directly(
        workspace,
        portfolio_id=portfolio.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=_teacher_actor(),
        proposed_section_ids=(section_id,),
        intended_profile_requirement_ids=requirement_ids,
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=gate,
        rationale_text="Issue 71 explicitly selects this exact synthetic Candidate.",
        clock=lambda: NOW,
        id_factory=ids,
    )
    selection = _record(selected, PortfolioSelection)
    assert isinstance(selection, PortfolioSelection)
    placed = place_selection(
        workspace,
        portfolio_id=portfolio.portfolio_id,
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=_teacher_actor(),
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_arrangement_pointer_revision=_arrangement_pointer_revision(
            workspace,
            portfolio=portfolio,
            section_id=section_id,
        ),
        authority_gate=gate,
        clock=lambda: NOW,
        id_factory=ids,
    )
    placement = _record(placed, PortfolioPlacement)
    assert isinstance(placement, PortfolioPlacement)
    return selection, placement


def curate_representative_portfolio(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    ids: DeterministicIds,
) -> tuple[CuratedPortfolio, ExactCurationGate]:
    """Curate exact baseline/later/feedback evidence and freeze one Composition."""

    gate = ExactCurationGate(portfolio)
    baseline = _one_candidate(
        workspace,
        producer="scoreform",
        artifact_kind="assessment_summary",
        native_revision=1,
    )
    quillan_work = _one_candidate(
        workspace,
        producer="quillan",
        artifact_kind="original_student_work",
        representation_kind="quillan:selected_student_work",
    )
    concord_work = _one_candidate(
        workspace,
        producer="concord",
        artifact_kind="collaborative_artifact",
        representation_kind="concord:returned_artifact_pdf",
    )
    quillan_feedback = _one_candidate(
        workspace,
        producer="quillan",
        artifact_kind="rendered_feedback",
        representation_kind="quillan:feedback_pdf",
    )

    selection_pairs = (
        (baseline, "baseline", ("baseline_cardinality",)),
        (quillan_work, "later_evidence", ("later_evidence_cardinality",)),
        (concord_work, "later_evidence", ("later_evidence_cardinality",)),
        (quillan_feedback, "supporting_feedback", ()),
    )
    selections: list[PortfolioSelection] = []
    placements: list[PortfolioPlacement] = []
    for candidate, section_id, requirement_ids in selection_pairs:
        selection, placement = _select_and_place(
            workspace,
            portfolio=portfolio,
            candidate=candidate,
            section_id=section_id,
            requirement_ids=requirement_ids,
            gate=gate,
            ids=ids,
        )
        selections.append(selection)
        placements.append(placement)

    reflected = create_reflection(
        workspace,
        portfolio_id=portfolio.portfolio_id,
        reflection_requirement_id="comparison_reflection",
        prompt_id="issue71_compare_exact_evidence",
        prompt_version="1",
        prompt_snapshot=(
            "Compare the exact baseline and later evidence and explain what changed "
            "without treating the Profile as proof that improvement occurred."
        ),
        author=_student_actor(),
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[0].selection_id,
                semantic_role="baseline",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[1].selection_id,
                semantic_role="later_student_work",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=selections[2].selection_id,
                semantic_role="later_collaborative_work",
            ),
        ),
        content=(
            "The later evidence makes the reasoning more explicit and easier to "
            "follow. I am comparing only these exact selected artifacts, not "
            "claiming that a score or date automatically proves improvement."
        ),
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=gate,
        clock=lambda: NOW,
        id_factory=ids,
    )
    reflection = _record(reflected, PortfolioReflection)
    assert isinstance(reflection, PortfolioReflection)

    review_targets = tuple(
        CurationTargetRef(
            target_kind="selection",
            target_id=item.selection_id,
            semantic_role="reviewed_selection",
        )
        for item in selections
    ) + (
        CurationTargetRef(
            target_kind="reflection",
            target_id=reflection.reflection_id,
            target_revision=reflection.reflection_revision,
            semantic_role="reviewed_reflection",
        ),
    )
    reviewed = review_curation_target(
        workspace,
        portfolio_id=portfolio.portfolio_id,
        target_scope="portfolio",
        target_references=review_targets,
        decision="approved",
        reviewed_by=_teacher_actor(),
        reason="Synthetic teacher review approves the exact curated comparison.",
        approval_requirement_id="teacher_review",
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=gate,
        clock=lambda: NOW,
        id_factory=ids,
    )
    review = _record(reviewed, CurationReviewDecision)
    assert isinstance(review, CurationReviewDecision)

    composed = create_working_composition(
        workspace,
        portfolio_id=portfolio.portfolio_id,
        created_by=_teacher_actor(),
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=gate,
        composition_note="Freeze exact issue #71 cross-producer curation.",
        clock=lambda: NOW,
        id_factory=ids,
    )
    composition = _record(composed, WorkingPortfolioCompositionRevision)
    assert isinstance(composition, WorkingPortfolioCompositionRevision)

    if len(selections) != 4 or len(placements) != 4:
        raise RuntimeError("representative curation cardinality drifted")
    return (
        CuratedPortfolio(
            selection_ids=tuple(item.selection_id for item in selections),
            placement_ids=tuple(item.placement_id for item in placements),
            reflection_id=reflection.reflection_id,
            review_id=review.curation_review_decision_id,
            composition_revision=composition.composition_revision,
        ),
        gate,
    )


def build_representative_snapshot(
    workspace: Path,
    *,
    portfolio: LivePortfolioContext,
    publications: tuple[ProducerPublication, ...],
    curation_gate: ExactCurationGate,
) -> BuiltPortfolio:
    """Build, seal, verify, and export the exact curated Current Portfolio."""

    publication_ids = {item.publication_id for item in publications}
    source_gate = ExactSnapshotSourceReadGate(publication_ids)
    quillan_gate = ExactQuillanArtifactGate()
    concord_gate = ExactConcordArtifactGate()
    snapshot_gate = ExactSnapshotBuildGate(portfolio)

    quillan_resolver = build_canonical_quillan_artifact_source_context_resolver(
        workspace,
        source_read_authorization_gate=source_gate,
    )
    concord_resolver = build_canonical_concord_artifact_source_context_resolver(
        workspace,
        source_read_authorization_gate=source_gate,
    )
    providers = SnapshotSourceProviderRegistry(
        (
            *build_quillan_artifact_source_providers(
                context_resolver=quillan_resolver,
                authorization_gate=quillan_gate,
            ),
            build_concord_artifact_source_provider(
                context_resolver=concord_resolver,
                authorization_gate=concord_gate,
            ),
        )
    )
    preview = prepare_current_portfolio_build(
        workspace,
        portfolio.portfolio_id,
        audience_rule_id="student_review",
        source_providers=providers,
    )
    if preview.unresolved_obligation_codes != ("collaborator_review_required",):
        raise RuntimeError("Current Portfolio unresolved obligation inventory drifted")
    preparation = prepare_current_portfolio_build(
        workspace,
        portfolio.portfolio_id,
        audience_rule_id="student_review",
        acknowledged_obligation_codes=preview.unresolved_obligation_codes,
        source_providers=providers,
    )
    if not preparation.ready_for_plan_execution:
        raise RuntimeError(
            "Current Portfolio preparation remained blocked after exact acknowledgement"
        )
    materialization_plan = Counter(
        item.materialization_kind for item in preparation.planned_items
    )
    materialization_plan.update(
        item.materialization_kind for item in preparation.generated_reflections
    )
    expected_plan = Counter(
        {"reference_only": 1, "copied_source": 3, "generated_vitrine": 1}
    )
    if materialization_plan != expected_plan:
        raise RuntimeError("Current Portfolio materialization plan inventory drifted")

    result = execute_prepared_current_portfolio_build(
        workspace,
        preparation,
        actor=_teacher_actor(),
        authority_gate=snapshot_gate,
        source_providers=providers,
    )
    if result.attempt_terminal_outcome != "sealed" or not result.export_path.is_dir():
        raise RuntimeError("Current Portfolio build/export did not succeed")

    records = load_current_records(workspace)
    edition_materializations = tuple(
        item
        for item in records
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition.snapshot_series_id == result.snapshot_series_id
        and item.snapshot_edition.edition_number == result.edition_number
    )
    actual_counts = Counter(item.materialization_kind for item in edition_materializations)
    if actual_counts != expected_plan:
        raise RuntimeError("sealed Edition materialization inventory drifted")
    copied_artifact_kinds = tuple(
        sorted(
            item.source_artifact.artifact_kind
            for item in edition_materializations
            if item.materialization_kind == "copied_source"
            and item.source_artifact is not None
        )
    )
    if copied_artifact_kinds != (
        "collaborative_artifact",
        "original_student_work",
        "rendered_feedback",
    ):
        raise RuntimeError("copied-source Artifact inventory drifted")
    reference_only = tuple(
        item
        for item in edition_materializations
        if item.materialization_kind == "reference_only"
    )
    if (
        len(reference_only) != 1
        or reference_only[0].source_artifact is None
        or reference_only[0].source_artifact.artifact_kind != "assessment_summary"
        or reference_only[0].output_digest is not None
        or reference_only[0].byte_size is not None
    ):
        raise RuntimeError("ScoreForm reference-only custody boundary drifted")
    if len(source_gate.requests) != 3:
        raise RuntimeError("Snapshot source reauthorization did not occur exactly three times")
    if len(quillan_gate.requests) != 2:
        raise RuntimeError("Quillan Artifact authorization did not occur exactly twice")
    if len(concord_gate.requests) != 1:
        raise RuntimeError("Concord Artifact authorization did not occur exactly once")
    if len(snapshot_gate.requests) != 1:
        raise RuntimeError("Snapshot build authorization did not occur exactly once")

    return BuiltPortfolio(
        snapshot_series_id=result.snapshot_series_id,
        edition_number=result.edition_number,
        materialization_counts=dict(sorted(actual_counts.items())),
        copied_artifact_kinds=copied_artifact_kinds,
        curation_authorization_requests=len(curation_gate.requests),
        snapshot_source_read_requests=len(source_gate.requests),
        quillan_artifact_authorization_requests=len(quillan_gate.requests),
        concord_artifact_authorization_requests=len(concord_gate.requests),
        snapshot_build_authorization_requests=len(snapshot_gate.requests),
    )
