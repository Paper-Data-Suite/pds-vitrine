from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery

import vitrine.candidate_review as candidate_review
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
from vitrine.curation_state import project_curation_state
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import PortfolioCandidate, SectionArrangementPointerRevision
from vitrine.storage import load_current_records, load_current_state


def _discover(setup: object, module_id: str) -> None:
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
        id_factory=DeterministicIds(),
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


@pytest.mark.parametrize("decision", ["select", "decline"])
def test_fresh_decision_rejects_semantic_section_blocked_by_current_actionability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    section_id = candidate.eligible_section_ids[0]
    records = load_current_records(setup.workspace)
    pointers = (
        SectionArrangementPointerRevision(
            arrangement_pointer_id="issue97_pointer_a",
            pointer_revision=1,
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
            section_id=section_id,
            arrangement_id="issue97_arrangement_a",
            pointed_at=fixed_clock(),
            pointed_by=ACTOR,
            authority_reference="issue97_test",
        ),
        SectionArrangementPointerRevision(
            arrangement_pointer_id="issue97_pointer_b",
            pointer_revision=1,
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
            section_id=section_id,
            arrangement_id="issue97_arrangement_b",
            pointed_at=fixed_clock(),
            pointed_by=ACTOR,
            authority_reference="issue97_test",
        ),
    )
    conflicted = project_curation_state((*records, *pointers))
    monkeypatch.setattr(
        candidate_review,
        "_load_curation_state",
        lambda _workspace_root, _expected_state_revision: conflicted,
    )
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=f"candidate:{candidate.candidate_id}",
            decision=decision,
            proposed_section_ids=(section_id,),
        )

    assert error.value.code == "candidate_review.action_not_available"
    assert candidate.eligible_section_ids == (section_id,)
    assert load_current_state(setup.workspace).state_revision == before


def test_fresh_decision_scopes_requirement_intent_to_exact_selected_sections(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    entry_id = f"candidate:{candidate.candidate_id}"
    detail = get_candidate_review_detail(setup.workspace, entry_id)
    section_id = candidate.eligible_section_ids[0]
    section = next(item for item in detail.sections if item.section_id == section_id)
    matched = set(candidate.eligible_profile_rule_ids)
    applicable_requirement_id = next(
        requirement_id
        for requirement_id in section.relevant_profile_requirement_ids
        if requirement_id in matched
    )
    unrelated_requirement_id = next(
        requirement_id
        for requirement_id in detail.profile_requirement_ids
        if requirement_id != applicable_requirement_id
    )
    before = load_current_state(setup.workspace).state_revision

    valid = plan_candidate_decision(
        setup.workspace,
        entry_id=entry_id,
        decision="select",
        proposed_section_ids=(section_id,),
        intended_profile_requirement_ids=(applicable_requirement_id,),
    )
    assert valid.proposed_section_ids == (section_id,)
    assert valid.intended_profile_requirement_ids == (applicable_requirement_id,)

    with pytest.raises(CandidateReviewError) as error:
        plan_candidate_decision(
            setup.workspace,
            entry_id=entry_id,
            decision="select",
            proposed_section_ids=(section_id,),
            intended_profile_requirement_ids=(unrelated_requirement_id,),
        )

    assert error.value.code == "candidate_review.action_not_available"
    assert load_current_state(setup.workspace).state_revision == before


def test_fresh_decision_keeps_empty_requirement_intent_valid(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    candidate = _candidate(setup, "vitrine_scoreform_fixture")
    section_id = candidate.eligible_section_ids[0]
    before = load_current_state(setup.workspace).state_revision

    plan = plan_candidate_decision(
        setup.workspace,
        entry_id=f"candidate:{candidate.candidate_id}",
        decision="select",
        proposed_section_ids=(section_id,),
        intended_profile_requirement_ids=(),
    )

    assert plan.proposed_section_ids == (section_id,)
    assert plan.intended_profile_requirement_ids == ()
    assert load_current_state(setup.workspace).state_revision == before
