from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
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
from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    list_candidate_inbox,
)
from vitrine.candidate_inbox import (
    get_candidate_inbox_detail as get_inbox_detail,
)
from vitrine.candidate_review import (
    CANDIDATE_REVIEW_CONTRACT_VERSION,
    CandidateReviewError,
    get_candidate_review_detail,
    list_candidate_review_entries,
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
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    PortfolioCandidate,
    PortfolioSubject,
)
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


def test_review_list_reuses_candidate_inbox_and_is_read_only(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    query = CandidateInboxQuery(portfolio_id=setup.portfolio_id)
    before = load_current_state(setup.workspace).state_revision

    expected = list_candidate_inbox(setup.workspace, query)
    actual = list_candidate_review_entries(setup.workspace, query)

    assert actual == expected
    assert actual.observed_state_revision == before
    assert load_current_state(setup.workspace).state_revision == before


def test_review_detail_projects_direct_selection_without_implicit_placement(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, _evaluation = _candidate_and_evaluation(setup)
    selected_section = candidate.eligible_section_ids[0]
    after_discovery = load_current_state(setup.workspace).state_revision
    select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(selected_section,),
        expected_state_revision=after_discovery,
        authority_gate=_AllowedCurationGate(),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    before_review = load_current_state(setup.workspace).state_revision

    detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{candidate.candidate_id}",
    )

    assert detail.contract_version == CANDIDATE_REVIEW_CONTRACT_VERSION
    assert detail.selectable is True
    assert len(detail.proposals) == 1
    assert detail.proposals[0].proposal_origin == "direct_selection"
    assert detail.proposals[0].proposed_section_ids == (selected_section,)
    assert len(detail.proposals[0].decisions) == 1
    assert detail.proposals[0].decisions[0].decision == "accepted"
    assert len(detail.selections) == 1
    assert detail.selections[0].lifecycle_state == "activated"
    assert detail.selections[0].proposal_ids == (
        detail.proposals[0].selection_proposal_id,
    )
    assert detail.placements == ()
    section = next(
        item for item in detail.sections if item.section_id == selected_section
    )
    assert section.active_placement_count == 0
    assert section.relevant_profile_requirement_ids
    assert load_current_state(setup.workspace).state_revision == before_review


def test_review_detail_keeps_current_and_curation_evaluations_distinct(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, evaluation = _candidate_and_evaluation(setup)
    successor = replace(
        evaluation,
        candidate_evaluation_id="candidate_evaluation_review_successor",
        predecessor_evaluation_id=evaluation.candidate_evaluation_id,
        evaluated_at=evaluation.evaluated_at + timedelta(seconds=30),
    )
    pointer = CandidateCurrentEvaluationPointerRevision(
        candidate_id=candidate.candidate_id,
        pointer_revision=2,
        current_candidate_evaluation_id=successor.candidate_evaluation_id,
        predecessor_pointer_revision=1,
        previous_candidate_evaluation_id=evaluation.candidate_evaluation_id,
        updated_at=successor.evaluated_at,
        updated_by=ACTOR,
        reason="Synthetic guided-review reevaluation.",
    )
    before_pointer = load_current_state(setup.workspace).state_revision
    commit_record_batch(
        setup.workspace,
        (successor, pointer),
        expected_state_revision=before_pointer,
    )

    detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{candidate.candidate_id}",
    )

    assert detail.current_review_evaluation_id == successor.candidate_evaluation_id
    assert (
        detail.curation_provenance_evaluation_id
        == evaluation.candidate_evaluation_id
    )
    assert detail.current_evaluation_differs_from_curation_provenance is True
    assert detail.inbox_detail.candidate is not None
    assert (
        detail.inbox_detail.candidate.candidate_evaluation_id
        == evaluation.candidate_evaluation_id
    )


def test_evaluation_only_entry_is_reviewable_but_not_selectable(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    _candidate, evaluation = _candidate_and_evaluation(setup)
    negative = replace(
        evaluation,
        candidate_evaluation_id="candidate_evaluation_review_ineligible",
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

    detail = get_candidate_review_detail(
        setup.workspace,
        f"evaluation:{negative.candidate_evaluation_id}",
    )

    assert detail.selectable is False
    assert detail.current_review_evaluation_id == negative.candidate_evaluation_id
    assert detail.curation_provenance_evaluation_id is None
    assert detail.proposals == ()
    assert detail.selections == ()
    assert detail.placements == ()
    assert detail.inbox_detail.item.evaluation_outcome == "ineligible"


def test_suppressed_evaluation_remains_absent_from_guided_review_list(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    _candidate, evaluation = _candidate_and_evaluation(setup)
    suppressed = replace(
        evaluation,
        candidate_evaluation_id="candidate_evaluation_review_suppressed",
        predecessor_evaluation_id=None,
        eligible_section_ids=(),
        outcome="suppressed",
        reason_codes=("fixture_suppressed",),
        evaluated_at=evaluation.evaluated_at + timedelta(seconds=90),
    )
    before_suppressed = load_current_state(setup.workspace).state_revision
    commit_record_batch(
        setup.workspace,
        (suppressed,),
        expected_state_revision=before_suppressed,
    )

    result = list_candidate_review_entries(
        setup.workspace,
        CandidateInboxQuery(portfolio_id=setup.portfolio_id),
    )

    assert all(
        item.current_evaluation_id != suppressed.candidate_evaluation_id
        for item in result.items
    )


def test_review_detail_fails_closed_when_state_changes_after_inbox_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate, _evaluation = _candidate_and_evaluation(setup)

    def _read_then_advance(
        workspace_root: str | Path,
        entry_id: str,
    ):
        detail = get_inbox_detail(workspace_root, entry_id)
        extra_subject = PortfolioSubject(
            portfolio_subject_id="subject_candidate_review_concurrency",
            created_at=fixed_clock() + timedelta(seconds=120),
            created_by=ACTOR,
            display_name_snapshot="Concurrent Review Subject",
        )
        commit_record_batch(
            setup.workspace,
            (extra_subject,),
            expected_state_revision=detail.observed_state_revision,
        )
        return detail

    monkeypatch.setattr(
        candidate_review,
        "get_candidate_inbox_detail",
        _read_then_advance,
    )

    with pytest.raises(CandidateReviewError) as error:
        candidate_review.get_candidate_review_detail(
            setup.workspace,
            f"candidate:{candidate.candidate_id}",
        )

    assert error.value.code == "candidate_review.state_changed"
