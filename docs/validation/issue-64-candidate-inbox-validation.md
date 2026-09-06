# Issue #64 Candidate Inbox Validation

This document records the reusable acceptance surface for issue #64. The branch is complete only when the focused and complete repository gates pass.

See [Candidate Inbox v1](../contracts/candidate-inbox-v1.md) and [Candidate Inbox Development](../development/candidate-inbox.md).

## Focused runtime acceptance

The issue-specific tests cover:

- pointer revision 1 initialization and exact replay;
- explicit pointer successors, branch/cycle/context failures;
- legacy unambiguous fallback and ambiguous legacy unresolved state;
- positive Candidates plus ineligible and unresolved Evaluation-only rows;
- suppression before counts/detail;
- explicit `evaluated_since` and deterministic bounded filters;
- Profile Binding drift/conflict;
- Publication supersession and withdrawal;
- exact Subject-link drift and exact Subject identity conflict;
- every non-ready Candidate review condition in the attention taxonomy;
- selected stale Candidate attention without automatic curation;
- Selection provenance remaining frozen when the Candidate pointer advances;
- no producer source-read service during ordinary inbox display;
- state-revision preservation for list/detail/menu/CLI;
- workspace teacher menu and direct CLI exposure;
- Portfolio-scoped reuse of the same inbox service.

Run:

```powershell
python scripts/validate_candidate_inbox.py
```

## Package acceptance

`check_package.py` requires `vitrine/candidate_state.py`, `vitrine/candidate_inbox.py`, and `vitrine/candidate_inbox_menu.py` in the wheel. The sdist retains the Candidate inbox contract/development/validation documents, validator, wheel smoke, and focused tests.

The wheel smoke installs only the qualified Core wheel and built Vitrine wheel. It verifies explicit current-Evaluation resolution, positive and negative rows, suppression, stale Profile Binding explanation, bounded provenance detail, read-only state revisions, and absence of sibling producer distributions.

## Complete repository gate

```powershell
python scripts/validate_candidate_inbox.py
python scripts/validate_candidate_discovery.py
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
git diff --check

python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```

The complete validator runs pytest, Ruff, strict Mypy, repository validators, documentation checks, representative Portfolio validation, package build, Twine, distribution-content validation, isolated wheel smokes including Candidate inbox acceptance, installed end-to-end acceptance, and `git diff --check`. Hosted CI must remain green after the branch is pushed.
