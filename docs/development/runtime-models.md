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

Use `VitrineModelValidationError` for structurally invalid foundational values.

Issue #32 transient adapter values live in `vitrine.producer_adapters` rather than
becoming required `VitrineRecordGraph` collections. This preserves the exact
foundational graph wire shape and fixture bytes.

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
python scripts\validate_producer_adapters.py
python scripts\validate_candidate_discovery.py
```

The runtime-model validator checks exact improvement/showcase foundational
fixtures. The producer-adapter validator separately exercises strict synthetic
ScoreForm-, Quillan-, and Concord-shaped bytes without changing the foundational
fixture hashes.

## Focused tests

```powershell
python -m pytest `
  tests\test_runtime_models.py `
  tests\test_runtime_serialization.py `
  tests\test_runtime_graph.py `
  tests\test_validate_runtime_models.py `
  tests\test_producer_adapters.py `
  tests\test_adapter_cli.py `
  tests\test_validate_producer_adapters.py `
  -q
```

## Full validation

Install the authenticated Core wheel and run:

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

The repository gate runs runtime/workflow fixture validation before
documentation, foundation, build, distribution, and installed-wheel checks.

## Package boundary

The built wheel includes `vitrine.models`, the producer-adapter interfaces,
explicit development-adapter implementations, CLI diagnostics, and `py.typed`.
Synthetic producer JSON fixtures, development scripts, tests, and documentation
remain source-distribution assets. Core remains the only runtime dependency.

Issue #32 adds a separate isolated installed-wheel adapter smoke. Issue #33 adds
a Candidate-service smoke proving Candidate imports remain side-effect-free,
ordinary registries remain fixture-free, and ScoreForm, Quillan, Concord, and
Meridian need not be installed.

## Persistence boundary

Canonical persistence lives under `vitrine.storage`. Producer adapter
declarations, registries, reader models, and projection batches are transient
integration configuration/observations and are not persisted merely by
construction or selection.

## Portfolio Subject identity history

Issue #30 adds canonical identity-history records that use the same strict record
conversion APIs but are intentionally not required `VitrineRecordGraph`
collections.

Use `vitrine.identity_state` to project and validate this history. Do not add
mutable status fields to foundational Subject/link records for UI convenience.

## Profile supplemental records

Issue #31 adds canonical `PortfolioProfileRequirement`,
`PortfolioProfileLifecycleEvent`, `PortfolioProfileOverlayRevision`,
`PortfolioProfileComposition`, and `PortfolioProfileMigration` records without
changing the required `VitrineRecordGraph` JSON shape or existing fixture bytes.

## Producer adapter boundary

Issue #32 adds transient exact support requests/keys, adapter declarations,
reader descriptors, deterministic registry selection, projection batches, and
producer-native transient relationships. See
[`producer-adapters.md`](producer-adapters.md) for implementation guidance.

## Candidate discovery boundary

Issue #33 persists the existing `CandidateEvaluation` and `PortfolioCandidate`
models without changing foundational wire shapes. Producer projection fields
remain transient in `CandidateEvaluationResult`; canonical Candidate endpoints
preserve exact source identity, Artifact/representation, relationship, privacy,
and Core provenance. See [`candidate-discovery.md`](candidate-discovery.md).
