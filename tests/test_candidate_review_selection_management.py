from __future__ import annotations

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
    execute_candidate_decision,
    execute_selection_placement,
    execute_selection_replacement,
    execute_selection_withdrawal,
    get_candidate_review_detail,
    plan_candidate_decision,
    plan_selection_placement,
    plan_selection_replacement,
    plan_selection_withdrawal,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
    CurationWorkflowError,
    create_annotation,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SelectionProposal,
)
from vitrine.storage import load_current_records, load_current_state


class _CurationGate:
    def __init__(self) -> None:
        self.requests: list[CurationAuthorityRequest] = []

    def authorize(
        self,
        request: CurationAuthorityRequest,
    ) -> CurationAuthorityDecision:
        self.requests.append(request)
        condition = request.candidate_condition_state
        acknowledged = (
            ()
            if condition in {None, "ready_for_consideration"}
            else (condition,)
        )
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="fixture:teacher",
            acknowledged_condition_codes=acknowledged,
        )


def _discover(
    setup: object,
    module_id: str,
    *,
    id_factory: DeterministicIds | None = None,
) -> None:
    ids = DeterministicIds() if id_factory is None else id_factory
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id=module_id,
                state="current",
                limit=20,
            ),
            expected_state_revision=load_current_state(
                getattr(setup, "workspace")
            ).state_revision,
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=ids,
    )
    assert result.findings == ()


def _candidate(setup: object, module_id: str) -> PortfolioCandidate:
    matches = tuple(
        item
        for item in load_current_records(getattr(setup, "workspace"))
        if isinstance(item, PortfolioCandidate)
        and item.source_endpoint.producer_source.producer_module_id == module_id
    )
    assert matches
    return sorted(matches, key=lambda item: item.candidate_id)[0]


def _select(setup: object, candidate: PortfolioCandidate) -> PortfolioSelection:
    entry_id = f"candidate:{candidate.candidate_id}"
    plan = plan_candidate_decision(
        getattr(setup, "workspace"),
        entry_id=entry_id,
        decision="select",
        proposed_section_ids=(candidate.eligible_section_ids[0],),
    )
    result = execute_candidate_decision(
        getattr(setup, "workspace"),
        plan,
        actor=ACTOR,
        authority_gate=_CurationGate(),
        rationale_text="Use this exact Candidate in the working Portfolio.",
    )
    selection = next(
        item for item in result.records if isinstance(item, PortfolioSelection)
    )
    return selection


def _place(
    setup: object,
    candidate: PortfolioCandidate,
    selection: PortfolioSelection,
) -> PortfolioPlacement:
    plan = plan_selection_placement(
        getattr(setup, "workspace"),
        entry_id=f"candidate:{candidate.candidate_id}",
        selection_id=selection.selection_id,
        section_id=candidate.eligible_section_ids[0],
    )
    result = execute_selection_placement(
        getattr(setup, "workspace"),
        plan,
        placed_by=ACTOR,
        authority_gate=_CurationGate(),
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def test_guided_select_executes_exact_plan_without_implicit_placement(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    before = load_current_state(setup.workspace).state_revision
    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        decision="select",
        proposed_section_ids=(candidate.eligible_section_ids[0],),
    )

    result = execute_candidate_decision(
        setup.workspace,
        plan,
        actor=ACTOR,
        authority_gate=_CurationGate(),
        rationale_text="Selected after exact review.",
    )

    assert result.state_revision == before + 1
    assert any(isinstance(item, PortfolioSelection) for item in result.records)
    assert not any(isinstance(item, PortfolioPlacement) for item in result.records)
    proposal = next(item for item in result.records if isinstance(item, SelectionProposal))
    assert proposal.proposed_section_ids == (candidate.eligible_section_ids[0],)


def test_guided_decline_executes_plan_without_selection(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        decision="decline",
        proposed_section_ids=(candidate.eligible_section_ids[0],),
    )

    result = execute_candidate_decision(
        setup.workspace,
        plan,
        actor=ACTOR,
        authority_gate=_CurationGate(),
        rationale_text="Decline this proposed Portfolio use.",
    )

    assert any(isinstance(item, SelectionProposal) for item in result.records)
    assert not any(isinstance(item, PortfolioSelection) for item in result.records)
    assert not any(isinstance(item, PortfolioPlacement) for item in result.records)


def test_explicit_placement_uses_observed_pointer_and_blocks_duplicate_plan(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    selection = _select(setup, candidate)
    section_id = candidate.eligible_section_ids[0]
    before = load_current_state(setup.workspace).state_revision
    plan = plan_selection_placement(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        selection_id=selection.selection_id,
        section_id=section_id,
    )

    assert plan.confirmation_phrase == "PLACE SELECTION"
    assert plan.expected_arrangement_pointer_revision is None
    result = execute_selection_placement(
        setup.workspace,
        plan,
        placed_by=ACTOR,
        authority_gate=_CurationGate(),
    )
    assert result.state_revision == before + 1
    assert any(isinstance(item, PortfolioPlacement) for item in result.records)

    with pytest.raises(CandidateReviewError) as error:
        plan_selection_placement(
            setup.workspace,
            entry_id=f"candidate:{candidate.candidate_id}",
            selection_id=selection.selection_id,
            section_id=section_id,
        )
    assert error.value.code == "candidate_review.action_not_available"


def test_placement_execution_fails_closed_after_review_state_changes(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    selection = _select(setup, candidate)
    plan = plan_selection_placement(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        selection_id=selection.selection_id,
        section_id=candidate.eligible_section_ids[0],
    )
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
        content="Concurrent curation change.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=_CurationGate(),
    )
    before_execute = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError) as error:
        execute_selection_placement(
            setup.workspace,
            plan,
            placed_by=ACTOR,
            authority_gate=_CurationGate(),
        )

    assert error.value.code == "curation.state_conflict"
    assert load_current_state(setup.workspace).state_revision == before_execute


def test_guided_withdrawal_preserves_selection_and_placement_history(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    selection = _select(setup, candidate)
    placement = _place(setup, candidate, selection)
    plan = plan_selection_withdrawal(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        selection_id=selection.selection_id,
        reason="Remove this Selection from the active Portfolio.",
    )

    assert plan.active_placement_ids == (placement.placement_id,)
    assert plan.confirmation_phrase == "WITHDRAW SELECTION"
    assert len(plan.arrangement_pointers) == 1
    assert plan.arrangement_pointers[0].pointer_revision == 1
    execute_selection_withdrawal(
        setup.workspace,
        plan,
        withdrawn_by=ACTOR,
        authority_gate=_CurationGate(),
    )

    detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{candidate.candidate_id}",
    )
    selected = next(item for item in detail.selections if item.selection_id == selection.selection_id)
    historical_placement = next(
        item for item in detail.placements if item.placement_id == placement.placement_id
    )
    assert selected.lifecycle_state == "withdrawn"
    assert historical_placement.lifecycle_state == "withdrawn"
    records = load_current_records(setup.workspace)
    assert any(
        isinstance(item, PortfolioSelection)
        and item.selection_id == selection.selection_id
        for item in records
    )
    assert any(
        isinstance(item, PortfolioPlacement)
        and item.placement_id == placement.placement_id
        for item in records
    )


def test_replacement_requires_every_placement_disposition_and_exact_successor(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    ids = DeterministicIds()
    _discover(setup, "vitrine_scoreform_fixture", id_factory=ids)
    _discover(setup, "vitrine_quillan_fixture", id_factory=ids)
    current = _candidate(setup, "vitrine_scoreform_fixture")
    successor = _candidate(setup, "vitrine_quillan_fixture")
    selection = _select(setup, current)
    placement = _place(setup, current, selection)
    successor_section = successor.eligible_section_ids[0]

    with pytest.raises(CandidateReviewError) as error:
        plan_selection_replacement(
            setup.workspace,
            entry_id=f"candidate:{current.candidate_id}",
            selection_id=selection.selection_id,
            successor_entry_id=f"candidate:{successor.candidate_id}",
            proposed_section_ids=(successor_section,),
            placement_dispositions={},
            reason="Use the successor Candidate instead.",
        )
    assert error.value.code == "candidate_review.invalid_request"

    with pytest.raises(CandidateReviewError) as self_error:
        plan_selection_replacement(
            setup.workspace,
            entry_id=f"candidate:{current.candidate_id}",
            selection_id=selection.selection_id,
            successor_entry_id=f"candidate:{current.candidate_id}",
            proposed_section_ids=(current.eligible_section_ids[0],),
            placement_dispositions={placement.placement_id: None},
            reason="Invalid self replacement.",
        )
    assert self_error.value.code == "candidate_review.action_not_available"


def test_explicit_replacement_migrates_placement_and_preserves_old_history(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    ids = DeterministicIds()
    _discover(setup, "vitrine_scoreform_fixture", id_factory=ids)
    _discover(setup, "vitrine_quillan_fixture", id_factory=ids)
    current = _candidate(setup, "vitrine_scoreform_fixture")
    successor = _candidate(setup, "vitrine_quillan_fixture")
    selection = _select(setup, current)
    placement = _place(setup, current, selection)
    target_section = successor.eligible_section_ids[0]
    plan = plan_selection_replacement(
        setup.workspace,
        entry_id=f"candidate:{current.candidate_id}",
        selection_id=selection.selection_id,
        successor_entry_id=f"candidate:{successor.candidate_id}",
        proposed_section_ids=(target_section,),
        placement_dispositions={placement.placement_id: target_section},
        reason="Replace with the explicitly reviewed successor Candidate.",
    )

    assert plan.confirmation_phrase == "REPLACE SELECTION"
    assert plan.proposed_section_ids == (target_section,)
    assert plan.placement_dispositions[0].placement_id == placement.placement_id
    assert plan.placement_dispositions[0].target_section_id == target_section
    result = execute_selection_replacement(
        setup.workspace,
        plan,
        replaced_by=ACTOR,
        authority_gate=_CurationGate(),
    )

    proposal = next(item for item in result.records if isinstance(item, SelectionProposal))
    new_selection = next(
        item
        for item in result.records
        if isinstance(item, PortfolioSelection)
        and item.selection_id != selection.selection_id
    )
    assert proposal.candidate_id == successor.candidate_id
    assert proposal.proposed_section_ids == (target_section,)
    assert new_selection.candidate_id == successor.candidate_id
    old_detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{current.candidate_id}",
    )
    successor_detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{successor.candidate_id}",
    )
    old_summary = next(
        item for item in old_detail.selections if item.selection_id == selection.selection_id
    )
    successor_summary = next(
        item
        for item in successor_detail.selections
        if item.selection_id == new_selection.selection_id
    )
    assert old_summary.lifecycle_state == "replaced"
    assert successor_summary.lifecycle_state == "activated"
    assert any(
        item.selection_id == new_selection.selection_id
        and item.section_id == target_section
        and item.lifecycle_state == "activated"
        for item in successor_detail.placements
    )
