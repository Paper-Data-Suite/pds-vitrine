# Cross-Producer Compatibility Diagnostics Development Guide

Issue #62 adds read-only diagnostic services and a direct CLI over the released
ScoreForm, Quillan, and Concord integration boundaries.

## Direct CLI

The three direct commands are:

```text
vitrine compatibility producers
vitrine compatibility contract ...
vitrine compatibility publication <publication_id> ...
```

`compatibility producers` is observational. Missing optional producer packages
are reported independently and do not make the Vitrine package itself invalid.

`compatibility contract` requires no workspace and does not import producer
packages merely to explain an exact semantic support request.

`compatibility publication` reads canonical Core metadata only. It never creates
or updates Candidate, Selection, Snapshot, producer, or Core state.

## Contract-only example

```powershell
vitrine compatibility contract `
  --producer scoreform `
  --core-publication-schema-version 1 `
  --publication-kind academic_result_set `
  --manifest-contract-version scoreform_academic_result_manifest_v1 `
  --producer-contract-version scoreform_academic_work_v1 `
  --capability multiple_attempts `
  --capability points `
  --capability question_evidence
```

An exact request reports `supported`. A semantic mismatch reports the preserved
`adapter.unsupported_contract` code plus one or more explanatory
`compatibility.*` reasons. No nearest adapter is selected.

## Publication metadata preflight

```powershell
vitrine compatibility publication <publication_id> `
  --workspace-root <workspace>
```

This sequence is bounded to canonical metadata and audited reader readiness:

```text
Publication
Registration
series / withdrawal state
Core producer Profile compatibility
exact Vitrine adapter support
reader distribution / public API readiness
```

It does not open the manifest.

## Explicit protected read probe

Use `--verify-read` only when the calling integration supplies an appropriate
source-read authorization gate:

```powershell
vitrine compatibility publication <publication_id> `
  --workspace-root <workspace> `
  --verify-read `
  --portfolio-id <portfolio_id> `
  --portfolio-subject-id <subject_id> `
  --purpose "Explain source readiness"
```

The ordinary CLI dependency context is intentionally fail-closed. It does not
implicitly grant source access. With the default unconfigured gate, a deep probe
reports unresolved authorization and stops before manifest existence or digest
inspection.

A deployment that owns authorization policy may inject
`VitrineWorkflowDependencies` when calling `vitrine.cli.main(...)` directly.

## Safe presentation

CLI presentation is rendered only from the machine-readable diagnostic result.
The presentation layer must not use `str()` on producer exceptions to explain a
failure.

Expected sections include:

```text
Status
Producer / Publication / Adapter when applicable
Stage
Why
Technical
Reasons
safe actual/expected fields
Next action
```

The CLI may state whether protected source inspection occurred. It must not reveal
manifest bodies, student work content, feedback bodies, private paths, or raw
producer exception messages.

## Artifact failures

Do not bypass the existing Quillan/Concord Snapshot source providers to diagnose
Artifacts. Map the existing `SnapshotMaterializationError` instead:

```python
from vitrine.artifact_diagnostics import explain_artifact_failure
```

The originating Snapshot code and producer-specific stage remain authoritative.
ScoreForm Artifact applicability is explicitly `not_applicable`.

## Package version rule

Installed package version is informational only. Do not add package version to
`ProducerAdapterSupportRequest` or `ProducerAdapterSupportKey`.

If a future producer release preserves the audited public API and semantic
Publication contract, a differing distribution version alone must not make it
unsupported. Conversely, a familiar distribution version never overrides a
mismatching semantic contract.

## Validation during development

Focused validation:

```powershell
python -m pytest `
  tests/test_compatibility_cli.py `
  tests/test_compatibility_diagnostics.py `
  tests/test_compatibility_publication_diagnostics.py `
  tests/test_artifact_diagnostics.py `
  tests/test_validate_compatibility_diagnostics.py

python scripts/validate_compatibility_diagnostics.py

python -m ruff check `
  vitrine/compatibility_cli.py `
  vitrine/compatibility_diagnostics.py `
  vitrine/publication_diagnostics.py `
  vitrine/artifact_diagnostics.py `
  scripts/validate_compatibility_diagnostics.py `
  scripts/smoke_test_compatibility_wheel.py

python -m mypy

git diff --check
```

The complete repository gate remains `scripts/validate_repository.py`.
