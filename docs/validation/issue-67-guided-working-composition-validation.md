# Issue #67 guided Working Composition validation

This document records the reusable qualification surface for issue #67.

## Contract under test

```text
vitrine_guided_working_composition_v1
```

The implementation must preserve:

```text
preparation != Composition
Composition != Audience Context
Composition != Snapshot
coherent != approved
coherent_with_unresolved_obligations != invalid
stale source != automatically invalid
teacher confirmation != obligation cleared
```

## Focused acceptance

The issue-focused suite covers:

- one shared Composition derivation for preview and writes;
- read-only preparation;
- exact Profile section and Arrangement Placement ordering;
- explicit unplaced active Selections;
- structured Requirement explanation without prose inference;
- bounded Core Publication current-use observations;
- exact Review applicability;
- audience-rule explanation without Audience Context creation;
- deterministic preparation fingerprints;
- fail-closed Vitrine state/pointer/source/fingerprint checks;
- denied/unresolved authority write isolation;
- exact semantic replay;
- teacher menu routing and confirmation;
- task-level prepared CLI with explicit state/pointer expectations;
- append-preserving historical Composition behavior;
- #66 guided Candidate selection/Placement handoff.

## Dedicated validator

```text
python scripts/validate_working_composition.py
```

Inside the complete repository gate:

```text
python scripts/validate_working_composition.py --skip-focused-tests
```

The validator checks contract identity, transient preparation fields, one shared
derivation boundary, prepared concurrency/source guards, no producer/Snapshot/
Audience mutation imports, no durable preparation record family, menu/CLI
wiring, package guards, documentation, and repository-validation wiring.

## Static analysis and documentation

```text
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
git diff --check
```

## Package and installed-wheel acceptance

The package guard requires the three guided Working Composition runtime modules,
documentation, validator, wheel smoke, and focused tests.

The isolated smoke installs only:

```text
released Core wheel
built Vitrine wheel
```

It proves:

- installed guided modules import;
- preparation is read-only;
- explicit Profile section order is preserved;
- unresolved section Requirement state is explained;
- Profile audience constraints are projected without Audience Context;
- one exact Composition freezes;
- exact replay reuses the current Composition without state advancement;
- task-level prepare/freeze CLI parsers are installed;
- ScoreForm, Quillan, Concord, Portia, and Meridian are absent.

The richer Placement-order, Review, source-drift, and cross-workflow cases remain
in the source acceptance matrix because they require Vitrine's development-only
synthetic curation fixtures; those fixtures are intentionally not runtime
dependencies of the installed wheel smoke.

## Complete repository qualification

Use the authenticated Core wheel:

```text
python scripts/validate_repository.py \
  --core-wheel /path/to/pds_core-0.6.3-py3-none-any.whl \
  --allow-dirty \
  --reuse-static-caches
```

Successful qualification ends with:

```text
PASS complete repository validation
```
