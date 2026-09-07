# Guided Working Composition development

Issue #67 provides one reusable preparation/freeze orchestration layer shared by
the teacher menu and task-level CLI.

## Runtime modules

```text
vitrine/working_composition.py
vitrine/working_composition_menu.py
vitrine/working_composition_cli.py
```

Canonical Composition persistence remains in:

```text
vitrine/curation_services.py
```

## Preparation

Use:

```python
from vitrine.working_composition import prepare_working_composition

preparation = prepare_working_composition(
    workspace_root,
    portfolio_id,
    composition_note=None,
)
```

This is read-only. The returned preparation contains the exact observed Vitrine
state/pointer revisions, semantic Composition payload, explanation projections,
Core source observations, and deterministic fingerprint.

Do not persist the preparation object as a new Vitrine record.

## Freeze

Use:

```python
from vitrine.working_composition import freeze_prepared_working_composition

result = freeze_prepared_working_composition(
    workspace_root,
    preparation,
    created_by=actor,
    authority_gate=curation_authority_gate,
)
```

Always pass the same preparation the user/caller reviewed. Do not silently call
`prepare_working_composition(...)` again immediately before freezing and then
pretend the caller reviewed the refreshed result.

The executor revalidates:

- Vitrine state revision;
- Composition pointer;
- canonical derivation;
- bounded Core Publication state;
- preparation fingerprint.

The canonical Composition service performs the final guarded check and
persistence.

## Shared derivation

`derive_working_composition(...)` and the internal canonical derivation are the
single semantic source for both preview and write behavior.

When changing Composition semantics, update the shared derivation rather than
adding presentation-specific reimplementation.

## Requirement explanation

Requirement status is derived only from explicit fields such as
`requirement_kind`, `obligation`, `scope_kind`, `scope_reference`, and
`satisfaction_class`.

Do not parse `statement` prose.

Unknown or human-only semantics should remain `not_machine_evaluable` rather
than being guessed.

## Ordering

Profile sections are already stored in explicit ascending `order`.

For sections with active Placements, use only the exact current Arrangement's
`placement_ids` ordering.

Do not use sorted IDs or timestamps as presentation ordering authority.

## Audience boundary

Audience rules are explanatory constraints only.

Do not import or invoke `create_audience_context(...)` from Working Composition
preparation. Audience Context and Snapshot item-level inclusion/omission remain
downstream.

## Producer boundary

The preparation layer may use the bounded Core Publication current-use
observation already owned by the curation service.

Do not call Candidate discovery or producer readers. No ScoreForm, Quillan, or
Concord runtime dependency belongs in this workflow.

## Menu

Portfolio option 5 delegates to `run_working_composition_menu(...)`.

The menu must pass the exact reviewed `WorkingCompositionPreparation` into the
freeze executor.

The confirmation phrase is:

```text
FREEZE COMPOSITION
```

Teacher confirmation does not clear unresolved obligations.

## CLI

Read-only:

```text
vitrine composition prepare PORTFOLIO_ID
```

Prepared write:

```text
vitrine composition freeze PORTFOLIO_ID \
  --preparation-fingerprint <64 hex chars> \
  --expected-state-revision <revision> \
  --expected-composition-pointer-revision <revision|none> \
  --actor-id <actor>
```

The prepared freeze command reconstructs current preparation to compare the
explicit reviewed observations. A mismatch fails closed before authority.

The older `composition show` and `composition build` commands remain
compatibility/advanced primitives.

## Validation

Focused validation:

```text
python scripts/validate_working_composition.py
```

When the complete repository pytest suite already ran:

```text
python scripts/validate_working_composition.py --skip-focused-tests
```

Installed-wheel smoke:

```text
python scripts/smoke_test_working_composition_wheel.py \
  dist/pds_vitrine-0.2.0-py3-none-any.whl \
  /path/to/pds_core-0.6.3-py3-none-any.whl
```

The wheel smoke installs Core and Vitrine only and proves read-only preparation,
unresolved Requirement/audience explanation, freeze, exact replay, CLI parser
availability, and sibling-package absence.
