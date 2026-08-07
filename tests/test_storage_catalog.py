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
    VitrineCatalogIntegrityError,
    VitrineCatalogNotFoundError,
    VitrineCatalogSourceError,
    catalog_path,
    commit_record_batch,
    load_current_record_graph,
    query_catalog_records,
    rebuild_catalog,
)


def test_catalog_is_rebuildable_and_nonauthoritative(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    path = rebuild_catalog(tmp_path)
    assert len(query_catalog_records(tmp_path, state="current")) == 27

    path.unlink()
    with pytest.raises(VitrineCatalogNotFoundError):
        query_catalog_records(tmp_path)
    assert load_current_record_graph(tmp_path).graph == graph


def test_stale_catalog_does_not_affect_canonical_reads(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    base = improvement_base_graph(graph)
    commit_record_batch(tmp_path, flatten_graph(base), expected_state_revision=None)
    rebuild_catalog(tmp_path)
    commit_record_batch(tmp_path, snapshot_records(graph), expected_state_revision=1)

    with pytest.raises(VitrineCatalogSourceError):
        query_catalog_records(tmp_path)
    assert load_current_record_graph(tmp_path).graph == graph


def test_corrupt_catalog_does_not_affect_canonical_reads(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    rebuild_catalog(tmp_path)
    catalog_path(tmp_path).write_bytes(b"not sqlite")

    with pytest.raises(VitrineCatalogIntegrityError):
        query_catalog_records(tmp_path)
    assert load_current_record_graph(tmp_path).graph == graph


def test_catalog_rebuild_rejects_source_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vitrine.storage import VitrineCatalogConflictError
    from vitrine.storage import catalog as catalog_module

    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    original = catalog_module.canonical_source_inventory
    calls = 0

    def changing_inventory(root: str | Path):
        nonlocal calls
        calls += 1
        inventory = original(root)
        if calls == 2:
            return (*inventory, ("synthetic-drift", 1, "0" * 64))
        return inventory

    monkeypatch.setattr(catalog_module, "canonical_source_inventory", changing_inventory)
    with pytest.raises(VitrineCatalogConflictError):
        rebuild_catalog(tmp_path)
    assert not catalog_path(tmp_path).exists()
