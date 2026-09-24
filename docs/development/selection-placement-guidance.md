# Selection and Placement guidance development

Issue #97 centralizes Selection/Placement actionability in
`vitrine.selection_placement_guidance`.

## Architectural boundary

Keep these concepts separate:

```text
semantic Candidate/Profile fit
!=
current Selection/Placement actionability
```

The former is persisted Candidate/Evaluation evidence. The latter is derived
from exact current Portfolio curation state.

Do not "fix" full or conflicted sections by mutating
`eligible_section_ids`, `eligible_profile_rule_ids`, or historical Proposal
intent.

## Reusable projection

Use `project_selection_placement_guidance(...)` for:

```text
fresh Selection intent
ordinary Placement
Selection replacement
```

Use `profile_requirement_ids_for_sections(...)` to derive the exact
section-scoped requirement intersection for fresh Selection decisions.

Callers should consume `current_actionable` and bounded reason codes rather than
reimplementing cardinality or Arrangement logic.

## Canonical enforcement

Menu filtering is not sufficient. Canonical write paths must independently
revalidate through the shared projection.

The curation service preserves its stable `curation.*` error vocabulary while
mapping shared read-model unavailability into the corresponding canonical
workflow error.

Existing historical Proposal rejection is intentionally different from
acceptance: rejection may close stale historical intent, while acceptance would
create positive current Selection state and therefore must revalidate.

## Replacement

Replacement capacity is transaction-aware.

The exact set of active predecessor Placement IDs is supplied as
`releasing_placement_ids`. The projection subtracts only those Placements before
evaluating target capacity. It must never free unrelated Placement capacity.

This is what permits:

```text
max-one section
+ predecessor owns the current Placement
+ one-for-one replacement
= actionable
```

while still rejecting a target occupied by an unrelated Selection.

## Candidate Review presentation

`CandidateReviewDetail.sections` remains the semantic Profile-fit projection.
Its rows may expose current fresh-selection observations, but removing a row
because it is currently full would erase useful semantic context.

Teacher action menus filter to operation-specific actionability. Replacement
must request replacement guidance rather than reuse fresh-selection availability.

## Validation

Run:

```powershell
python scripts/validate_selection_placement_guidance.py
```

The validator checks contract fields, bounded reasons, integration at planner
and service boundaries, teacher-menu wiring, documentation, package guards, and
repository-gate integration.
