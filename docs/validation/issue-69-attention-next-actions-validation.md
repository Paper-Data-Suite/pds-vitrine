# Issue #69 Attention and Next Actions validation

## Scope

This validation freezes and qualifies:

```text
vitrine_attention_next_actions_v1
```

The issue is accepted only when the read-only projection, menu/CLI surfaces,
package boundaries, isolated Core+Vitrine wheel behavior, and complete repository
gate all pass.

## Release baseline

Qualification uses the latest released contracts available when issue #69 was
implemented:

| Component | Qualification baseline |
| --- | --- |
| PDS Core | 0.6.3 |
| ScoreForm | 0.11.0 compatibility anchor |
| Quillan | 0.10.0 compatibility anchor |
| Concord | 0.3.0 compatibility anchor |
| Meridian | 0.2.0 sibling precedent; no runtime dependency |
| Paper Data Suite shell | 0.1.0 later consumer; no runtime dependency |
| Portia | no published GitHub Release; no release claim |

The authenticated Core wheel is:

```text
pds_core-0.6.3-py3-none-any.whl
SHA-256 98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5
```

Current Vitrine development requires:

```text
pds-core>=0.6.3,<0.7
```

The frozen v0.2.0 release documents continue to describe the historical v0.2.0
Core requirement. The release-contract validator distinguishes that immutable
release evidence from the current Unreleased development dependency floor.

## Dedicated validator

Run:

```powershell
python scripts/validate_attention_next_actions.py
```

The validator freezes:

- contract identity;
- evaluation, notice, attention-class, attention-code, and action vocabularies;
- label/count-unit/class/action mapping;
- privacy-minimal DTO fields;
- Core 0.6.3 owner-action lexical compatibility;
- Core 0.6.3 / ScoreForm 0.11.0 / Quillan 0.10.0 / Concord 0.3.0 release anchors;
- current Core dependency floor and absence of sibling runtime dependencies;
- absence of `paper_data_suite.module_operations` registration;
- absence of durable attention/notification/seen record families;
- producer-independent, read-only attention imports/calls;
- Candidate Inbox, Working Composition, Snapshot custody, and Export verifier delegation;
- canonical Attempt sequence rather than timestamp/ID currentness;
- menu/CLI shared-service routing;
- package/repository-validator wiring;
- required issue documentation.

The complete repository gate invokes the validator with
`--skip-focused-tests` because full pytest has already run.

## Acceptance matrix

`tests/test_attention_acceptance_matrix.py` ties issue-level requirements to real
behavior tests in:

```text
tests/test_attention.py
tests/test_attention_snapshot.py
tests/test_attention_cli.py
tests/test_attention_menu.py
```

The matrix covers:

- unavailable versus evaluated-empty semantics;
- zero-write behavior;
- Candidate review pending, stale, and unresolved state;
- viewed versus explicitly decided Candidate behavior;
- Proposal decision/follow-up state;
- unplaced Selection attention;
- exact Review follow-up;
- structured/human-only Composition Requirements;
- Composition refresh and unresolved obligations;
- incomplete Snapshot recovery;
- current failure versus superseded historical failure;
- current sealed Edition omissions;
- post-seal Export follow-up;
- current Export verification failure and deduplication;
- workspace-only unscoped custody anomalies;
- deterministic workspace aggregation;
- fixed definition ordering;
- privacy-minimal DTO fields;
- workspace and exact-Portfolio menu/CLI routing.

## Installed-wheel smoke

After building the Vitrine wheel, run:

```powershell
python scripts/smoke_test_attention_next_actions_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  .\pds_core-0.6.3-py3-none-any.whl
```

The smoke creates a fresh isolated virtual environment containing only the
authenticated Core wheel and the built Vitrine wheel.

It constructs synthetic canonical Core/Vitrine state and exercises representative:

```text
Candidate review attention
Selection/Placement attention
Working Composition refresh
incomplete Snapshot recovery
current terminal Snapshot failure
historical-failure supersession
current sealed audience omission
healthy Export verification
corrupted current Export verification
attention CLI
attention teacher presentation
```

It proves that ScoreForm, Quillan, Concord, Portia, Meridian, and the suite shell
are not required imports and that attention inspection does not change the
canonical Vitrine state revision.

## Package boundary

`check_package.py` must include:

```text
vitrine/attention.py
vitrine/attention_cli.py
vitrine/attention_menu.py
```

and require the issue #69 contract/development/validation documents, dedicated
validator, wheel smoke, acceptance matrix, and focused tests in the source
distribution.

Wheel metadata must require:

```text
pds-core>=0.6.3,<0.7
```

and no sibling PDS application dependency.

## Complete repository qualification

Use the exact authenticated Core v0.6.3 wheel:

```powershell
python scripts/validate_repository.py `
  --core-wheel .\pds_core-0.6.3-py3-none-any.whl `
  --allow-dirty `
  --reuse-static-caches
```

The complete gate must include:

```text
Core artifact verification
installed Core verification
pip check
full pytest
Ruff
strict MyPy
all existing contract validators
Issue #69 attention validator
documentation validation
representative Portfolio validation
package build
Twine
package-content validation
all existing installed-wheel smokes
Issue #69 isolated attention wheel smoke
installed end-to-end acceptance
git diff --check
working-tree isolation
```

Final acceptance requires:

```text
PASS isolated Vitrine attention wheel smoke test
PASS Vitrine attention and next-action validation
PASS complete repository validation
```

Do not record those final PASS lines as achieved until the authoritative complete
repository run actually produces them.

## Issue #70 boundary

This qualification intentionally does not require a Core module-operations entry
point, Vitrine readiness provider, suite doctor integration, launcher integration,
backup integration, or cross-module attention aggregation. Those remain issue
#70.
