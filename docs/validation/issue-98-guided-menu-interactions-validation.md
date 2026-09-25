# Issue #98 guided menu interaction validation

Issue #98 is qualified by focused teacher-interaction tests, a dedicated
architectural validator, package guards, an isolated Core+Vitrine wheel smoke,
and complete repository validation.

## Acceptance matrix

The focused matrix covers:

```text
A. controlled confirmation is capitalization-insensitive but otherwise exact
B. wrong nonblank confirmation is explicit, non-mutating, and retryable
C. blank/B cancels; M/Q preserve Core unwind semantics
D. required zero/one/many choice handling preserves exact identity
E. Candidate multi-step reviews clear/redraw rather than accumulate stale menus
F. Selection and Placement remain separate writes with contextual Place-now routing
G. discovery completion can route directly to persisted Candidate Review
H. a newly created Portfolio immediately becomes the current Portfolio context
I. Working Composition freeze uses the same confirmation/result transition
J. Current Portfolio skips redundant required single choices and preserves T drill-down
K. Portfolio-scoped and standalone Profile mutations use the shared confirmation contract
L. Subject identity mutations use the shared confirmation contract without auto-inferring identity
M. Workspace SET/CREATE/RESET use the shared confirmation contract
N. dormant legacy Portfolio curation remains unreachable from the active Portfolio menu
O. the runtime interaction module, docs, validator, and wheel smoke are package-guarded
```

## Focused tests

```powershell
python -m pytest -q `
  tests/test_menu_interactions.py `
  tests/test_candidate_review_menu.py `
  tests/test_candidate_discovery_menu.py `
  tests/test_portfolio_setup_menu.py `
  tests/test_working_composition_menu.py `
  tests/test_current_portfolio_menu.py `
  tests/test_portfolio_menu.py `
  tests/test_profile_menu.py `
  tests/test_subject_menu.py `
  tests/test_menu.py
```

## Dedicated validator

```powershell
python scripts/validate_guided_menu_interactions.py
```

The complete repository gate invokes the same validator with
`--skip-focused-tests` after full pytest has already run.

## Package guards and installed smoke

`vitrine/menu_interactions.py` is an installed runtime module.

`scripts/check_package.py` requires the runtime module in the wheel and requires
the #98 contract/development/validation documentation, validator, installed
smoke, and validator regression test in the source distribution.

After building distributions, run:

```powershell
python scripts/smoke_test_guided_menu_interactions_wheel.py `
  .\dist\<pds-vitrine-wheel>.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

The smoke creates an isolated environment containing only the supplied Core and
Vitrine wheels, exercises zero/one/many required choice handling and controlled
confirmation retry, imports every active standardized teacher menu, and verifies
ScoreForm, Quillan, Concord, Portia, and Meridian are not installed as hidden
runtime dependencies.

## Complete qualification

After the Slice 13 closeout commit, run from a clean branch:

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --reuse-static-caches
```

During development before the closeout commit, `--allow-dirty` may be used.

The complete gate runs full pytest, Ruff, Mypy, the #98 validator,
documentation validation, representative/foundation validators, package
build/Twine/content checks, the isolated #98 wheel smoke, all existing installed
smokes and end-to-end acceptance, and `git diff --check`.
