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
    plan_selection_placement,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    place_selection,
    select_candidate_directly,
)
from vitrine.models import PortfolioCandidate, PortfolioSelection
from vitrine.storage import load_current_state


def _shared_max_one_candidates(
    setup: object,
) -> tuple[str, PortfolioCandidate, PortfolioCandidate]:
    candidates = tuple(
        getattr(setup, "candidate_records_by_source").values()
    )
    for section_id in (
        "baseline",
        "later_work",
        "feedback",
        "assessment",
        "collaborative",
    ):
        matches = tuple(
            candidate
            for candidate in candidates
            if section_id in candidate.eligible_section_ids
        )
        if len(matches) >= 2:
            return section_id, matches[0], matches[1]
    raise AssertionError("Fixture needs two Candidates sharing one max-one section.")


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
) -> None:
    place_selection(
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


def test_full_section_is_rejected_by_guided_and_canonical_placement(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    section_id, first, second = _shared_max_one_candidates(setup)
    first_selection = _select(setup, first, section_id)
    second_selection = _select(setup, second, section_id)
    _place(setup, first_selection, section_id)
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as guided_error:
        plan_selection_placement(
            setup.workspace,
            entry_id=f"candidate:{second.candidate_id}",
            selection_id=second_selection.selection_id,
            section_id=section_id,
        )
    assert guided_error.value.code == "candidate_review.action_not_available"
    assert load_current_state(setup.workspace).state_revision == before

    with pytest.raises(CurationWorkflowError) as service_error:
        place_selection(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            selection_id=second_selection.selection_id,
            section_id=section_id,
            placed_by=ACTOR,
            expected_state_revision=before,
            expected_arrangement_pointer_revision=None,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert service_error.value.code == "curation.section_cardinality_exceeded"
    assert load_current_state(setup.workspace).state_revision == before


def test_duplicate_placement_keeps_specific_canonical_error_priority(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    section_id, candidate, _other = _shared_max_one_candidates(setup)
    selection = _select(setup, candidate, section_id)
    _place(setup, selection, section_id)
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError) as error:
        place_selection(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            selection_id=selection.selection_id,
            section_id=section_id,
            placed_by=ACTOR,
            expected_state_revision=before,
            expected_arrangement_pointer_revision=None,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )

    assert error.value.code == "curation.placement_duplicate_active"
    assert load_current_state(setup.workspace).state_revision == before
