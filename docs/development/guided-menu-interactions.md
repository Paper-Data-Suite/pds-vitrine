# Guided menu interaction development

Issue #98 centralizes teacher interaction mechanics in
`vitrine.menu_interactions`.

## Shared helpers

Use:

```python
confirm_exact_phrase(...)
resolve_required_choice(...)
```

for interaction behavior only.

Do not put domain validation, authorization, persistence, ranking, or identity
in these helpers.

### Controlled confirmation

A consequential mutation should define a renderer for the exact state being
confirmed, then delegate to the shared helper:

```python
def render_review() -> None:
    # Render the exact planned action and current context.
    ...

if not confirm_exact_phrase(
    expected_phrase="MUTATE",
    input_fn=input_fn,
    output=output,
    clear_fn=clear_fn,
    render_review=render_review,
):
    return

# Call the existing canonical service with the already-reviewed exact inputs.
```

Do not print the review first and then call the helper with an empty renderer.
The helper owns clear/redraw and retry.

When a final review supports a read-only drill-down such as Technical Details /
Provenance, use `handle_review_action`. The callback must not mutate canonical
state.

### Required cardinality

Use `resolve_required_choice` only when the workflow already requires exactly
one value from a bounded set.

```text
0 -> unavailable
1 -> exact value carried forward
2+ -> explicit choice
```

Do not use it to skip consent, optional intent, identity decisions, or a choice
whose meaning changes the write.

## Refresh after mutation

A post-write success view should be based on resulting state whenever the owning
service exposes enough state to reload it. This matters especially for:

- post-Selection Placement continuation;
- Portfolio creation continuity;
- Profile Binding/migration success;
- Current Portfolio build/export result rendering.

A stale or ambiguous refresh must fail closed rather than infer a successor
record.

## Navigation

Shared confirmation delegates B/M/Q parsing to Core
`pds_core.menu_navigation`.

Keep module-specific outer navigation intact. Do not invent a parallel
navigation vocabulary.

## Active versus dormant workflows

Issue #98 standardizes active teacher routes. The legacy
`portfolio_menu._curation_workflow` is intentionally left dormant because the
active Portfolio context routes curation through Candidate Review.

Do not use its remaining legacy confirmation strings as justification for
routing teachers back into it.

## Validation

Run the focused contract gate:

```powershell
python scripts/validate_guided_menu_interactions.py
```

The validator checks the shared contract, active-surface wiring, documentation,
package guards, repository-gate integration, and the #98 focused pytest matrix.

For complete repository qualification, use `scripts/validate_repository.py`
with the exact Core wheel required by the repository.
