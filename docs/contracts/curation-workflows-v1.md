# Curation Workflows v1

## Status

This contract implements the v0.2.0 fixture-backed curation slice from issue #34.
It is additive to the frozen foundational runtime records established by #28.

## Governing separation

```text
Candidate != Proposal != Decision != Selection != Placement
Selection != grading-evidence selection
Annotation != producer fact
Reflection != Grade, proficiency, or proof of growth
Curation review != disclosure authorization
Composition != Snapshot
```

## Frozen foundational records

The serialized meanings of these existing records remain unchanged:

```text
PortfolioSelection
PortfolioPlacement
SectionArrangementRevision
WorkingPortfolioCompositionRevision
VitrineRecordGraph
```

Workflow history is represented by additional top-level records rather than by
adding fields to those frozen records.

## Additive record families

The executable curation layer adds:

```text
SelectionProposal
SelectionDecision
SelectionLifecycleEvent
PlacementLifecycleEvent
SectionArrangementPointerRevision
CurationRationale
CurationAnnotation
PortfolioReflection
CurationReviewDecision
WorkingPortfolioCompositionInventory
WorkingPortfolioCompositionPointerRevision
```

These records are persisted canonically but are not added to the locked
`VitrineRecordGraph` envelope. `vitrine.curation_state` projects and validates
their relationships with the existing Candidate, Selection, Placement,
Arrangement, Profile, and Composition records.

## Authority

Every mutating application service requires an injected curation-authority
answer:

```text
allowed
denied
unresolved
```

Actor attribution is not authorization. An absent answer is not permission.
Profile titles, statements, and other prose are never parsed as authorization
rules.

Curation authority is also not source-read authorization, recipient
authorization, consent, or disclosure authorization.

## Proposal and decision

A Proposal records actor intent toward one exact Candidate and Candidate
Evaluation in one exact Portfolio/Profile context. A system suggestion remains
a Proposal until an explicitly authorized Decision occurs.

Decision outcomes are:

```text
accepted
rejected
changes_requested
withdrawn
expired
```

Only `accepted` creates a positive `PortfolioSelection`. Accepted Decision,
Selection, and initial `activated` lifecycle event are committed atomically.
Direct Selection is implemented as an explicit direct-selection Proposal plus
accepted Decision rather than as an unattributed shortcut.

## Selection lifecycle

Lifecycle events are append-preserving:

```text
activated
withdrawn
replaced
invalidated
superseded
```

Current Selection state comes from one validated lifecycle head, never the
newest timestamp. A Candidate has at most one active Selection in one exact
Portfolio/Profile Binding. Historical Selections remain resolvable.

A conditional Candidate may be curated only when the authority decision
explicitly acknowledges the Candidate condition. Selection does not clear that
condition.

## Placement and presentation

A Placement requires an active Selection and a Candidate-eligible,
non-prohibited Profile section. Section maximum cardinality is enforced.

One Selection may appear in several eligible sections through several
Placements. Duplicate active same-section Placement is rejected.

`PlacementPresentation` remains curator-authored display state. Producer source
metadata and the Candidate display snapshot are not overwritten. A presentation
change creates a replacement Placement and successor Arrangement rather than
mutating the original Placement.

## Arrangement and current pointer

A `SectionArrangementRevision` is the complete explicit ordered Placement list
for one section. Every insert, removal, replacement, or reorder creates a new
complete revision.

`SectionArrangementPointerRevision` provides append-preserving explicit current
state. Updates require both the exact observed Vitrine state revision and the
expected Arrangement pointer revision. Concurrent reorder uses fail-closed
optimistic concurrency; there is no last-write-wins merge.

## Rationale and Annotation

Rationale is process provenance for a curation action. It is distinct from
Annotation and Reflection and is not automatically audience-facing.

Annotation is revisioned Vitrine-authored explanatory context. Supported scopes
include Selection, Placement, section, comparison set, and Composition.
Annotation does not become producer feedback, source authorship, Score, Grade,
proficiency, approval, or permission.

## Reflection

Reflection is revisioned actor-authored interpretation tied to an exact Profile
Reflection requirement, prompt identity/version, and exact targets.

Supported scopes include:

```text
selection
placement
comparison_set
section
checkpoint
portfolio
```

Comparison Reflection identifies every Selection explicitly and preserves
semantic roles such as `baseline` and `later`; roles are not inferred from
timestamps.

Reflection is not proof of growth, proficiency, mastery, consent, confession,
remorse, or compliance.

## Curation review

Review outcomes are:

```text
approved
rejected
changes_requested
acknowledged
waived
```

A Review targets one exact immutable curation revision/state. When it claims to
address a Profile approval requirement, that exact requirement must exist.
Waiver requires explicit waiver authority.

Approval never carries automatically to a changed Annotation, Reflection,
Arrangement, or Composition. Curation approval does not authorize disclosure or
Snapshot issuance.

## Withdrawal and replacement

Withdrawal and invalidation append lifecycle state and preserve all prior
records. Replacement creates a new Candidate-bound Selection with its own
Proposal/Decision provenance. The old Selection is never retargeted.

Placement migration during Selection replacement is explicit and section
eligibility is reevaluated. Historical Reflections continue to reference their
historical Selections.

## Candidate source currency

Before a new positive Selection, Vitrine reloads canonical Core Publication
metadata and exact publication-series/withdrawal state. It does not reread the
producer manifest. A historical or withdrawn Candidate source is never silently
retargeted to a successor Publication.

Later source withdrawal does not erase historical curation.

## Working Composition

`WorkingPortfolioCompositionRevision` remains the primary immutable byte-free
Composition identity and preserves exact Selection, Placement, and Arrangement
IDs.

`WorkingPortfolioCompositionInventory` is a one-to-one additive companion that
freezes exact:

```text
rationale IDs
Annotation/Reflection revisions
applicable Review decisions
Profile requirement IDs
unresolved obligation codes
```

Coherence is either:

```text
coherent
coherent_with_unresolved_obligations
```

It is never labeled approved, authorized, disclosure-ready, or issue-ready.
Unknown or human-only Profile semantics remain unresolved rather than being
parsed from requirement prose.

`WorkingPortfolioCompositionPointerRevision` supplies explicit current working
Composition state. Composition creation requires the expected Vitrine state and
expected pointer revision and commits Composition, Inventory, and pointer
atomically.

The Snapshot builder in #35 must consume the exact Composition Revision plus its
exact Inventory rather than recomputing current curation state.

## Producer boundaries

Fixture-backed ScoreForm attempts remain separate and Vitrine never chooses an
official, best, highest, or latest grading attempt. Quillan work and student
feedback remain separate. Concord Group Membership, Artifact Author,
documented contribution, Artifact Subject, and Group Score target remain
distinct. Portia ingestion is not added. Meridian is not a runtime dependency.

## Guided Candidate review and Selection

Issue #66 adds `vitrine_guided_candidate_review_v1` as a transient
presentation-independent orchestration layer over the Candidate Inbox and these
canonical curation services. It does not add a durable review-session record or
a second Selection model.

Fresh teacher decline is represented atomically as an optional rationale plus
`SelectionProposal(proposal_origin=teacher)` and
`SelectionDecision(decision=rejected)`, with no positive Selection or Placement.
Fresh positive Selection continues through direct-selection Proposal + accepted
Decision + Selection + activation event.

Guided actions require explicit section intent, preserve the distinction between
Candidate Inbox current Evaluation and immutable Candidate/curation provenance
Evaluation, and carry exact observed Vitrine state revisions. Placement,
withdrawal, and replacement also carry exact observed Arrangement pointer
revisions. Replacement requires a disposition for every active old Placement;
the guided path never infers same-section preservation or first/best/all section
intent.

Annotation, Reflection, and curation Review remain the existing revisioned
canonical records. Teacher acknowledgement of a Candidate condition does not
clear the condition, and every mutation continues through the injected
`CurationAuthorityGate`.

## Failures

Application failures use stable `curation.*` codes through
`CurationWorkflowError`. Diagnostics are bounded and must not include student
work bodies, private producer material, manifest contents, or workstation paths.

## Guided Working Composition preparation handoff

Issue #67 adds a transient preparation/explanation layer over this canonical
curation contract. `prepare_working_composition(...)` and canonical
`create_working_composition(...)` share the same Composition derivation.
Prepared freeze revalidates Vitrine state, the Composition pointer, bounded Core
Publication currentness, and the deterministic preparation fingerprint before
the canonical write. Preparation is not a new durable curation record and does
not clear unresolved obligations.
