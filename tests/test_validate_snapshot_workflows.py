from __future__ import annotations

from scripts.validate_snapshot_workflows import (
    validate_locked_runtime_fixture_hashes,
    validate_snapshot_fixture_index,
)


def test_locked_runtime_fixture_hashes_remain_unchanged() -> None:
    validate_locked_runtime_fixture_hashes()


def test_snapshot_workflow_fixture_index_is_exact() -> None:
    validate_snapshot_fixture_index()
