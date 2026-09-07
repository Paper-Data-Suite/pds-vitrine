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
)
from vitrine.candidate_review import (
    CandidateReviewError,
    execute_annotation_action,
    execute_curation_review,
    execute_reflection_action,
    get_candidate_review_detail,
    plan_annotation_creation,
    plan_annotation_revision,
    plan_curation_review,
    plan_reflection_creation,
    plan_reflection_revision,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    create_annotation,
    select_candidate_directly,
)
from vitrine.models import (
    CurationAnnotation,
    CurationReviewDecision,
    CurationTargetRef,
    PortfolioReflection,
    PortfolioSelection,
)
from vitrine.storage import load_current_records, load_current_state


def _entry_id(candidate_id: str) -> str:
    return f"candidate:{candidate_id}"


def _select(setup: object, source_record_id: str) -> tuple[object, PortfolioSelection]:
    candidate = setup.candidate(source_record_id)
    result = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(candidate.eligible_section_ids[0],),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
    )
    selection = next(
        item for item in result.records if isinstance(item, PortfolioSelection)
    )
    return candidate, selection


def test_detail_exposes_exact_reflection_and_approval_requirements(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    before = setup.state_revision

    detail = get_candidate_review_detail(
        setup.workspace,
        _entry_id(candidate.candidate_id),
    )

    requirements = {
        item.requirement_id: item.requirement_kind
        for item in detail.profile_requirements
    }
    assert requirements[REFLECTION_REQUIREMENT_ID] == "reflection"
    assert requirements[APPROVAL_REQUIREMENT_ID] == "approval"
    assert detail.profile_requirement_ids == tuple(
        item.requirement_id for item in detail.profile_requirements
    )
    assert setup.state_revision == before


def test_guided_annotation_create_and_revision_preserve_history(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate, selection = _select(setup, "evidence_selected")
    target = CurationTargetRef(
        target_kind="selection",
        target_id=selection.selection_id,
    )
    before_plan = setup.state_revision
    create_plan = plan_annotation_creation(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        purpose="curator_context",
        target_scope="selection",
        target_references=(target,),
        content="Why this exact Selection is useful in the Portfolio.",
    )

    assert create_plan.confirmation_phrase == "SAVE ANNOTATION"
    assert setup.state_revision == before_plan
    created = execute_annotation_action(
        setup.workspace,
        create_plan,
        author=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    annotation = next(
        item for item in created.records if isinstance(item, CurationAnnotation)
    )
    revise_plan = plan_annotation_revision(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        annotation_id=annotation.annotation_id,
        content="Revised curator context without rewriting revision one.",
    )

    assert revise_plan.expected_annotation_revision == 1
    revised = execute_annotation_action(
        setup.workspace,
        revise_plan,
        author=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    successor = next(
        item for item in revised.records if isinstance(item, CurationAnnotation)
    )
    assert successor.annotation_id == annotation.annotation_id
    assert successor.annotation_revision == 2
    assert successor.predecessor_annotation_revision == 1
    persisted = [
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, CurationAnnotation)
        and item.annotation_id == annotation.annotation_id
    ]
    assert [item.annotation_revision for item in persisted] == [1, 2]
    detail = get_candidate_review_detail(
        setup.workspace,
        _entry_id(candidate.candidate_id),
    )
    assert not hasattr(detail.annotations[-1], "content")


def test_guided_reflection_requires_exact_requirement_and_revises_append_only(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate, selection = _select(setup, "evidence_selected")
    target = CurationTargetRef(
        target_kind="selection",
        target_id=selection.selection_id,
    )
    with pytest.raises(CandidateReviewError) as wrong_requirement:
        plan_reflection_creation(
            setup.workspace,
            entry_id=_entry_id(candidate.candidate_id),
            reflection_requirement_id=APPROVAL_REQUIREMENT_ID,
            prompt_id="growth_prompt",
            prompt_version="1",
            prompt_snapshot="What changed in this work?",
            target_scope="selection",
            target_references=(target,),
            content="Student reflection.",
        )
    assert wrong_requirement.value.code == "candidate_review.action_not_available"

    plan = plan_reflection_creation(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_prompt",
        prompt_version="1",
        prompt_snapshot="What changed in this work?",
        target_scope="selection",
        target_references=(target,),
        content="I can identify one concrete change in my work.",
    )
    created = execute_reflection_action(
        setup.workspace,
        plan,
        author=STUDENT_ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    reflection = next(
        item for item in created.records if isinstance(item, PortfolioReflection)
    )
    revision_plan = plan_reflection_revision(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        reflection_id=reflection.reflection_id,
        prompt_version="2",
        prompt_snapshot="What changed, and what evidence supports that description?",
        content="I revised the explanation and named the evidence I used.",
    )
    assert revision_plan.reflection_requirement_id == REFLECTION_REQUIREMENT_ID
    assert revision_plan.expected_reflection_revision == 1
    revised = execute_reflection_action(
        setup.workspace,
        revision_plan,
        author=STUDENT_ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    successor = next(
        item for item in revised.records if isinstance(item, PortfolioReflection)
    )
    assert successor.reflection_revision == 2
    assert successor.predecessor_reflection_revision == 1
    assert successor.prompt_version == "2"
    assert successor.reflection_requirement_id == REFLECTION_REQUIREMENT_ID


def test_comparison_reflection_requires_explicit_semantic_roles(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first_candidate, first_selection = _select(setup, "evidence_selected")
    _, second_selection = _select(setup, "evidence_approved")
    targets = (
        CurationTargetRef(
            target_kind="selection",
            target_id=first_selection.selection_id,
        ),
        CurationTargetRef(
            target_kind="selection",
            target_id=second_selection.selection_id,
        ),
    )

    with pytest.raises(CandidateReviewError) as error:
        plan_reflection_creation(
            setup.workspace,
            entry_id=_entry_id(first_candidate.candidate_id),
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="comparison_prompt",
            prompt_version="1",
            prompt_snapshot="Compare the two selected works.",
            target_scope="comparison_set",
            target_references=targets,
            content="Comparison reflection.",
        )
    assert error.value.code == "candidate_review.invalid_request"

    exact_targets = (
        CurationTargetRef(
            target_kind="selection",
            target_id=first_selection.selection_id,
            semantic_role="baseline",
        ),
        CurationTargetRef(
            target_kind="selection",
            target_id=second_selection.selection_id,
            semantic_role="later",
        ),
    )
    plan = plan_reflection_creation(
        setup.workspace,
        entry_id=_entry_id(first_candidate.candidate_id),
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="comparison_prompt",
        prompt_version="1",
        prompt_snapshot="Compare the two selected works.",
        target_scope="comparison_set",
        target_references=exact_targets,
        content="The two roles are explicit; chronology was not inferred.",
    )
    assert plan.target_references == exact_targets


def test_review_targets_exact_annotation_revision_and_does_not_carry_forward(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate, selection = _select(setup, "evidence_selected")
    selection_target = CurationTargetRef(
        target_kind="selection",
        target_id=selection.selection_id,
    )
    annotation_plan = plan_annotation_creation(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        purpose="curator_context",
        target_scope="selection",
        target_references=(selection_target,),
        content="Annotation to review.",
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
    revision_one = CurationTargetRef(
        target_kind="annotation",
        target_id=annotation.annotation_id,
        target_revision=1,
    )
    review_plan = plan_curation_review(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        target_scope="annotation",
        target_references=(revision_one,),
        decision="approved",
        reason="Approve this exact Annotation revision for curation purposes.",
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
    )
    reviewed = execute_curation_review(
        setup.workspace,
        review_plan,
        reviewed_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    review = next(
        item for item in reviewed.records if isinstance(item, CurationReviewDecision)
    )
    assert review.target_references == (revision_one,)

    revise_plan = plan_annotation_revision(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        annotation_id=annotation.annotation_id,
        content="Changed Annotation content requires a new exact review.",
    )
    execute_annotation_action(
        setup.workspace,
        revise_plan,
        author=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    detail = get_candidate_review_detail(
        setup.workspace,
        _entry_id(candidate.candidate_id),
    )
    matching = next(
        item
        for item in detail.reviews
        if item.curation_review_decision_id == review.curation_review_decision_id
    )
    assert matching.target_references[0].target_revision == 1
    assert not any(
        item.target_references[0].target_kind == "annotation"
        and item.target_references[0].target_id == annotation.annotation_id
        and item.target_references[0].target_revision == 2
        for item in detail.reviews
    )


def test_planned_curation_content_fails_closed_on_state_change_or_denied_authority(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate, selection = _select(setup, "evidence_selected")
    target = CurationTargetRef(
        target_kind="selection",
        target_id=selection.selection_id,
    )
    annotation_plan = plan_annotation_creation(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        purpose="curator_context",
        target_scope="selection",
        target_references=(target,),
        content="Denied write.",
    )
    before_denied = setup.state_revision
    with pytest.raises(CurationWorkflowError) as denied:
        execute_annotation_action(
            setup.workspace,
            annotation_plan,
            author=ACTOR,
            authority_gate=StaticCurationAuthorityGate("denied"),
        )
    assert denied.value.code == "curation.authority_denied"
    assert setup.state_revision == before_denied

    reflection_plan = plan_reflection_creation(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_prompt",
        prompt_version="1",
        prompt_snapshot="What changed?",
        target_scope="selection",
        target_references=(target,),
        content="Planned before another curation write.",
    )
    create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(target,),
        author=ACTOR,
        content="Concurrent curation mutation.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
    )
    before_execute = load_current_state(setup.workspace).state_revision
    with pytest.raises(CurationWorkflowError) as conflict:
        execute_reflection_action(
            setup.workspace,
            reflection_plan,
            author=STUDENT_ACTOR,
            authority_gate=StaticCurationAuthorityGate(),
        )
    assert conflict.value.code == "curation.state_conflict"
    assert load_current_state(setup.workspace).state_revision == before_execute
