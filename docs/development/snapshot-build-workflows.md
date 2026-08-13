# Snapshot Build Workflow Development

This guide covers the issue #35 runtime implementation. For governing semantics,
read [Snapshot Build Workflows v1](../contracts/snapshot-build-workflows-v1.md)
and accepted ADR 0007 first.

## Runtime modules

```text
vitrine/models/snapshot_workflow.py
vitrine/snapshot_state.py
vitrine/snapshot_custody.py
vitrine/snapshot_materialization.py
vitrine/snapshot_sealing.py
vitrine/snapshot_services.py
vitrine/snapshot_distribution.py
```

The frozen issue #28 models remain in `vitrine/models/snapshots.py`.

## Control-plane sequence

Application code uses:

```python
from vitrine.snapshot_services import (
    create_snapshot_series,
    request_snapshot_build,
    plan_snapshot_build,
    start_snapshot_build_attempt,
    execute_snapshot_build_attempt,
    seal_snapshot_build_attempt,
)
```

A normal build is explicit:

```text
create Series
-> request exact Composition
-> plan complete Entry inventory
-> start Attempt
-> execute exact source/render work
-> seal verified prepared Attempt
```

Export and promotion are separate:

```python
from vitrine.snapshot_distribution import (
    advance_snapshot_current_pointer,
    create_snapshot_directory_export,
    verify_snapshot_edition,
    verify_snapshot_export,
)
```

## Expected state revisions

Every mutation requires the caller's exact expected Vitrine state revision.

Do not refresh and silently retry a stale build request, Plan, Attempt, Export,
or pointer update.

Pointer promotion additionally requires the exact expected pointer revision and
current Edition.

## Exact Composition planning

Load or otherwise identify one exact
`WorkingPortfolioCompositionRevision` and its one-to-one
`WorkingPortfolioCompositionInventory`.

The Request service checks:

- Series Portfolio/Subject;
- Profile Binding/Revision;
- Composition Revision;
- Audience Context;
- frozen curation Review IDs.

The Plan service validates each source chain against canonical records and the
exact Composition. It never asks a current Composition pointer which source to
use.

## Source Entry Plans

A copied source Entry Plan must preserve:

```text
Placement
Selection
Candidate
Candidate Evaluation
Core Publication
producer module
projection kind/contract
Source Artifact
producer digest claim, if any
target path/media/content class
```

Use the exact values already present in the Candidate endpoint.

Do not create a generic "read this path" Plan.

## Generated Entry Plans

A generated Entry has no fabricated producer source fields.

It preserves:

```text
renderer ID/version/contract
configuration digest
optional template digest
exact SnapshotInputReference values
target path/media/content class
```

Valid exact inputs include Composition-frozen Selection/Placement/Candidate/
Evaluation references and exact Annotation/Reflection revisions frozen by the
Composition Inventory.

## Provider implementation

Implement the `SnapshotSourceProvider` protocol only for a documented exact
source contract.

A provider descriptor is one exact support key. A provider result returns one
approved root plus exact relative locator.

The materialization layer, not the provider, owns containment/link/reparse/
regular-file and independent digest enforcement.

Production code must not add a provider that simply treats arbitrary
`source_locator` values as readable local files.

## Renderer implementation

Implement the `SnapshotRenderer` protocol for one exact renderer key.

Renderers receive the immutable Entry Plan. They must validate their expected
input references and return:

```text
renderer identity
bytes
media type
configuration digest
optional template digest
optional language
```

The materialization layer compares the returned identities to the Plan and
independently hashes the staged output.

## Build authority

Inject a `SnapshotBuildAuthorityGate`.

The external gate is evaluated once at the Attempt execution boundary before
protected source access. The materialization primitives receive the already
approved decision defensively.

Do not interpret `AudienceContext`, curation approval, actor role, or Profile
prose as build permission.

Build permission is still not recipient/disclosure permission.

## Series lock

`start_snapshot_build_attempt(...)` persists the Attempt, then exclusively
acquires the Series build lock before staging.

Use:

```python
from vitrine.snapshot_custody import (
    acquire_snapshot_series_lock,
    inspect_snapshot_series_lock,
    release_snapshot_series_lock,
)
```

Do not manually delete a lock. Explicit release requires exact Attempt ownership
and expected lock SHA-256.

Never clear a lock because its timestamp appears old.

## Staging

The Attempt staging root is:

```text
vitrine/snapshots/staging/<attempt-id>/
```

It contains only:

```text
content/
internal/
```

Execution refuses staging residue because residue may represent interrupted
work. Use recovery inspection instead of overwriting it.

## Successful execution

`execute_snapshot_build_attempt(...)` returns
`SnapshotAttemptExecutionResult`.

That object is pre-seal state only. It may contain:

```text
prepared_bytes
reference_only
omission_pending
```

It is intentionally not canonical and does not fabricate an Edition reference.

## Blocking execution

A blocking materialization failure produces a terminal immutable Attempt Result
with complete per-item disposition inventory and no Edition.

Permitted runtime omission mapping is intentionally narrow. Integrity failures
remain blocking.

## Sealing

`seal_snapshot_build_attempt(...)`:

1. reloads exact canonical Attempt/Plan;
2. requires the exact Series lock;
3. reopens and verifies staging;
4. allocates the real Edition number;
5. constructs frozen Materialization/Entry/Omission records;
6. constructs additive Materialization provenance;
7. generates deterministic logical inventory;
8. generates canonical internal Manifest bytes;
9. independently hashes Manifest and logical inventory;
10. creates Seal and Edition;
11. canonically commits sealed state;
12. exclusively publishes Edition custody;
13. releases the exact Series lock;
14. persists terminal Attempt Result and Edition build provenance.

A post-seal publication/cleanup failure preserves the Edition and is reported as
partial success.

## Edition verification

Use:

```python
verify_snapshot_edition(
    workspace,
    snapshot_series_id=...,
    edition_number=...,
)
```

Verification deliberately does not accept a source provider or producer reader.
It is based only on Vitrine canonical state and sealed Vitrine custody.

## Export

Use:

```python
create_snapshot_directory_export(
    workspace,
    snapshot_series_id=...,
    edition_number=...,
    export_plan_id=...,
    expected_state_revision=...,
)
```

The service verifies the Edition first. It copies only byte-bearing canonical
Entries selected by the exact immutable Export Plan, independently verifies the
directory inventory, then persists the Export Artifact.

Exact replay returns the existing immutable Artifact.

## Export verification

Use:

```python
verify_snapshot_export(
    workspace,
    snapshot_export_artifact_id=...,
)
```

It checks the canonical included/excluded Entry partition and exact directory
file inventory/digest. It also re-verifies the underlying Edition.

## Current pointer

Use `advance_snapshot_current_pointer(...)` only after a caller explicitly
chooses to promote a sealed Edition.

The pointer is not automatically advanced by sealing or Export creation.

## Recovery

Read-only inspection:

```python
from vitrine.snapshot_distribution import inspect_snapshot_attempt_recovery
```

Inspection reports terminal state, staging residue, lock state, and sealed
Edition association.

Explicit abandonment:

```python
abandon_snapshot_build_attempt_after_recovery(...)
```

is allowed only for an unresolved unsealed Attempt. It preserves staging.

No API adopts, deletes, promotes, or repairs ambiguous custody automatically.
An unresolved Attempt with `internal/manifest.json` is treated as an allocated,
possibly durable Edition identity and cannot be abandoned into reuse.

For a workspace-wide read-only audit:

```python
from vitrine.snapshot_distribution import inspect_snapshot_custody

audit = inspect_snapshot_custody(workspace)
for finding in audit.findings:
    print(finding.code, finding.subject_kind, finding.subject_id)
```

The audit distinguishes incomplete/failed Attempts, orphan staging, locks,
Edition canonical/custody mismatches, corrupted Manifest or Entry custody,
orphan/corrupted Exports, and durability uncertainty.

## Development fixtures

The fixture-backed acceptance flow is intentionally separate from generic
runtime code:

```text
scripts/snapshot_fixture_support.py
fixtures/snapshot-workflows/
scripts/validate_snapshot_workflows.py
```

The Quillan-shaped fixture provider has an exact approved inventory. The
ScoreForm-shaped and Reflection fixtures use deterministic explicit renderers.
The ScoreForm renderer configuration commits the exact structured fixture input
SHA-256 in addition to exact canonical Candidate/Selection/Placement/Evaluation
references; the Reflection renderer reads the exact canonical Reflection revision
frozen by the Composition Inventory.

These are not installed producer integrations.

## Focused validation

During development:

```powershell
python -m ruff check .
python -m mypy

python -m pytest `
  tests\test_snapshot_workflow_models.py `
  tests\test_snapshot_state.py `
  tests\test_snapshot_persistence_wiring.py `
  tests\test_snapshot_custody.py `
  tests\test_snapshot_materialization.py `
  tests\test_snapshot_sealing.py `
  tests\test_snapshot_services.py `
  tests\test_validate_snapshot_workflows.py `
  -q

python scripts\validate_snapshot_workflows.py
git diff --check
```

The dedicated validator intentionally runs outside the ordinary focused unit
suite because it executes the full persisted Candidate/curation/Snapshot stack.

## Installed-wheel smoke

After building Vitrine:

```powershell
python scripts\smoke_test_snapshot_wheel.py `
  .\dist\pds_vitrine-0.2.0.dev0-py3-none-any.whl `
  C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

Only the Vitrine and Core wheels are installed in the isolated environment.

## Complete validation

```powershell
python scripts\validate_repository.py `
  --core-wheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```

During an uncommitted issue branch:

```powershell
python scripts\validate_repository.py `
  --core-wheel C:\path\to\pds_core-0.6.0-py3-none-any.whl `
  --allow-dirty
```

The validator must leave the working tree byte-for-byte unchanged.
