# Selection and Placement Guidance v1

- **Issue:** #97
- **Contract:** `vitrine_selection_placement_guidance_v1`
- **Status:** Implemented transient actionability contract

## Purpose

This contract separates persisted Candidate/Profile semantic fit from the
current ability to create Selection or Placement intent.

`PortfolioCandidate.eligible_section_ids`,
`PortfolioCandidate.eligible_profile_rule_ids`, and their Evaluation provenance
remain historical semantic evidence. They are not rewritten when Portfolio
capacity, Placement state, or Arrangement state changes.

Current actionability is projected transiently by
`vitrine.selection_placement_guidance`.

## Operations

The projection is operation-aware:

```text
fresh_selection
placement
replacement
```

Fresh Selection requires a semantically eligible, placement-bearing,
non-prohibited section with remaining capacity and no Arrangement pointer
conflict.

Placement adds the rule that the same active Selection cannot already occupy the
same section.

Replacement releases the exact active predecessor Placements supplied by the
caller before capacity is evaluated. This preserves valid one-for-one
replacement in a full max-one section while still rejecting post-replacement
overflow caused by unrelated Placements.

## Section projection

Each section projection exposes semantic eligibility separately from current
actionability, including:

```text
section identity / label / operation
semantic Candidate eligibility
placement-bearing state
obligation / minimum
active Placement count
released Placement count
effective Placement count
maximum / remaining capacity
Arrangement pointer state / revision
current_actionable
bounded unavailability reason codes
relevant Candidate-matched Profile requirement IDs
```

`minimum_placements` is descriptive obligation context. It is never treated as
capacity.

## Unavailability reasons

The bounded reasons include:

```text
candidate_not_semantically_eligible
section_prohibited
section_not_placement_bearing
section_full
arrangement_pointer_conflict
selection_already_placed_in_section
```

They are transient observations and are not persisted into Candidate,
Evaluation, Proposal, Selection, or Placement records.

## Profile requirements

Requirement applicability is derived from structured fields only. A Candidate
matched rule is relevant to a chosen section only when the exact bound Profile
Revision requirement is section-scoped to that section.

Fresh decision requirement intent may be empty. When explicit requirement IDs
are supplied, every ID must be applicable to the exact selected sections.

## Write boundaries

Teacher menus are advisory surfaces, not authority. Canonical curation services
independently revalidate actionability for fresh Selection intent, ordinary
Placement, existing Proposal acceptance, and Selection replacement.

An existing Proposal remains immutable and readable if its target later becomes
unavailable. Positive acceptance fails closed against current actionability.
Negative rejection remains permitted and does not rewrite or retarget the
Proposal.

No unavailable target is silently substituted, auto-expired, or inferred.
