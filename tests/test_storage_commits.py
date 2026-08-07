from __future__ import annotations

from pathlib import Path

import pytest

from tests.runtime_fixture_factory import make_improvement_graph
from tests.storage_helpers import (
    flatten_graph,
    improvement_base_graph,
    snapshot_records,
)
from vitrine.models import Portfolio
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageGraphIntegrityError,
    VitrineStoragePartialSuccessError,
    commit_record_batch,
    load_current_record_graph,
)


def test_bootstrap_advance_replay_and_stale_conflict(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    base = improvement_base_graph(graph)

    first = commit_record_batch(
        tmp_path, flatten_graph(base), expected_state_revision=None
    )
    assert first.state_revision == 1
    assert len(first.created_record_revisions) == 18

    second = commit_record_batch(
        tmp_path, snapshot_records(graph), expected_state_revision=1
    )
    assert second.state_revision == 2
    assert len(second.created_record_revisions) == 9

    replay = commit_record_batch(
        tmp_path, snapshot_records(graph), expected_state_revision=2
    )
    assert replay.no_op
    assert replay.state_revision == 2

    with pytest.raises(VitrineStorageConflictError):
        commit_record_batch(
            tmp_path, snapshot_records(graph), expected_state_revision=1
        )

    loaded = load_current_record_graph(tmp_path)
    assert loaded.state_revision == 2
    assert loaded.graph == graph


def test_existing_semantic_identity_cannot_be_rewritten(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    portfolio = graph.portfolios[0]
    changed = Portfolio(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        created_at=portfolio.created_at,
        created_by=portfolio.created_by,
        title_snapshot="Changed title",
        description_snapshot=portfolio.description_snapshot,
    )
    with pytest.raises(VitrineStorageConflictError):
        commit_record_batch(tmp_path, (changed,), expected_state_revision=1)


def test_invalid_complete_candidate_graph_is_rejected_before_record_writes(
    tmp_path: Path,
) -> None:
    graph = make_improvement_graph()
    portfolio_only = (graph.portfolios[0],)
    with pytest.raises(VitrineStorageGraphIntegrityError):
        commit_record_batch(tmp_path, portfolio_only, expected_state_revision=None)
    assert not (tmp_path / "vitrine" / "state" / "store.json").exists()


def test_failure_before_pointer_publication_reports_partial_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vitrine.storage import store as storage_module

    graph = improvement_base_graph(make_improvement_graph())

    def fail_publish(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected pointer failure")

    monkeypatch.setattr(storage_module, "_publish", fail_publish)
    with pytest.raises(VitrineStoragePartialSuccessError) as raised:
        commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    assert not raised.value.pointer_published
    assert raised.value.durable_paths
    assert not (tmp_path / "vitrine" / "state" / "current.json").exists()


def test_failure_after_pointer_publication_reports_committed_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vitrine.storage import store as storage_module

    graph = improvement_base_graph(make_improvement_graph())
    original = storage_module.load_current_record_graph
    calls = 0

    def fail_final(root: str | Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected final verification failure")
        return original(root)

    monkeypatch.setattr(storage_module, "load_current_record_graph", fail_final)
    with pytest.raises(VitrineStoragePartialSuccessError) as raised:
        commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    assert raised.value.pointer_published
    assert raised.value.state_revision == 1
    assert (tmp_path / "vitrine" / "state" / "current.json").exists()


def test_commit_requires_existing_writable_core_workspace(tmp_path: Path) -> None:
    from vitrine.storage import VitrineStorageWriteError

    graph = improvement_base_graph(make_improvement_graph())
    missing = tmp_path / "missing-workspace"
    with pytest.raises(VitrineStorageWriteError):
        commit_record_batch(
            missing,
            flatten_graph(graph),
            expected_state_revision=None,
        )
    assert not missing.exists()
