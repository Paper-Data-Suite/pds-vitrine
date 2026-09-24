from __future__ import annotations

from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_review import (
    CandidateReviewError,
    execute_selection_replacement,
    plan_selection_replacement,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    place_selection,
    replace_selection,
    select_candidate_directly,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
)
from vitrine.storage import load_current_records, load_current_state

MAX_ONE_SECTIONS = (
    "baseline",
    "later_work",
    "feedback",
    "assessment",
    "collaborative",
)


def _select(
    setup: object,
    candidate: PortfolioCandidate,
    section_id: str,
) -> PortfolioSelection:
    result = select_candidate_directly(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(section_id,),
        expected_state_revision=load_current_state(
            getattr(setup, "workspace")
        ).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    return next(
        item for item in result.records if isinstance(item, PortfolioSelection)
    )


def _place(
    setup: object,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    result = place_selection(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=ACTOR,
        expected_state_revision=load_current_state(
            getattr(setup, "workspace")
        ).state_revision,
        expected_arrangement_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    return next(
        item for item in result.records if isinstance(item, PortfolioPlacement)
    )


def _shared_max_one_candidates(
    setup: object,
) -> tuple[str, PortfolioCandidate, PortfolioCandidate]:
    candidates = tuple(
        getattr(setup, "candidate_records_by_source").values()
    )
    for section_id in MAX_ONE_SECTIONS:
        matches = tuple(
            candidate
            for candidate in candidates
            if section_id in candidate.eligible_section_ids
        )
        if len(matches) >= 2:
            return section_id, matches[0], matches[1]
    raise AssertionError("Fixture needs two Candidates sharing one max-one section.")


def _overflow_case(
    setup: object,
) -> tuple[
    str,
    str,
    PortfolioCandidate,
    PortfolioCandidate,
    PortfolioCandidate,
]:
    candidates = tuple(
        getattr(setup, "candidate_records_by_source").values()
    )
    for target_section in MAX_ONE_SECTIONS:
        target_candidates = tuple(
            candidate
            for candidate in candidates
            if target_section in candidate.eligible_section_ids
        )
        if len(target_candidates) < 2:
            continue
        successor, blocker = target_candidates[:2]
        for predecessor in candidates:
            if predecessor.candidate_id in {
                successor.candidate_id,
                blocker.candidate_id,
            }:
                continue
            predecessor_sections = tuple(
                section_id
                for section_id in MAX_ONE_SECTIONS
                if section_id != target_section
                and section_id in predecessor.eligible_section_ids
            )
            if predecessor_sections:
                return (
                    predecessor_sections[0],
                    target_section,
                    predecessor,
                    successor,
                    blocker,
                )
    raise AssertionError(
        "Fixture needs a third Candidate to exercise unrelated replacement capacity."
    )


def test_one_for_one_replacement_preserves_max_one_capacity(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    section_id, predecessor, successor = _shared_max_one_candidates(setup)
    old_selection = _select(setup, predecessor, section_id)
    old_placement = _place(setup, old_selection, section_id)

    plan = plan_selection_replacement(
        setup.workspace,
        entry_id=f"candidate:{predecessor.candidate_id}",
        selection_id=old_selection.selection_id,
        successor_entry_id=f"candidate:{successor.candidate_id}",
        proposed_section_ids=(section_id,),
        placement_dispositions={old_placement.placement_id: section_id},
        reason="Replace with the reviewed successor while keeping the same section.",
    )

    assert plan.proposed_section_ids == (section_id,)
    assert plan.placement_dispositions[0].placement_id == old_placement.placement_id
    assert plan.placement_dispositions[0].target_section_id == section_id

    result = execute_selection_replacement(
        setup.workspace,
        plan,
        replaced_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )

    new_selection = next(
        item
        for item in result.records
        if isinstance(item, PortfolioSelection)
        and item.selection_id != old_selection.selection_id
    )
    new_placement = next(
        item
        for item in result.records
        if isinstance(item, PortfolioPlacement)
        and item.selection_id == new_selection.selection_id
    )
    assert new_placement.section_id == section_id

    curation = project_curation_state(load_current_records(setup.workspace))
    assert curation.selection_status(old_selection.selection_id) == "replaced"
    assert curation.selection_status(new_selection.selection_id) == "activated"
    assert curation.placement_status(old_placement.placement_id) == "replaced"
    assert curation.placement_status(new_placement.placement_id) == "activated"


def test_unrelated_full_target_is_rejected_by_planner_and_service(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    (
        predecessor_section,
        target_section,
        predecessor,
        successor,
        blocker,
    ) = _overflow_case(setup)
    predecessor_selection = _select(
        setup,
        predecessor,
        predecessor_section,
    )
    predecessor_placement = _place(
        setup,
        predecessor_selection,
        predecessor_section,
    )
    blocker_selection = _select(setup, blocker, target_section)
    _place(setup, blocker_selection, target_section)
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as guided_error:
        plan_selection_replacement(
            setup.workspace,
            entry_id=f"candidate:{predecessor.candidate_id}",
            selection_id=predecessor_selection.selection_id,
            successor_entry_id=f"candidate:{successor.candidate_id}",
            proposed_section_ids=(target_section,),
            placement_dispositions={
                predecessor_placement.placement_id: target_section
            },
            reason="Attempt replacement into an unrelated full target.",
        )
    assert guided_error.value.code == "candidate_review.action_not_available"
    assert load_current_state(setup.workspace).state_revision == before

    with pytest.raises(CurationWorkflowError) as service_error:
        replace_selection(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            selection_id=predecessor_selection.selection_id,
            successor_candidate_id=successor.candidate_id,
            replaced_by=ACTOR,
            placement_dispositions={
                predecessor_placement.placement_id: target_section
            },
            expected_state_revision=before,
            expected_pointer_revisions={},
            authority_gate=StaticCurationAuthorityGate(),
            reason="Attempt replacement into an unrelated full target.",
            proposed_section_ids=(target_section,),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert service_error.value.code == "curation.section_cardinality_exceeded"
    assert load_current_state(setup.workspace).state_revision == before
