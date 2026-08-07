# Canonical Storage Development Guide

Vitrine canonical storage is available from:

```python
from vitrine.storage import ...
```

It persists the immutable `vitrine.models` records beneath one existing Core
workspace. It does not create a workspace implicitly.

## Bootstrap

```python
from vitrine.storage import commit_record_batch

result = commit_record_batch(
    workspace_root,
    records,
    expected_state_revision=None,
)
```

The complete candidate graph must pass existing runtime graph validation.

## Later commits

```python
result = commit_record_batch(
    workspace_root,
    new_records,
    expected_state_revision=current_revision,
)
```

A stale expected revision raises `VitrineStorageConflictError`. Exact replay at
the correct expected revision returns `no_op=True` without advancing state.
Existing semantic keys cannot be rewritten with different bodies.

## Reads

```python
from vitrine.storage import (
    load_current_record_graph,
    load_state_revision,
)

current = load_current_record_graph(workspace_root)
historical_state, digest, historical_graph = load_state_revision(workspace_root, 1)
```

Current and historical reads use canonical JSON only. They do not require or
create SQLite.

## Audit

```python
from vitrine.storage import audit_canonical_storage

issues = audit_canonical_storage(workspace_root)
```

The audit is read-only. Do not treat an audit failure as permission to repair or
select another revision automatically.

## Derived catalog

```python
from vitrine.storage import rebuild_catalog, query_catalog_records

rebuild_catalog(workspace_root)
rows = query_catalog_records(workspace_root, state="current")
```

Catalog rows are discovery metadata, not canonical authority. A missing, stale,
incompatible, or corrupt catalog must be rebuilt explicitly after canonical state
validates.

## Locks

Ordinary commits and catalog rebuilds use separate exclusive locks.

```python
from vitrine.storage import inspect_write_lock, clear_write_lock

inspection = inspect_write_lock(workspace_root)
clear_write_lock(workspace_root, expected_sha256=inspection.sha256)
```

Clearing is a recovery primitive. Do not clear a lock based on age alone.

## Validation

Focused persistence validation:

```powershell
python scripts\validate_canonical_storage.py
```

Focused tests:

```powershell
python -m pytest `
  tests\test_storage_models.py `
  tests\test_storage_paths.py `
  tests\test_storage_commits.py `
  tests\test_storage_reads.py `
  tests\test_storage_catalog.py `
  tests\test_storage_diagnostics.py `
  -q
```

Complete repository validation remains:

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

All persistence tests and validation scripts use disposable workspaces and must
leave the configured user workspace untouched.
