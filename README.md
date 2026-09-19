# pds-vitrine

A local-first portfolio module for curating authorized student work, preserving
provenance, and producing purpose-specific, immutable portfolio snapshots.

## Current status

Vitrine is in **v0.3.0 release preparation**. The merged implementation consumes
released ScoreForm 0.11.0, Quillan 0.10.0, and Concord 0.3.0 evidence through public
producer boundaries while keeping `pds-core>=0.6.3,<0.7` as Vitrine's only
unconditional runtime dependency.

The source release identity is `0.3.0` during issue #72 preparation. That does not
mean a `v0.3.0` GitHub Release has already been published; exact-main qualification,
artifact hashing/publication, and fresh-download verification remain separate gates.

The v0.3.0 teacher-local workflow provides:

- exact Core-backed Portfolio Subject identity and cross-class linking;
- packaged Improvement and Showcase starter Profiles;
- released ScoreForm/Quillan/Concord Candidate discovery through exact semantic
  adapter support and authorization-gated public producer readers;
- a suppression-safe Candidate inbox and bounded compatibility/readiness diagnostics;
- guided Create Portfolio for Student setup;
- explicit Candidate review, Selection, Placement, Annotation, Reflection, and
  Curation Review workflows;
- exact Working Portfolio Composition preparation/freeze;
- authorized immutable Snapshot Edition construction and verified local
  `directory_package` Export;
- bounded Vitrine attention/next-action summaries; and
- Core `paper_data_suite.module_operations` integration for suite
  doctor/launcher/backup/attention workflows.

Development fixture producers/adapters remain explicit opt-in test infrastructure and
cannot masquerade as the released live integrations.

The authority boundaries remain deliberate:

```text
Candidate != Selection
Selection != Placement
actor attribution != authorization
Selection != Snapshot build authority
Snapshot build authority != disclosure authorization
Audience Context != recipient identity / relationship / consent
local Export != external delivery
```

ScoreForm attempts remain separate attempts; Vitrine does not choose the latest,
highest, best, official, Grade-bearing, or proficiency-bearing attempt. Quillan and
Concord copied Artifact bytes require a separate producer Artifact authorization.
ScoreForm Snapshot evidence remains `reference_only`.

Vitrine persists its own canonical metadata beneath `<workspace>/vitrine/` and guards
Snapshot custody beneath `<workspace>/vitrine/snapshots/`. Sealed Edition and Export
verification is producer-independent after custody is established.

Vitrine v0.3.0 does not implement production institutional authentication,
recipient/guardian verification, consent management, production
redaction/de-identification, disclosure authorization, secure delivery, public
hosting, or external submission.

## Requirements and installation

```text
Python >=3.11
pds-core>=0.6.3,<0.7
```

Core v0.6.3 is distributed through its GitHub Release rather than PyPI. Install
the authenticated Core wheel first:

```powershell
python scripts\verify_core_wheel.py .\pds_core-0.6.3-py3-none-any.whl
python -m pip install .\pds_core-0.6.3-py3-none-any.whl
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
vitrine attention list [--portfolio-id PORTFOLIO_ID]
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
`paper_data_suite.publication_producers` entry point. It declares the Core
`paper_data_suite.module_operations` provider
`vitrine = vitrine.pds_operations:get_module_operations_profile` and adds no
runtime dependency on ScoreForm, Quillan, Concord, Portia, or Meridian.

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
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.3-py3-none-any.whl
```

Cross-platform form:

```text
python scripts/validate_repository.py --core-wheel <wheel>
```

The complete gate authenticates Core; runs pytest, Ruff, strict Mypy, runtime and
workflow validators including the narrow v0.2.0 release-contract gate; validates
documentation and representative fixtures; builds distributions; checks
Twine/package contents; runs the installed-wheel smokes once each;
runs the combined installed end-to-end acceptance exactly once; and verifies
repository cleanliness.

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

- [v0.2.0 release notes](RELEASE_NOTES_v0.2.0.md)
- [v0.2.0 release audit](docs/v0.2.0-release-audit.md)
- [v0.2.0 release compatibility](docs/v0.2.0-release-compatibility.md)
- [Release checklist](docs/release_checklist.md)
- [Foundational runtime models](docs/contracts/foundational-runtime-models-v1.md)
- [Canonical storage](docs/contracts/canonical-storage-v1.md)
- [Portfolio Subject workflows](docs/contracts/portfolio-subject-workflows-v1.md)
- [Portfolio Profile workflows](docs/contracts/portfolio-profile-workflows-v1.md)
- [Producer projection adapter boundary](docs/contracts/producer-projection-adapters-v1.md)
- [Candidate discovery and evaluation](docs/contracts/candidate-discovery-evaluation-v1.md)
- [Curation workflows](docs/contracts/curation-workflows-v1.md)
- [Snapshot build workflows](docs/contracts/snapshot-build-workflows-v1.md)
- [Attention and Next Actions](docs/contracts/attention-next-actions-v1.md)
- [Runtime-model development](docs/development/runtime-models.md)
- [Producer-adapter development](docs/development/producer-adapters.md)
- [Candidate-discovery development](docs/development/candidate-discovery.md)
- [Curation-workflow development](docs/development/curation-workflows.md)
- [Snapshot-build development](docs/development/snapshot-build-workflows.md)
- [Attention and Next Actions development](docs/development/attention-next-actions.md)
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
