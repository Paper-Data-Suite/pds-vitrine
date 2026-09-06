from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_inbox import (
    CANDIDATE_INBOX_CONDITION_ATTENTION_CODES,
    CandidateInboxQuery,
    list_candidate_inbox,
)
from vitrine.candidate_inbox_menu import run_candidate_inbox_menu
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
    PortfolioSelection,
    PortfolioSubject,
    PortfolioSubjectClassLink,
)
from vitrine.models.candidates import CANDIDATE_CONDITION_STATES
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)


def _scripted_input(values: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(values)
    return lambda _prompt: next(iterator)


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


def test_attention_taxonomy_covers_every_nonready_candidate_condition() -> None:
    assert set(CANDIDATE_INBOX_CONDITION_ATTENTION_CODES) == (
        CANDIDATE_CONDITION_STATES - {"ready_for_consideration"}
    )
    assert all(
        code == f"candidate_inbox.{condition}"
        for condition, code in CANDIDATE_INBOX_CONDITION_ATTENTION_CODES.items()
    )


def test_exact_subject_identity_conflict_is_unresolved_attention(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    records = load_current_records(setup.workspace)
    source_link = next(
        item
        for item in records
        if isinstance(item, PortfolioSubjectClassLink)
        and item.portfolio_subject_id == setup.portfolio_subject_id
    )
    other_subject = PortfolioSubject(
        portfolio_subject_id="subject_candidate_inbox_conflict",
        created_at=fixed_clock() + timedelta(seconds=10),
        created_by=ACTOR,
        display_name_snapshot="Synthetic Conflict",
    )
    other_link = PortfolioSubjectClassLink(
        subject_link_id="subject_link_candidate_inbox_conflict",
        portfolio_subject_id=other_subject.portfolio_subject_id,
        student_reference=source_link.student_reference,
        confirmed_at=fixed_clock() + timedelta(seconds=10),
        confirmed_by=ACTOR,
        confirmation_basis="teacher_confirmed",
        authority_reference="fixture:conflict",
    )
    before = load_current_state(setup.workspace).state_revision
    commit_record_batch(
        setup.workspace,
        (other_subject, other_link),
        expected_state_revision=before,
    )
    before_read = load_current_state(setup.workspace).state_revision

    result = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(attention_only=True),
    )

    assert result.matched_count == 2
    assert all(item.stale_state == "unresolved" for item in result.items)
    assert all(
        "candidate_inbox.subject_relationship_conflict" in item.stale_reason_codes
        for item in result.items
    )
    assert load_current_state(setup.workspace).state_revision == before_read


def test_selection_provenance_does_not_retarget_when_pointer_advances(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    records = load_current_records(setup.workspace)
    candidate = next(item for item in records if isinstance(item, PortfolioCandidate))
    evaluation = next(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
        and item.candidate_evaluation_id == candidate.candidate_evaluation_id
    )
    after_discovery = load_current_state(setup.workspace).state_revision
    select_candidate_directly(
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
    records = load_current_records(setup.workspace)
    selection = next(
        item
        for item in records
        if isinstance(item, PortfolioSelection)
        and item.candidate_id == candidate.candidate_id
    )
    assert selection.candidate_evaluation_id == evaluation.candidate_evaluation_id

    successor = replace(
        evaluation,
        candidate_evaluation_id="candidate_evaluation_pointer_successor",
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
        reason="Explicit synthetic reevaluation.",
    )
    before_pointer = load_current_state(setup.workspace).state_revision
    commit_record_batch(
        setup.workspace,
        (successor, pointer),
        expected_state_revision=before_pointer,
    )

    after = load_current_records(setup.workspace)
    preserved = next(
        item
        for item in after
        if isinstance(item, PortfolioSelection)
        and item.selection_id == selection.selection_id
    )
    assert preserved.candidate_evaluation_id == evaluation.candidate_evaluation_id

    current = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(selected_state="selected"),
    )
    assert current.matched_count == 1
    assert current.items[0].current_evaluation_id == successor.candidate_evaluation_id


def test_candidate_inbox_menu_help_preserves_standard_navigation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    before = load_current_state(setup.workspace).state_revision
    output = io.StringIO()

    run_candidate_inbox_menu(
        input_fn=_scripted_input(["h", "", "b"]),
        output=output,
        clear_fn=lambda: None,
    )

    assert "Candidate Inbox Help" in output.getvalue()
    assert load_current_state(setup.workspace).state_revision == before
