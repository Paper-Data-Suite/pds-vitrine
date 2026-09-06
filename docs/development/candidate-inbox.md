# Candidate Inbox Development

Issue #64 adds one read-only Candidate review model shared by direct CLI, teacher menu, and Portfolio-scoped review.

## Runtime modules

```text
vitrine/candidate_state.py
vitrine/candidate_inbox.py
vitrine/candidate_inbox_menu.py
```

`candidate_state.py` owns current-Evaluation pointer projection and validation. `candidate_inbox.py` owns transient list/detail, staleness, attention, and Selection observation. Presentation layers must consume this service rather than implementing another Candidate-currentness algorithm.

## Current Evaluation rule

Never choose an Evaluation using time, ID, storage position, or filename. Create a new `CandidateCurrentEvaluationPointerRevision` only for an explicit successor Evaluation in the same exact Candidate series.

New positive Candidate persistence is one guarded batch:

```text
CandidateEvaluation
PortfolioCandidate
CandidateCurrentEvaluationPointerRevision(pointer_revision=1)
```

Exact positive replay must reuse the existing records and must not bump pointer revision. Legacy pointerless Candidates are readable only while the creation Evaluation has no explicit successor history.

## Read-only inbox

Use `CandidateInboxQuery` with `list_candidate_inbox(...)`. Do not inject producer registries, adapter registries, source-read authorization gates, or Artifact providers into ordinary inbox display. Staleness may read canonical Core Publication metadata plus canonical Vitrine Profile/Subject state, but must not cross into producer content.

Retained `ineligible` and `unresolved` Evaluation-only heads remain visible without a fabricated Candidate. Suppression is applied before ordinary list counts and detail identity lookup; never add a hidden count for suppressed state.

Every non-ready Candidate condition maps through `CANDIDATE_INBOX_CONDITION_ATTENTION_CODES`. Adding a future condition requires updating that mapping and validator coverage. Attention is workflow routing only; do not add Grade, proficiency, mastery, growth, quality, or ranking semantics.

## Portfolio workflow

The existing Portfolio Discover / Review Candidates screen may still run explicit `discover_and_evaluate_candidates(...)` after teacher confirmation. Persisted review must then render through the shared service with `CandidateInboxQuery(portfolio_id=portfolio_id, limit=100)`. Curation remains a separate explicit action.

## Focused validation

```powershell
python -m pytest `
  tests/test_candidate_current_evaluation.py `
  tests/test_candidate_inbox.py `
  tests/test_candidate_inbox_status.py `
  tests/test_candidate_inbox_acceptance.py `
  tests/test_candidate_inbox_cli.py `
  tests/test_candidate_inbox_menu.py `
  tests/test_curation_services.py

python scripts/validate_candidate_inbox.py
python scripts/validate_candidate_discovery.py
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
git diff --check
```

## Installed wheel

```powershell
python scripts/smoke_test_candidate_inbox_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

The smoke installs only Core + Vitrine, creates synthetic canonical Candidate state, resolves an explicit current pointer, verifies positive/negative/unresolved rows, confirms suppression, explains Profile staleness, checks bounded detail, and proves read operations preserve the Vitrine state revision.

## Complete qualification

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```
