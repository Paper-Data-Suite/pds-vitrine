from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import pytest

import vitrine.working_composition as working_composition
from scripts.curation_fixture_support import (
    ACTOR,
    APPROVAL_REQUIREMENT_ID,
    CurationFixtureWorkspace,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine import cli
from vitrine.candidate_review import (
    execute_candidate_decision,
    execute_selection_placement,
    plan_candidate_decision,
    plan_selection_placement,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    WorkingCompositionSourceCurrentness,
    create_annotation,
    reorder_section,
    review_curation_target,
    revise_annotation,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CurationAnnotation,
    CurationReviewDecision,
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
    WorkingPortfolioCompositionRevision,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.workflow_context import default_workflow_dependencies
from vitrine.workflow_views import show_composition
from vitrine.working_composition import (
    WorkingCompositionError,
    freeze_prepared_working_composition,
    prepare_working_composition,
)


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


def _guided_select(
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


def _guided_place(
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


def _guided_select_and_place(
    setup: CurationFixtureWorkspace,
    candidate: PortfolioCandidate,
    section_id: str,
) -> tuple[PortfolioSelection, PortfolioPlacement]:
    selection = _guided_select(setup, candidate, section_id)
    return selection, _guided_place(setup, candidate, selection, section_id)


def _composition_records(
    setup: CurationFixtureWorkspace,
) -> tuple[
    tuple[WorkingPortfolioCompositionRevision, ...],
    tuple[WorkingPortfolioCompositionInventory, ...],
    tuple[WorkingPortfolioCompositionPointerRevision, ...],
]:
    records = load_current_records(setup.workspace)
    compositions = tuple(
        item for item in records if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    inventories = tuple(
        item for item in records if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    pointers = tuple(
        item
        for item in records
        if isinstance(item, WorkingPortfolioCompositionPointerRevision)
    )
    return compositions, inventories, pointers


def test_acceptance_guided_candidate_flow_freezes_append_preserving_composition_history(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline_candidate = _candidate_for_section(setup, "baseline")
    later_candidate = _candidate_for_section(
        setup,
        "later_work",
        excluding={baseline_candidate.candidate_id},
    )
    baseline, baseline_placement = _guided_select_and_place(
        setup, baseline_candidate, "baseline"
    )
    later, later_placement = _guided_select_and_place(
        setup, later_candidate, "later_work"
    )

    first_preparation = prepare_working_composition(
        setup.workspace,
        setup.portfolio_id,
        composition_note="First exact frozen curation state.",
    )
    first_result = freeze_prepared_working_composition(
        setup.workspace,
        first_preparation,
        created_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    first_composition = next(
        item
        for item in first_result.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    first_inventory = next(
        item
        for item in first_result.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    assert first_composition.selection_ids == (
        baseline.selection_id,
        later.selection_id,
    )
    assert first_composition.placement_ids == (
        baseline_placement.placement_id,
        later_placement.placement_id,
    )

    create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=baseline.selection_id,
            ),
        ),
        author=ACTOR,
        content="Successor-only curation context.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    second_preparation = prepare_working_composition(
        setup.workspace,
        setup.portfolio_id,
        composition_note="Second exact frozen curation state.",
    )
    assert second_preparation.disposition == "create_successor"
    assert second_preparation.predecessor_composition_revision == 1

    second_result = freeze_prepared_working_composition(
        setup.workspace,
        second_preparation,
        created_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    second_composition = next(
        item
        for item in second_result.records
        if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    assert second_composition.composition_revision == 2
    assert second_composition.predecessor_composition_revision == 1

    compositions, inventories, pointers = _composition_records(setup)
    assert len(compositions) == 2
    assert len(inventories) == 2
    assert len(pointers) == 2
    assert first_composition in compositions
    assert first_inventory in inventories

    historical = show_composition(setup.workspace, setup.portfolio_id, revision=1)
    current = show_composition(setup.workspace, setup.portfolio_id)
    assert historical.composition == first_composition
    assert historical.inventory == first_inventory
    assert current.composition is not None
    assert current.composition.composition_revision == 2
    assert current.pointer_revision == 2


def test_acceptance_cli_prepare_preserves_arrangement_order_and_unplaced_selection(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first_candidate, second_candidate = _two_candidates_for_section(setup, "gallery")
    first, first_placement = _guided_select_and_place(
        setup, first_candidate, "gallery"
    )
    second, second_placement = _guided_select_and_place(
        setup, second_candidate, "gallery"
    )
    assessment_candidate = _candidate_for_section(
        setup,
        "assessment",
        excluding={first_candidate.candidate_id, second_candidate.candidate_id},
    )
    unplaced = _guided_select(setup, assessment_candidate, "assessment")

    state = project_curation_state(load_current_records(setup.workspace))
    pointer = state.arrangement_pointer_heads(
        setup.portfolio_id,
        setup.profile_binding_id,
        "gallery",
    )[0]
    reorder_section(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        section_id="gallery",
        placement_ids=(
            second_placement.placement_id,
            first_placement.placement_id,
        ),
        arranged_by=ACTOR,
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        expected_arrangement_pointer_revision=pointer.pointer_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    output = io.StringIO()
    assert (
        cli.main(
            [
                "composition",
                "prepare",
                setup.portfolio_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            output=output,
            error=io.StringIO(),
        )
        == 0
    )

    text = output.getvalue()
    placement_summary = (
        f"Placement IDs: {second_placement.placement_id}, "
        f"{first_placement.placement_id}"
    )
    assert placement_summary in text
    assert (
        f"Unplaced active Selections: {unplaced.selection_id}"
        in text
    )
    assert first.selection_id in text
    assert second.selection_id in text


def test_acceptance_unresolved_requirements_and_audience_constraints_freeze_without_context(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert preparation.payload.coherence_state == (
        "coherent_with_unresolved_obligations"
    )
    assert "section_minimum_missing" in preparation.payload.unresolved_obligation_codes
    assert "reflection_required" in preparation.payload.unresolved_obligation_codes
    assert len(preparation.audience_rules) == 1
    audience = preparation.audience_rules[0]
    assert audience.audience_rule_id == "student_internal"
    assert audience.prohibited_content_classes == ("private_teacher_note",)
    assert audience.required_review_classes == ("privacy_review",)

    result = freeze_prepared_working_composition(
        setup.workspace,
        preparation,
        created_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    inventory = next(
        item
        for item in result.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    assert inventory.coherence_state == "coherent_with_unresolved_obligations"
    assert inventory.unresolved_obligation_codes == (
        preparation.payload.unresolved_obligation_codes
    )
    assert not any(
        item.record_type == "audience_context"
        for item in load_current_records(setup.workspace)
    )


def test_acceptance_review_of_old_annotation_revision_does_not_follow_successor(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "gallery")
    selection = _guided_select(setup, candidate, "gallery")
    created = create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selection.selection_id,
            ),
        ),
        author=ACTOR,
        content="Annotation revision one.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    annotation = next(
        item for item in created.records if isinstance(item, CurationAnnotation)
    )
    reviewed = review_curation_target(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        target_scope="annotation",
        target_references=(
            CurationTargetRef(
                target_kind="annotation",
                target_id=annotation.annotation_id,
                target_revision=annotation.annotation_revision,
            ),
        ),
        decision="approved",
        reviewed_by=ACTOR,
        reason="Approve only this exact annotation revision.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    review = next(
        item
        for item in reviewed.records
        if isinstance(item, CurationReviewDecision)
    )
    before_revision = prepare_working_composition(setup.workspace, setup.portfolio_id)
    assert review.curation_review_decision_id in (
        before_revision.payload.applicable_review_decision_ids
    )

    revised = revise_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        annotation_id=annotation.annotation_id,
        expected_annotation_revision=annotation.annotation_revision,
        author=ACTOR,
        content="Annotation revision two.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
    )
    revised_annotation = next(
        item for item in revised.records if isinstance(item, CurationAnnotation)
    )
    assert revised_annotation.annotation_revision == 2

    after_revision = prepare_working_composition(setup.workspace, setup.portfolio_id)

    assert review.curation_review_decision_id not in (
        after_revision.payload.applicable_review_decision_ids
    )
    assert all(
        item.curation_review_decision_id != review.curation_review_decision_id
        for item in after_revision.reviews
    )
    assert any(
        item.record_kind == "annotation"
        and item.record_id == annotation.annotation_id
        and item.revision == 2
        for item in after_revision.payload.included_curation_revisions
    )


def test_acceptance_core_source_drift_fails_closed_before_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "gallery")
    _guided_select(setup, candidate, "gallery")
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
        working_composition,
        "observe_working_composition_source",
        changed_source,
    )
    before_state = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)
    gate = StaticCurationAuthorityGate()

    with pytest.raises(WorkingCompositionError) as error:
        freeze_prepared_working_composition(
            setup.workspace,
            preparation,
            created_by=ACTOR,
            authority_gate=gate,
        )

    assert error.value.code == "working_composition.source_state_changed"
    assert gate.requests == []
    assert load_current_state(setup.workspace).state_revision == before_state
    assert load_current_records(setup.workspace) == before_records


@pytest.mark.parametrize(
    ("outcome", "expected_code"),
    (
        ("denied", "curation.authority_denied"),
        ("unresolved", "curation.authority_unresolved"),
    ),
)
def test_acceptance_composition_authority_failure_writes_nothing(
    tmp_path: Path,
    outcome: str,
    expected_code: str,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    before_state = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)
    gate = StaticCurationAuthorityGate(outcome)

    with pytest.raises(CurationWorkflowError) as error:
        freeze_prepared_working_composition(
            setup.workspace,
            preparation,
            created_by=ACTOR,
            authority_gate=gate,
        )

    assert error.value.code == expected_code
    assert len(gate.requests) == 1
    assert gate.requests[0].operation == "compose_portfolio"
    assert load_current_state(setup.workspace).state_revision == before_state
    assert load_current_records(setup.workspace) == before_records


def test_acceptance_exact_semantic_replay_reuses_without_new_history(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "gallery")
    _guided_select_and_place(setup, candidate, "gallery")
    first = prepare_working_composition(setup.workspace, setup.portfolio_id)
    created = freeze_prepared_working_composition(
        setup.workspace,
        first,
        created_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )
    assert created.disposition == "created"

    replay = prepare_working_composition(setup.workspace, setup.portfolio_id)
    assert replay.disposition == "reuse_exact_current"
    before_state = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)
    gate = StaticCurationAuthorityGate()

    result = freeze_prepared_working_composition(
        setup.workspace,
        replay,
        created_by=ACTOR,
        authority_gate=gate,
    )

    assert result.disposition == "existing"
    assert load_current_state(setup.workspace).state_revision == before_state
    assert load_current_records(setup.workspace) == before_records
    compositions, inventories, pointers = _composition_records(setup)
    assert len(compositions) == 1
    assert len(inventories) == 1
    assert len(pointers) == 1


def test_acceptance_cli_prepared_freeze_rejects_stale_vitrine_state_without_authority(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate_for_section(setup, "gallery")
    selection = _guided_select(setup, candidate, "gallery")
    preparation = prepare_working_composition(setup.workspace, setup.portfolio_id)
    create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selection.selection_id,
            ),
        ),
        author=ACTOR,
        content="Advance state after direct CLI preparation.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    before_state = load_current_state(setup.workspace).state_revision
    before_records = load_current_records(setup.workspace)
    gate = StaticCurationAuthorityGate()
    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=gate,
        development_fixture_mode=True,
    )
    error = io.StringIO()

    assert (
        cli.main(
            [
                "composition",
                "freeze",
                setup.portfolio_id,
                "--preparation-fingerprint",
                preparation.preparation_fingerprint,
                "--expected-state-revision",
                str(preparation.observed_state_revision),
                "--expected-composition-pointer-revision",
                "none",
                "--actor-id",
                ACTOR.actor_id,
                "--workspace-root",
                str(setup.workspace),
            ],
            dependencies=dependencies,
            output=io.StringIO(),
            error=error,
        )
        == 1
    )

    assert error.getvalue().startswith("working_composition.state_changed:")
    assert gate.requests == []
    assert load_current_state(setup.workspace).state_revision == before_state
    assert load_current_records(setup.workspace) == before_records
