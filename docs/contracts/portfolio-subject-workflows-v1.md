# Portfolio Subject Workflows v1

**Status:** Implemented
**Issue:** #30

## Purpose

This contract defines the first executable Vitrine workflows for workspace-scoped
Portfolio Subject identity and exact Core roster associations. It implements the
accepted Portfolio Subject identity design without creating an institutional
person registry.

## Exact roster identity

One historical Core roster endpoint is exactly:

```text
school_year + class_id + student_id
```

All three values are preserved. `student_id` remains a string, including leading
zeros. Display names, preferred names, repeated local IDs, periods, course
sequence, and producer history are never identity authority and never trigger an
automatic cross-class association.

At confirmation time Vitrine requires valid Core class metadata, an exact school
year match, a valid canonical roster, and exactly one matching student ID.

## Canonical identity history

The existing `PortfolioSubject` and `PortfolioSubjectClassLink` records remain
unchanged. Issue #30 adds canonical, append-only history records:

- `PortfolioSubjectDisplaySnapshot` — nonauthoritative roster display values;
- `PortfolioSubjectIdentityDecision` — attributable creation, confirmation,
  invalidation, supersession, merge, and split decisions;
- `PortfolioSubjectIdentityTransition` — successor-based Subject transitions;
- `SubjectAssociationAllocation` — exact predecessor-link allocation for merge
  and split transitions.

These records are persisted by the canonical storage layer but are not added as
required collections to `VitrineRecordGraph`. Existing foundational graph fixture
bytes therefore remain stable.

## Current state is derived

Current Subject and link status is derived from immutable decision and transition
history. Historical records are never rewritten to change status.

A confirmed link may become historical through explicit invalidation or
supersession. Loss of a current Core roster source does not invalidate historical
confirmation and never causes name-based repair.

A duplicate active exact-reference claim is a diagnosable identity conflict. It
blocks ordinary exact-reference resolution but remains readable so an explicit
merge, split, invalidation, or supersession can repair the identity state.

## Creation and linking

Teacher or CLI creation of a Portfolio Subject persists atomically:

1. one new Subject;
2. one exact class/year/student link;
3. one display snapshot;
4. attributable creation and confirmation decisions.

Adding another class or year requires independent explicit confirmation and uses
the same guarded persistence protocol.

Identity confirmation does not grant source access, disclosure authority,
producer authorship, grading eligibility, or institutional identity.

## Correction and invalidation

A wrong link endpoint is never edited.

Replacement creates a new link and preserves the old link as superseded history.
Invalidation preserves the old link and records an explicit terminal decision.

`predecessor_link_id` is used for same-Subject link correction. Merge/split
cross-Subject ancestry is expressed through transition allocations instead.

## Merge

Merge requires two or more current predecessor Subjects and creates exactly one
new successor Subject.

- predecessors remain canonical history;
- current predecessor links are superseded explicitly;
- successor links are created for the exact references that remain valid;
- duplicate exact references are deliberately consolidated;
- allocations identify all predecessor links represented by each successor link;
- existing Portfolios remain bound to their historical Subjects and are only
  reported as affected.

No producer data or issued Snapshot is moved or rewritten.

## Split

Split requires one current predecessor Subject and two or more successor groups.
Every current predecessor link must be allocated exactly once.

- the predecessor Subject remains historical;
- one new Subject is created per group;
- successor links preserve exact roster references;
- allocation is explicit and validated;
- existing Portfolios remain bound to the historical predecessor.

Vitrine never infers split groups from names, student IDs, classes, or artifacts.

## Concurrency

Application workflows observe one canonical Vitrine state revision before the
human decision and commit through the #29 guarded persistence API using that exact
revision. A stale writer fails with a state conflict; the decision is not silently
replayed against newer state.

Core roster references are revalidated before mutation.

## CLI and teacher menu

Both interfaces are first-class and call the same presentation-independent
application services.

Direct CLI commands are noninteractive and expose `vitrine subject` operations
for list, show, create, link, correction, invalidation, merge, and split.

Teacher menus use the shared PDS navigation conventions:

```text
H. Help
B. Back
M. Main Menu
Q. Quit
```

After a choice, the default behavior is to clear the screen and render only the
information needed for the next action. Roster lists, prior menus, and detailed
history do not remain visible on confirmation screens unless they are required
for the decision.

## Privacy

Vitrine stores only the identity information required for the local workflow.
It does not copy complete rosters or identity documents and does not store birth
dates, addresses, guardian records, disability details, intervention history, or
behavioral/biometric-like matching signals.

## Nonauthoritative derived state

Identity reads remain canonical-JSON based. The SQLite catalog is optional
acceleration only. Missing or corrupt catalog state cannot change identity
results.
