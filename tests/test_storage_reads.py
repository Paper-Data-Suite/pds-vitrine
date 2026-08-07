from __future__ import annotations

from pathlib import Path

import pytest

from tests.runtime_fixture_factory import make_improvement_graph
from tests.storage_helpers import (
    flatten_graph,
    improvement_base_graph,
    snapshot_records,
)
from vitrine.storage import (
    VitrineStorageIntegrityError,
    commit_record_batch,
    key_for_record,
    load_current_record,
    load_current_record_graph,
    load_state_revision,
    state_revision_path,
)


def test_historical_and_current_reads_use_canonical_state(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    base = improvement_base_graph(graph)
    commit_record_batch(tmp_path, flatten_graph(base), expected_state_revision=None)
    commit_record_batch(tmp_path, snapshot_records(graph), expected_state_revision=1)

    _, _, historical = load_state_revision(tmp_path, 1)
    assert historical == base
    assert load_current_record_graph(tmp_path).graph == graph

    portfolio = graph.portfolios[0]
    record, envelope = load_current_record(tmp_path, key_for_record(portfolio))
    assert record == portfolio
    assert envelope.storage_revision == 1


def test_state_digest_tampering_fails_closed(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    path = state_revision_path(tmp_path, 1)
    data = path.read_bytes()
    marker = b'"sha256": "'
    start = data.index(marker) + len(marker)
    path.write_bytes(data[:start] + b"0" * 64 + data[start + 64 :])
    with pytest.raises(VitrineStorageIntegrityError):
        load_current_record_graph(tmp_path)


def test_orphan_state_revision_blocks_future_writes(tmp_path: Path) -> None:
    graph = improvement_base_graph(make_improvement_graph())
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    source = state_revision_path(tmp_path, 1)
    orphan = state_revision_path(tmp_path, 2)
    orphan.write_bytes(source.read_bytes())
    with pytest.raises(VitrineStorageIntegrityError):
        commit_record_batch(
            tmp_path,
            (graph.portfolios[0],),
            expected_state_revision=1,
        )


def test_missing_store_read_is_side_effect_free(tmp_path: Path) -> None:
    from vitrine.storage import VitrineStorageNotFoundError, load_store_marker

    before = tuple(tmp_path.iterdir())
    with pytest.raises(VitrineStorageNotFoundError):
        load_store_marker(tmp_path)
    assert tuple(tmp_path.iterdir()) == before
    assert not (tmp_path / "vitrine").exists()
