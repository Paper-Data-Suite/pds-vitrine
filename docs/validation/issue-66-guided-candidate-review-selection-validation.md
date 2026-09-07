# Issue #66 guided Candidate review and Selection validation

Issue #66 is qualified by focused API/menu/CLI tests, a cross-workflow acceptance
matrix, a dedicated architectural validator, package-content checks, an isolated
Core+Vitrine wheel smoke, and complete repository validation.

## Focused tests

Coverage includes read-only Candidate Inbox reuse, positive and evaluation-only
review, suppression safety, current-versus-curation Evaluation provenance,
fresh atomic select/decline planning, existing Proposal identity, explicit
section intent, Selection/Placement separation, Placement pointer concurrency,
withdrawal history, fully explicit replacement dispositions, Annotation and
Reflection revisioning, exact curation Review targets, authority denial and
unresolved outcomes, stale-state conflicts, Portfolio-menu routing, and
noninteractive task-level CLI behavior.

```powershell
python -m pytest `
  tests/test_candidate_review.py `
  tests/test_candidate_review_actions.py `
  tests/test_candidate_review_selection_management.py `
  tests/test_candidate_review_curation_content.py `
  tests/test_candidate_review_menu.py `
  tests/test_candidate_review_cli.py `
  tests/test_candidate_review_acceptance_matrix.py `
  tests/test_portfolio_menu.py `
  tests/test_workflow_cli.py `
  tests/test_curation_services.py
```

## Cross-workflow acceptance matrix

`tests/test_candidate_review_acceptance_matrix.py` exercises the shared guided
API, direct CLI, and canonical persisted state together. It verifies full
select/place/content/review/withdraw history, CLI decline observed through the
API, stale decision failure, denied/unresolved authority with no partial writes,
Arrangement pointer conflicts, explicit replacement drop behavior, frozen versus
current Evaluation provenance, evaluation-only nonselectability, and suppressed
absence.

## Dedicated validator

```powershell
python scripts/validate_candidate_review_selection.py
```

The validator checks the contract identity and transient plan fields, Candidate
Inbox reuse, producer/discovery isolation, atomic fresh-decline semantics,
explicit replacement intent, menu and CLI wiring, documentation/package guards,
and repository-validation integration. The complete repository gate uses
`--skip-focused-tests` because pytest already ran the full suite.

## Package-content guards

`scripts/check_package.py` requires all three guided runtime modules in the
wheel:

```text
vitrine/candidate_review.py
vitrine/candidate_review_menu.py
vitrine/candidate_review_cli.py
```

It also requires the #66 contract/development/validation documentation,
dedicated validator, isolated-wheel smoke, and focused acceptance tests in the
source distribution. Distribution metadata continues to forbid ScoreForm,
Quillan, Concord, Portia, and Meridian runtime dependencies.

## Installed-wheel smoke

```powershell
python scripts/smoke_test_candidate_review_selection_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

The smoke creates a fresh isolated environment, installs only the supplied Core
wheel and built Vitrine wheel, runs `pip check`, imports the guided API/menu/CLI
surface and fresh-decline service, verifies the exact task-level parser
vocabulary, and proves ScoreForm, Quillan, Concord, Portia, and Meridian are not
installed.

## Complete qualification

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```

The complete gate runs the full pytest/Ruff/Mypy suite, the dedicated #66
validator, documentation checks, package build/Twine/content validation, the
isolated #66 wheel smoke, all existing wheel smokes and end-to-end acceptance,
and `git diff --check` while ensuring validation does not change the working
tree.
