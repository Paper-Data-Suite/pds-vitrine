# Issue #70 Suite Operations Integration validation

## Scope

This validation qualifies the Vitrine side of:

```text
paper_data_suite.module_operations
Core contract version 1
module_id = vitrine
```

It covers installed provider discovery, workspace-level readiness, issue #69 attention
adaptation, the explicit unsupported class-scope rule, opaque whole-workspace
backup/restore relocation, package boundaries, and integration into the complete Vitrine
repository gate.

The normative contract is
[Vitrine Suite Operations Integration v1](../contracts/suite-operations-integration-v1.md).

## Release baseline

Qualification uses:

| Component | Qualification baseline |
| --- | --- |
| PDS Core | 0.6.3 |
| ScoreForm | 0.11.0 compatibility anchor |
| Quillan | 0.10.0 compatibility anchor |
| Concord | 0.3.0 compatibility anchor |
| Meridian | 0.2.0 sibling precedent only |
| Paper Data Suite shell | 0.1.0 downstream consumer only |
| Portia | no published baseline required |

Vitrine retains:

```text
pds-core>=0.6.3,<0.7
```

No sibling runtime dependency is permitted.

## Dedicated issue validator

Run:

```powershell
python scripts/validate_suite_operations_integration.py
```

The validator freezes:

- Core operations contract/group identity;
- exact `module_id=vitrine` profile identity;
- both readiness and attention capabilities;
- exact installed entry-point target;
- unchanged `vitrine` console script;
- no sibling runtime dependencies;
- side-effect-free provider profile module structure;
- workspace-level readiness semantics;
- missing-workspace `unavailable` semantics;
- healthy empty-workspace readiness without initialization;
- positively diagnosed blocking-state semantics;
- Core report revalidation;
- issue #69 code/label/count mapping;
- no invented Core `class_id` or `ModuleWorkRef`;
- exact owner-action ID reuse with Portfolio identity removed;
- class-scoped attention unavailable behavior;
- package-content registration;
- complete repository-gate wiring; and
- required issue documentation and ownership markers.

The complete repository gate invokes this validator with `--skip-focused-tests` because
full pytest has already run.

## Focused behavior tests

The focused set includes:

```text
tests/test_pds_operations.py
tests/test_metadata.py
tests/test_side_effects.py
tests/test_operations_package_contract.py
tests/test_validate_workspace_relocation.py
tests/test_validate_suite_operations_integration.py
```

These tests cover profile identity, explicit workspace handling, empty and invalid Vitrine
namespace readiness, class-scope rejection before native attention evaluation, native to
Core attention mapping, unavailable/evaluated distinction, package metadata, import
side effects, relocation acceptance, and issue-contract validation.

Existing issue #69 attention tests remain part of full pytest and the complete repository
gate. Existing Snapshot workflow regressions likewise remain part of full pytest.

## Installed-wheel provider smoke

After building Vitrine, run against the exact released Core 0.6.3 wheel:

```powershell
python scripts/smoke_test_operations_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  .\pds_core-0.6.3-py3-none-any.whl
```

The isolated environment contains Vitrine plus Core only. The smoke proves:

- Core metadata inspection discovers exactly one Vitrine operations provider;
- provider metadata inspection creates no workspace;
- Core provider diagnostics load and validate the profile;
- diagnostics do not create or evaluate workspace state;
- readiness with no workspace is unavailable;
- class-scoped attention is unavailable without requiring a workspace;
- a valid empty shared workspace is ready without Vitrine initialization;
- workspace-wide attention with no Vitrine state stays unavailable without mutation;
- an incomplete Vitrine namespace is positively diagnosed as not ready;
- the installed `vitrine` console script still resolves to `vitrine.cli:main`; and
- ScoreForm, Quillan, Concord, Portia, Meridian, and the suite shell are not required
  imports.

Expected success line:

```text
PASS isolated Vitrine module-operations wheel smoke test
```

## Opaque backup/restore relocation

Run:

```powershell
python scripts/validate_workspace_relocation.py
```

The validator does not call a Vitrine backup hook because no such hook exists. It models
the suite contract as an opaque byte-for-byte whole-workspace copy to a different root.

The healthy case constructs real canonical Vitrine state, a sealed Snapshot Edition, and
a verified directory Export. It inventories and hashes all workspace files, copies the
workspace, compares relative paths and SHA-256 digests, removes the original workspace
and external producer-source bytes, and verifies the relocated state using only the new
root.

The relocated workspace must preserve readable current/historical canonical state,
healthy readiness, equivalent issue #69/Core attention, Snapshot custody, Edition
verification, and Export verification without rewriting bytes.

A second case relocates an interrupted Snapshot Attempt. The restored workspace must
still report recovery-required custody/attention. Restore must not abandon the Attempt,
clear the condition, or otherwise repair the workflow.

Expected success line:

```text
PASS opaque whole-workspace Vitrine relocation validation
```

## Package boundary

`scripts/check_package.py` must:

- allow `vitrine/pds_operations.py` and `vitrine/operations_provider.py` in the wheel;
- require the module-operations entry-point group and exact Vitrine target;
- preserve the public `vitrine` console script;
- reject routing/publication entry points not owned by this issue;
- require the operations smoke, relocation validator, issue validator, focused tests, and
  issue documentation in the source distribution; and
- preserve the Core-only runtime dependency boundary.

## Complete repository qualification

Run with the exact released Core 0.6.3 wheel:

```powershell
python scripts/validate_repository.py `
  --core-wheel .\pds_core-0.6.3-py3-none-any.whl `
  --allow-dirty `
  --reuse-static-caches
```

The complete gate must include all pre-existing validation plus:

```text
Vitrine suite operations integration validator
opaque workspace relocation validator
isolated Vitrine module-operations wheel smoke
```

It also provides the issue-level acceptance evidence for:

```text
full pytest
Ruff
strict MyPy
documentation validation
package build
Twine
package-content validation
existing installed-wheel smokes
installed end-to-end acceptance
git diff --check
working-tree isolation
```

Final acceptance requires all of these success lines from authoritative qualification:

```text
PASS Vitrine suite operations integration validation
PASS opaque whole-workspace Vitrine relocation validation
PASS isolated Vitrine module-operations wheel smoke test
PASS distribution content validation
PASS complete repository validation
```

Do not record the final complete-repository PASS as achieved until that command actually
produces it. Supported CI must also pass after the branch is pushed.

## Ownership boundary confirmed by acceptance

Issue #70 establishes only the Vitrine provider side. It makes no Core or Paper Data
Suite repository change and does not add a Vitrine backup system.

The accepted architecture remains:

```text
suite orchestrates
Core defines neutral interoperability
Vitrine owns Vitrine meaning and state
```

In particular:

```text
readiness != attention
readiness != launchability
Portfolio linked to class != class-owned attention
owner action reference != executable command
backup copy != Vitrine export
suite restore != Vitrine repair
```
