# Runtime Model Development

Issue #28 implements Vitrine's side-effect-free foundational runtime layer.

## Imports

```python
from vitrine.models import (
    Portfolio,
    PortfolioSubject,
    VitrineRecordGraph,
    graph_from_json_bytes,
    graph_to_canonical_json_bytes,
    validate_record_graph,
)
```

The package root remains lightweight. Importing `vitrine.models` does not resolve
a workspace, discover producers, read manifests, or create files.

## Structural validation

Each frozen, slotted model validates local invariants during construction:

- Core-compatible identifiers;
- exact controlled values;
- positive non-Boolean revisions;
- aware timestamps;
- immutable ordered collections;
- conditional required and forbidden fields;
- safe relative paths;
- and lowercase SHA-256 values.

Use `VitrineModelValidationError` for structurally invalid values.

## Cross-record validation

Build a complete immutable `VitrineRecordGraph`, then call:

```python
issues = collect_record_graph_issues(graph)
validate_record_graph(graph)
```

The collector is useful for diagnostics and tests. The validator raises one
aggregate exception when issues exist. Neither function reads the filesystem.

## Exact serialization

```python
content = graph_to_canonical_json_bytes(graph)
loaded = graph_from_json_bytes(content)
assert graph_to_canonical_json_bytes(loaded) == content
```

The decoder is strict about UTF-8, duplicate keys, exact fields, and numeric
values. Canonical JSON uses sorted keys, two-space indentation, and one trailing
LF.

Do not use `dataclasses.asdict()` as a persistence contract.

## Fixture validation

```powershell
python scripts\validate_runtime_models.py
```

The validator checks the exact improvement and showcase fixture set, complete
graph validity, expected record counts, canonical byte equality, and fixture
SHA-256 output. It writes nothing.

## Focused tests

```powershell
python -m pytest `
  tests\test_runtime_models.py `
  tests\test_runtime_serialization.py `
  tests\test_runtime_graph.py `
  tests\test_validate_runtime_models.py `
  -q
```

## Full validation

Install the authenticated Core wheel and run:

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

The repository gate runs runtime-model fixture validation before documentation,
foundation, build, distribution, and installed-wheel checks.

## Package boundary

The built wheel includes `vitrine.models` and `py.typed`. Test fixtures,
development scripts, and documentation remain source-distribution assets. Core
remains the only runtime dependency.

The installed-wheel smoke test constructs and serializes a minimal Portfolio
graph, then exercises canonical Vitrine persistence in a disposable Core
workspace, including a guarded state advance, catalog rebuild/removal, and a
canonical reload without SQLite. It does not modify the installed package or
configured user workspace.

## Deferred implementation

Keep persistence out of the pure `vitrine.models` package. Canonical persistence
lives under `vitrine.storage`; producer imports, authorization, Snapshot byte
construction, export rendering, and teacher workflows remain later v0.2.0 work.
