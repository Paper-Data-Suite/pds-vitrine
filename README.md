# pds-vitrine

A local-first portfolio module for curating authorized student work, preserving
provenance, and producing purpose-specific, immutable portfolio snapshots.

## Current status

Vitrine has entered v0.2.0 implementation after completing its audited v0.1.0
foundation with a `ready_for_implementation` verdict. The repository now provides
an installable, strictly typed package baseline at development version
`0.2.0.dev0`, a minimal teacher-facing menu, thin Core-owned workspace wrappers,
tests, packaging, CI, and release-validation tooling.

The package can currently:

- install as `pds-vitrine`;
- import as `vitrine`;
- report help and version through `vitrine` and `python -m vitrine`;
- launch a minimal teacher-facing menu; and
- show, set, validate/create, and reset the shared Core workspace.

It cannot yet create a Portfolio, identify or link a Portfolio Subject, bind a
Profile, discover Candidates, read producer artifacts, select or arrange work,
persist Vitrine records, build a Snapshot, issue or export a Portfolio, authorize
recipients, or perform regulated workflows.

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

Bare `vitrine` launches the teacher-facing menu. Help, version, imports, parser
construction, `workspace show`, and immediate menu exit are side-effect-free.

Vitrine declares no `paper_data_suite.modules` routing entry point and no
`paper_data_suite.publication_producers` entry point. It is neither a PDS2 page
handler nor an academic-result producer in this milestone.

## Validation

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

Cross-platform form:

```text
python scripts/validate_repository.py --core-wheel <wheel>
```

See [Package Foundation](docs/development/package-foundation.md) and the
[Synthetic Data Policy](docs/development/synthetic-data.md).

## Documentation

Documentation is indexed in [`docs/README.md`](docs/README.md).

Key entry points:

- [Package foundation](docs/development/package-foundation.md)
- [Synthetic data policy](docs/development/synthetic-data.md)
- [Portfolio-purpose research](docs/research/portfolio-purpose-workflows.md)
- [Module boundaries and authority](docs/architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](docs/design/portfolio-subject-identity.md)
- [Versioned Portfolio Profiles](docs/design/portfolio-profile-contract.md)
- [Candidate and source-reference contract](docs/design/candidate-source-reference-contract.md)
- [Producer artifact exposure boundaries](docs/design/producer-artifact-exposure-boundaries.md)
- [Selection, ordering, annotation, and reflection records](docs/design/selection-curation-records.md)
- [Snapshot, export, checksum, and immutability contracts](docs/design/snapshot-export-immutability-contracts.md)
- [Privacy, redaction, and audience controls](docs/design/privacy-redaction-audience-controls.md)
- [Regulated Portfolio and compliance profiles](docs/design/regulated-portfolio-compliance-profiles.md)
- [Representative synthetic Portfolio corpus](docs/examples/representative-synthetic-portfolios.md)
- [Portfolio foundation audit](docs/audits/portfolio-foundation-audit.md)
- [Portfolio foundation traceability](docs/audits/portfolio-foundation-traceability.md)
- [Architecture Decision Records](docs/decisions/README.md)
