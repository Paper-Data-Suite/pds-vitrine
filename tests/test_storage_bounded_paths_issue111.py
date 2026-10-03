from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.runtime_fixture_factory import make_improvement_graph
from tests.storage_helpers import (
    flatten_graph,
    improvement_base_graph,
    snapshot_records,
)
from vitrine.path_policy import CUSTODY_TOKEN_MAX_LENGTH
from vitrine.storage import (
    VitrineStorageIntegrityError,
    VitrineStorageRecordKey,
    bounded_record_identity_path,
    bounded_record_revision_path,
    bounded_records_root,
    canonical_source_inventory,
    commit_record_batch,
    key_for_record,
    list_record_keys,
    load_current_record_graph,
    record_identity_path,
    record_revision_path,
    resolve_record_revision_path,
)


def _relocate_all_bounded_records_to_legacy(workspace: Path) -> None:
    keys = list_record_keys(workspace)
    assert keys
    for key in keys:
        source = bounded_record_identity_path(workspace, key)
        target = record_identity_path(workspace, key)
        assert source.is_dir()
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    shutil.rmtree(bounded_records_root(workspace))


def test_new_canonical_records_use_bounded_custody_without_changing_key(
    tmp_path: Path,
) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)

    portfolio = graph.portfolios[0]
    key = key_for_record(portfolio)
    bounded = bounded_record_revision_path(tmp_path, key, 1)

    assert bounded.is_file()
    assert len(bounded_record_identity_path(tmp_path, key).name) == (
        CUSTODY_TOKEN_MAX_LENGTH
    )
    assert not record_revision_path(tmp_path, key, 1).exists()
    assert resolve_record_revision_path(tmp_path, key, 1) == bounded
    assert key in list_record_keys(tmp_path)
    assert load_current_record_graph(tmp_path).graph == graph


def test_bounded_record_path_size_does_not_scale_with_long_semantic_identity(
    tmp_path: Path,
) -> None:
    key = VitrineStorageRecordKey(
        "portfolio_profile_requirement",
        (
            "profile_" + ("x" * 10_000),
            "1",
            "requirement_" + ("y" * 10_000),
        ),
    )

    identity = bounded_record_identity_path(tmp_path, key)
    assert len(identity.name) == CUSTODY_TOKEN_MAX_LENGTH
    assert len(identity.name) < len(key.identity_segments[0])
    assert len(identity.name) < len(key.identity_segments[2])


def test_legacy_record_layout_remains_readable_without_migration(
    tmp_path: Path,
) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    _relocate_all_bounded_records_to_legacy(tmp_path)

    assert not bounded_records_root(tmp_path).exists()
    assert load_current_record_graph(tmp_path).graph == graph
    assert not bounded_records_root(tmp_path).exists()

    portfolio_key = key_for_record(graph.portfolios[0])
    assert resolve_record_revision_path(tmp_path, portfolio_key, 1) == (
        record_revision_path(tmp_path, portfolio_key, 1)
    )


def test_existing_legacy_history_and_new_bounded_records_can_coexist(
    tmp_path: Path,
) -> None:
    graph = make_improvement_graph()
    base = improvement_base_graph(graph)
    commit_record_batch(tmp_path, flatten_graph(base), expected_state_revision=None)
    _relocate_all_bounded_records_to_legacy(tmp_path)

    result = commit_record_batch(
        tmp_path,
        snapshot_records(graph),
        expected_state_revision=1,
    )
    assert result.state_revision == 2
    assert load_current_record_graph(tmp_path).graph == graph

    portfolio_key = key_for_record(graph.portfolios[0])
    edition_key = key_for_record(graph.snapshot_editions[0])
    assert record_revision_path(tmp_path, portfolio_key, 1).is_file()
    assert not bounded_record_revision_path(tmp_path, portfolio_key, 1).exists()
    assert bounded_record_revision_path(tmp_path, edition_key, 1).is_file()
    assert not record_revision_path(tmp_path, edition_key, 1).exists()


def test_duplicate_legacy_and_bounded_custody_for_same_key_fails_closed(
    tmp_path: Path,
) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)

    key = key_for_record(graph.portfolios[0])
    bounded_identity = bounded_record_identity_path(tmp_path, key)
    legacy_identity = record_identity_path(tmp_path, key)
    legacy_identity.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bounded_identity, legacy_identity)

    with pytest.raises(
        VitrineStorageIntegrityError,
        match="both legacy and bounded custody",
    ):
        load_current_record_graph(tmp_path)


def test_catalog_inventory_uses_exact_resolved_bounded_record_paths(
    tmp_path: Path,
) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)

    inventory = canonical_source_inventory(tmp_path)
    relative_paths = tuple(item[0] for item in inventory)
    assert any(path.startswith("records-bounded-v1/") for path in relative_paths)
    assert not any(path.startswith("records/portfolio/") for path in relative_paths)
