# Issue #68 Build and Export Current Portfolio validation

This document records the reusable qualification surface for issue #68.

## Contract under test

```text
vitrine_build_export_current_portfolio_v1
```

The implementation preserves:

```text
current Working Composition != greatest Composition revision by inference
Build preparation != Build Request
Build Request != Build Plan
Build Plan != Build Attempt
Build Attempt != Snapshot Edition
Snapshot Edition != Export Artifact
Export Artifact != delivery

Profile Audience Rule != disclosure authorization
Snapshot build authority != producer Artifact authorization
Curation Review != disclosure authorization

reference_only != omitted
unresolved obligation acknowledgement != obligation satisfaction
verification != disclosure permission
```

## Focused acceptance matrix

`tests/test_current_portfolio_acceptance_matrix.py` binds the issue-level
acceptance groups to the focused behavior tests already exercising them.

The focused matrix covers:

- no/stale current Working Composition and unplaced Selection blocking;
- exact Audience Context/Series create/reuse/choice semantics;
- required Review and unresolved-obligation acknowledgement behavior;
- deterministic Profile/Arrangement ordering and PII-free identities/paths;
- exact-provider copied source, missing-provider reference-only, ScoreForm
  reference-only, deferred media, and audience-prohibited omission planning;
- exact immutable Reflection rendering, unsupported/external-reference failure,
  no Annotation document fabrication, and fingerprint changes;
- pre-write revalidation, sequential canonical state revisions, Request/Plan
  fidelity, provider commitment, Attempt/materialization/seal/verification,
  partial success, exact recovery, and Export resume/replay;
- shared teacher-facing preparation explanation;
- direct CLI fingerprint/state guards and exact ambiguity inputs;
- menu exact-choice/obligation/final-confirmation behavior;
- Portfolio option-6 routing and retained advanced Snapshot CLI surface.

The focused test files are:

```text
tests/test_current_portfolio_build.py
tests/test_current_portfolio_build_planning.py
tests/test_current_portfolio_reflection.py
tests/test_current_portfolio_execution.py
tests/test_current_portfolio_surface.py
tests/test_current_portfolio_cli.py
tests/test_current_portfolio_menu.py
tests/test_current_portfolio_routing.py
tests/test_current_portfolio_acceptance_matrix.py
```

## Dedicated validator

```text
python scripts/validate_current_portfolio_build_export.py
```

Inside the complete repository gate:

```text
python scripts/validate_current_portfolio_build_export.py --skip-focused-tests
```

The validator checks:

- exact task and Reflection renderer contract identities;
- transient preparation/result fields;
- read-only preparation with no Audience/Snapshot mutation-service ownership;
- no durable Build/Export wizard record family;
- issue #67 `reuse_exact_current` handoff and unplaced Selection blocking;
- Audience Context/Series exact-match semantics;
- ScoreForm reference-only policy and no `retained_source_path` inference;
- exact-provider and audience-omission planning markers;
- Reflection-only first-party generated-content boundary and no external
  dereference;
- deterministic fingerprint/ordering foundations;
- canonical Request/Plan/Attempt/Seal/Edition/Export service composition;
- no implicit current-pointer advancement;
- shared menu/CLI task orchestration;
- retained advanced Snapshot commands;
- Core-only hard runtime dependency boundary;
- package guards, documentation, and repository-validation wiring.

## Static analysis and documentation

```text
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
git diff --check
```

## Package-content guards

`scripts/check_package.py` requires the six #68 runtime modules in the wheel
allowlist and requires the #68 contract/development/validation docs, validator,
installed-wheel smoke, acceptance matrix, validator tests, and focused tests in
the source distribution.

No frozen fixture hashes or unrelated schema packages are changed for issue #68.

## Isolated Core+Vitrine wheel smoke

```text
python scripts/smoke_test_current_portfolio_build_export_wheel.py \
  dist/pds_vitrine-0.2.0-py3-none-any.whl \
  /path/to/pds_core-0.6.3-py3-none-any.whl
```

The smoke creates a synthetic Vitrine Profile whose only required content is one
exact section-scoped inline/plain-text `PortfolioReflection`.

Using only installed Core and Vitrine wheels, it proves:

- issue #67 can freeze the exact Reflection-bearing Working Composition;
- issue #68 preparation is read-only and sees `reuse_exact_current`;
- Audience Context and Snapshot Series creation are predicted exactly;
- the Reflection becomes one deterministic `generated_vitrine` Entry;
- the full canonical Request/Plan/Attempt/Seal/Edition/Export chain executes;
- one real Export file contains the exact frozen Reflection bytes;
- the Edition pointer remains unadvanced;
- installed task-level CLI preparation is available and read-only;
- ScoreForm, Quillan, Concord, Portia, and Meridian are absent.

This smoke intentionally avoids development producer fixtures so they cannot
masquerade as installed integrations.

## Complete repository qualification

Use the authenticated released Core wheel:

```text
python scripts/validate_repository.py \
  --core-wheel /path/to/pds_core-0.6.3-py3-none-any.whl \
  --allow-dirty \
  --reuse-static-caches
```

The repository gate runs complete pytest/Ruff/MyPy, every reusable validator,
documentation checks, package build/twine/package-content checks, isolated wheel
smokes including issue #68, installed end-to-end acceptance, and `git diff
--check`.

Issue #68 is not complete until this command ends with:

```text
PASS complete repository validation
```
