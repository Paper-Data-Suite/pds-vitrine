# Issue #96 Candidate Evidence Review validation

## Scope

This validation freezes the focused functional acceptance for:

```text
vitrine_candidate_evidence_presentation_v1
vitrine_candidate_discovery_presentation_v1
vitrine_candidate_evidence_preview_v1
vitrine_candidate_evidence_artifact_preview_v1
```

It does not claim the exact installed-producer/wheel gate; that remains the next
closure slice.

## A-N acceptance matrix

`tests/test_candidate_evidence_review_acceptance.py` maps every Issue #96
acceptance group A-N to concrete behavior tests covering:

```text
instructional ScoreForm / Quillan / Concord naming
display labels excluded from Candidate authority
Quillan PDF / Markdown representation distinction
instructional discovery preflight and bounded completion summary
Ready-to-consider exclusion of active Selections
human-readable Profile fit
explicit preview before Selection
no ordinary detail-time Artifact I/O
exact source revalidation
fail-closed Artifact authorization and integrity
metadata-only structured summaries
transient temporary viewer bytes
suppressed/denied/private-data boundaries
Technical Details / Provenance retention
```

The file also adds a direct negative test proving a suppressed Evaluation cannot
be resolved through the Candidate preview authority service.

## Dedicated validator

Run:

```powershell
python scripts/validate_candidate_evidence_review.py
```

The validator freezes contract identities, required teacher workflow affordances,
public producer Artifact API markers, absence of Snapshot/native-file shortcuts,
required documentation, package guards, repository-validator wiring, and the A-N
traceability matrix.

The complete repository validator invokes it with `--skip-focused-tests` after
the full pytest suite.

## Package boundary

This slice requires the source distribution to contain the #96 contract,
development, validation, validator, matrix, and validator-test files. Runtime
preview modules were already added to the wheel allowlist by their implementation
slices.

## Remaining installed acceptance

Issue #96 additionally requires exact released-producer acceptance using:

```text
pds-core 0.6.3
scoreform 0.11.0
quillan 0.10.0
pds-concord 0.3.0
```

and an isolated installed Vitrine wheel smoke. Those are deliberately separated
into Slice 12 so live-package failures do not obscure the focused functional
acceptance layer.

## Current qualification

Do not record final PASS claims here until the commands have actually run.

Focused Slice 11 qualification:

```powershell
python -m pytest -q `
  tests/test_candidate_evidence_review_acceptance.py `
  tests/test_validate_candidate_evidence_review.py

python scripts/validate_candidate_evidence_review.py --skip-focused-tests

python -m ruff check `
  scripts/validate_candidate_evidence_review.py `
  tests/test_candidate_evidence_review_acceptance.py `
  tests/test_validate_candidate_evidence_review.py

python -m mypy
python scripts/check_documentation.py
git diff --check
```
