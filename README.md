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
- strict testing, typing, packaging, and cross-platform CI gates.

The runtime models cover Portfolio and Subject identity, class-qualified Subject
links, Profile revisions and Bindings, source provenance, Candidate Evaluations,
Candidates, Selections, Placements, Arrangements, Composition Revisions,
Audience Contexts, and foundational Snapshot metadata.

The model layer remains side-effect free. Vitrine now persists its own metadata
beneath `<workspace>/vitrine/` with immutable record/state history, an explicit
current pointer, optimistic concurrency, and a disposable derived catalog. It
still cannot parse live producer manifests, discover Candidates, run curation
workflows, copy source bytes, build Snapshot packages, authorize recipients, or
export and deliver portfolios.

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
vitrine workspace show [--workspace-root PATH]
vitrine workspace set PATH
vitrine workspace validate [--workspace-root PATH]
vitrine workspace reset
python -m vitrine ...
```

No Portfolio editing command is added by the foundational model issue. Bare
`vitrine` still launches the minimal teacher-facing menu.

Vitrine declares no `paper_data_suite.modules` routing entry point and no
`paper_data_suite.publication_producers` entry point.

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

See the [foundational runtime contract](docs/contracts/foundational-runtime-models-v1.md),
[canonical storage contract](docs/contracts/canonical-storage-v1.md), and
[canonical storage development guide](docs/development/canonical-storage.md).

## Validation

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

Cross-platform form:

```text
python scripts/validate_repository.py --core-wheel <wheel>
```

The complete gate authenticates Core, runs pytest, Ruff, strict Mypy,
documentation and fixture validators, builds distributions, checks Twine and
package contents, runs an isolated installed-wheel smoke test, and verifies
repository cleanliness.

## Documentation

Documentation is indexed in [`docs/README.md`](docs/README.md).

Key entry points:

- [Foundational runtime models](docs/contracts/foundational-runtime-models-v1.md)
- [Canonical storage](docs/contracts/canonical-storage-v1.md)
- [Runtime-model development](docs/development/runtime-models.md)
- [Canonical-storage development](docs/development/canonical-storage.md)
- [Package foundation](docs/development/package-foundation.md)
- [Synthetic data policy](docs/development/synthetic-data.md)
- [Module boundaries and authority](docs/architecture/module-boundaries.md)
- [Portfolio Subject identity](docs/design/portfolio-subject-identity.md)
- [Versioned Portfolio Profiles](docs/design/portfolio-profile-contract.md)
- [Candidate and source references](docs/design/candidate-source-reference-contract.md)
- [Selection and curation](docs/design/selection-curation-records.md)
- [Snapshot and immutability contracts](docs/design/snapshot-export-immutability-contracts.md)
- [Privacy and audience controls](docs/design/privacy-redaction-audience-controls.md)
- [Representative synthetic Portfolio corpus](docs/examples/representative-synthetic-portfolios.md)
- [Architecture Decision Records](docs/decisions/README.md)
