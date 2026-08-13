from __future__ import annotations

from pathlib import Path

from scripts.validate_snapshot_workflows import (
    _copy_source_fixture,
    validate_locked_runtime_fixture_hashes,
    validate_snapshot_fixture_index,
)


def test_locked_runtime_fixture_hashes_remain_unchanged() -> None:
    validate_locked_runtime_fixture_hashes()


def test_snapshot_workflow_fixture_index_is_exact() -> None:
    validate_snapshot_fixture_index()


def test_snapshot_workflow_source_fixture_root_is_canonical(tmp_path: Path) -> None:
    source_root = _copy_source_fixture(tmp_path / "source-root")
    assert source_root == source_root.resolve(strict=True)
