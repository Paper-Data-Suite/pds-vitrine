# Issue #63 starter Profile validation

## Purpose

This document records the executable acceptance boundary for issue #63,
"Install starter Improvement and Showcase Profile families." The authoritative
behavioral contract is
[Starter Portfolio Profiles v1](../contracts/starter-portfolio-profiles-v1.md).

## Slice-level evidence

The implementation was developed and exercised in guarded slices. Local Windows
PowerShell validation reported:

- catalog/package resources: 19 focused tests passed, Ruff and mypy passed, and
  distribution-content validation passed;
- read-only installation planning: 27 focused tests passed, Ruff and mypy passed;
- atomic guarded installation: 41 focused tests passed, Ruff and mypy passed;
- direct starter CLI: 56 focused tests passed, Ruff and mypy passed;
- teacher-facing Starter Profiles workflow: 70 focused tests passed, Ruff and
  mypy passed;
- final menu EOF normalization recheck: 44 focused starter/menu/CLI tests passed,
  Ruff and mypy passed, and `git diff --check` was clean.

These counts are incremental development evidence, not a substitute for the
complete repository gate.

## Dedicated starter validator

`scripts/validate_starter_profiles.py` verifies:

- exact catalog and pack contract versions;
- deterministic pack order and frozen pack, Family, Profile, purpose, and
  Revision identities;
- Revision 1/predecessor rules;
- ordinary Profile aggregate validity;
- deterministic Vitrine catalog authorship and authority references;
- explicit ordered section and Requirement identities;
- Requirement exact-Revision and section-scope references;
- broad general applicability and explicit known limitations;
- current producer-neutral Candidate vocabulary;
- Improvement non-inference and Showcase audience/review boundaries; and
- absence of hard ScoreForm, Quillan, or Concord package dependencies/imports.

Expected result:

```text
PASS starter Profile validation
```

## CLI and teacher workflow coverage

Focused tests cover:

- starter list from packaged resources;
- complete starter preview;
- read-only starter validation;
- read-only installation planning;
- install refusal without explicit confirmation;
- confirmed guarded installation;
- exact idempotent reinstall;
- stable immutable/lifecycle conflict handling;
- teacher menu preview and plan review;
- final `INSTALL` confirmation; and
- ordinary bindable Profile visibility after installation.

## Installed-wheel acceptance

`scripts/smoke_test_starter_profiles_wheel.py` creates a clean temporary virtual
environment, installs only the exact Core wheel plus the built Vitrine wheel,
and proves:

- list, show, and validate work outside the source checkout;
- ScoreForm, Quillan, and Concord distributions are not required;
- a fresh Core workspace has no Vitrine state before planning;
- starter planning does not create canonical state;
- confirmed installation activates the exact Improvement starter;
- ordinary Profile APIs report the installed Revision as bindable;
- only ordinary Family/Revision/Requirement/lifecycle records are created;
- no Portfolio or Profile Binding is created;
- no Candidate, Selection, Snapshot, or producer records are created; and
- a second identical install is a no-op with no additional lifecycle event.

Expected result:

```text
PASS installed starter Profile wheel smoke
```

## Package-content acceptance

`scripts/check_package.py` requires the starter runtime module, packaged JSON
resources, focused tests, validator, wheel smoke, and starter documentation in
the appropriate wheel/source-distribution boundaries. The wheel must contain
runtime starter resources but no tests, docs, scripts, or sibling producer
packages.

## Complete repository gate

The final pre-merge qualification is the standard reusable repository validator
against the exact qualified Core wheel:

```text
python scripts/validate_repository.py \
  --core-wheel <pds_core-0.6.3-py3-none-any.whl> \
  --allow-dirty \
  --reuse-static-caches
```

That gate covers full pytest, Ruff, strict mypy, all reusable validators,
documentation validation, representative Portfolio/foundation checks, package
build, Twine, exact distribution contents, all isolated wheel smokes including
starter Profiles, installed end-to-end acceptance, `git diff --check`, and a
working-tree unchanged check.

The exact terminal output for that final environment-dependent gate belongs in
the implementing pull request/merge evidence. This document does not claim a
final PASS before that command has actually completed on the exact candidate
working tree.
