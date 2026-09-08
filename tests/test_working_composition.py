from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import vitrine.curation_services as curation_services
import vitrine.working_composition as working_composition
from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    STUDENT_ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    WorkingCompositionSourceCurrentness,
    create_annotation,
    create_reflection,
    create_working_composition,
    derive_working_composition,
    observe_working_composition_source,
    place_selection,
    reorder_section,
    review_curation_target,
    select_candidate_directly,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CurationTargetRef,
    PortfolioPlacement,
    PortfolioSelection,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
    WorkingPortfolioCompositionRevision,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.working_composition import (
    WORKING_COMPOSITION_CONTRACT_VERSION,
    WorkingCompositionError,
    freeze_prepared_working_composition,
    prepare_working_composition,
)


def _select(
    setup: object,
    source_record_id: str,
    section_id: str,
) -> PortfolioSelection:
    workspace = getattr(setup, "workspace")
    candidate = getattr(setup, "candidate")(source_record_id)
    ids = getattr(setup, "ids")
    selected = select_candidate_directly(
        workspace,
        portfolio_id=getattr(setup, "portfolio_id"),
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(section_id,),
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=ids,
    )
    return next(
        item for item in selected.records if isinstance(item, PortfolioSelection)
    )


def _place(
    setup: object,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    workspace = getattr(setup, "workspace")
    state = project_curation_state(load_current_records(workspace))
    heads = state.arrangement_pointer_heads(
        getattr(setup, "portfolio_id"),
        getattr(setup, "profile_binding_id"),
        section_id,
    )
    expected_pointer = heads[0].pointer_revision if len(heads) == 1 else None
    placed = place_selection(
        workspace,
        portfolio_id=getattr(setup, "portfolio_id"),
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=ACTOR,
        expected_state_revision=load_current_state(workspace).state_revision,
        expected_arrangement_pointer_revision=expected_pointer,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    return next(
        item for item in placed.records if isinstance(item, PortfolioPlacement)
    )


def _select_and_place(
    setup: object,
    source_record_id: str,
    section_id: str,
) -> tuple[PortfolioSelection, PortfolioPlacement]:
    selection = _select(setup, source_record_id, section_id)
    return selection, _place(setup, selection, section_id)


def _requirement(preparation: object, requirement_id: str):
    values = tuple(
        item
        for item in getattr(preparation, "requirements")
        if item.requirement_id == requirement_id
    )
    assert len(values) == 1
    return values[0]


def test_preparation_is_read_only_and_requires_no_curation_authority(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    before = load_current_state(setup.workspace).state_revision

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert load_current_state(setup.workspace).state_revision == before
    assert preparation.contract_version == WORKING_COMPOSITION_CONTRACT_VERSION
    assert preparation.observed_state_revision == before
    assert preparation.observed_composition_pointer_revision is None
    assert preparation.current_composition_revision is None
    assert preparation.predicted_composition_revision == 1
    assert preparation.predicted_composition_pointer_revision == 1
    assert preparation.disposition == "create_initial"
    assert preparation.payload.coherence_state == "coherent_with_unresolved_obligations"
    assert "section_minimum_missing" in preparation.payload.unresolved_obligation_codes


def test_preparation_payload_matches_canonical_composition_write(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline, baseline_placement = _select_and_place(
        setup, "evidence_selected", "baseline"
    )
    later, later_placement = _select_and_place(
        setup, "evidence_approved", "later_work"
    )
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    gate = StaticCurationAuthorityGate()

    result = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=preparation.observed_state_revision,
        expected_composition_pointer_revision=(
            preparation.observed_composition_pointer_revision
        ),
        authority_gate=gate,
        composition_note="Freeze the exact prepared state.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    composition = next(
        item
        for item in result.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in result.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    pointer = next(
        item
        for item in result.records
        if isinstance(item, WorkingPortfolioCompositionPointerRevision)
    )
    assert preparation.payload.selection_ids == (
        baseline.selection_id,
        later.selection_id,
    )
    assert preparation.payload.placement_ids == (
        baseline_placement.placement_id,
        later_placement.placement_id,
    )
    assert composition.selection_ids == preparation.payload.selection_ids
    assert composition.placement_ids == preparation.payload.placement_ids
    assert composition.arrangement_ids == preparation.payload.arrangement_ids
    assert (
        inventory.included_rationale_ids == preparation.payload.included_rationale_ids
    )
    assert (
        inventory.included_curation_revisions
        == preparation.payload.included_curation_revisions
    )
    assert (
        inventory.applicable_review_decision_ids
        == preparation.payload.applicable_review_decision_ids
    )
    assert (
        inventory.related_profile_requirement_ids
        == preparation.payload.related_profile_requirement_ids
    )
    assert (
        inventory.unresolved_obligation_codes
        == preparation.payload.unresolved_obligation_codes
    )
    assert inventory.coherence_state == preparation.payload.coherence_state
    assert (
        composition.composition_revision == preparation.predicted_composition_revision
    )
    assert (
        pointer.pointer_revision == preparation.predicted_composition_pointer_revision
    )
    assert [request.operation for request in gate.requests] == ["compose_portfolio"]


def test_exact_current_payload_prepares_as_reuse_without_writing(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    _select_and_place(setup, "evidence_selected", "baseline")
    _select_and_place(setup, "evidence_approved", "later_work")
    first_preparation = prepare_working_composition(
        setup.workspace, setup.portfolio_id
    )
    created = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=first_preparation.observed_state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert created.disposition == "created"
    before = load_current_state(setup.workspace).state_revision

    replay = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert load_current_state(setup.workspace).state_revision == before
    assert replay.disposition == "reuse_exact_current"
    assert replay.current_composition_revision == 1
    assert replay.predicted_composition_revision == 1
    assert replay.observed_composition_pointer_revision == 1
    assert replay.predicted_composition_pointer_revision == 1


def test_successor_preparation_advances_only_after_semantic_curation_change(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline, _ = _select_and_place(setup, "evidence_selected", "baseline")
    _select_and_place(setup, "evidence_approved", "later_work")
    first = prepare_working_composition(setup.workspace, setup.portfolio_id)
    create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=first.observed_state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection", target_id=baseline.selection_id
            ),
        ),
        author=ACTOR,
        content="New exact curation context after the first Composition.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    successor = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert successor.disposition == "create_successor"
    assert successor.current_composition_revision == 1
    assert successor.predicted_composition_revision == 2
    assert successor.predecessor_composition_revision == 1
    assert successor.observed_composition_pointer_revision == 1
    assert successor.predicted_composition_pointer_revision == 2
    records = load_current_records(setup.workspace)
    assert sum(
        isinstance(item, WorkingPortfolioCompositionRevision) for item in records
    ) == 1


def test_section_and_placement_preview_preserves_profile_and_arrangement_order(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first = _select(setup, "evidence_selected", "gallery")
    second = _select(setup, "evidence_approved", "gallery")
    p1 = _place(setup, first, "gallery")
    p2 = _place(setup, second, "gallery")
    state = project_curation_state(load_current_records(setup.workspace))
    pointer = state.arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, "gallery"
    )[0]
    reorder_section(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        section_id="gallery",
        placement_ids=(p2.placement_id, p1.placement_id),
        arranged_by=ACTOR,
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        expected_arrangement_pointer_revision=pointer.pointer_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert tuple(item.section_id for item in preparation.sections) == (
        "baseline",
        "later_work",
        "feedback",
        "assessment",
        "collaborative",
        "gallery",
        "prohibited_internal",
    )
    gallery = next(
        item for item in preparation.sections if item.section_id == "gallery"
    )
    assert tuple(item.placement_id for item in gallery.placements) == (
        p2.placement_id,
        p1.placement_id,
    )
    assert preparation.payload.placement_ids == (p2.placement_id, p1.placement_id)
    assert gallery.active_placement_count == 2
    assert gallery.current_arrangement_id is not None
    assert gallery.current_arrangement_revision == 3
    assert gallery.current_arrangement_pointer_revision == 3


def test_unplaced_active_selection_is_visible_and_remains_in_exact_payload(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _select(setup, "evidence_selected", "gallery")
    before = load_current_state(setup.workspace).state_revision

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    summary = next(
        item
        for item in preparation.selections
        if item.selection_id == selection.selection_id
    )
    assert summary.is_placed is False
    assert summary.placement_ids == ()
    assert summary.section_ids == ()
    assert preparation.unplaced_selection_ids == (selection.selection_id,)
    assert selection.selection_id in preparation.payload.selection_ids
    assert preparation.payload.placement_ids == ()
    assert load_current_state(setup.workspace).state_revision == before


def test_requirement_explanation_uses_only_structured_profile_semantics(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    baseline = _requirement(preparation, "baseline_section_rule")
    later = _requirement(preparation, "later_work_section_rule")
    feedback = _requirement(preparation, "feedback_section_rule")
    prohibited = _requirement(preparation, "prohibited_internal_section_rule")
    reflection = _requirement(preparation, REFLECTION_REQUIREMENT_ID)
    approval = _requirement(preparation, "approval_teacher_review")
    assert baseline.status == "unresolved_missing"
    assert baseline.associated_unresolved_obligation_codes == (
        "section_minimum_missing",
    )
    assert later.status == "unresolved_missing"
    assert feedback.status == "optional_absent"
    assert prohibited.status == "prohibited_clear"
    assert reflection.status == "unresolved_missing"
    assert reflection.associated_unresolved_obligation_codes == (
        "reflection_required",
    )
    assert reflection.related_to_frozen_inventory is True
    assert approval.status == "optional_absent"
    assert approval.associated_unresolved_obligation_codes == ()
    assert approval.statement == "Teacher may review an exact curation target."


def test_required_section_and_reflection_requirements_become_satisfied_explicitly(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline, _ = _select_and_place(setup, "evidence_selected", "baseline")
    later, _ = _select_and_place(setup, "evidence_approved", "later_work")
    create_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_prompt",
        prompt_version="1",
        prompt_snapshot="Compare the exact curated baseline and later work.",
        author=STUDENT_ACTOR,
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=baseline.selection_id,
                semantic_role="baseline",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id=later.selection_id,
                semantic_role="later",
            ),
        ),
        content="Synthetic student interpretation only.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert _requirement(preparation, "baseline_section_rule").status == (
        "satisfied_current_curation"
    )
    assert _requirement(preparation, "later_work_section_rule").status == (
        "satisfied_current_curation"
    )
    reflection = _requirement(preparation, REFLECTION_REQUIREMENT_ID)
    assert reflection.status == "satisfied_current_curation"
    assert reflection.associated_unresolved_obligation_codes == ()
    assert (
        "section_minimum_missing"
        not in preparation.payload.unresolved_obligation_codes
    )
    assert "reflection_required" not in preparation.payload.unresolved_obligation_codes


def test_source_currentness_observation_is_bounded_and_exact(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _select(setup, "evidence_selected", "gallery")
    before = load_current_state(setup.workspace).state_revision

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert load_current_state(setup.workspace).state_revision == before
    assert len(preparation.source_observations) == 1
    observation = preparation.source_observations[0]
    candidate = setup.candidate("evidence_selected")
    assert observation.selection_id == selection.selection_id
    assert observation.candidate_id == candidate.candidate_id
    assert observation.publication_id == (
        candidate.source_endpoint.core_publication.publication_id
    )
    assert observation.series_head_publication_id == observation.publication_id
    assert observation.observed_series_state == "current"
    assert observation.observed_withdrawal_state == "not_withdrawn"
    assert observation.current_use_state == "current"


def test_applicable_review_projection_preserves_exact_target_and_attention(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _select(setup, "evidence_selected", "gallery")
    reviewed = review_curation_target(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selection.selection_id,
            ),
        ),
        decision="changes_requested",
        reviewed_by=ACTOR,
        reason="Revise the exact current curation before later use.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        approval_requirement_id="approval_teacher_review",
        required_follow_up_codes=("revise_context",),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    review = next(
        item
        for item in reviewed.records
        if item.record_type == "curation_review_decision"
    )

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert preparation.payload.applicable_review_decision_ids == (
        review.curation_review_decision_id,
    )
    assert len(preparation.reviews) == 1
    summary = preparation.reviews[0]
    assert summary.curation_review_decision_id == review.curation_review_decision_id
    assert summary.decision == "changes_requested"
    assert summary.approval_requirement_id == "approval_teacher_review"
    assert summary.target_references == review.target_references
    assert summary.required_follow_up_codes == ("revise_context",)
    assert summary.requires_attention is True


def test_profile_audience_rules_are_constraints_not_audience_context(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    before_records = load_current_records(setup.workspace)

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert len(preparation.audience_rules) == 1
    audience = preparation.audience_rules[0]
    assert audience.audience_rule_id == "student_internal"
    assert audience.audience_class == "student"
    assert audience.allowed_content_classes == (
        "assessment_summary",
        "feedback",
        "student_work",
    )
    assert audience.prohibited_content_classes == ("private_teacher_note",)
    assert audience.required_review_classes == ("privacy_review",)
    assert audience.presentation_class == "student_portfolio"
    assert not any(item.record_type == "audience_context" for item in before_records)
    assert not any(
        item.record_type == "audience_context"
        for item in load_current_records(setup.workspace)
    )


def test_preparation_fingerprint_is_deterministic_and_note_aware_only_when_persisted(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    _select_and_place(setup, "evidence_selected", "baseline")
    _select_and_place(setup, "evidence_approved", "later_work")

    first = prepare_working_composition(
        setup.workspace, setup.portfolio_id, composition_note="Prepared note A"
    )
    repeated = prepare_working_composition(
        setup.workspace, setup.portfolio_id, composition_note="Prepared note A"
    )
    changed_note = prepare_working_composition(
        setup.workspace, setup.portfolio_id, composition_note="Prepared note B"
    )

    assert first.preparation_fingerprint == repeated.preparation_fingerprint
    assert len(first.preparation_fingerprint) == 64
    assert first.preparation_fingerprint != changed_note.preparation_fingerprint
    assert first.composition_note_will_persist is True
    assert first.requested_composition_note == "Prepared note A"

    create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=first.observed_state_revision,
        expected_composition_pointer_revision=(
            first.observed_composition_pointer_revision
        ),
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Prepared note A",
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    replay_a = prepare_working_composition(
        setup.workspace, setup.portfolio_id, composition_note="Ignored replay note A"
    )
    replay_b = prepare_working_composition(
        setup.workspace, setup.portfolio_id, composition_note="Ignored replay note B"
    )
    assert replay_a.disposition == "reuse_exact_current"
    assert replay_a.composition_note_will_persist is False
    assert replay_b.composition_note_will_persist is False
    assert replay_a.preparation_fingerprint == replay_b.preparation_fingerprint

def test_prepared_freeze_commits_exact_reviewed_payload_after_authority(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    _select_and_place(setup, "evidence_selected", "baseline")
    _select_and_place(setup, "evidence_approved", "later_work")
    preparation = prepare_working_composition(
        setup.workspace,
        setup.portfolio_id,
        composition_note="Freeze this exact reviewed state.",
    )
    gate = StaticCurationAuthorityGate()

    result = freeze_prepared_working_composition(
        setup.workspace, preparation, created_by=ACTOR, authority_gate=gate
    )

    assert result.disposition == "created"
    composition = next(
        item
        for item in result.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in result.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    assert composition.selection_ids == preparation.payload.selection_ids
    assert composition.placement_ids == preparation.payload.placement_ids
    assert composition.arrangement_ids == preparation.payload.arrangement_ids
    assert composition.composition_note == "Freeze this exact reviewed state."
    assert inventory.unresolved_obligation_codes == (
        preparation.payload.unresolved_obligation_codes
    )
    assert [request.operation for request in gate.requests] == ["compose_portfolio"]


def test_prepared_freeze_fails_closed_when_vitrine_state_changes(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _select(setup, "evidence_selected", "gallery")
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection", target_id=selection.selection_id
            ),
        ),
        author=ACTOR,
        content="Advance Vitrine state after the preview.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    before = load_current_state(setup.workspace).state_revision
    gate = StaticCurationAuthorityGate()

    with pytest.raises(WorkingCompositionError) as exc:
        freeze_prepared_working_composition(
            setup.workspace, preparation, created_by=ACTOR, authority_gate=gate
        )

    assert exc.value.code == "working_composition.state_changed"
    assert load_current_state(setup.workspace).state_revision == before
    assert gate.requests == []


def test_prepared_freeze_fails_closed_when_core_source_observation_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    _select(setup, "evidence_selected", "gallery")
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    original = preparation.source_observations[0]

    def changed_source(
        workspace_root: str | Path,
        *,
        selection_id: str,
        candidate: object,
    ) -> WorkingCompositionSourceCurrentness:
        del workspace_root, candidate
        return WorkingCompositionSourceCurrentness(
            selection_id=selection_id,
            candidate_id=original.candidate_id,
            publication_id=original.publication_id,
            series_head_publication_id="publication_successor",
            observed_series_state="historical",
            observed_withdrawal_state="not_withdrawn",
            current_use_state="historical",
        )

    monkeypatch.setattr(
        working_composition, "observe_working_composition_source", changed_source
    )
    before = load_current_state(setup.workspace).state_revision
    gate = StaticCurationAuthorityGate()

    with pytest.raises(WorkingCompositionError) as exc:
        freeze_prepared_working_composition(
            setup.workspace, preparation, created_by=ACTOR, authority_gate=gate
        )

    assert exc.value.code == "working_composition.source_state_changed"
    assert load_current_state(setup.workspace).state_revision == before
    assert gate.requests == []


def test_prepared_freeze_rejects_tampered_fingerprint_and_pointer(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    _select(setup, "evidence_selected", "gallery")
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    before = load_current_state(setup.workspace).state_revision

    fingerprint_gate = StaticCurationAuthorityGate()
    with pytest.raises(WorkingCompositionError) as fingerprint_exc:
        freeze_prepared_working_composition(
            setup.workspace,
            replace(preparation, preparation_fingerprint="0" * 64),
            created_by=ACTOR,
            authority_gate=fingerprint_gate,
        )
    assert fingerprint_exc.value.code == "working_composition.preparation_mismatch"
    assert fingerprint_gate.requests == []

    pointer_gate = StaticCurationAuthorityGate()
    with pytest.raises(WorkingCompositionError) as pointer_exc:
        freeze_prepared_working_composition(
            setup.workspace,
            replace(preparation, observed_composition_pointer_revision=99),
            created_by=ACTOR,
            authority_gate=pointer_gate,
        )
    assert pointer_exc.value.code == (
        "working_composition.composition_pointer_changed"
    )
    assert pointer_gate.requests == []
    assert load_current_state(setup.workspace).state_revision == before


def test_canonical_prepared_guard_checks_derivation_before_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _select(setup, "evidence_selected", "gallery")
    expected_derivation = derive_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        expected_state_revision=load_current_state(setup.workspace).state_revision,
    )
    candidate = setup.candidate("evidence_selected")
    observed = observe_working_composition_source(
        setup.workspace, selection_id=selection.selection_id, candidate=candidate
    )

    def changed_source(
        workspace_root: str | Path,
        *,
        selection_id: str,
        candidate: object,
    ) -> WorkingCompositionSourceCurrentness:
        del workspace_root, candidate
        return WorkingCompositionSourceCurrentness(
            selection_id=selection_id,
            candidate_id=observed.candidate_id,
            publication_id=observed.publication_id,
            series_head_publication_id="publication_successor",
            observed_series_state="historical",
            observed_withdrawal_state="not_withdrawn",
            current_use_state="historical",
        )

    monkeypatch.setattr(
        curation_services, "_observe_working_composition_source", changed_source
    )
    gate = StaticCurationAuthorityGate()
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError) as exc:
        create_working_composition(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            created_by=ACTOR,
            expected_state_revision=before,
            expected_composition_pointer_revision=None,
            authority_gate=gate,
            expected_derivation=expected_derivation,
            expected_source_observations=(observed,),
        )

    assert exc.value.code == "curation.composition_preparation_mismatch"
    assert gate.requests == []
    assert load_current_state(setup.workspace).state_revision == before

