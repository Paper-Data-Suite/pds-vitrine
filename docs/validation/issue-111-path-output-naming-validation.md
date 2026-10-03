# Issue #111 — Bounded Vitrine paths and output file names validation

Issue #111 separates durable semantic identity, Vitrine-owned filesystem custody,
and student-facing presentation naming.

## Implemented boundary

New canonical-record and Snapshot-owned custody uses deterministic bounded opaque
tokens. Historical direct-identity custody remains readable in place and is not
migrated or renamed.

Current Portfolio custody filenames remain digest-bounded. Paper Reflection output
keeps its fixed Vitrine-owned PDF leaf. Historical Core retained-source paths remain
historical facts and are consumed from the exact persisted
`retained_source_relative_path`.

The #101 handoff provides bounded readable presentation filenames/directories with
semantic disambiguation and fail-closed portable collision checks.

## Core qualification anchor

Final Issue #111 qualification targets the exact published Core 0.6.4 wheel:

```text
pds_core-0.6.4-py3-none-any.whl
SHA-256:
48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b
release source commit:
152d1c65064c4f8fe55249ff2ca3379d7c4d6ccb
```

Core 0.6.4 bounds newly written retained-source filenames and generated
source-scan IDs while preserving historical retained-source provenance without
migration.

Vitrine continues to declare:

```text
pds-core>=0.6.3,<0.7
```

because Issue #111 does not consume a Core 0.6.4-only API. Core 0.6.4 is the exact
qualification target, not a new semantic dependency floor.

The active compatibility and complete-qualification CI jobs download and
authenticate Core 0.6.4. The separate Issue #71 live installed acceptance job
remains intentionally frozen on its audited Core 0.6.3 artifact.

## Automated qualification

Focused source qualification:

```text
python scripts/validate_path_output_naming.py
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
git diff --check
```

Installed-wheel qualification:

```text
python scripts/smoke_test_path_output_naming_wheel.py   <pds-vitrine-wheel>   <pds_core-0.6.4-py3-none-any.whl>
```

The isolated smoke verifies the exact Core 0.6.4 artifact before installation,
installs Vitrine with `--no-deps`, checks package metadata, exercises long
Snapshot identities through bounded staging/lock path creation, exercises the
#101 presentation helpers, retains a long-named source through Core 0.6.4, and
materializes those exact retained bytes through Vitrine without reconstructing
the Core filename.

Complete repository qualification remains:

```text
python scripts/validate_repository.py   --core-wheel <pds_core-0.6.4-py3-none-any.whl>   --allow-dirty
```

The repository gate builds the Vitrine wheel/sdist, validates package content,
runs the Issue #111 validator, and executes the isolated Issue #111 wheel smoke
alongside the existing installed acceptance matrix.
