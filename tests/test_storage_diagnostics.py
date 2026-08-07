from __future__ import annotations

from pathlib import Path

from tests.runtime_fixture_factory import make_improvement_graph
from tests.storage_helpers import flatten_graph
from vitrine.storage import (
    audit_canonical_storage,
    commit_record_batch,
    write_lock_path,
)


def test_canonical_audit_is_clean_and_does_not_require_catalog(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    assert audit_canonical_storage(tmp_path) == ()
    assert not (tmp_path / "vitrine" / "state" / "derived" / "catalog.sqlite").exists()


def test_lock_presence_is_reported_without_clearing_it(tmp_path: Path) -> None:
    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    path = write_lock_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"{}\n")
    issues = audit_canonical_storage(tmp_path)
    assert any(issue.code == "storage.lock.present" for issue in issues)
    assert path.exists()


def test_write_lock_clear_requires_exact_inspected_fingerprint(tmp_path: Path) -> None:
    from vitrine.storage import (
        VitrineStorageConflictError,
        clear_write_lock,
        inspect_write_lock,
    )

    graph = make_improvement_graph()
    commit_record_batch(tmp_path, flatten_graph(graph), expected_state_revision=None)
    path = write_lock_path(tmp_path)
    path.write_bytes(b"{}\n")
    first = inspect_write_lock(tmp_path)
    path.write_bytes(b'{"changed": true}\n')

    try:
        clear_write_lock(tmp_path, expected_sha256=first.sha256)
    except VitrineStorageConflictError:
        pass
    else:
        raise AssertionError("changed lock was cleared with a stale fingerprint")

    current = inspect_write_lock(tmp_path)
    clear_write_lock(tmp_path, expected_sha256=current.sha256)
    assert not path.exists()
