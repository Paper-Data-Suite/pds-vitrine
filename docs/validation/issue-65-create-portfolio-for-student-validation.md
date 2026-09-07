# Issue #65 Create Portfolio for Student validation

Issue #65 is qualified by focused tests, a dedicated architectural validator,
package-content checks, an isolated Core+Vitrine wheel smoke, and complete
repository validation.

## Focused tests

Coverage includes exact roster resolution, no name/repeated-ID inference,
explicit Subject association, identity conflict, historical Subjects, existing
Portfolio awareness, purpose/Profile matching, exact Profile choice, lifecycle
and applicability, read-only planning, reviewed-ID persistence, Vitrine/Core
drift, atomic creation, menu confirmation/cancellation, CLI dry-run, and
primitive CLI compatibility.

```powershell
python -m pytest `
  tests/test_portfolio_setup_planner.py `
  tests/test_portfolio_setup_atomic.py `
  tests/test_portfolio_setup_menu.py `
  tests/test_portfolio_setup_cli.py `
  tests/test_portfolio_setup_acceptance.py
```

## Dedicated validator

```powershell
python scripts/validate_portfolio_setup.py
```

The complete repository gate uses `--skip-focused-tests` because pytest already
ran the full suite.

## Installed-wheel smoke

```powershell
python scripts/smoke_test_portfolio_setup_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

The smoke runs with Core and Vitrine only, creates two classes containing the
same local student ID, proves no automatic cross-class association, explicitly
creates/activates one Profile, performs both atomic setup paths, reloads state,
and verifies no Candidate/Selection/Placement state or sibling producer
distribution is present.

## Complete qualification

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```
