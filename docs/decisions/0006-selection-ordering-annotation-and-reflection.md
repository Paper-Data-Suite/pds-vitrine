# ADR 0006: Selection, Ordering, Annotation, and Reflection

- **Status:** Accepted
- **Date:** 2026-08-05
- **Accepted:** 2026-08-06 — approved by issue #13 portfolio foundation audit
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #8, “Define selection, ordering, annotation, and reflection records”
- **Related design:** [`../design/selection-curation-records.md`](../design/selection-curation-records.md)
- **Related examples:** [`../examples/selection-curation-examples.md`](../examples/selection-curation-examples.md)

## Context

Vitrine now has conceptual contracts for:

- Portfolio and Portfolio Subject identity;
- exact versioned Portfolio Profiles;
- Candidate discovery and source references;
- and producer-owned artifact-exposure boundaries.

Those contracts establish what may be considered for a Portfolio, but not how an authorized student, teacher, curator, or reviewer deliberately constructs the working Portfolio.

A curation model must support materially different workflows:

- a student proposes work and a teacher accepts or rejects it;
- a teacher directly selects work where the Profile permits direct curation;
- one selected source appears in several sections without duplicating source provenance;
- section item order changes over time;
- curator titles and captions differ from producer titles;
- rationales explain decisions but are not necessarily audience-facing;
- students or teachers create item, comparison, section, checkpoint, or whole-Portfolio reflections;
- exact curation revisions receive staged approval;
- a Selection is withdrawn or replaced without erasing history;
- and one coherent working state later becomes the input to immutable snapshot construction.

The model must also preserve existing authority boundaries:

- Candidates identify exact eligible producer projections;
- producer modules retain native source meaning;
- Portfolio Profiles define curation policy;
- Meridian owns grading evidence selection;
- institutional systems own authorization and consent;
- and issue #9 owns copied bytes and snapshot issuance.

A mutable list of selected files would lose this provenance and would make correction, review, migration, concurrency, and historical snapshot reproduction unsafe.

## Decision

Vitrine will use separate, immutable, append-preserving curation records for:

1. Selection Proposals;
2. Selection Decisions;
3. positive Portfolio Selections;
4. Selection lifecycle events;
5. Section Placements;
6. immutable Section Arrangement Revisions and explicit current pointers;
7. revisioned Selection Presentations;
8. Selection Rationales;
9. revisioned Annotations;
10. revisioned Reflection Records;
11. Curation Review Decisions scoped to exact target revisions;
12. immutable Working Portfolio Composition Revisions;
13. and explicit Composition Current Pointers.

The governing sequence is:

```text
Candidate
  -> Proposal
  -> Decision
  -> Selection
  -> Placement
  -> Arrangement
  -> Presentation / Annotation / Reflection
  -> Review Decision
  -> Composition Revision
  -> later Snapshot
```

No stage is implied by the preceding stage.

## Decision details

### Proposals and positive Selections are separate

A Proposal preserves actor intent before inclusion becomes authoritative working-Portfolio state.

Rejected, withdrawn, expired, and changes-requested Proposals remain canonical history but do not create positive Selections.

A system may create a recommendation or Proposal only where permitted. It must not silently activate a Selection.

### Selection Decisions are immutable

One Decision applies to one exact Proposal revision.

The initial decision vocabulary is:

```text
accepted
rejected
changes_requested
withdrawn
expired
```

A revised Proposal receives a new identity and predecessor reference.

Contradictory mutable statuses are not appended to one Proposal.

### One Selection binds one exact Candidate

A positive Portfolio Selection is scoped to:

```text
Portfolio
+ Portfolio Subject
+ exact Portfolio Profile Binding
+ exact Candidate
+ exact Candidate Evaluation relied upon
```

Candidate endpoint and curation context are immutable.

A later Candidate Current Pointer change does not retarget the Selection.

### Direct Selection requires equivalent provenance

A Profile may permit an authorized actor to select directly without a prior Proposal.

The direct workflow must still preserve:

- actor;
- asserted role;
- Profile authority rule;
- exact Candidate Evaluation;
- required rationale;
- time;
- and unresolved obligations.

The implementation may model this as an explicit direct-selection authority envelope or an equivalent implicit Proposal/Decision pair. It may not create an unattributed Selection.

### One active Selection, multiple Placements

For v0.1.0, one Candidate may have at most one active Selection within one Portfolio, Portfolio Subject, and Profile Binding.

When the same selected source appears in several permitted sections, Vitrine creates several Section Placements referencing the same Selection.

This preserves one source-selection decision while allowing several presentation roles.

### Placement is distinct from Selection

A Placement identifies one exact Profile section and optional requirement intent.

Changing a section creates a successor Placement and new arrangements. It does not rewrite the Selection.

Requirement intent is a curation claim, not a satisfied requirement finding.

### Ordering uses immutable complete arrangement revisions

Each Profile section has an immutable Section Arrangement Revision containing the complete ordered list of active Placement IDs for that section.

Ordering is not inferred from:

- creation time;
- filenames;
- Selection IDs;
- directory order;
- or mutable integer positions scattered across Placements.

Every insertion, removal, or reorder creates a new complete Arrangement Revision.

### Current arrangement is explicit

A Section Arrangement Current Pointer identifies the Arrangement Revision governing current working use.

Pointer updates use an expected predecessor or equivalent optimistic concurrency control.

Concurrent reorders fail closed. Last-write-wins behavior is rejected.

### Producer titles and curator presentation remain separate

Selection Presentation records curator-authored:

- display title;
- caption;
- context label;
- language;
- and intended presentation class.

It does not overwrite the producer source title preserved by the Candidate.

An intended `public`, `family`, or `reviewer` presentation class does not authorize that audience.

### Rationale, Annotation, and Reflection remain distinct

A **Selection Rationale** explains a curation action or decision.

An **Annotation** provides curator-authored explanatory or presentation context.

A **Reflection** is actor-authored interpretation under one exact Profile reflection rule and prompt version.

They are not combined into one generic notes field because they have different:

- authors;
- authority;
- targets;
- visibility expectations;
- lifecycle;
- and approval requirements.

### Annotation is revisioned

Annotations target exact Selections, Placements, sections, comparison sets, or Composition Revisions.

Corrections create successor revisions.

Annotations do not become producer facts, proficiency results, authorship findings, or audience authorization.

### Reflection scope is explicit

The initial Reflection scopes are:

```text
selection
placement
comparison_set
section
checkpoint
portfolio
```

A Reflection preserves:

- exact Profile Binding;
- exact reflection rule;
- prompt identity and version;
- author and role;
- exact target IDs;
- target ordering semantics where relevant;
- content mode;
- language;
- and revision history.

### Comparison Reflections bind exact targets

A comparison Reflection identifies every compared Selection and any semantic roles such as baseline, intermediate, or current.

Replacing a Selection does not rewrite the earlier Reflection.

A new comparison with a successor Selection requires a new Reflection revision.

### Reflection is interpretation, not proof

Reflection does not automatically prove:

- growth;
- proficiency;
- consent;
- remorse;
- confession;
- legal compliance;
- or external attestation.

### Curation review is scoped to exact revisions

A Curation Review Decision targets one exact Proposal, Selection, Placement, Arrangement Revision, Presentation revision, Annotation revision, Reflection revision, or Working Portfolio Composition Revision.

The initial review vocabulary is:

```text
approved
rejected
changes_requested
acknowledged
waived
```

Waiver is allowed only when the exact Profile rule and actor authority permit it.

### Approval does not carry silently

Approval remains valid historically for the exact target revision.

A changed target does not inherit approval automatically.

Profile reapproval rules determine whether a successor requires a new review.

### Approval does not grant unrelated authority

Curation approval does not establish:

- source-access authorization;
- recipient authorization;
- consent;
- redaction completion;
- signature validity;
- copied bytes;
- snapshot issuance;
- submission;
- or external acceptance.

### Working Portfolio Composition Revision freezes curation state

A Working Portfolio Composition Revision identifies one exact coherent curation state, including:

- active Selections;
- active Placements;
- exact section Arrangement Revisions;
- exact Presentation revisions;
- included Annotation revisions;
- included Reflection revisions;
- Profile validation findings;
- and unresolved obligations.

It contains no producer bytes.

Issue #9 will consume this exact revision when defining snapshot construction.

### Current composition is explicit

A Composition Current Pointer identifies the current working Composition Revision.

Currency is not inferred from greatest revision, newest timestamp, directory order, or newest Selection.

Pointer rollback may be permitted but remains explicit and nondestructive.

### Current curation records are canonical; views are derived

Canonical state includes Proposals, Decisions, Selections, lifecycle events, Placements, Arrangement Revisions and pointers, Presentations, Rationales, Annotations, Reflections, Review Decisions, Composition Revisions and pointers, and correction relationships.

Derived state includes selected-item lists, section views, order previews, approval queues, requirement-intent summaries, duplicate warnings, migration previews, and dashboards.

Derived state is rebuildable.

### Correction is nondestructive

Material endpoint corrections never edit an operational record in place.

Examples include changing:

- Portfolio;
- Portfolio Subject;
- Profile Binding;
- Candidate;
- Candidate Evaluation;
- section;
- reflection rule;
- approval target;
- or source representation.

The invalid record remains historical and a successor is created.

### Selection lifecycle is append-preserving

The initial lifecycle event vocabulary is:

```text
activated
withdrawn
replaced
invalidated
superseded
```

Current lifecycle is resolved from a validated event graph and explicit policy, not timestamp ordering.

### Replacement preserves all affected curation

Selection replacement creates a new Selection and explicit replacement relationship.

It records effects on:

- Placements;
- arrangements;
- Presentation;
- Annotation;
- Reflection;
- approvals;
- and Composition Revisions.

Old records are not deleted or retargeted.

### Profile migration does not silently migrate curation

Moving to a successor Profile Binding requires explicit analysis of:

- Candidate eligibility;
- section identity;
- requirement identity;
- placement rules;
- Reflection rules and prompts;
- approval rules;
- and reapproval triggers.

Successor Selections, Placements, arrangements, Reflections, approvals, and Composition Revisions are created where required.

Old curation remains reproducible under the old Profile revision.

## Producer-specific decisions

### ScoreForm

Vitrine may explicitly select one exact ScoreForm attempt Candidate or permitted question-evidence Candidate.

It must not:

- select highest, latest, first, official, or Grade-bearing attempt automatically;
- change ScoreForm attempt history;
- convert points to Grade or proficiency;
- or change Meridian grading attempt policy.

Separate attempts require separate Candidates and separate curation decisions.

### Quillan

Quillan's selected evidence remains producer-owned.

Vitrine selects only the exposed Quillan projection.

It must not:

- reopen candidate, duplicate, replacement-only, or excluded evidence;
- change `selected_evidence_id`;
- alter review state;
- expose private notes;
- or merge original work and rendered feedback into one Selection.

### Concord

Concord Selections preserve exact:

- Artifact;
- Page;
- Author;
- Subject;
- Group;
- contribution;
- representation;
- Score target;
- privacy;
- moderation;
- and correction semantics.

Vitrine does not infer authorship from Group Membership or individual Score from Group Score.

Curator Annotation cannot override disputed or unknown attribution.

### Portia

Only an exact Portia-owned portfolio-safe projection may be selected.

Selection does not reveal or authorize access to the underlying Portia graph.

Revoked, withdrawn, corrected, or replaced safe projections preserve historical curation and require explicit current-use review.

### Meridian

Portfolio Selection does not affect Meridian evidence eligibility, Grade-item membership, attempt policy, proficiency, Grades, overrides, or reports.

## Core impact

No blocking Core change is required.

Core should not gain a universal Selection, Annotation, Reflection, or Portfolio approval registry.

Those records are Vitrine-specific consumer policy and belong in the Vitrine namespace.

## Consequences

### Positive

- Unsuccessful student and teacher proposals remain auditable.
- Positive Selections have exact source and authority provenance.
- Repeated section appearance does not duplicate source selection.
- Ordering is deterministic and conflict-aware.
- Producer and curator titles remain distinct.
- Rationale, Annotation, Reflection, and Approval retain honest meanings.
- Reflection prompts and targets remain historically reproducible.
- Approval staleness is explicit.
- Whole-Portfolio review targets one coherent curation revision.
- Replacement and Profile migration preserve history.
- Snapshot construction receives one exact curation input.
- Producer and grading authority remain intact.

### Costs

- The model contains several explicit record families.
- Reordering creates complete Arrangement Revisions.
- Composition changes create new immutable revisions.
- Offline concurrency requires conflict handling.
- Profile migration requires deliberate curation analysis.
- Historical prompt and projection versions may need long-term support.
- UI design must explain distinctions that a single mutable list would hide.

### Risks

- Implementers may collapse rationale, Annotation, and Reflection into free-form notes.
- UI may imply approval or audience permission where none exists.
- Mutable caches may be mistaken for canonical state.
- Broad direct-selection workflows may bypass required student participation.
- Curator captions may accidentally assert unsupported authorship or proficiency.
- Profile migration may be treated as a bulk copy.
- Concurrent reorder conflicts may be hidden by last-write-wins storage.

These risks require exact schemas, validation, permission checks, conflict-aware writes, and adversarial tests in later implementation work.

## Rejected alternatives

### Treat Candidate existence as automatic Selection

Rejected because Candidate eligibility is not actor curation intent.

### Keep one mutable selected-items list

Rejected because it loses proposal, authority, correction, replacement, ordering, and review history.

### Represent rejected Proposals as inactive Selections

Rejected because a positive Selection never existed.

### Let the system select automatically

Rejected because recommendation and actor decision have different authority.

### Duplicate Selection records for repeated section appearance

Rejected because source-selection provenance would be duplicated and could diverge.

### Order by timestamp, filename, or ID

Rejected because incidental ordering is not curator authority.

### Store mutable integer positions on Placements

Rejected as the sole ordering authority because partial writes and concurrent updates can create gaps, duplicates, and ambiguous order.

### Let curator title overwrite producer title

Rejected because source provenance and presentation metadata have different authority.

### Collapse rationale, Annotation, and Reflection into `notes`

Rejected because the concepts differ in author, purpose, visibility, scope, and review.

### Treat Reflection as proof of proficiency or growth

Rejected because Reflection is actor-authored interpretation, not an authoritative academic calculation.

### Treat Reflection as confession, remorse, or compliance

Rejected because that would create unsafe and false semantics, especially around sensitive workflows.

### Store approval as a Boolean

Rejected because approval requires target, revision, actor, authority, time, decision, and reason.

### Carry approval automatically to changed revisions

Rejected because the approved content may have changed materially.

### Treat Selection as source authorization

Rejected because source access is a separate authorization decision.

### Treat Selection as audience consent

Rejected because curation does not verify recipient, guardian, consent, or disclosure authority.

### Select ScoreForm highest or latest attempt automatically

Rejected because ScoreForm preserves all attempts and Meridian owns grading attempt policy.

### Let Vitrine alter Quillan evidence state

Rejected because Quillan owns submission assembly and selected evidence.

### Infer Concord authorship from Group Membership

Rejected because Concord models membership and authorship separately.

### Let a Portia Selection expose the source graph

Rejected because only the minimum-necessary safe projection is permitted.

### Let Portfolio Selection change Meridian grading evidence

Rejected because Portfolio curation and grading policy are separate domains.

### Retarget Selection to a successor Candidate

Rejected because historical source meaning would be rewritten.

### Silently carry curation through Profile migration

Rejected because section, eligibility, reflection, and approval rules may have changed.

### Hard-delete withdrawn or replaced records

Rejected because audit, correction, and snapshot provenance require historical resolution.

### Infer working composition from directory contents

Rejected because filesystem presence is not curation authority.

### Embed snapshot construction in Selection records

Rejected because Selection identifies source inclusion intent, while snapshots own copied bytes and issuance.

### Add a Core Selection registry

Rejected because Portfolio curation is Vitrine-owned consumer policy rather than shared canonical infrastructure.

## Follow-up

Later contract and implementation issues must define:

- exact serialized record schemas;
- actor-reference integration;
- persistence paths and atomic-write behavior;
- lifecycle graph validation;
- pointer transition records;
- text and structured-content restrictions;
- conflict-resolution UI;
- Profile evaluator integration;
- privacy and audience authorization;
- snapshot construction from exact Composition Revisions;
- retention and archival treatment;
- and comprehensive synthetic and property-based tests.

## Related decisions

- [ADR 0001: Vitrine Module Boundaries and Authority](0001-vitrine-module-boundaries-and-authority.md)
- [ADR 0002: Portfolio Subject Identity and Roster Linking](0002-portfolio-subject-identity-and-roster-linking.md)
- [ADR 0003: Versioned Portfolio Profiles](0003-versioned-portfolio-profiles.md)
- [ADR 0004: Candidate Discovery and Source References](0004-candidate-discovery-and-source-references.md)
- [ADR 0005: Producer Artifact Exposure Boundaries](0005-producer-artifact-exposure-boundaries.md)
