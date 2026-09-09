# Build and Export Current Portfolio development

Issue #68 adds one task-oriented layer over the exact current Working
Composition and the existing immutable Snapshot pipeline.

## Runtime modules

```text
vitrine/current_portfolio_build.py
vitrine/current_portfolio_reflection.py
vitrine/current_portfolio_execution.py
vitrine/current_portfolio_surface.py
vitrine/current_portfolio_cli.py
vitrine/current_portfolio_menu.py
```

Canonical Audience/Snapshot persistence remains in the existing audience,
Snapshot service, sealing, custody, and distribution modules.

## Read-only preparation

Use:

```python
from vitrine.current_portfolio_build import prepare_current_portfolio_build

preparation = prepare_current_portfolio_build(
    workspace_root,
    portfolio_id,
    audience_rule_id="student_review",
    audience_context_id=None,
    snapshot_series_id=None,
    acknowledged_obligation_codes=(),
    source_providers=snapshot_source_providers,
)
```

Preparation is read-only. It does not acquire producer bytes, authorize a build,
or write Audience/Snapshot state.

Always present the exact preparation that will later be executed. Do not silently
reprepare after confirmation and pretend the refreshed state was reviewed.

## Current Composition precondition

Preparation delegates to issue #67 and requires
`working_composition_disposition == "reuse_exact_current"`.

If #67 predicts `create_initial`/`create_successor`, or active Selections are
unplaced, return the teacher/caller to Working Composition. Do not build stale or
partially placed curation.

## Audience and Series ambiguity

Callers may supply:

```text
audience_context_id
snapshot_series_id
```

only as exact disambiguation choices from the preparation's matching immutable
IDs. Do not choose equivalent contexts/series by timestamp or opaque identifier.

## Materialization preview

`CurrentPortfolioBuildPreparation.planned_items` exposes one exact source-backed
logical item per Placement.

The first-party policy is:

- exact Quillan/Concord provider -> `copied_source`;
- ScoreForm `assessment_summary` -> `reference_only`;
- otherwise valid source with no exact provider -> `reference_only`;
- exact audience prohibition -> explicit `audience_prohibited` omission;
- supported frozen section Reflection -> `generated_vitrine`.

Never call a source provider during preview. Provider selection is descriptor-only
until guarded Attempt execution.

## Reflection renderer

The first-party renderer supports only exact frozen:

```text
content_mode = inline_text
content_format = plain_text
```

It returns the exact UTF-8 bytes already present in the immutable
`PortfolioReflection`. It performs no URL/path/foreign-document dereference.

If extending Reflection support later, add an explicit renderer contract/version
instead of reinterpreting unsupported content under v1.

## Plan execution

To persist only the reviewed pre-Attempt chain:

```python
from vitrine.current_portfolio_execution import (
    execute_prepared_current_portfolio_plan,
)

plan_result = execute_prepared_current_portfolio_plan(
    workspace_root,
    preparation,
    actor=actor,
    source_providers=snapshot_source_providers,
)
```

This revalidates preparation before the first write and then creates/reuses the
Audience Context and Series before persisting the canonical Build Request and
immutable Build Plan.

## Full build/export

For the ordinary task:

```python
from vitrine.current_portfolio_execution import (
    execute_prepared_current_portfolio_build,
)

result = execute_prepared_current_portfolio_build(
    workspace_root,
    preparation,
    actor=actor,
    authority_gate=snapshot_build_authority_gate,
    source_providers=snapshot_source_providers,
)
```

The full executor composes the existing Attempt/materialization/seal/verification
and directory Export services. Do not add a parallel persistence path.

The same `SnapshotSourceProviderRegistry` instance should be passed through
planning and execution so the reviewed provider commitment can be revalidated.

## Authority

Snapshot build authority is separate from producer Artifact authorization.

A Quillan/Concord provider owns its producer authorization decision. The task
must not open producer-private paths to bypass that boundary.

Neither authority establishes disclosure permission.

## Concurrency

Execution never silently refreshes a reviewed preparation. State/fingerprint/
provider drift fails closed before the applicable stage.

After each canonical mutation, use exactly the returned state revision for the
next mutation.

Persisted Request/Plan/Attempt/Edition/Export history survives later-stage
failure.

## Recovery

`CurrentPortfolioExecutionError` carries bounded privacy-safe diagnostics such as:

```text
underlying_code
underlying_stage
snapshot_build_attempt_id
edition_number
snapshot_export_artifact_id
next_safe_action
```

Do not infer a recoverable Attempt/Edition/Export by greatest number, newest
timestamp, or opaque ID order.

If an exact sealed Edition exists and only Export creation/verification remains,
use:

```python
from vitrine.current_portfolio_execution import resume_current_portfolio_export
```

The resume path verifies Vitrine-owned Edition custody and does not reacquire
producer bytes.

## Current pointer

The task deliberately stops after Export verification.

Do not add a current-pointer mutation to the full executor, menu, or task-level
CLI. Current Edition selection remains a separate explicit Snapshot operation.

## Shared presentation

Both menu and CLI use:

```text
vitrine/current_portfolio_surface.py
```

to explain the exact reviewed preparation. Keep policy explanation shared rather
than reimplementing materialization semantics in each presentation layer.

## Teacher menu

Portfolio option 6 delegates to:

```text
run_current_portfolio_build_export_menu(...)
```

The ordinary menu no longer exposes the old manual Snapshot wizard. Advanced
Snapshot commands remain available through the direct Snapshot CLI.

## Direct CLI

Read-only:

```text
vitrine portfolio build-export prepare PORTFOLIO_ID \
  --audience-rule-id RULE_ID
```

Prepared execution:

```text
vitrine portfolio build-export execute PORTFOLIO_ID \
  --audience-rule-id RULE_ID \
  --preparation-fingerprint SHA256 \
  --expected-state-revision REVISION \
  --actor-id ACTOR
```

Use `--audience-context-id` and `--snapshot-series-id` only when exact ambiguity
requires a choice. Use repeatable `--acknowledge-obligation` for the exact
reviewed unresolved set.

## Validation

Focused contract validation:

```text
python scripts/validate_current_portfolio_build_export.py
```

When complete repository pytest already ran:

```text
python scripts/validate_current_portfolio_build_export.py --skip-focused-tests
```

Installed Core+Vitrine smoke:

```text
python scripts/smoke_test_current_portfolio_build_export_wheel.py \
  dist/pds_vitrine-0.2.0-py3-none-any.whl \
  /path/to/pds_core-0.6.3-py3-none-any.whl
```

The wheel smoke uses one exact Vitrine-owned Reflection to produce real bytes,
seal and verify an Edition, create and verify a directory Export, prove no
current-pointer advancement, exercise installed CLI preparation, and confirm
ScoreForm/Quillan/Concord/Portia/Meridian are absent.
