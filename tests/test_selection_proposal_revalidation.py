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
    plan_candidate_decision,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    decide_selection_proposal,
    place_selection,
    propose_candidate_selection,
    select_candidate_directly,
)
from vitrine.models import (
    PortfolioSelection,
    SelectionDecision,
    SelectionProposal,
)
from vitrine.storage import load_current_records, load_current_state


def _baseline_candidates(setup: object) -> tuple[object, object]:
    candidates = tuple(
        sorted(
            (
                item
                for item in getattr(setup, "candidate_records_by_source").values()
                if "baseline" in item.eligible_section_ids
            ),
            key=lambda item: item.candidate_id,
        )
    )
    assert len(candidates) >= 2
    return candidates[0], candidates[1]


def _proposal_then_fill_baseline(setup: object) -> tuple[object, SelectionProposal]:
    candidate, occupying_candidate = _baseline_candidates(setup)
    proposed = propose_candidate_selection(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        candidate_id=candidate.candidate_id,
        proposer=ACTOR,
        proposal_origin="teacher",
        proposed_section_ids=("baseline",),
        expected_state_revision=getattr(setup, "state_revision"),
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    proposal = next(
        item for item in proposed.records if isinstance(item, SelectionProposal)
    )
    selected = select_candidate_directly(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        candidate_id=occupying_candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=getattr(setup, "state_revision"),
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    selection = next(
        item for item in selected.records if isinstance(item, PortfolioSelection)
    )
    place_selection(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        selection_id=selection.selection_id,
        section_id="baseline",
        placed_by=ACTOR,
        expected_state_revision=getattr(setup, "state_revision"),
        expected_arrangement_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    return candidate, proposal


def test_guided_proposal_acceptance_revalidates_but_decline_remains_available(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate, proposal = _proposal_then_fill_baseline(setup)
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=f"candidate:{candidate.candidate_id}",
            decision="select",
            selection_proposal_id=proposal.selection_proposal_id,
        )

    assert error.value.code == "candidate_review.action_not_available"
    assert load_current_state(setup.workspace).state_revision == before

    decline = plan_candidate_decision(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        decision="decline",
        selection_proposal_id=proposal.selection_proposal_id,
    )

    assert decline.operation == "decide_selection"
    assert decline.selection_proposal_id == proposal.selection_proposal_id
    assert decline.proposed_section_ids == proposal.proposed_section_ids
    assert load_current_state(setup.workspace).state_revision == before


def test_canonical_acceptance_fails_closed_without_rewriting_historical_proposal(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate, proposal = _proposal_then_fill_baseline(setup)
    before_records = load_current_records(setup.workspace)
    preserved = next(
        item
        for item in before_records
        if isinstance(item, SelectionProposal)
        and item.selection_proposal_id == proposal.selection_proposal_id
    )
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError) as error:
        decide_selection_proposal(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            selection_proposal_id=proposal.selection_proposal_id,
            decision="accepted",
            decided_by=ACTOR,
            expected_state_revision=before,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )

    assert error.value.code == "curation.section_cardinality_exceeded"
    assert load_current_state(setup.workspace).state_revision == before
    after_failed_accept = load_current_records(setup.workspace)
    assert next(
        item
        for item in after_failed_accept
        if isinstance(item, SelectionProposal)
        and item.selection_proposal_id == proposal.selection_proposal_id
    ) == preserved
    assert not any(
        isinstance(item, SelectionDecision)
        and item.selection_proposal_id == proposal.selection_proposal_id
        for item in after_failed_accept
    )
    assert not any(
        isinstance(item, PortfolioSelection)
        and item.candidate_id == candidate.candidate_id
        for item in after_failed_accept
    )

    rejected = decide_selection_proposal(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="rejected",
        decided_by=ACTOR,
        expected_state_revision=before,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    decision = next(
        item for item in rejected.records if isinstance(item, SelectionDecision)
    )

    assert decision.selection_proposal_id == proposal.selection_proposal_id
    assert decision.decision == "rejected"
    final_records = load_current_records(setup.workspace)
    assert next(
        item
        for item in final_records
        if isinstance(item, SelectionProposal)
        and item.selection_proposal_id == proposal.selection_proposal_id
    ) == preserved
    assert not any(
        isinstance(item, PortfolioSelection)
        and item.candidate_id == candidate.candidate_id
        for item in final_records
    )
