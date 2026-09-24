# Issue #97 Selection and Placement guidance validation

Issue #97 is qualified by focused domain/actionability tests, a dedicated
architectural validator, package-content checks, an isolated Core+Vitrine wheel
smoke, and complete repository validation.

## Focused tests

```powershell
python -m pytest -q `
  tests/test_selection_placement_guidance.py `
  tests/test_candidate_review_selection_guidance.py `
  tests/test_curation_selection_guidance.py `
  tests/test_selection_proposal_revalidation.py `
  tests/test_selection_placement_execution_guidance.py `
  tests/test_selection_replacement_guidance.py `
  tests/test_candidate_review_section_actionability.py `
  tests/test_candidate_review_menu.py
```

Coverage includes max-zero semantic matches, full sections, Arrangement
conflicts, same-Selection duplicate Placement, section-scoped requirement
intersection, canonical fresh-write enforcement, stale Proposal acceptance,
negative Proposal rejection, ordinary Placement enforcement, valid one-for-one
replacement, unrelated full replacement targets, and teacher-menu filtering.

## Dedicated validator

```powershell
python scripts/validate_selection_placement_guidance.py
```

The complete repository gate invokes the same validator with
`--skip-focused-tests` after the full pytest suite has already run.

## Package guards and installed smoke

`vitrine/selection_placement_guidance.py` is an installed runtime module.
`scripts/check_package.py` requires it in the wheel and requires this Issue #97
documentation, validator, smoke script, and validator test in the source
distribution.

After building distributions, run:

```powershell
python scripts/smoke_test_selection_placement_guidance_wheel.py `
  .\dist\pds_vitrine-0.3.0-py3-none-any.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

The smoke creates an isolated environment with only the supplied Core and
Vitrine wheels, imports the public #97 guidance surface, checks the contract
projection fields, and verifies producer applications are not installed.

## Complete qualification

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```

The complete gate runs full pytest, Ruff, Mypy, the #97 validator,
documentation checks, package build/Twine/content checks, the #97 isolated wheel
smoke, all existing acceptance smokes, and `git diff --check`.
