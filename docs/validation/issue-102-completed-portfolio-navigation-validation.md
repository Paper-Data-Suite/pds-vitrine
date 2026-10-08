# Issue #102 completed Portfolio navigation validation

Issue #102 is qualified through focused source tests, a dedicated validator,
package/repository guards, and isolated installed-wheel acceptance.

## Release checkpoint

Rechecked against GitHub Releases on October 7, 2026:

- Core 0.6.4 — `pds_core-0.6.4-py3-none-any.whl`
  SHA-256 `48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b`
- ScoreForm 0.12.0 — `scoreform-0.12.0-py3-none-any.whl`
  SHA-256 `84ad10ada72a99bebd5455d8c18a0725f9406f8279e57156f3e424efa5678d20`
- Quillan 0.10.5 — `quillan-0.10.5-py3-none-any.whl`
  SHA-256 `031e5a5455c222da6b9a7d8f72e7823dd4c61acde7d90ddce94b49d9bcbe123f`
- Concord 0.3.0 — `pds_concord-0.3.0-py3-none-any.whl`
  SHA-256 `dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12`

No newer compatible release was published at this checkpoint, so the Slice 0
frozen audit identities remain current.

## Dedicated validator

Run:

```powershell
python scripts/validate_completed_portfolio_navigation.py
```

It checks the canonical contract identity, producer-free runtime imports,
local-open/verification/build-routing markers, package/repository wiring,
documentation, release anchors, and the focused Issue #102 test set.

## Installed-wheel acceptance

Build the candidate wheel, then run:

```powershell
python scripts/smoke_test_completed_portfolio_navigation_wheel.py `
  <candidate-vitrine-wheel> `
  <exact-core-0.6.4-wheel>
```

The installed-wheel scenario installs only Core plus `pds-vitrine[paper]`.
ScoreForm, Quillan, Concord, Portia, and Meridian must be absent. It creates two
real sealed Editions from successive frozen Working Compositions, keeps the
Series in an explicit no-current-pointer state, verifies canonical history,
uses an injected local opener to prove exact HTML/PDF/Presentation/Export
targets without GUI launch, verifies the selected chain, detects Presentation
tampering, proves read-only state revision stability, and checks Build Updated
Edition routing back to the existing current build workflow.

Physical printing is not claimed.

## Full repository qualification

Final qualification includes:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
python scripts/validate_completed_portfolio_navigation.py
python scripts/validate_repository.py --core-wheel "<Core 0.6.4 wheel>" --allow-dirty
git diff --check
```

Repository validation also builds the candidate wheel and runs the dedicated
installed-wheel smoke.
