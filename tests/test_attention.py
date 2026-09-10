from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery
from pds_core.module_operations import ModuleOwnerActionRef
from pds_core.registry_services import (
    PublicationWithdrawalRequest,
    withdraw_publication,
)
from pds_core.workspace import ensure_workspace_root

import vitrine.attention as attention
from scripts.candidate_fixture_support import (
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
)
from scripts.candidate_fixture_support import (
    fixed_clock as candidate_fixed_clock,
)
from scripts.curation_fixture_support import (
    ACTOR,
    APPROVAL_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.attention import (
    VITRINE_ATTENTION_ACTION_IDS,
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VitrineAttentionError,
    VitrineAttentionQuery,
    evaluate_vitrine_attention,
)
from vitrine.candidate_inbox import CandidateInboxQuery, list_candidate_inbox
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    create_working_composition,
    decide_selection_proposal,
    propose_candidate_selection,
    reject_candidate_directly,
    review_curation_target,
    select_candidate_directly,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    CurationTargetRef,
    PortfolioProfileRequirement,
    PortfolioSelection,
    SelectionProposal,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)
from vitrine.working_composition import prepare_working_composition


def _count(report: object, code: str) -> int:
    values = tuple(
        item
        for item in getattr(report, "summaries")
        if item.code == code
    )
    assert len(values) <= 1
    return 0 if not values else values[0].count


def _codes(report: object) -> tuple[str, ...]:
    return tuple(item.code for item in getattr(report, "summaries"))


def _discover_scoreform(setup: object) -> None:
    discover_and_evaluate_candidates(
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
        clock=candidate_fixed_clock,
        id_factory=DeterministicIds(),
    )


def test_missing_vitrine_store_is_unavailable_without_creation(
    tmp_path: Path,
) -> None:
    workspace = ensure_workspace_root(tmp_path / "workspace", create=True)

    report = evaluate_vitrine_attention(workspace)

    assert report.contract_version == VITRINE_ATTENTION_CONTRACT_VERSION
    assert report.evaluation == "unavailable"
    assert report.observed_state_revision is None
    assert report.summaries == ()
    assert tuple(item.code for item in report.notices) == (
        "vitrine_attention_unavailable",
    )
    assert not (workspace / "vitrine").exists()


def test_current_core_action_ids_accept_core_063_owner_action_contract() -> None:
    for action_id in VITRINE_ATTENTION_ACTION_IDS:
        action = ModuleOwnerActionRef(module_id="vitrine", action_id=action_id)
        assert action.action_id == action_id


def test_unknown_exact_portfolio_fails_with_stable_query_error(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    with pytest.raises(VitrineAttentionError) as exc:
        evaluate_vitrine_attention(
            setup.workspace,
            VitrineAttentionQuery(portfolio_id="portfolio_missing"),
        )

    assert exc.value.code == "vitrine_attention.portfolio_not_found"


def test_candidate_staleness_is_reused_from_candidate_inbox(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    publication_id = candidate.source_endpoint.core_publication.publication_id
    withdraw_publication(
        setup.workspace,
        PublicationWithdrawalRequest(
            publication_id=publication_id,
            reason="Synthetic withdrawal for attention currentness.",
        ),
    )

    inbox = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(portfolio_id=setup.portfolio_id),
    )
    source_item = next(
        item for item in inbox.items if item.candidate_id == candidate.candidate_id
    )
    assert source_item.stale_state == "stale"

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    stale = next(
        item
        for item in report.summaries
        if item.code == "vitrine_candidate_evaluation_stale"
    )
    assert stale.count >= 1
    assert "candidate_inbox.publication_withdrawn" in stale.reason_codes


def test_evaluation_only_unresolved_is_attention_without_fake_candidate(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path, link_student=False)
    _discover_scoreform(setup)

    inbox = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(
            portfolio_id=setup.portfolio_id,
            evaluation_outcomes=("unresolved",),
        ),
    )
    assert inbox.matched_count > 0
    assert all(item.candidate_id is None for item in inbox.items)

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    assert _count(report, "vitrine_candidate_evaluation_unresolved") == (
        inbox.matched_count
    )


def test_curation_fixture_projects_candidate_and_composition_attention_read_only(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    before = load_current_state(setup.workspace).state_revision

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    assert report.evaluation == "evaluated"
    assert report.observed_state_revision == before
    assert _count(report, "vitrine_candidate_review_pending") > 0
    assert _count(report, "vitrine_working_composition_refresh_needed") == 1
    assert _count(report, "vitrine_composition_requirement_unresolved") >= 3
    assert _count(report, "vitrine_composition_obligation_unresolved") >= 1
    assert load_current_state(setup.workspace).state_revision == before


def test_viewing_candidate_inbox_does_not_clear_review_pending_attention(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    query = VitrineAttentionQuery(portfolio_id=setup.portfolio_id)
    before = evaluate_vitrine_attention(setup.workspace, query)

    list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(portfolio_id=setup.portfolio_id),
    )
    after = evaluate_vitrine_attention(setup.workspace, query)

    assert _count(after, "vitrine_candidate_review_pending") == _count(
        before,
        "vitrine_candidate_review_pending",
    )


def test_explicit_reject_resolves_one_candidate_review_pending_fact(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    query = VitrineAttentionQuery(portfolio_id=setup.portfolio_id)
    before = evaluate_vitrine_attention(setup.workspace, query)
    candidate = setup.candidate("evidence_selected")

    reject_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        rejected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    after = evaluate_vitrine_attention(setup.workspace, query)

    assert _count(after, "vitrine_candidate_review_pending") == (
        _count(before, "vitrine_candidate_review_pending") - 1
    )


def test_proposal_head_moves_from_pending_decision_to_follow_up(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    proposed = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=ACTOR,
        proposal_origin="teacher",
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    proposal = next(
        item for item in proposed.records if isinstance(item, SelectionProposal)
    )
    query = VitrineAttentionQuery(portfolio_id=setup.portfolio_id)
    pending = evaluate_vitrine_attention(setup.workspace, query)
    assert _count(pending, "vitrine_selection_decision_pending") == 1

    decide_selection_proposal(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="changes_requested",
        decided_by=ACTOR,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    follow_up = evaluate_vitrine_attention(setup.workspace, query)

    assert _count(follow_up, "vitrine_selection_decision_pending") == 0
    assert _count(follow_up, "vitrine_selection_follow_up_required") == 1
    assert _count(follow_up, "vitrine_candidate_review_pending") < _count(
        pending,
        "vitrine_candidate_review_pending",
    )


def test_active_unplaced_selection_routes_to_existing_review_workflow(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    summary = next(
        item
        for item in report.summaries
        if item.code == "vitrine_selection_unplaced"
    )

    assert summary.count == 1
    assert summary.count_unit == "selections"
    assert summary.next_action is not None
    assert summary.next_action.action_id == "open_candidate_review"
    assert summary.portfolio_id == setup.portfolio_id


def test_review_follow_up_reuses_working_composition_review_projection(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    selected = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    selection = next(
        item for item in selected.records if isinstance(item, PortfolioSelection)
    )
    review_curation_target(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selection.selection_id,
            ),
        ),
        decision="changes_requested",
        reviewed_by=ACTOR,
        reason="Revise this exact current Selection.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
        required_follow_up_codes=("revise_context",),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )
    summary = next(
        item
        for item in report.summaries
        if item.code == "vitrine_curation_review_follow_up"
    )

    assert summary.count == 1
    assert "curation_review_changes_requested" in summary.reason_codes
    assert "revise_context" in summary.reason_codes


def test_required_review_and_human_requirement_stay_structured(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    approval = next(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, PortfolioProfileRequirement)
        and item.requirement_id == APPROVAL_REQUIREMENT_ID
    )
    required_review = replace(
        approval,
        requirement_id="approval_required_attention",
        obligation="required",
        title="Required exact curation review",
    )
    human_review = replace(
        approval,
        requirement_id="manual_required_attention",
        obligation="required",
        satisfaction_class="teacher_judgment",
        title="Required human judgment",
    )
    commit_record_batch(
        setup.workspace,
        (required_review, human_review),
        expected_state_revision=setup.state_revision,
    )

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    assert _count(report, "vitrine_curation_review_required") == 1
    assert _count(report, "vitrine_composition_requirement_human_review") == 1


def test_exact_current_composition_removes_refresh_but_not_obligations(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    initial = prepare_working_composition(setup.workspace, setup.portfolio_id)
    assert initial.disposition == "create_initial"
    create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=initial.observed_state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    assert "vitrine_working_composition_refresh_needed" not in _codes(report)
    assert _count(report, "vitrine_composition_obligation_unresolved") >= 1


def test_isolatable_working_composition_failure_returns_partial_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    def fail_preparation(_root: str | Path, _portfolio_id: str):
        raise CurationWorkflowError(
            "curation.composition_inconsistent",
            "Synthetic isolated preparation failure.",
            stage="preparation",
        )

    monkeypatch.setattr(attention, "prepare_working_composition", fail_preparation)

    report = evaluate_vitrine_attention(
        setup.workspace,
        VitrineAttentionQuery(portfolio_id=setup.portfolio_id),
    )

    assert report.evaluation == "evaluated"
    assert _count(report, "vitrine_candidate_review_pending") > 0
    assert tuple(item.code for item in report.notices) == (
        "vitrine_attention_partial",
    )
