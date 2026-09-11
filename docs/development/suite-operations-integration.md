# Suite operations integration development

Issue #70 exposes Vitrine through PDS Core 0.6.3 module operations while keeping Vitrine
state and semantics inside Vitrine.

The normative behavior is documented in
[Vitrine Suite Operations Integration v1](../contracts/suite-operations-integration-v1.md).

## Runtime surface

The runtime implementation is deliberately small:

```text
vitrine/pds_operations.py
vitrine/operations_provider.py
```

`vitrine/pds_operations.py` is the installed discovery/profile boundary. It builds and
Core-validates the profile and lazily imports capability implementations so provider
metadata discovery does not touch a workspace.

`vitrine/operations_provider.py` owns the workspace-level readiness interpretation and
the adapter from issue #69 native attention into Core v1 reports.

Do not put suite-shell policy in either module.

## Release baseline

Develop and qualify against:

```text
PDS Core 0.6.3
ScoreForm 0.11.0 compatibility anchor
Quillan 0.10.0 compatibility anchor
Concord 0.3.0 compatibility anchor
Meridian 0.2.0 sibling precedent
Paper Data Suite shell 0.1.0 downstream consumer
```

Only Core is a Vitrine runtime dependency. Keep:

```text
pds-core>=0.6.3,<0.7
```

Do not add sibling application dependencies.

## Provider discovery

Registration is:

```toml
[project.entry-points."paper_data_suite.module_operations"]
vitrine = "vitrine.pds_operations:get_module_operations_profile"
```

Profile construction must remain side-effect free. It must not resolve a default
workspace or import the implementation in a way that evaluates Vitrine state.

Use Core provider diagnostics for installed qualification rather than importing suite
shell doctor code. The isolated wheel smoke proves metadata inspection and full provider
diagnosis against released Core 0.6.3.

## Readiness implementation

Readiness is workspace-level and read-only.

The current decision tree is:

```text
no explicit workspace
-> unavailable

workspace missing/not a directory
-> unavailable

workspace not writable
-> evaluated, ready=False

valid workspace with no Vitrine namespace
-> evaluated, ready=True

existing Vitrine namespace
-> audit Vitrine canonical storage
   -> blocking Vitrine-owned issue: evaluated, ready=False
   -> healthy audit: evaluated, ready=True
   -> unable to inspect safely: unavailable
```

Do not change readiness into a data-presence test. No Portfolio/Candidate/Snapshot state
is required for an empty shared workspace to be ready.

Do not filter readiness by `class_id` or `active_school_year`.

## Attention implementation

Core attention must delegate to:

```text
vitrine.attention.evaluate_vitrine_attention
```

for workspace-wide requests. Do not rebuild issue #69 logic in the Core adapter.

The exact v1 scope rule is:

```text
class_id is None
-> evaluate issue #69 workspace attention

class_id is not None
-> unavailable + zero summaries
-> do not call issue #69
```

The class rule is conservative because Vitrine Portfolios and Portfolio-wide obligations
may span classes.

Mapping into Core intentionally drops Vitrine-only fields such as `portfolio_id`,
`attention_class`, `count_unit`, and `reason_codes` where Core v1 has no field. Preserve
code, label, safe count, notices, and exact action ID.

Core summaries must leave `class_id` and `work_ref` unset.

## Owner actions

Map actions only as:

```text
ModuleOwnerActionRef(
    module_id="vitrine",
    action_id=<exact issue #69 action_id>,
)
```

Do not append Portfolio identity. Do not create command strings, URLs, paths, imports, or
menu-number routes.

## Opaque workspace relocation

There is no Vitrine backup adapter. The suite backup contract is whole-workspace byte
custody.

`scripts/validate_workspace_relocation.py` is the executable acceptance proof. It uses
real deterministic Snapshot workflow fixtures and Vitrine Snapshot services rather than
a backup-specific fake format.

The validator exercises two cases:

1. A healthy canonical Portfolio/Snapshot state with a sealed Edition and verified
   directory Export. The complete workspace is copied byte-for-byte to a different root,
   the original workspace and producer source bytes are removed, and the copied root is
   used to reload canonical state, inspect custody, verify Edition/Export bytes, and
   evaluate Vitrine readiness/attention.
2. An interrupted Snapshot Attempt. Relocation must preserve its exact recovery-required
   state and issue #69 recovery attention. Copying the workspace must not clear or repair
   that condition.

Before and after observational validation, file inventory and SHA-256 digests are
compared so reads cannot silently rewrite canonical or Snapshot/Export bytes.

## Package boundary

The wheel contains the two runtime operation modules and no suite/sibling package code.
The source distribution contains the issue validator, relocation validator, wheel smoke,
focused tests, and issue documentation.

`scripts/check_package.py` remains the strict package-content gate.

## Repository gate

`scripts/validate_repository.py` must run:

```text
Vitrine suite operations integration validator
opaque workspace relocation validator
isolated Vitrine module-operations wheel smoke
```

in addition to all pre-existing repository validation, package, Snapshot, attention, and
end-to-end gates.

The issue validator is run with `--skip-focused-tests` from the complete gate because
full pytest has already run there.

## Focused qualification

Use:

```powershell
python -m pytest `
  tests/test_pds_operations.py `
  tests/test_metadata.py `
  tests/test_side_effects.py `
  tests/test_operations_package_contract.py `
  tests/test_validate_workspace_relocation.py `
  tests/test_validate_suite_operations_integration.py

python scripts/validate_suite_operations_integration.py
python scripts/validate_workspace_relocation.py

python -m ruff check `
  vitrine/pds_operations.py `
  vitrine/operations_provider.py `
  scripts/smoke_test_operations_wheel.py `
  scripts/validate_workspace_relocation.py `
  scripts/validate_suite_operations_integration.py `
  tests/test_pds_operations.py `
  tests/test_operations_package_contract.py `
  tests/test_validate_workspace_relocation.py `
  tests/test_validate_suite_operations_integration.py

python -m mypy
python -m pip check
python scripts/check_documentation.py
git diff --check
```

Installed-wheel qualification uses the built Vitrine wheel and the exact released Core
0.6.3 wheel:

```powershell
python scripts/smoke_test_operations_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  .\pds_core-0.6.3-py3-none-any.whl
```

Complete acceptance is recorded in
[Issue #70 validation](../validation/issue-70-suite-operations-integration-validation.md).
