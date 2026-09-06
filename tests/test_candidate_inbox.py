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
from vitrine.candidate_inbox import (
    CandidateInboxError,
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
    select_candidate_directly,
)
from vitrine.development_adapters import (
    build_development_fixture_adapter_registry,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import CandidateEvaluation, PortfolioCandidate
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)


class _AllowedCurationGate:
    def authorize(
        self,
        _request: CurationAuthorityRequest,
    ) -> CurationAuthorityDecision:
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="fixture:teacher",
        )


def _discover_scoreform(
    setup: object,
    *,
    expected_state_revision: int | None = None,
):
    return discover_and_evaluate_candidates(
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
            expected_state_revision=(
                getattr(setup, "state_revision")
                if expected_state_revision is None
                else expected_state_revision
            ),
        ),
        producer_registry=(
            build_development_fixture_producer_registry()
        ),
        adapter_registry=(
            build_development_fixture_adapter_registry()
        ),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )


def test_workspace_inbox_lists_positive_candidates_read_only(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    discovery = _discover_scoreform(setup)
    assert discovery.findings == ()
    before = load_current_state(setup.workspace).state_revision

    result = list_candidate_inbox(setup.workspace)

    assert result.observed_state_revision == before
    assert result.matched_count == 2
    assert not result.truncated
    assert len(result.items) == 2
    assert all(
        item.entry_id.startswith("candidate:")
        for item in result.items
    )
    assert all(
        item.current_resolution == "explicit"
        for item in result.items
    )
    assert all(
        item.evaluation_outcome == "eligible"
        for item in result.items
    )
    assert all(
        item.candidate_condition == "ready_for_consideration"
        for item in result.items
    )
    assert all(
        item.profile_purpose == "improvement"
        for item in result.items
    )
    assert all(
        item.selected_state == "unselected"
        for item in result.items
    )
    assert all(
        item.producer_module_id == "vitrine_scoreform_fixture"
        for item in result.items
    )
    assert load_current_state(setup.workspace).state_revision == before


def test_inbox_filters_and_limit_are_deterministic(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)

    query = CandidateInboxQuery(
        portfolio_id=setup.portfolio_id,
        profile_purpose="improvement",
        evaluation_outcomes=("eligible",),
        candidate_conditions=("ready_for_consideration",),
        selected_state="unselected",
        producer_module_id="vitrine_scoreform_fixture",
        evaluated_since=fixed_clock() - timedelta(seconds=1),
        limit=1,
    )
    first = list_candidate_inbox(setup.workspace, query)
    second = list_candidate_inbox(setup.workspace, query)

    assert first == second
    assert first.matched_count == 2
    assert first.truncated
    assert len(first.items) == 1
    assert first.items[0].portfolio_id == setup.portfolio_id


def test_ineligible_evaluations_are_visible_without_fake_candidates(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    discovery = _discover_scoreform(setup)
    assert all(
        item.evaluation.outcome == "ineligible"
        for item in discovery.evaluation_results
    )

    result = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(
            evaluation_outcomes=("ineligible",),
        ),
    )

    assert result.matched_count == 2
    assert all(
        item.entry_id.startswith("evaluation:")
        for item in result.items
    )
    assert all(item.candidate_id is None for item in result.items)
    assert all(
        item.current_resolution == "evaluation_only"
        for item in result.items
    )
    assert all(
        item.selected_state == "unselected"
        for item in result.items
    )
    records = load_current_records(setup.workspace)
    assert not any(
        isinstance(item, PortfolioCandidate)
        for item in records
    )


def test_unresolved_evaluations_are_visible_without_fake_candidates(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        link_student=False,
    )
    _discover_scoreform(setup)

    result = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(
            evaluation_outcomes=("unresolved",),
        ),
    )

    assert result.matched_count == 2
    assert all(
        item.evaluation_outcome == "unresolved"
        for item in result.items
    )
    assert all(item.candidate_id is None for item in result.items)


def test_suppressed_head_is_removed_before_counts_and_filters(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations = tuple(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
    )
    first = evaluations[0]
    suppressed = replace(
        first,
        candidate_evaluation_id="candidate_evaluation_suppressed",
        predecessor_evaluation_id=first.candidate_evaluation_id,
        outcome="suppressed",
        reason_codes=("candidate:suppressed",),
        evaluated_at=first.evaluated_at + timedelta(seconds=1),
    )
    before_commit = load_current_state(
        setup.workspace
    ).state_revision
    commit_record_batch(
        setup.workspace,
        (suppressed,),
        expected_state_revision=before_commit,
    )
    before_read = load_current_state(setup.workspace).state_revision

    result = list_candidate_inbox(setup.workspace)

    assert result.matched_count == 1
    assert len(result.items) == 1
    assert (
        "candidate_evaluation_suppressed"
        not in repr(result)
    )
    assert load_current_state(setup.workspace).state_revision == before_read


def test_selection_status_is_observational_and_filterable(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    candidate = next(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
    )
    after_discovery = load_current_state(
        setup.workspace
    ).state_revision

    selection = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(candidate.eligible_section_ids[0],),
        expected_state_revision=after_discovery,
        authority_gate=_AllowedCurationGate(),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    before_read = load_current_state(setup.workspace).state_revision
    assert selection.state_revision == before_read

    result = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(selected_state="selected"),
    )

    assert result.matched_count == 1
    item = result.items[0]
    assert item.candidate_id == candidate.candidate_id
    assert item.selected_state == "selected"
    assert len(item.active_selection_ids) == 1
    assert item.historical_selection_ids == ()
    assert load_current_state(setup.workspace).state_revision == before_read


def test_detail_preserves_current_history_and_exact_profile_context(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    listing = list_candidate_inbox(setup.workspace)
    entry = listing.items[0]
    before = load_current_state(setup.workspace).state_revision

    detail = get_candidate_inbox_detail(
        setup.workspace,
        entry.entry_id,
    )

    assert detail.observed_state_revision == before
    assert detail.item == entry
    assert detail.candidate is not None
    assert detail.evaluation is not None
    assert detail.evaluation_history == (detail.evaluation,)
    assert len(detail.pointer_history) == 1
    assert detail.pointer_history[0].pointer_revision == 1
    assert (
        detail.profile_revision.reference
        == detail.candidate.profile_revision
    )
    assert detail.selection_history == ()
    assert load_current_state(setup.workspace).state_revision == before


def test_suppressed_entry_cannot_be_retrieved_by_detail(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    first = next(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
    )
    suppressed = replace(
        first,
        candidate_evaluation_id="candidate_evaluation_suppressed",
        predecessor_evaluation_id=first.candidate_evaluation_id,
        outcome="suppressed",
        reason_codes=("candidate:suppressed",),
        evaluated_at=first.evaluated_at + timedelta(seconds=1),
    )
    state_revision = load_current_state(
        setup.workspace
    ).state_revision
    commit_record_batch(
        setup.workspace,
        (suppressed,),
        expected_state_revision=state_revision,
    )

    with pytest.raises(CandidateInboxError) as caught:
        get_candidate_inbox_detail(
            setup.workspace,
            "evaluation:candidate_evaluation_suppressed",
        )
    assert caught.value.code == "candidate_inbox.entry_not_found"


def test_query_rejects_suppressed_outcome_and_unbounded_limit() -> None:
    with pytest.raises(CandidateInboxError) as suppressed:
        CandidateInboxQuery(evaluation_outcomes=("suppressed",))
    assert suppressed.value.code == "candidate_inbox.invalid_query"

    with pytest.raises(CandidateInboxError) as limit:
        CandidateInboxQuery(limit=501)
    assert limit.value.code == "candidate_inbox.invalid_query"
