from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_review import (
    CandidateReviewError,
    get_candidate_review_detail,
    plan_candidate_decision,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
    CurationWorkflowError,
    decide_selection_proposal,
    propose_candidate_selection,
    reject_candidate_directly,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    CandidateEvaluation,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SelectionDecision,
    SelectionProposal,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)


class _RecordingCurationGate:
    def __init__(self, outcome: str = "allowed") -> None:
        self.outcome = outcome
        self.requests: list[CurationAuthorityRequest] = []

    def authorize(
        self,
        request: CurationAuthorityRequest,
    ) -> CurationAuthorityDecision:
        self.requests.append(request)
        if self.outcome == "allowed":
            return CurationAuthorityDecision(
                outcome="allowed",
                authority_reference="fixture:teacher",
            )
        return CurationAuthorityDecision(outcome=self.outcome)


def _discover(setup: object) -> None:
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="vitrine_scoreform_fixture",
                state="current",
                limit=20,
            ),
            expected_state_revision=getattr(setup, "state_revision"),
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.findings == ()


def _candidate_and_evaluation(
    setup: object,
) -> tuple[PortfolioCandidate, CandidateEvaluation]:
    records = load_current_records(getattr(setup, "workspace"))
    candidate = next(item for item in records if isinstance(item, PortfolioCandidate))
    evaluation = next(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == candidate.candidate_evaluation_id
    )
    return candidate, evaluation


def test_fresh_decline_is_one_atomic_proposal_rejection_batch(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, evaluation = _candidate_and_evaluation(setup)
    section_id = candidate.eligible_section_ids[0]
    requirement_id = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{candidate.candidate_id}",
    ).sections[0].relevant_profile_requirement_ids[0]
    before = load_current_state(setup.workspace).state_revision
    gate = _RecordingCurationGate()

    result = reject_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        rejected_by=ACTOR,
        proposed_section_ids=(section_id,),
        intended_profile_requirement_ids=(requirement_id,),
        rationale_text="Not for this proposed Portfolio use.",
        expected_state_revision=before,
        authority_gate=gate,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )

    assert result.state_revision == before + 1
    proposals = tuple(item for item in result.records if isinstance(item, SelectionProposal))
    decisions = tuple(item for item in result.records if isinstance(item, SelectionDecision))
    assert len(proposals) == 1
    assert len(decisions) == 1
    assert proposals[0].proposal_origin == "teacher"
    assert proposals[0].candidate_evaluation_id == candidate.candidate_evaluation_id
    assert proposals[0].proposed_section_ids == (section_id,)
    assert proposals[0].intended_profile_requirement_ids == (requirement_id,)
    assert decisions[0].selection_proposal_id == proposals[0].selection_proposal_id
    assert decisions[0].decision == "rejected"
    assert decisions[0].resulting_selection_id is None
    assert gate.requests[-1].operation == "direct_decline"

    records = load_current_records(setup.workspace)
    assert not any(isinstance(item, PortfolioSelection) for item in records)
    assert not any(isinstance(item, PortfolioPlacement) for item in records)
    preserved_candidate = next(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
        and item.candidate_id == candidate.candidate_id
    )
    preserved_evaluation = next(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == evaluation.candidate_evaluation_id
    )
    assert preserved_candidate == candidate
    assert preserved_evaluation == evaluation


def test_fresh_decline_denied_authority_writes_nothing(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, _evaluation = _candidate_and_evaluation(setup)
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError) as error:
        reject_candidate_directly(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            candidate_id=candidate.candidate_id,
            rejected_by=ACTOR,
            proposed_section_ids=(candidate.eligible_section_ids[0],),
            expected_state_revision=before,
            authority_gate=_RecordingCurationGate("denied"),
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )

    assert error.value.code == "curation.authority_denied"
    assert load_current_state(setup.workspace).state_revision == before
    records = load_current_records(setup.workspace)
    assert not any(isinstance(item, SelectionProposal) for item in records)
    assert not any(isinstance(item, SelectionDecision) for item in records)


def test_fresh_decline_refuses_to_duplicate_undecided_proposal(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, _evaluation = _candidate_and_evaluation(setup)
    section_id = candidate.eligible_section_ids[0]
    proposed = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=ACTOR,
        proposal_origin="teacher",
        proposed_section_ids=(section_id,),
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=_RecordingCurationGate(),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    proposal = next(item for item in proposed.records if isinstance(item, SelectionProposal))
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError) as error:
        reject_candidate_directly(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            candidate_id=candidate.candidate_id,
            rejected_by=ACTOR,
            proposed_section_ids=(section_id,),
            expected_state_revision=before,
            authority_gate=_RecordingCurationGate(),
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )

    assert error.value.code == "curation.invalid_request"
    assert load_current_state(setup.workspace).state_revision == before
    assert sum(
        isinstance(item, SelectionProposal)
        for item in load_current_records(setup.workspace)
    ) == 1

    decided = decide_selection_proposal(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="rejected",
        decided_by=ACTOR,
        expected_state_revision=before,
        authority_gate=_RecordingCurationGate(),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    decision = next(item for item in decided.records if isinstance(item, SelectionDecision))
    assert decision.selection_proposal_id == proposal.selection_proposal_id
    assert decision.decision == "rejected"


def test_action_plan_requires_explicit_fresh_section_intent_and_is_read_only(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, _evaluation = _candidate_and_evaluation(setup)
    entry_id = f"candidate:{candidate.candidate_id}"
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=entry_id,
            decision="select",
        )
    assert error.value.code == "candidate_review.invalid_request"
    assert load_current_state(setup.workspace).state_revision == before

    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=entry_id,
        decision="decline",
        proposed_section_ids=(candidate.eligible_section_ids[0],),
    )

    assert plan.operation == "direct_decline"
    assert plan.confirmation_phrase == "DECLINE CANDIDATE"
    assert plan.observed_state_revision == before
    assert plan.candidate_id == candidate.candidate_id
    assert plan.current_review_evaluation_id == candidate.candidate_evaluation_id
    assert plan.curation_provenance_evaluation_id == candidate.candidate_evaluation_id
    assert plan.selection_proposal_id is None
    assert load_current_state(setup.workspace).state_revision == before


def test_action_plan_requires_exact_existing_proposal_identity(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, _evaluation = _candidate_and_evaluation(setup)
    entry_id = f"candidate:{candidate.candidate_id}"
    section_id = candidate.eligible_section_ids[0]
    proposed = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=ACTOR,
        proposal_origin="teacher",
        proposed_section_ids=(section_id,),
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=_RecordingCurationGate(),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    proposal = next(item for item in proposed.records if isinstance(item, SelectionProposal))
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=entry_id,
            decision="decline",
            proposed_section_ids=(section_id,),
        )
    assert error.value.code == "candidate_review.action_not_available"

    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=entry_id,
        decision="decline",
        selection_proposal_id=proposal.selection_proposal_id,
    )
    assert plan.operation == "decide_selection"
    assert plan.selection_proposal_id == proposal.selection_proposal_id
    assert plan.proposed_section_ids == proposal.proposed_section_ids
    assert load_current_state(setup.workspace).state_revision == before


def test_action_plan_rejects_evaluation_only_entry_as_not_selectable(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    _candidate, evaluation = _candidate_and_evaluation(setup)
    negative = replace(
        evaluation,
        candidate_evaluation_id="candidate_evaluation_action_ineligible",
        predecessor_evaluation_id=None,
        eligible_section_ids=(),
        outcome="ineligible",
        reason_codes=("fixture_not_eligible",),
        evaluated_at=evaluation.evaluated_at + timedelta(seconds=60),
    )
    before_negative = load_current_state(setup.workspace).state_revision
    commit_record_batch(
        setup.workspace,
        (negative,),
        expected_state_revision=before_negative,
    )
    before_plan = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=f"evaluation:{negative.candidate_evaluation_id}",
            decision="decline",
            proposed_section_ids=("student_work",),
        )

    assert error.value.code == "candidate_review.not_selectable"
    assert load_current_state(setup.workspace).state_revision == before_plan
