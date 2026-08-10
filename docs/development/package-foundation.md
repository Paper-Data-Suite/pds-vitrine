# Vitrine Package Foundation

- **Issue:** #27 baseline, extended through issue #32
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

The installed package provides:

- help, version, and the low-density teacher menu;
- Core-owned workspace show, set, validate, and reset operations;
- immutable foundational Portfolio runtime models;
- exact mapping conversion and canonical JSON;
- pure deterministic graph validation;
- workspace-scoped canonical storage, guarded commits, strict historical/current loading, and a rebuildable SQLite catalog;
- Portfolio Subject and versioned Profile application services;
- exact producer-adapter support/declaration/projection interfaces;
- explicit development-only ScoreForm-, Quillan-, and Concord-shaped adapter implementations;
- non-mutating adapter CLI diagnostics;
- Core-backed fixture Candidate discovery/evaluation application services;
- explicit development Core producer compatibility Profiles for the #32 fixture identities;
- package, typing, test, documentation, distribution, and installed-wheel validation.

The exact contracts are documented under `docs/contracts/`, including
[Producer Projection Adapter Boundary v1](../contracts/producer-projection-adapters-v1.md) and
[Candidate Discovery and Evaluation v1](../contracts/candidate-discovery-evaluation-v1.md).

## Command surface

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

Adapter diagnostics are deliberately direct/power-user commands. No ordinary
teacher-facing adapter-management menu is added by issue #32.

## Core ownership

Vitrine delegates workspace, identifier, school-year, class, roster, routing
reference, and academic-registry contracts to released Core public APIs. It
creates no parallel Core configuration or shared identity model.

Vitrine declares neither `paper_data_suite.modules` nor
`paper_data_suite.publication_producers`.

## Producer dependency boundary

Core remains Vitrine's only runtime dependency. Issues #32-#33 do not add
ScoreForm, Quillan, Concord, or Meridian to `Requires-Dist`, and ordinary
adapter/Candidate service construction does not discover or import installed
producer packages.

The wheel contains the adapter interfaces and explicit fixture adapter code so
that diagnostics can describe those development contracts. Synthetic fixture
JSON stays outside the wheel under `fixtures/producer-adapters/` in the repository
and source distribution.

```text
development fixture adapter
!= installed producer integration
!= producer publication support
```

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

The complete gate authenticates Core, runs pytest, Ruff, strict Mypy, runtime,
storage, Subject, Profile, producer-adapter, and Candidate-discovery validators, validates
documentation and representative fixtures, builds both distributions, runs Twine
and content checks, performs general, adapter-specific, and Candidate-service isolated installed-wheel
smoke tests, and confirms repository hygiene.

The adapter-specific smoke installs only Core and Vitrine, proves the default
registry is empty, proves fixture listing requires explicit opt-in, and verifies
that importing Vitrine does not require ScoreForm, Quillan, or Concord.

## Candidate discovery boundary

Issue #33 implements the fixture-backed Core-to-Vitrine Candidate orchestration.
The service is import-side-effect-free, requires explicit producer/adapter
registries and authorization, and writes only Candidate Evaluation/Candidate
records through guarded Vitrine persistence. Development fixture Core Profiles
remain explicit and do not establish live sibling support.

## Deferred behavior

Vitrine does not yet provide live producer-reader integration, Selection/Placement
workflows, source-byte copying, Snapshot construction, disclosure authorization,
export, or delivery.
