# Teacher Information Architecture v1

- **Issue:** #95
- **Branch:** `95-teacher-information-architecture-provenance-drilldown`
- **Contract:** `vitrine_teacher_information_architecture_v1`
- **Status:** Slice 3 — Portfolio, Candidate Inbox, and guided Candidate Review presentation

## Purpose

This contract defines the teacher-facing presentation boundary over Vitrine's
existing canonical Portfolio, Subject, Profile, curation, and Snapshot state.

It does not create another source of truth.

```text
canonical identity != display identity
exact provenance != primary teacher presentation
human-readable label != authority
technical detail hidden by default != technical detail discarded
low information density != loss of auditability
```

The ordinary teacher surface presents instructional context and current workflow
meaning first. Exact IDs, revisions, contracts, pointers, hashes, and lineage
remain available through explicit Technical Details / Provenance views when they
are useful for audit, diagnostics, or exact disambiguation.

## Authority

Human-readable labels are display-only.

They must never become authority for:

- Portfolio or Portfolio Subject identity;
- cross-class student association;
- Profile Binding;
- Candidate currentness;
- Selection or Placement provenance;
- Snapshot identity;
- authorization or disclosure.

Exact canonical references remain authoritative.

## Teacher information hierarchy

### Primary context

Ordinary teacher views should prefer:

- student / Portfolio display label;
- Portfolio purpose;
- human-readable Profile label and relevant revision;
- assignment/evidence labels already safely available;
- Portfolio section names and roles;
- current status;
- the decision or next action relevant to the screen.

### Secondary context

Show when useful to the current task:

- exact class-qualified student relationships;
- current/stale/attention state in teacher language;
- representation or media type;
- section capacity in ordinary language;
- current curation status;
- bounded explanatory dates or status.

### Technical Details / Provenance

Keep available, but normally secondary:

- opaque Vitrine record IDs;
- Profile Binding IDs;
- Candidate/Evaluation/Selection/Placement/Arrangement IDs;
- Publication and Snapshot IDs;
- record and pointer revisions;
- source-record identifiers;
- manifest/reader/projection contracts;
- provider/adapter identifiers;
- hashes/fingerprints;
- current-pointer and evaluation history;
- low-level reason/action/state codes.

A technical view is still privacy-bounded. Its name does not authorize disclosure
of raw producer bodies, answer keys, private notes, private paths, suppressed
Candidate state, authorization-provider prose, or absolute workspace paths.

## Slice 1 Portfolio projection

`vitrine.teacher_presentation` introduces the first transient view:

```text
TeacherPortfolioOverview
TeacherSubjectLink
```

`build_teacher_portfolio_overview(...)` composes existing read services only:

```text
Portfolio summary
+ exact Portfolio Subject detail
+ active Profile Binding
+ exact Profile Revision
-> transient teacher Portfolio overview
```

No record is persisted and no current pointer is advanced.

The default Portfolio Overview shows teacher context and exact class-qualified
links. An explicit `T. Technical details / provenance` action exposes the exact
Portfolio, Subject, Profile Binding, Profile, Subject-link, and state-summary
identifiers already available from canonical state.

Subject management is no longer entered implicitly after viewing the Portfolio
Overview. The teacher must explicitly choose `View / manage Subject details`.

## Slice 2 Candidate Inbox projection

The teacher Candidate Inbox now separates the ordinary decision-facing detail
from the exact bounded provenance already available in
`CandidateInboxDetail`.

The default teacher detail presents:

- recognizable evidence label already present in canonical Candidate state;
- Portfolio and student display context;
- Profile label and revision;
- Profile purpose;
- Evaluation eligibility;
- eligible Profile sections using their existing human labels;
- Candidate condition/status;
- current/stale/unresolved state in teacher language;
- attention signal;
- Selection state.

The default detail does not lead with Entry, Candidate, Evaluation, Profile
Binding, Publication, producer source, Artifact, contract, reason-code, or
pointer-history identifiers.

`T. Technical details / provenance` exposes the existing bounded exact detail,
including those identifiers, contracts, availability observations, Evaluation
history, and current-pointer history. This is a presentation split only.
Candidate currentness, staleness, eligibility, attention, and Selection state
continue to come from `vitrine_candidate_inbox_v1`.

Section labels are resolved only by exact `eligible_section_ids` against the
already-bound exact Profile Revision. A label never replaces the section ID as
authority. Missing labels fall back to the exact section ID rather than
fabricating meaning.

Issue #96 still owns richer evidence naming, representation differentiation,
Profile-role guidance, and evidence preview.

## Slice 3 guided Candidate Review presentation

Guided Candidate Review now reuses the teacher Candidate projection for its
ordinary review context. The default review screen presents evidence, student,
Portfolio, Profile, eligibility/status/currentness, attention, Selection state,
and human-readable eligible Portfolio sections before any technical identity.

The exact prior review projection remains available through
`T. Technical details / provenance`, including Entry/Candidate/Profile Binding,
current-versus-curation Evaluation IDs, Core Publication/producer/Artifact
identity, exact section IDs, Arrangement pointer revisions, Proposal IDs, and
Selection/Evaluation/Placement IDs.

Ordinary numbered section, Profile-requirement, active-Selection, and pending-
Proposal choices no longer require the teacher to read opaque IDs. The chosen
objects still carry their exact canonical IDs into the unchanged #66 planners
and executors.

Consequential mutation confirmation screens may continue to show the exact
frozen identifiers, state revisions, and Arrangement-pointer observations that
the teacher is explicitly about to confirm. Hiding those values is not required
when they are directly relevant to replay/concurrency safety.

This slice does not alter Candidate eligibility, available sections, section
capacity, Proposal/Selection/Placement validity, curation authority, or action
planning. Issue #97 owns domain-correct Selection/Placement choice behavior and
Issue #98 owns broader transition/confirmation mechanics.

## Privacy and provenance boundaries

Viewing the presentation projection or its technical drill-down must not:

- discover Candidate sources;
- invoke producer readers;
- acquire producer Artifact bytes;
- request new authorization;
- create or revise canonical Vitrine records;
- advance current pointers;
- perform curation;
- build a Snapshot;
- authorize or deliver disclosure.

Later #95 slices extend this same hierarchy to Candidate, Candidate Review,
Working Composition, build/export, and Attention surfaces without changing their
canonical authority.
