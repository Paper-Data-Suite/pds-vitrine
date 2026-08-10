# pds-vitrine

A local-first portfolio module for curating authorized student work, preserving
provenance, and producing purpose-specific, immutable portfolio snapshots.

## Current status

Vitrine is implementing its v0.2.0 runtime foundation after completing an
audited v0.1.0 architecture and fixture foundation. The package remains at
`0.2.0.dev0` and now provides:

- the installable `pds-vitrine` distribution and `vitrine` command;
- released Core 0.6 workspace integration;
- immutable foundational runtime models;
- exact mapping and canonical JSON conversion;
- deterministic cross-record validation;
- canonical synthetic improvement and showcase record graphs;
- workspace-scoped canonical JSON persistence with guarded state revisions;
- strict historical/current loading and deterministic storage diagnostics;
- a rebuildable nonauthoritative SQLite catalog;
- Portfolio Subject creation, exact cross-class linking, correction, merge, and split workflows;
- versioned improvement/showcase Profile services with explicit activation, Binding, overlays, and migration;
- an exact producer projection adapter boundary with deterministic conflict detection;
- explicit ScoreForm-, Quillan-, and Concord-shaped development fixture adapters;
- non-mutating `vitrine adapters` diagnostics that hide fixtures by default;
- fixture-backed Core catalog discovery, canonical verification, authorization-gated producer reading, and guarded Candidate Evaluation/Candidate persistence;
- direct `vitrine subject` and `vitrine profile` command families plus low-density teacher menus;
- strict testing, typing, packaging, and cross-platform CI gates.

The runtime models cover Portfolio and Subject identity, class-qualified Subject
links, Profile revisions and Bindings, source provenance, Candidate Evaluations,
Candidates, Selections, Placements, Arrangements, Composition Revisions,
Audience Contexts, and foundational Snapshot metadata.

Vitrine persists its own canonical metadata beneath `<workspace>/vitrine/`. The
producer-adapter layer is transient and side-effect free: it does not perform Core
catalog discovery, authorization, manifest path/digest verification, Portfolio
Subject resolution, Candidate evaluation, curation, Snapshot construction, or
recipient disclosure.

Issue #32's producer adapters are development fixtures only:

```text
development fixture adapter
!= installed producer integration
!= producer publication support
!= source authorization
!= Candidate eligibility
```

Vitrine still does not provide live ScoreForm, Quillan, or Concord ingestion.

Issue #33 adds the first fixture-backed Core-to-Vitrine Candidate pipeline. It
uses the Core catalog only for bounded discovery, reloads canonical Publication
and registration state, requires explicit source-read authorization before
manifest access, verifies the exact manifest bytes, invokes the #32 reader and
adapter, resolves exact Portfolio Subject relationships, evaluates the bound
Profile, and persists immutable Evaluations/Candidates. It creates no Selection.

## Requirements and installation

```text
Python >=3.11
pds-core>=0.6,<0.7
```

Core v0.6.0 is distributed through its GitHub Release rather than PyPI. Install
the authenticated Core wheel first:

```powershell
python scripts\verify_core_wheel.py .\pds_core-0.6.0-py3-none-any.whl
python -m pip install .\pds_core-0.6.0-py3-none-any.whl
python -m pip install -e ".[dev]"
python -m pip check
```

## Commands

```text
vitrine
vitrine menu
vitrine --help
vitrine --version
vitrine subject --help
vitrine profile --help
vitrine adapters list
vitrine adapters list --include-development-fixtures
vitrine adapters show <adapter_id> --include-development-fixtures
vitrine workspace show [--workspace-root PATH]
vitrine workspace set PATH
vitrine workspace validate [--workspace-root PATH]
vitrine workspace reset
python -m vitrine ...
```

Bare `vitrine` launches the low-density teacher-facing menu. Adapter diagnostics
are intentionally direct CLI infrastructure and are not exposed as teacher-facing
adapter choices.

Vitrine declares no `paper_data_suite.modules` routing entry point and no
`paper_data_suite.publication_producers` entry point. It adds no runtime
dependency on ScoreForm, Quillan, Concord, or Meridian.

## Runtime model example

```python
from vitrine.models import (
    Portfolio,
    PortfolioSubject,
    VitrineRecordGraph,
    graph_to_canonical_json_bytes,
    validate_record_graph,
)
```

Producer-adapter selection is separate:

```python
from vitrine.producer_adapters import build_adapter_registry

registry = build_adapter_registry()
assert registry.adapters == ()
```

Development fixtures require explicit opt-in through
`vitrine.development_adapters`.

## Validation

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

Cross-platform form:

```text
python scripts/validate_repository.py --core-wheel <wheel>
```

The complete gate authenticates Core, runs pytest, Ruff, strict Mypy, runtime and
workflow validators including the producer-adapter and Candidate-discovery validators, validates
documentation and representative fixtures, builds distributions, checks Twine
and package contents, runs isolated installed-wheel smoke tests, and verifies
repository cleanliness.

## Documentation

Documentation is indexed in [`docs/README.md`](docs/README.md).

Key entry points:

- [Foundational runtime models](docs/contracts/foundational-runtime-models-v1.md)
- [Canonical storage](docs/contracts/canonical-storage-v1.md)
- [Portfolio Subject workflows](docs/contracts/portfolio-subject-workflows-v1.md)
- [Portfolio Profile workflows](docs/contracts/portfolio-profile-workflows-v1.md)
- [Producer projection adapter boundary](docs/contracts/producer-projection-adapters-v1.md)
- [Candidate discovery and evaluation](docs/contracts/candidate-discovery-evaluation-v1.md)
- [Runtime-model development](docs/development/runtime-models.md)
- [Producer-adapter development](docs/development/producer-adapters.md)
- [Candidate-discovery development](docs/development/candidate-discovery.md)
- [Package foundation](docs/development/package-foundation.md)
- [Synthetic data policy](docs/development/synthetic-data.md)
- [Module boundaries and authority](docs/architecture/module-boundaries.md)
- [Candidate and source references](docs/design/candidate-source-reference-contract.md)
- [Producer Artifact exposure](docs/design/producer-artifact-exposure-boundaries.md)
- [Selection and curation](docs/design/selection-curation-records.md)
- [Snapshot and immutability contracts](docs/design/snapshot-export-immutability-contracts.md)
- [Privacy and audience controls](docs/design/privacy-redaction-audience-controls.md)
- [Representative synthetic Portfolio corpus](docs/examples/representative-synthetic-portfolios.md)
- [Architecture Decision Records](docs/decisions/README.md)
