# Vitrine Package Foundation

- **Issue:** #27
- **Milestone:** v0.2.0 — Runtime Foundations and Fixture-Backed Portfolio Slice
- **Package version:** `0.2.0.dev0`

## Package identities

```text
Distribution: pds-vitrine
Import:       vitrine
Command:      vitrine
Module ID:    vitrine
Python:       >=3.11
Core:         pds-core>=0.6,<0.7
```

Build metadata, `vitrine.__version__`, the command, and installed metadata use
one authoritative package version.

## Current implementation

The package provides:

- help, version, and a minimal teacher menu;
- Core-owned workspace show, set, validate, and reset operations;
- immutable foundational Portfolio runtime models;
- exact mapping conversion and canonical JSON;
- pure deterministic graph validation;
- canonical improvement and showcase model fixtures;
- workspace-scoped canonical storage, guarded commits, strict historical/current loading, and a rebuildable SQLite catalog;
- package, typing, test, documentation, and installed-wheel validation.

The model contract is documented in
[Foundational Runtime Models v1](../contracts/foundational-runtime-models-v1.md).
Persistence authority is documented in
[Canonical Storage v1](../contracts/canonical-storage-v1.md).

## Command surface

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

No model editing workflow is exposed through the CLI in issue #28.

## Core ownership

Vitrine delegates workspace, identifier, school-year, class, roster, routing
reference, and academic-registry contracts to released Core public APIs. It
creates no parallel Core configuration or shared identity model.

Vitrine declares neither `paper_data_suite.modules` nor
`paper_data_suite.publication_producers`.

## Development installation

Install the authenticated Core 0.6.0 release wheel before Vitrine:

```powershell
python scripts\verify_core_wheel.py .\pds_core-0.6.0-py3-none-any.whl
python -m pip install .\pds_core-0.6.0-py3-none-any.whl
python -m pip install -e ".[dev]"
python -m pip check
```

## Validation

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

The complete gate authenticates Core, runs pytest, Ruff, strict Mypy, canonical
runtime fixtures, canonical-storage validation, documentation and foundation validators, builds both
distributions, runs Twine and content checks, performs isolated installed-wheel
smoke testing, and confirms repository hygiene.

## Deferred behavior

Vitrine now persists Vitrine-owned runtime metadata and selects current state
through its own explicit pointer. It does not query the Core catalog, parse
producer manifests, discover Candidates, execute Selection or Placement
workflows, copy source bytes, build Snapshot packages, authorize disclosure,
export, or deliver portfolios.
