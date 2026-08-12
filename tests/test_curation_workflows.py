from __future__ import annotations

from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    ACTOR,
    APPROVAL_REQUIREMENT_ID,
    REFLECTION_REQUIREMENT_ID,
    STUDENT_ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    create_annotation,
    create_reflection,
    create_working_composition,
    decide_selection_proposal,
    place_selection,
    propose_candidate_selection,
    reorder_section,
    replace_placement,
    review_curation_target,
    revise_reflection,
    select_candidate_directly,
    withdraw_selection,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CurationAnnotation,
    CurationReviewDecision,
    CurationTargetRef,
    PlacementPresentation,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioReflection,
    PortfolioSelection,
    SectionArrangementPointerRevision,
    SelectionDecision,
    SelectionLifecycleEvent,
    SelectionProposal,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
    WorkingPortfolioCompositionRevision,
)
from vitrine.storage import load_current_records, load_current_state


def _records(setup: object):
    return load_current_records(getattr(setup, "workspace"))


def _state(setup: object):
    return project_curation_state(_records(setup))


def _candidate_by(
    setup: object,
    *,
    module_id: str,
    native_revision: int | None = None,
) -> PortfolioCandidate:
    values = tuple(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioCandidate)
        and item.source_endpoint.producer_source.producer_module_id == module_id
        and (
            native_revision is None
            or item.source_endpoint.producer_source.native_revision == native_revision
        )
    )
    assert len(values) == 1
    return values[0]


def _direct_select(setup: object, candidate: PortfolioCandidate, section_id: str) -> PortfolioSelection:
    result = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(section_id,),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text=f"Select exact Candidate for {section_id}.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioSelection))


def _place(setup: object, selection: PortfolioSelection, section_id: str) -> PortfolioPlacement:
    state = _state(setup)
    heads = state.arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, section_id
    )
    expected_pointer = heads[0].pointer_revision if len(heads) == 1 else None
    result = place_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_arrangement_pointer_revision=expected_pointer,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def test_student_proposal_acceptance_creates_explicit_selection_provenance(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    proposed = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=STUDENT_ACTOR,
        proposal_origin="student",
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="I want this sample to represent my baseline.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    proposal = next(item for item in proposed.records if isinstance(item, SelectionProposal))
    accepted = decide_selection_proposal(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="accepted",
        decided_by=ACTOR,
        expected_state_revision=proposed.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="Accept the exact student proposal.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    decision = next(item for item in accepted.records if isinstance(item, SelectionDecision))
    selection = next(item for item in accepted.records if isinstance(item, PortfolioSelection))
    event = next(item for item in accepted.records if isinstance(item, SelectionLifecycleEvent))
    assert decision.resulting_selection_id == selection.selection_id
    assert event.event_kind == "activated"
    assert event.basis_selection_decision_id == decision.selection_decision_id
    assert selection.candidate_id == candidate.candidate_id
    assert selection.candidate_evaluation_id == candidate.candidate_evaluation_id


def test_rejected_proposal_and_system_suggestion_never_create_selection(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    proposal_result = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=ACTOR,
        proposal_origin="system_suggestion",
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert not any(isinstance(item, PortfolioSelection) for item in _records(setup))
    proposal = next(item for item in proposal_result.records if isinstance(item, SelectionProposal))
    decision_result = decide_selection_proposal(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="rejected",
        decided_by=ACTOR,
        expected_state_revision=proposal_result.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="Not part of this curation decision.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert any(
        isinstance(item, SelectionDecision) and item.decision == "rejected"
        for item in decision_result.records
    )
    assert not any(isinstance(item, PortfolioSelection) for item in _records(setup))


def test_denied_or_unresolved_authority_writes_nothing(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    start = setup.state_revision
    for outcome in ("denied", "unresolved"):
        with pytest.raises(CurationWorkflowError) as exc:
            propose_candidate_selection(
                setup.workspace,
                portfolio_id=setup.portfolio_id,
                candidate_id=candidate.candidate_id,
                proposer=STUDENT_ACTOR,
                proposal_origin="student",
                proposed_section_ids=("baseline",),
                expected_state_revision=start,
                authority_gate=StaticCurationAuthorityGate(outcome),
                clock=fixed_clock,
                id_factory=setup.ids,
            )
        assert exc.value.code == f"curation.authority_{outcome}"
        assert load_current_state(setup.workspace).state_revision == start


def test_conditional_concord_selection_requires_explicit_condition_acknowledgment(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_by(setup, module_id="vitrine_concord_fixture")
    assert candidate.condition_state == "collaborator_review_required"
    with pytest.raises(CurationWorkflowError) as exc:
        select_candidate_directly(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            candidate_id=candidate.candidate_id,
            selected_by=ACTOR,
            proposed_section_ids=("collaborative",),
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(acknowledge_conditions=False),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.candidate_condition_unresolved"

    selection = _direct_select(setup, candidate, "collaborative")
    head = _state(setup).selection_heads(selection.selection_id)
    assert len(head) == 1
    assert head[0].unresolved_condition_codes == ("collaborator_review_required",)


def test_placement_arrangement_and_pointer_are_atomic_and_complete(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    placement = _place(setup, selection, "baseline")
    state = _state(setup)
    arrangement = state.current_arrangement(
        setup.portfolio_id, setup.profile_binding_id, "baseline"
    )
    assert arrangement is not None
    assert arrangement.placement_ids == (placement.placement_id,)
    heads = state.arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, "baseline"
    )
    assert len(heads) == 1 and heads[0].arrangement_id == arrangement.arrangement_id


def test_same_selection_can_appear_in_distinct_sections_but_not_twice_in_one(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    selection = _direct_select(setup, candidate, "baseline")
    _place(setup, selection, "baseline")
    _place(setup, selection, "gallery")
    with pytest.raises(CurationWorkflowError) as exc:
        _place(setup, selection, "gallery")
    assert exc.value.code == "curation.placement_duplicate_active"


def test_section_maximum_prevents_second_scoreform_attempt_placement(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    attempt1 = _candidate_by(
        setup, module_id="vitrine_scoreform_fixture", native_revision=1
    )
    attempt2 = _candidate_by(
        setup, module_id="vitrine_scoreform_fixture", native_revision=2
    )
    selection1 = _direct_select(setup, attempt1, "assessment")
    selection2 = _direct_select(setup, attempt2, "assessment")
    _place(setup, selection1, "assessment")
    with pytest.raises(CurationWorkflowError) as exc:
        _place(setup, selection2, "assessment")
    assert exc.value.code == "curation.section_cardinality_exceeded"
    assert selection1.candidate_id != selection2.candidate_id


def test_reorder_requires_exact_pointer_and_preserves_explicit_order(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first = _direct_select(setup, setup.candidate("evidence_selected"), "gallery")
    second = _direct_select(setup, setup.candidate("evidence_approved"), "gallery")
    p1 = _place(setup, first, "gallery")
    p2 = _place(setup, second, "gallery")
    pointer = _state(setup).arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, "gallery"
    )[0]
    result = reorder_section(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        section_id="gallery",
        placement_ids=(p2.placement_id, p1.placement_id),
        arranged_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_arrangement_pointer_revision=pointer.pointer_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    next_pointer = next(
        item for item in result.records if isinstance(item, SectionArrangementPointerRevision)
    )
    assert next_pointer.pointer_revision == pointer.pointer_revision + 1
    arrangement = _state(setup).current_arrangement(
        setup.portfolio_id, setup.profile_binding_id, "gallery"
    )
    assert arrangement is not None
    assert arrangement.placement_ids == (p2.placement_id, p1.placement_id)
    with pytest.raises(CurationWorkflowError) as exc:
        reorder_section(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            section_id="gallery",
            placement_ids=(p1.placement_id, p2.placement_id),
            arranged_by=ACTOR,
            expected_state_revision=setup.state_revision,
            expected_arrangement_pointer_revision=pointer.pointer_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.arrangement_conflict"


def test_presentation_change_replaces_placement_without_mutation(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    old = _place(setup, selection, "baseline")
    pointer = _state(setup).arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, "baseline"
    )[0]
    result = replace_placement(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        placement_id=old.placement_id,
        replaced_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_pointer_revisions={"baseline": pointer.pointer_revision},
        authority_gate=StaticCurationAuthorityGate(),
        presentation=PlacementPresentation(
            display_title="Curator Display Title",
            display_caption="Curator caption only.",
        ),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    new = next(
        item
        for item in result.records
        if isinstance(item, PortfolioPlacement) and item.placement_id != old.placement_id
    )
    assert old.presentation is None
    assert new.presentation is not None
    assert new.presentation.display_title == "Curator Display Title"
    assert selection.candidate_id == setup.candidate("evidence_selected").candidate_id
    arrangement = _state(setup).current_arrangement(
        setup.portfolio_id, setup.profile_binding_id, "baseline"
    )
    assert arrangement is not None and arrangement.placement_ids == (new.placement_id,)


def test_annotation_and_reflection_are_revisioned_distinct_records(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    later = _direct_select(setup, setup.candidate("evidence_approved"), "later_work")
    annotation_result = create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(target_kind="selection", target_id=baseline.selection_id),
        ),
        author=ACTOR,
        content="Teacher context for this exact Selection.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    annotation = next(
        item for item in annotation_result.records if isinstance(item, CurationAnnotation)
    )
    reflection_result = create_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="compare_growth_prompt",
        prompt_version="1",
        prompt_snapshot="Compare these two works and explain what changed.",
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
        content="I changed my use of textual evidence between these drafts.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    reflection = next(
        item for item in reflection_result.records if isinstance(item, PortfolioReflection)
    )
    assert annotation.record_type != reflection.record_type
    assert reflection.reflection_requirement_id == REFLECTION_REQUIREMENT_ID
    assert tuple(item.semantic_role for item in reflection.target_references) == (
        "baseline",
        "later",
    )


def test_review_binds_exact_reflection_revision_and_does_not_follow_revision(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    later = _direct_select(setup, setup.candidate("evidence_approved"), "later_work")
    reflection_result = create_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="compare_growth_prompt",
        prompt_version="1",
        prompt_snapshot="Compare the exact selections.",
        author=STUDENT_ACTOR,
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection", target_id=baseline.selection_id, semantic_role="baseline"
            ),
            CurationTargetRef(
                target_kind="selection", target_id=later.selection_id, semantic_role="later"
            ),
        ),
        content="First reflection.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    reflection = next(
        item for item in reflection_result.records if isinstance(item, PortfolioReflection)
    )
    review_result = review_curation_target(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        target_scope="reflection",
        target_references=(
            CurationTargetRef(
                target_kind="reflection",
                target_id=reflection.reflection_id,
                target_revision=1,
            ),
        ),
        decision="approved",
        reviewed_by=ACTOR,
        reason="Approve only revision one.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    review = next(
        item for item in review_result.records if isinstance(item, CurationReviewDecision)
    )
    revised = revise_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_id=reflection.reflection_id,
        expected_reflection_revision=1,
        author=STUDENT_ACTOR,
        content="Revised reflection.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
    )
    reflection2 = next(
        item for item in revised.records if isinstance(item, PortfolioReflection)
    )
    assert reflection2.reflection_revision == 2
    assert review.target_references[0].target_revision == 1


def test_withdrawal_retires_placements_and_advances_empty_arrangement(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    _place(setup, selection, "baseline")
    pointer = _state(setup).arrangement_pointer_heads(
        setup.portfolio_id, setup.profile_binding_id, "baseline"
    )[0]
    withdraw_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=selection.selection_id,
        withdrawn_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_pointer_revisions={"baseline": pointer.pointer_revision},
        authority_gate=StaticCurationAuthorityGate(),
        reason="Remove this Selection from current curation.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    state = _state(setup)
    assert state.selection_status(selection.selection_id) == "withdrawn"
    assert state.active_placements(
        portfolio_id=setup.portfolio_id,
        profile_binding_id=setup.profile_binding_id,
        section_id="baseline",
    ) == ()
    arrangement = state.current_arrangement(
        setup.portfolio_id, setup.profile_binding_id, "baseline"
    )
    assert arrangement is not None and arrangement.placement_ids == ()


def test_composition_freezes_exact_curation_state_and_replays_identically(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    later = _direct_select(setup, setup.candidate("evidence_approved"), "later_work")
    _place(setup, baseline, "baseline")
    _place(setup, later, "later_work")
    reflection_result = create_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="compare_growth_prompt",
        prompt_version="1",
        prompt_snapshot="Compare the exact baseline and later work.",
        author=STUDENT_ACTOR,
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection", target_id=baseline.selection_id, semantic_role="baseline"
            ),
            CurationTargetRef(
                target_kind="selection", target_id=later.selection_id, semantic_role="later"
            ),
        ),
        content="Synthetic student interpretation, not a proficiency claim.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    reflection = next(
        item for item in reflection_result.records if isinstance(item, PortfolioReflection)
    )
    annotation_result = create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="comparison_note",
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(target_kind="selection", target_id=baseline.selection_id),
            CurationTargetRef(target_kind="selection", target_id=later.selection_id),
        ),
        author=ACTOR,
        content="Teacher context remains separate from student Reflection.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    annotation = next(
        item for item in annotation_result.records if isinstance(item, CurationAnnotation)
    )
    first = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Freeze exact synthetic working curation.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    composition = next(
        item
        for item in first.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventory = next(
        item
        for item in first.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    pointer = next(
        item
        for item in first.records
        if isinstance(item, WorkingPortfolioCompositionPointerRevision)
    )
    assert composition.composition_revision == 1
    assert {ref.record_id for ref in inventory.included_curation_revisions} >= {
        reflection.reflection_id,
        annotation.annotation_id,
    }
    assert "reflection_required" not in inventory.unresolved_obligation_codes
    second = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_composition_pointer_revision=pointer.pointer_revision,
        authority_gate=StaticCurationAuthorityGate(),
        composition_note="Freeze exact synthetic working curation.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert second.disposition == "existing"
    assert second.state_revision == first.state_revision


def test_curation_never_creates_snapshot_or_grading_records(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    _place(setup, selection, "baseline")
    rendered_types = {getattr(item, "record_type", "") for item in _records(setup)}
    assert not any(value.startswith("snapshot_") for value in rendered_types)
    assert not any("grade" in value.lower() or "proficiency" in value.lower() for value in rendered_types)
