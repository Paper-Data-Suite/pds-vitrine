# Issue #96 Candidate Evidence Review validation

## Scope

This validation freezes the focused functional acceptance for:

```text
vitrine_candidate_evidence_presentation_v1
vitrine_candidate_discovery_presentation_v1
vitrine_candidate_evidence_preview_v1
vitrine_candidate_evidence_artifact_preview_v1
```

Slice 12 adds the exact installed-producer/wheel gate while preserving the
focused A-N acceptance from Slice 11.

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

## Installed acceptance

Slice 12 reuses the frozen issue #71 exact-wheel harness rather than creating a
second release-authentication system.

The new `--candidate-evidence-review-only` mode authenticates and installs:

```text
pds-core 0.6.3
scoreform 0.11.0
quillan 0.10.1
pds-concord 0.3.0
pds-vitrine 0.3.0 candidate wheel
```

It builds real producer-native synthetic Publications, discovers live Candidates,
asserts exact instructional naming, executes one ScoreForm structured preview,
one authorized Quillan PDF preview, and one authorized Concord returned-Artifact
preview, verifies digests/sizes/media and state non-mutation, and prints no source
content.

The Core+Vitrine-only installed smoke proves every #96 runtime module imports and
the four contract identities are packaged while producer distributions remain
absent and unimported.

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

## Slice 12 qualification

Build the Vitrine wheel:

```powershell
Remove-Item .\dist -Recurse -Force -ErrorAction SilentlyContinue
python -m build --outdir .\dist
```

Run the isolated installed Vitrine smoke:

```powershell
python .\scripts\smoke_test_candidate_evidence_review_wheel.py `
  .\dist\pds_vitrine-0.3.0-py3-none-any.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

Run exact live producer acceptance:

```powershell
python .\scripts\qualify_installed_live_portfolio.py `
  --vitrine-wheel .\dist\pds_vitrine-0.3.0-py3-none-any.whl `
  --wheel-dir "$HOME\Downloads" `
  --candidate-evidence-review-only
```

Expected terminal markers are:

```text
PASS isolated Candidate evidence review wheel smoke test
PASS exact release wheel authentication
PASS issue #96 installed Candidate evidence review acceptance
```

The normal complete repository gate also runs the isolated wheel smoke. The
heavy exact-producer gate remains an explicit exact-wheel qualification because
it requires the caller-prepared offline wheelhouse.

## Quillan v0.10.1 endpoint

The #96 installed gate uses `quillan-0.10.1-py3-none-any.whl` with SHA-256 `5311cccc03a012a7d319827e30b5a989901a9e77693171a8861e4e58409764ad`. The existing #71 frozen 0.10.0 composition remains historical and unchanged; only the #96 qualifier mode substitutes the newer exact Quillan wheel.
