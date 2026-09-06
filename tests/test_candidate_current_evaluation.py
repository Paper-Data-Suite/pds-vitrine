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
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.candidate_state import (
    collect_candidate_state_issues,
    project_candidate_state,
)
from vitrine.development_adapters import (
    build_development_fixture_adapter_registry,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    PortfolioCandidate,
    VitrineModelValidationError,
    record_from_dict,
    record_to_dict,
)
from vitrine.storage import (
    VitrineStorageValidationError,
    commit_record_batch,
    load_current_records,
    load_current_state,
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


def _candidate_records(
    records: tuple[object, ...],
) -> tuple[
    tuple[CandidateEvaluation, ...],
    tuple[PortfolioCandidate, ...],
    tuple[CandidateCurrentEvaluationPointerRevision, ...],
]:
    evaluations = tuple(
        item
        for item in records
        if isinstance(item, CandidateEvaluation)
    )
    candidates = tuple(
        item
        for item in records
        if isinstance(item, PortfolioCandidate)
    )
    pointers = tuple(
        item
        for item in records
        if isinstance(
            item,
            CandidateCurrentEvaluationPointerRevision,
        )
    )
    return evaluations, candidates, pointers


def test_new_positive_candidates_initialize_pointer_atomically(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    result = _discover_scoreform(setup)

    assert result.findings == ()
    assert len(result.evaluation_results) == 2

    records = load_current_records(setup.workspace)
    evaluations, candidates, pointers = _candidate_records(records)
    assert len(evaluations) == 2
    assert len(candidates) == 2
    assert len(pointers) == 2

    evaluation_ids = {
        item.candidate_evaluation_id
        for item in evaluations
    }
    state = project_candidate_state(records)
    for candidate in candidates:
        pointer = next(
            item
            for item in pointers
            if item.candidate_id == candidate.candidate_id
        )
        assert pointer.pointer_revision == 1
        assert (
            pointer.current_candidate_evaluation_id
            == candidate.candidate_evaluation_id
        )
        assert (
            pointer.current_candidate_evaluation_id
            in evaluation_ids
        )
        assert pointer.predecessor_pointer_revision is None
        assert pointer.previous_candidate_evaluation_id is None
        assert pointer.reason == "candidate_created"

        resolution = state.resolve_current_evaluation(
            candidate.candidate_id
        )
        assert resolution.mode == "explicit"
        assert resolution.pointer == pointer
        assert resolution.evaluation is not None
        assert (
            resolution.evaluation.candidate_evaluation_id
            == candidate.candidate_evaluation_id
        )


def test_pointer_round_trips_through_record_conversion(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    _evaluations, _candidates, pointers = _candidate_records(
        records
    )

    payload = record_to_dict(pointers[0])
    assert payload["record_type"] == (
        "candidate_current_evaluation_pointer_revision"
    )
    assert record_from_dict(payload) == pointers[0]


def test_exact_positive_replay_does_not_create_pointer_revision(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    after_first = load_current_state(
        setup.workspace
    ).state_revision
    before_records = load_current_records(setup.workspace)
    _evaluations, _candidates, before_pointers = (
        _candidate_records(before_records)
    )

    second = _discover_scoreform(
        setup,
        expected_state_revision=after_first,
    )

    assert tuple(
        item.disposition
        for item in second.evaluation_results
    ) == ("existing", "existing")
    assert second.committed_state_revision is None
    assert (
        load_current_state(setup.workspace).state_revision
        == after_first
    )
    after_records = load_current_records(setup.workspace)
    _evaluations, _candidates, after_pointers = (
        _candidate_records(after_records)
    )
    assert after_pointers == before_pointers


def test_legacy_candidate_uses_creation_evaluation_without_history(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations, candidates, _pointers = _candidate_records(
        records
    )

    legacy_state = project_candidate_state(
        (*evaluations, *candidates)
    )
    candidate = candidates[0]
    resolution = legacy_state.resolve_current_evaluation(
        candidate.candidate_id
    )

    assert resolution.mode == "legacy"
    assert resolution.pointer is None
    assert resolution.evaluation is not None
    assert (
        resolution.evaluation.candidate_evaluation_id
        == candidate.candidate_evaluation_id
    )


def test_legacy_successor_history_is_unresolved_not_newest_inferred(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations, candidates, _pointers = _candidate_records(
        records
    )
    candidate = candidates[0]
    creation = next(
        item
        for item in evaluations
        if item.candidate_evaluation_id
        == candidate.candidate_evaluation_id
    )
    successor = replace(
        creation,
        candidate_evaluation_id=(
            "candidate_evaluation_successor"
        ),
        predecessor_evaluation_id=(
            creation.candidate_evaluation_id
        ),
        evaluated_at=(
            creation.evaluated_at + timedelta(seconds=1)
        ),
    )

    legacy_state = project_candidate_state(
        (*evaluations, *candidates, successor)
    )
    resolution = legacy_state.resolve_current_evaluation(
        candidate.candidate_id
    )

    assert resolution.mode == "unresolved"
    assert resolution.evaluation is None
    assert resolution.reason_code == (
        "candidate.legacy_current_evaluation_ambiguous"
    )


def test_explicit_pointer_successor_follows_evaluation_lineage(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations, candidates, pointers = _candidate_records(
        records
    )
    candidate = candidates[0]
    creation = next(
        item
        for item in evaluations
        if item.candidate_evaluation_id
        == candidate.candidate_evaluation_id
    )
    successor = replace(
        creation,
        candidate_evaluation_id=(
            "candidate_evaluation_successor"
        ),
        predecessor_evaluation_id=(
            creation.candidate_evaluation_id
        ),
        evaluated_at=(
            creation.evaluated_at + timedelta(seconds=1)
        ),
    )
    successor_pointer = (
        CandidateCurrentEvaluationPointerRevision(
            candidate_id=candidate.candidate_id,
            pointer_revision=2,
            current_candidate_evaluation_id=(
                successor.candidate_evaluation_id
            ),
            updated_at=successor.evaluated_at,
            updated_by=ACTOR,
            reason="candidate_reevaluated",
            predecessor_pointer_revision=1,
            previous_candidate_evaluation_id=(
                creation.candidate_evaluation_id
            ),
        )
    )

    state = project_candidate_state(
        (
            *evaluations,
            *candidates,
            *pointers,
            successor,
            successor_pointer,
        )
    )
    assert collect_candidate_state_issues(state) == ()
    resolution = state.resolve_current_evaluation(
        candidate.candidate_id
    )
    assert resolution.mode == "explicit"
    assert resolution.pointer == successor_pointer
    assert resolution.evaluation == successor


def test_evaluation_and_pointer_branches_are_rejected(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations, candidates, pointers = _candidate_records(
        records
    )
    candidate = candidates[0]
    creation = next(
        item
        for item in evaluations
        if item.candidate_evaluation_id
        == candidate.candidate_evaluation_id
    )
    successor_a = replace(
        creation,
        candidate_evaluation_id=(
            "candidate_evaluation_successor_a"
        ),
        predecessor_evaluation_id=(
            creation.candidate_evaluation_id
        ),
        evaluated_at=(
            creation.evaluated_at + timedelta(seconds=1)
        ),
    )
    successor_b = replace(
        creation,
        candidate_evaluation_id=(
            "candidate_evaluation_successor_b"
        ),
        predecessor_evaluation_id=(
            creation.candidate_evaluation_id
        ),
        evaluated_at=(
            creation.evaluated_at + timedelta(seconds=2)
        ),
    )
    pointer_a = CandidateCurrentEvaluationPointerRevision(
        candidate_id=candidate.candidate_id,
        pointer_revision=2,
        current_candidate_evaluation_id=(
            successor_a.candidate_evaluation_id
        ),
        updated_at=successor_a.evaluated_at,
        updated_by=ACTOR,
        reason="candidate_reevaluated",
        predecessor_pointer_revision=1,
        previous_candidate_evaluation_id=(
            creation.candidate_evaluation_id
        ),
    )
    pointer_b = CandidateCurrentEvaluationPointerRevision(
        candidate_id=candidate.candidate_id,
        pointer_revision=3,
        current_candidate_evaluation_id=(
            successor_b.candidate_evaluation_id
        ),
        updated_at=successor_b.evaluated_at,
        updated_by=ACTOR,
        reason="candidate_reevaluated",
        predecessor_pointer_revision=1,
        previous_candidate_evaluation_id=(
            creation.candidate_evaluation_id
        ),
    )

    state = project_candidate_state(
        (
            *evaluations,
            *candidates,
            *pointers,
            successor_a,
            successor_b,
            pointer_a,
            pointer_b,
        )
    )
    codes = {
        item.code
        for item in collect_candidate_state_issues(state)
    }
    assert "candidate.evaluation_branch" in codes
    assert "candidate.pointer_branch" in codes
    assert "candidate.pointer_head_conflict" in codes


def test_evaluation_cycle_is_rejected(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations, candidates, pointers = _candidate_records(
        records
    )
    candidate = candidates[0]
    creation = next(
        item
        for item in evaluations
        if item.candidate_evaluation_id
        == candidate.candidate_evaluation_id
    )
    cyclic_creation = replace(
        creation,
        predecessor_evaluation_id=(
            "candidate_evaluation_cycle_peer"
        ),
    )
    peer = replace(
        creation,
        candidate_evaluation_id=(
            "candidate_evaluation_cycle_peer"
        ),
        predecessor_evaluation_id=(
            creation.candidate_evaluation_id
        ),
        evaluated_at=(
            creation.evaluated_at + timedelta(seconds=1)
        ),
    )
    state = project_candidate_state(
        (
            *(
                item
                for item in evaluations
                if item != creation
            ),
            cyclic_creation,
            peer,
            *candidates,
            *pointers,
        )
    )
    codes = {
        item.code
        for item in collect_candidate_state_issues(state)
    }
    assert "candidate.evaluation_cycle" in codes
    assert "candidate.creation_evaluation_not_root" in codes


def test_pointer_rejects_non_decreasing_predecessor_revision() -> None:
    with pytest.raises(VitrineModelValidationError):
        CandidateCurrentEvaluationPointerRevision(
            candidate_id="candidate_fixture",
            pointer_revision=2,
            current_candidate_evaluation_id=(
                "candidate_evaluation_2"
            ),
            updated_at=fixed_clock(),
            updated_by=ACTOR,
            reason="candidate_reevaluated",
            predecessor_pointer_revision=2,
            previous_candidate_evaluation_id=(
                "candidate_evaluation_1"
            ),
        )


def test_pointer_to_other_candidate_source_context_is_rejected(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    records = load_current_records(setup.workspace)
    evaluations, candidates, pointers = _candidate_records(
        records
    )
    first, second = candidates
    second_evaluation = next(
        item
        for item in evaluations
        if item.candidate_evaluation_id
        == second.candidate_evaluation_id
    )
    bad_pointer = replace(
        next(
            item
            for item in pointers
            if item.candidate_id == first.candidate_id
        ),
        current_candidate_evaluation_id=(
            second_evaluation.candidate_evaluation_id
        ),
    )
    state = project_candidate_state(
        (
            *evaluations,
            *candidates,
            *(
                item
                for item in pointers
                if item.candidate_id != first.candidate_id
            ),
            bad_pointer,
        )
    )
    codes = {
        item.code
        for item in collect_candidate_state_issues(state)
    }
    assert "candidate.pointer_evaluation_context_mismatch" in codes
    assert "candidate.pointer_source_endpoint_mismatch" in codes
    assert "candidate.pointer_initial_evaluation_mismatch" in codes


def test_public_commit_rejects_pointer_without_candidate_or_evaluation(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    pointer = CandidateCurrentEvaluationPointerRevision(
        candidate_id="candidate_missing",
        pointer_revision=1,
        current_candidate_evaluation_id=(
            "candidate_evaluation_missing"
        ),
        updated_at=fixed_clock(),
        updated_by=ACTOR,
        reason="candidate_created",
    )

    with pytest.raises(VitrineStorageValidationError) as caught:
        commit_record_batch(
            setup.workspace,
            (pointer,),
            expected_state_revision=setup.state_revision,
        )
    assert "candidate.pointer_candidate_missing" in str(
        caught.value
    )
