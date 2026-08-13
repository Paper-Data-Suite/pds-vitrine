from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    acquire_snapshot_series_lock,
    create_snapshot_staging,
    inspect_snapshot_series_lock,
    load_snapshot_staging,
    normalize_snapshot_relative_path,
    release_snapshot_series_lock,
    require_empty_snapshot_staging,
    snapshot_editions_root,
    snapshot_exports_root,
    snapshot_locks_root,
    snapshot_path_collision_key,
    snapshot_staging_root,
    validate_snapshot_path_inventory,
    write_staging_bytes_exclusive,
)


@pytest.mark.parametrize(
    "value",
    (
        "../escape.txt",
        "content/../escape.txt",
        "/absolute.txt",
        "C:/escape.txt",
        "https://example.test/file.txt",
        "folder\\file.txt",
        "folder//file.txt",
        "./file.txt",
        "file.txt ",
    ),
)
def test_snapshot_path_policy_rejects_nonportable_paths(value: str) -> None:
    with pytest.raises(SnapshotCustodyError) as captured:
        normalize_snapshot_relative_path(value)
    assert captured.value.code == "snapshot.path_invalid"


def test_snapshot_path_inventory_rejects_unicode_case_collision() -> None:
    assert snapshot_path_collision_key("Résumé.txt") == snapshot_path_collision_key(
        "re\u0301sume\u0301.TXT"
    )
    with pytest.raises(SnapshotCustodyError) as captured:
        validate_snapshot_path_inventory(("Résumé.txt", "re\u0301sume\u0301.TXT"))
    assert captured.value.code == "snapshot.path_collision"


def test_snapshot_custody_layout_and_staging_are_workspace_scoped(tmp_path: Path) -> None:
    assert snapshot_staging_root(tmp_path) == tmp_path.resolve() / "vitrine" / "snapshots" / "staging"
    assert snapshot_editions_root(tmp_path) == tmp_path.resolve() / "vitrine" / "snapshots" / "editions"
    assert snapshot_exports_root(tmp_path) == tmp_path.resolve() / "vitrine" / "snapshots" / "exports"
    assert snapshot_locks_root(tmp_path) == tmp_path.resolve() / "vitrine" / "snapshots" / ".locks"

    staging = create_snapshot_staging(tmp_path, "snapshot_attempt_1")
    assert staging.root == snapshot_staging_root(tmp_path) / "snapshot_attempt_1"
    assert staging.content_root.is_dir()
    assert staging.internal_root.is_dir()

    with pytest.raises(SnapshotCustodyError) as captured:
        create_snapshot_staging(tmp_path, "snapshot_attempt_1")
    assert captured.value.code == "snapshot.staging_conflict"


def test_staging_writes_are_exclusive_and_exact(tmp_path: Path) -> None:
    staging = create_snapshot_staging(tmp_path, "snapshot_attempt_2")
    target = write_staging_bytes_exclusive(
        staging,
        "section/01-work.txt",
        b"exact snapshot bytes\n",
    )
    assert target.read_bytes() == b"exact snapshot bytes\n"

    with pytest.raises(SnapshotCustodyError) as captured:
        write_staging_bytes_exclusive(
            staging,
            "section/01-work.txt",
            b"replacement bytes\n",
        )
    assert captured.value.code == "snapshot.staging_conflict"
    assert target.read_bytes() == b"exact snapshot bytes\n"



def test_existing_staging_can_be_reopened_but_not_implicitly_reused(
    tmp_path: Path,
) -> None:
    staging = create_snapshot_staging(tmp_path, "snapshot_attempt_reopen")
    reopened = load_snapshot_staging(tmp_path, "snapshot_attempt_reopen")
    assert reopened.root == staging.root
    require_empty_snapshot_staging(reopened)
    reopened.content_path("residue.txt").write_text("residue", encoding="utf-8")
    with pytest.raises(SnapshotCustodyError) as captured:
        require_empty_snapshot_staging(reopened)
    assert captured.value.code == "snapshot.staging_conflict"



def test_series_build_lock_is_exclusive_exact_and_not_age_cleared(
    tmp_path: Path,
) -> None:
    acquired = datetime(2026, 8, 12, 23, 0, tzinfo=timezone.utc)
    lock = acquire_snapshot_series_lock(
        tmp_path,
        snapshot_series_id="snapshot_series_lock_fixture",
        snapshot_build_attempt_id="snapshot_attempt_lock_fixture",
        snapshot_build_plan_id="snapshot_plan_lock_fixture",
        acquired_at=acquired,
    )
    assert lock.acquired_at == acquired
    inspected = inspect_snapshot_series_lock(
        tmp_path, snapshot_series_id="snapshot_series_lock_fixture"
    )
    assert inspected == lock
    with pytest.raises(SnapshotCustodyError) as captured:
        acquire_snapshot_series_lock(
            tmp_path,
            snapshot_series_id="snapshot_series_lock_fixture",
            snapshot_build_attempt_id="snapshot_attempt_other",
            snapshot_build_plan_id="snapshot_plan_other",
            acquired_at=datetime(2036, 8, 12, 23, 0, tzinfo=timezone.utc),
        )
    assert captured.value.code == "snapshot.build_lock_conflict"
    # Age is irrelevant; only exact expected identity/digest may release.
    with pytest.raises(SnapshotCustodyError) as captured:
        release_snapshot_series_lock(
            tmp_path,
            snapshot_series_id="snapshot_series_lock_fixture",
            snapshot_build_attempt_id="snapshot_attempt_other",
            expected_sha256=lock.sha256,
        )
    assert captured.value.code == "snapshot.build_lock_conflict"
    release_snapshot_series_lock(
        tmp_path,
        snapshot_series_id="snapshot_series_lock_fixture",
        snapshot_build_attempt_id="snapshot_attempt_lock_fixture",
        expected_sha256=lock.sha256,
    )
    with pytest.raises(SnapshotCustodyError) as captured:
        inspect_snapshot_series_lock(
            tmp_path, snapshot_series_id="snapshot_series_lock_fixture"
        )
    assert captured.value.code == "snapshot.build_lock_missing"
