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
- explicit Proposal/Decision/Selection provenance, append-preserving Selection and Placement lifecycle, complete section Arrangements, and conflict-aware current pointers;
- revisioned curator Annotation, student Reflection, exact Curation Review Decisions, Selection replacement/withdrawal history, and immutable byte-free Working Portfolio Composition revisions;
- immutable Snapshot Series/Request/Plan/Attempt workflows with exact source-provider and deterministic renderer boundaries;
- guarded Snapshot staging, Series build locks, independent source/output hashing, explicit Omissions, deterministic Manifests, Seals, and immutable Editions;
- producer-independent Edition verification, independently verified directory Export Artifacts, explicit current-Edition pointers, and explicit recovery inspection;
- an executable representative improvement Portfolio slice spanning exact cross-class identity, Profile-governed Candidate discovery, explicit curation, student Reflection, immutable Composition, four-entry Snapshot/Export custody, and producer-source drift proof;
- an executable representative showcase Portfolio slice preserving Concord-shaped Group, Author, Subject, contribution, Score-target, and collaborator-treatment semantics through a five-entry audience-safe Edition and reproducible directory Export;
- Portfolio-centered direct command families and a low-density teacher menu, all backed by shared application services;
- strict testing, typing, packaging, and cross-platform CI gates.

The foundational runtime models cover Portfolio and Subject identity,
class-qualified Subject links, Profile revisions and Bindings, source provenance,
Candidate Evaluations, Candidates, Selections, Placements, Arrangements,
Composition Revisions, Audience Contexts, and foundational Snapshot metadata.
Issue #34 adds richer curation workflow/history records without changing the
frozen #28 Selection, Placement, Arrangement, Composition, or graph wire shapes.
Issue #35 likewise reuses the frozen #28 Snapshot Materialization, Entry,
Omission, Manifest, Seal, and Edition wire shapes while adding immutable build
history and executable byte custody.

Vitrine persists its own canonical metadata beneath `<workspace>/vitrine/`.
Snapshot bytes are separately guarded beneath `<workspace>/vitrine/snapshots/`.
Producer adapters remain transient and side-effect free. Candidate discovery,
working-Portfolio curation, and Snapshot construction use explicit application
services and guarded persistence.

Issue #32's producer adapters are development fixtures only:

```text
development fixture adapter
!= installed producer integration
!= producer publication support
!= source authorization
!= Candidate eligibility
```

Vitrine still does not provide live ScoreForm, Quillan, or Concord ingestion.

Issue #33 provides the first fixture-backed Core-to-Vitrine Candidate pipeline.
It uses the Core catalog only for bounded discovery, reloads canonical
Publication and registration state, requires explicit source-read authorization,
verifies exact manifest bytes, resolves exact Portfolio Subject relationships,
and persists immutable Evaluations/Candidates.

Issue #34 consumes those positive Candidates through explicit byte-free
curation:

```text
Candidate
  -> Proposal
  -> Decision
  -> Selection
  -> Placement
  -> Arrangement
  -> Annotation / Reflection / Review
  -> Working Portfolio Composition Revision
```

Candidate eligibility does not imply Selection. Selection does not imply grading
policy or disclosure permission. Reflection does not establish proficiency or
prove improvement. Composition contains no producer bytes and is not a Snapshot.

Issue #35 consumes exactly one immutable Composition plus its exact Inventory and
Audience Context:

```text
exact Composition
  -> Snapshot Build Request
  -> immutable Plan
  -> Attempt
  -> exact source copy / deterministic render
  -> Entries / explicit Omissions
  -> deterministic internal Manifest
  -> Seal
  -> immutable Edition
  -> verified directory Export Artifact
```

The Plan never silently follows a successor Candidate, Publication, producer
revision, Placement, Reflection, or Composition. Snapshot build authority permits
local custody only and is not recipient/disclosure authorization. Historical
Edition and Export verification require only Vitrine canonical state and
Vitrine-owned sealed bytes, not the original producer.

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
vitrine portfolio --help
vitrine candidate --help
vitrine selection --help
vitrine arrangement --help
vitrine composition --help
vitrine audience --help
vitrine snapshot --help
vitrine adapters list
vitrine adapters list --include-development-fixtures
vitrine adapters show <adapter_id> --include-development-fixtures
vitrine workspace show [--workspace-root PATH]
vitrine workspace set PATH
vitrine workspace validate [--workspace-root PATH]
vitrine workspace reset
python -m vitrine ...
```

Bare `vitrine` launches the low-density, Portfolio-centered teacher menu.
Direct commands are noninteractive and preserve the same service, authority,
and optimistic-concurrency boundaries. See
[teacher-facing and direct workflows](docs/development/interface-workflows.md).

Vitrine declares no `paper_data_suite.modules` routing entry point and no
`paper_data_suite.publication_producers` entry point. It adds no runtime
dependency on ScoreForm, Quillan, Concord, Portia, or Meridian.

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

Snapshot application services are separate from curation:

```python
from vitrine.snapshot_services import (
    create_snapshot_series,
    request_snapshot_build,
    plan_snapshot_build,
    start_snapshot_build_attempt,
    execute_snapshot_build_attempt,
    seal_snapshot_build_attempt,
)
from vitrine.snapshot_distribution import (
    create_snapshot_directory_export,
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
```

## Validation

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

Cross-platform form:

```text
python scripts/validate_repository.py --core-wheel <wheel>
```

The complete gate authenticates Core; runs pytest, Ruff, strict Mypy, runtime and
workflow validators including producer-adapter, Candidate-discovery, curation,
and immutable Snapshot workflow validation; validates documentation and
representative fixtures; builds distributions; checks Twine/package contents;
runs isolated installed-wheel smoke tests including Snapshot imports; and
verifies repository cleanliness.

The dedicated Snapshot acceptance validator can also be run directly:

```text
python scripts/validate_snapshot_workflows.py
```

The complete representative improvement slice has its own validator:

```text
python scripts/validate_improvement_portfolio.py
```

The complete representative showcase slice has its own validator:

```text
python scripts/validate_showcase_portfolio.py
```

## Documentation

Documentation is indexed in [`docs/README.md`](docs/README.md).

Key entry points:

- [Foundational runtime models](docs/contracts/foundational-runtime-models-v1.md)
- [Canonical storage](docs/contracts/canonical-storage-v1.md)
- [Portfolio Subject workflows](docs/contracts/portfolio-subject-workflows-v1.md)
- [Portfolio Profile workflows](docs/contracts/portfolio-profile-workflows-v1.md)
- [Producer projection adapter boundary](docs/contracts/producer-projection-adapters-v1.md)
- [Candidate discovery and evaluation](docs/contracts/candidate-discovery-evaluation-v1.md)
- [Curation workflows](docs/contracts/curation-workflows-v1.md)
- [Snapshot build workflows](docs/contracts/snapshot-build-workflows-v1.md)
- [Runtime-model development](docs/development/runtime-models.md)
- [Producer-adapter development](docs/development/producer-adapters.md)
- [Candidate-discovery development](docs/development/candidate-discovery.md)
- [Curation-workflow development](docs/development/curation-workflows.md)
- [Snapshot-build development](docs/development/snapshot-build-workflows.md)
- [Executable improvement Portfolio slice](docs/development/improvement-portfolio-vertical-slice.md)
- [Executable showcase Portfolio slice](docs/development/showcase-portfolio-vertical-slice.md)
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
