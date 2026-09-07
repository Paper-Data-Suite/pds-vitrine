from __future__ import annotations

import io
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    ACTOR,
    APPROVAL_REQUIREMENT_ID,
    REFLECTION_REQUIREMENT_ID,
    STUDENT_ACTOR,
    CurationFixtureWorkspace,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
)
from vitrine import cli
from vitrine.candidate_inbox import CandidateInboxQuery
from vitrine.candidate_review import (
    CandidateReviewError,
    execute_annotation_action,
    execute_candidate_decision,
    execute_curation_review,
    execute_reflection_action,
    execute_selection_placement,
    execute_selection_replacement,
    execute_selection_withdrawal,
    get_candidate_review_detail,
    list_candidate_review_entries,
    plan_annotation_creation,
    plan_candidate_decision,
    plan_curation_review,
    plan_reflection_creation,
    plan_selection_placement,
    plan_selection_replacement,
    plan_selection_withdrawal,
)
from vitrine.curation_services import CurationWorkflowError
from vitrine.models import (
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    CurationAnnotation,
    CurationReviewDecision,
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioReflection,
    PortfolioSelection,
    SelectionDecision,
    SelectionProposal,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)
from vitrine.workflow_context import default_workflow_dependencies


def _entry(candidate: PortfolioCandidate) -> str:
    return f"candidate:{candidate.candidate_id}"


def _candidate_for_section(
    setup: CurationFixtureWorkspace,
    section_id: str,
    *,
    excluding: set[str] | None = None,
) -> PortfolioCandidate:
    excluded = excluding or set()
    return next(
        item
        for item in setup.candidate_records_by_source.values()
        if section_id in item.eligible_section_ids and item.candidate_id not in excluded
    )


def _two_candidates_for_section(
    setup: CurationFixtureWorkspace,
    section_id: str,
) -> tuple[PortfolioCandidate, PortfolioCandidate]:
    values = tuple(
        item
        for item in setup.candidate_records_by_source.values()
        if section_id in item.eligible_section_ids
    )
    assert len(values) >= 2
    return values[0], values[1]


def _select(
    setup: CurationFixtureWorkspace,
    candidate: PortfolioCandidate,
    section_id: str,
) -> PortfolioSelection:
    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=_entry(candidate),
        decision="select",
        proposed_section_ids=(section_id,),
    )
    result = execute_candidate_decision(
        setup.workspace,
        plan,
        actor=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    return next(item for item in result.records if isinstance(item, PortfolioSelection))


def _place(
    setup: CurationFixtureWorkspace,
    candidate: PortfolioCandidate,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    plan = plan_selection_placement(
        setup.workspace,
        entry_id=_entry(candidate),
        selection_id=selection.selection_id,
        section_id=section_id,
    )
    result = execute_selection_placement(
        setup.workspace,
        plan,
        placed_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def _current_evaluation(
    setup: CurationFixtureWorkspace,
    candidate: PortfolioCandidate,
) -> CandidateEvaluation:
    return next(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == candidate.candidate_evaluation_id
    )


def test_acceptance_full_guided_history_is_append_preserving(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    entry_id = _entry(candidate)

    decision_plan = plan_candidate_decision(
        setup.workspace,
        entry_id=entry_id,
        decision="select",
        proposed_section_ids=("baseline",),
    )
    selected = execute_candidate_decision(
        setup.workspace,
        decision_plan,
        actor=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
        rationale_text="Use this exact Candidate as baseline evidence.",
    )
    selection = next(
        item for item in selected.records if isinstance(item, PortfolioSelection)
    )
    assert not any(isinstance(item, PortfolioPlacement) for item in selected.records)

    placement = _place(setup, candidate, selection, "baseline")
    selection_target = CurationTargetRef(
        target_kind="selection",
        target_id=selection.selection_id,
    )
    annotation_plan = plan_annotation_creation(
        setup.workspace,
        entry_id=entry_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(selection_target,),
        content="Teacher-authored context for this exact Selection.",
    )
    annotation_result = execute_annotation_action(
        setup.workspace,
        annotation_plan,
        author=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    annotation = next(
        item for item in annotation_result.records if isinstance(item, CurationAnnotation)
    )

    reflection_plan = plan_reflection_creation(
        setup.workspace,
        entry_id=entry_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="acceptance_growth_prompt",
        prompt_version="1",
        prompt_snapshot="What changed in this work, and what evidence shows it?",
        target_scope="selection",
        target_references=(selection_target,),
        content="The reflection remains a separate authored curation record.",
    )
    reflection_result = execute_reflection_action(
        setup.workspace,
        reflection_plan,
        author=STUDENT_ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    reflection = next(
        item for item in reflection_result.records if isinstance(item, PortfolioReflection)
    )

    annotation_target = CurationTargetRef(
        target_kind="annotation",
        target_id=annotation.annotation_id,
        target_revision=annotation.annotation_revision,
    )
    review_plan = plan_curation_review(
        setup.workspace,
        entry_id=entry_id,
        target_scope="annotation",
        target_references=(annotation_target,),
        decision="approved",
        reason="Review this exact immutable Annotation revision.",
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
    )
    review_result = execute_curation_review(
        setup.workspace,
        review_plan,
        reviewed_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    review = next(
        item
        for item in review_result.records
        if isinstance(item, CurationReviewDecision)
    )

    withdrawal_plan = plan_selection_withdrawal(
        setup.workspace,
        entry_id=entry_id,
        selection_id=selection.selection_id,
        reason="Withdraw active use without deleting its history.",
    )
    execute_selection_withdrawal(
        setup.workspace,
        withdrawal_plan,
        withdrawn_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )

    detail = get_candidate_review_detail(setup.workspace, entry_id)
    selected_summary = next(
        item for item in detail.selections if item.selection_id == selection.selection_id
    )
    placement_summary = next(
        item for item in detail.placements if item.placement_id == placement.placement_id
    )
    assert selected_summary.lifecycle_state == "withdrawn"
    assert placement_summary.lifecycle_state == "withdrawn"
    assert any(item.annotation_id == annotation.annotation_id for item in detail.annotations)
    assert any(item.reflection_id == reflection.reflection_id for item in detail.reflections)
    assert any(
        item.curation_review_decision_id == review.curation_review_decision_id
        and item.target_references == (annotation_target,)
        for item in detail.reviews
    )
    persisted = load_current_records(setup.workspace)
    assert any(
        isinstance(item, PortfolioSelection)
        and item.selection_id == selection.selection_id
        for item in persisted
    )
    assert any(
        isinstance(item, PortfolioPlacement)
        and item.placement_id == placement.placement_id
        for item in persisted
    )


def test_acceptance_cli_decline_projects_through_guided_review_without_selection(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    entry_id = _entry(candidate)
    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=StaticCurationAuthorityGate(),
        development_fixture_mode=True,
    )

    assert (
        cli.main(
            [
                "candidate",
                "decide",
                entry_id,
                "--decision",
                "decline",
                "--section-id",
                "baseline",
                "--reason",
                "Do not use this Candidate in the Portfolio.",
                "--actor-id",
                "teacher_acceptance",
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=io.StringIO(),
        )
        == 0
    )

    detail = get_candidate_review_detail(setup.workspace, entry_id)
    proposal = detail.proposals[-1]
    assert proposal.proposal_origin == "teacher"
    assert proposal.proposed_section_ids == ("baseline",)
    assert proposal.decisions[-1].decision == "rejected"
    assert detail.selections == ()
    records = load_current_records(setup.workspace)
    assert any(isinstance(item, SelectionProposal) for item in records)
    assert any(
        isinstance(item, SelectionDecision) and item.decision == "rejected"
        for item in records
    )
    assert not any(isinstance(item, PortfolioSelection) for item in records)


def test_acceptance_stale_decision_plan_fails_closed_without_partial_write(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first, second = _two_candidates_for_section(setup, "gallery")
    stale_plan = plan_candidate_decision(
        setup.workspace,
        entry_id=_entry(first),
        decision="select",
        proposed_section_ids=("gallery",),
    )
    _select(setup, second, "gallery")
    before = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)

    with pytest.raises(CurationWorkflowError) as error:
        execute_candidate_decision(
            setup.workspace,
            stale_plan,
            actor=ACTOR,
            authority_gate=StaticCurationAuthorityGate(),
        )

    assert error.value.code == "curation.state_conflict"
    assert load_current_state(setup.workspace).state_revision == before
    assert load_current_records(setup.workspace) == before_records


@pytest.mark.parametrize(
    ("outcome", "decision", "expected_code"),
    (
        ("denied", "select", "curation.authority_denied"),
        ("unresolved", "decline", "curation.authority_unresolved"),
    ),
)
def test_acceptance_authority_failures_write_nothing(
    tmp_path: Path,
    outcome: str,
    decision: str,
    expected_code: str,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=_entry(candidate),
        decision=decision,
        proposed_section_ids=("baseline",),
    )
    before = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)

    with pytest.raises(CurationWorkflowError) as error:
        execute_candidate_decision(
            setup.workspace,
            plan,
            actor=ACTOR,
            authority_gate=StaticCurationAuthorityGate(outcome),
        )

    assert error.value.code == expected_code
    assert load_current_state(setup.workspace).state_revision == before
    assert load_current_records(setup.workspace) == before_records


def test_acceptance_arrangement_pointer_conflict_is_not_silently_refreshed(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first, second = _two_candidates_for_section(setup, "gallery")
    first_selection = _select(setup, first, "gallery")
    second_selection = _select(setup, second, "gallery")
    first_plan = plan_selection_placement(
        setup.workspace,
        entry_id=_entry(first),
        selection_id=first_selection.selection_id,
        section_id="gallery",
    )
    assert first_plan.expected_arrangement_pointer_revision is None
    _place(setup, second, second_selection, "gallery")
    current_revision = load_current_state(setup.workspace).state_revision
    pointer_stale_plan = replace(
        first_plan,
        observed_state_revision=current_revision,
    )
    before_records = load_current_records(setup.workspace)

    with pytest.raises(CurationWorkflowError) as error:
        execute_selection_placement(
            setup.workspace,
            pointer_stale_plan,
            placed_by=ACTOR,
            authority_gate=StaticCurationAuthorityGate(),
        )

    assert error.value.code == "curation.arrangement_conflict"
    assert load_current_state(setup.workspace).state_revision == current_revision
    assert load_current_records(setup.workspace) == before_records


def test_acceptance_replacement_drop_does_not_infer_same_section_placement(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    current, successor = _two_candidates_for_section(setup, "baseline")
    current_selection = _select(setup, current, "baseline")
    old_placement = _place(setup, current, current_selection, "baseline")
    plan = plan_selection_replacement(
        setup.workspace,
        entry_id=_entry(current),
        selection_id=current_selection.selection_id,
        successor_entry_id=_entry(successor),
        proposed_section_ids=("baseline",),
        placement_dispositions={old_placement.placement_id: None},
        reason="Replace the Selection but explicitly drop its old Placement.",
    )

    result = execute_selection_replacement(
        setup.workspace,
        plan,
        replaced_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    proposal = next(
        item for item in result.records if isinstance(item, SelectionProposal)
    )
    successor_selection = next(
        item
        for item in result.records
        if isinstance(item, PortfolioSelection)
        and item.candidate_id == successor.candidate_id
    )
    assert proposal.proposed_section_ids == ("baseline",)
    assert not any(
        isinstance(item, PortfolioPlacement)
        and item.selection_id == successor_selection.selection_id
        for item in result.records
    )
    successor_detail = get_candidate_review_detail(setup.workspace, _entry(successor))
    assert not any(
        item.selection_id == successor_selection.selection_id
        and item.lifecycle_state == "activated"
        for item in successor_detail.placements
    )
    assert any(
        isinstance(item, PortfolioPlacement)
        and item.placement_id == old_placement.placement_id
        for item in load_current_records(setup.workspace)
    )


def test_acceptance_current_evaluation_never_retargets_frozen_selection_provenance(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    original = _current_evaluation(setup, candidate)
    successor = replace(
        original,
        candidate_evaluation_id="candidate_evaluation_acceptance_successor",
        predecessor_evaluation_id=original.candidate_evaluation_id,
        evaluated_at=original.evaluated_at + timedelta(seconds=30),
    )
    pointer = CandidateCurrentEvaluationPointerRevision(
        candidate_id=candidate.candidate_id,
        pointer_revision=2,
        current_candidate_evaluation_id=successor.candidate_evaluation_id,
        predecessor_pointer_revision=1,
        previous_candidate_evaluation_id=original.candidate_evaluation_id,
        updated_at=successor.evaluated_at,
        updated_by=ACTOR,
        reason="Acceptance fixture reevaluation.",
    )
    commit_record_batch(
        setup.workspace,
        (successor, pointer),
        expected_state_revision=load_current_state(setup.workspace).state_revision,
    )

    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=_entry(candidate),
        decision="select",
        proposed_section_ids=("baseline",),
    )
    assert plan.current_review_evaluation_id == successor.candidate_evaluation_id
    assert plan.curation_provenance_evaluation_id == original.candidate_evaluation_id
    result = execute_candidate_decision(
        setup.workspace,
        plan,
        actor=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    selection = next(
        item for item in result.records if isinstance(item, PortfolioSelection)
    )
    proposal = next(item for item in result.records if isinstance(item, SelectionProposal))
    assert selection.candidate_evaluation_id == original.candidate_evaluation_id
    assert proposal.candidate_evaluation_id == original.candidate_evaluation_id


def test_acceptance_evaluation_only_is_unselectable_and_suppressed_stays_absent(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "baseline")
    original = _current_evaluation(setup, candidate)
    negative = replace(
        original,
        candidate_evaluation_id="candidate_evaluation_acceptance_ineligible",
        predecessor_evaluation_id=None,
        eligible_section_ids=(),
        outcome="ineligible",
        reason_codes=("acceptance_not_eligible",),
        evaluated_at=original.evaluated_at + timedelta(seconds=60),
    )
    suppressed = replace(
        original,
        candidate_evaluation_id="candidate_evaluation_acceptance_suppressed",
        predecessor_evaluation_id=None,
        eligible_section_ids=(),
        outcome="suppressed",
        reason_codes=("acceptance_suppressed",),
        evaluated_at=original.evaluated_at + timedelta(seconds=90),
    )
    commit_record_batch(
        setup.workspace,
        (negative, suppressed),
        expected_state_revision=load_current_state(setup.workspace).state_revision,
    )

    negative_entry = f"evaluation:{negative.candidate_evaluation_id}"
    detail = get_candidate_review_detail(setup.workspace, negative_entry)
    assert detail.selectable is False
    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=negative_entry,
            decision="decline",
            proposed_section_ids=("baseline",),
        )
    assert error.value.code == "candidate_review.not_selectable"

    listed = list_candidate_review_entries(
        setup.workspace,
        CandidateInboxQuery(portfolio_id=setup.portfolio_id, limit=100),
    )
    assert all(
        item.current_evaluation_id != suppressed.candidate_evaluation_id
        for item in listed.items
    )
