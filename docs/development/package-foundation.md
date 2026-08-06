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

The package uses one authoritative Python version declaration. Build metadata,
`vitrine.__version__`, the command, and installed metadata must agree.

## Current command surface

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

Bare `vitrine` launches a small teacher menu. The only available workflow is
Workspace Settings. No disabled Portfolio commands are shown.

## Core ownership

Vitrine delegates workspace resolution, creation, validation, saved preference,
identifier rules, class/roster contracts, and academic-registry contracts to
released Core public APIs. It creates no parallel workspace configuration.

The resolution order remains:

```text
explicit runtime root
  -> PDS_WORKSPACE_ROOT
  -> saved Core preference
  -> Core default
```

`workspace show` is read-only. `workspace validate` may create the resolved root
but does not save it. `workspace set` validates/creates and saves. `workspace
reset` clears only the preference and deletes no workspace files.

Vitrine declares neither `paper_data_suite.modules` nor
`paper_data_suite.publication_producers`. It is not a PDS2 route handler or an
academic-result producer in this milestone.

## Development installation

Core 0.6.0 is distributed as a GitHub Release wheel rather than from PyPI.
Install the authenticated Core wheel before Vitrine:

```powershell
python scripts\verify_core_wheel.py .\pds_core-0.6.0-py3-none-any.whl
python -m pip install .\pds_core-0.6.0-py3-none-any.whl
python -m pip install -e ".[dev]"
python -m pip check
vitrine --version
vitrine --help
```

The official baseline wheel SHA-256 is recorded in
`scripts/verify_core_wheel.py` and must be revalidated against the release
artifact when the baseline changes.

## Validation

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

Cross-platform form:

```text
python scripts/validate_repository.py --core-wheel <wheel>
```

Use `--allow-dirty` only during development. Complete validation authenticates
Core, runs tests, Ruff, strict Mypy, documentation and foundation validators,
builds distributions, runs Twine and wheel-content checks, performs an isolated
wheel smoke test, and confirms repository hygiene.

## Deferred behavior

The package does not yet create Portfolios or Subjects, bind Profiles, discover
or parse producer publications, create Candidates or Selections, persist Vitrine
records, build Snapshots, authorize recipients, or perform regulated workflows.
Those capabilities remain assigned to later v0.2.0 issues.
