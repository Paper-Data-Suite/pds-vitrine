# Portfolio Profile Workflows v1

- **Issue:** #31 — Implement versioned Portfolio Profile services
- **Milestone:** v0.2.0 — Runtime Foundations and Fixture-Backed Portfolio Slice
- **Status:** Operational runtime contract
- **Schema version:** `1`

## Purpose

This contract operationalizes versioned Vitrine Portfolio Profiles for the
`improvement` and `showcase` purpose kinds. It implements immutable policy,
explicit lifecycle activation, exact Portfolio Binding, local overlays, and
explicit migration while preserving the foundation design in ADR 0003.

It does not implement Candidate discovery, requirement findings, authorization,
Snapshot construction, regulated Profile instances, or external submission.

## Exact identities

A Profile Revision is identified only by:

```text
portfolio_profile_id + profile_revision
```

A requirement is identified by:

```text
portfolio_profile_id + profile_revision + requirement_id
```

An Overlay Revision is identified by:

```text
overlay_id + overlay_revision
```

These identities do not imply operational authority.

## Canonical record families

The foundational graph records remain unchanged:

- `PortfolioProfileFamily`
- `PortfolioProfileRevision`
- `PortfolioProfileBinding`

Issue #31 adds canonical supplemental records:

- `PortfolioProfileRequirement`
- `PortfolioProfileLifecycleEvent`
- `PortfolioProfileOverlayRevision`
- `PortfolioProfileComposition`
- `PortfolioProfileMigration`

The supplemental records are persisted through canonical storage but do not add
required collections to the foundational `VitrineRecordGraph`. Existing #28
fixture bytes therefore remain unchanged.

## Revision creation and activation

Creating a Profile Revision does not activate it.

Operational creation stores the complete foundational Revision and its exact
Requirement set atomically. The initial service supports `improvement` and
`showcase` only.

Activation is a separate append-preserving lifecycle event. A Revision is
bindable only when its unique explicit lifecycle head is `activated`.

The following never establish activation:

- largest Profile revision;
- newest timestamp;
- lexical identifier order;
- filename or directory order;
- derived SQLite state.

## Lifecycle

Supported lifecycle events are:

```text
activated
deprecated
superseded
withdrawn
retired
```

Events form an explicit predecessor chain for one exact Profile Revision.
Branching or multiple unresolved heads are integrity conflicts.

`deprecated`, `superseded`, `withdrawn`, and `retired` revisions remain
historically resolvable but are not selected for ordinary new Bindings.

## Stable Requirement identity

Requirement IDs may continue across direct successor Revisions only when the
policy-bearing meaning remains equivalent.

Presentation-only changes such as a title may preserve the ID. Changes to
obligation, statement meaning, scope, satisfaction class, or controlling
authority cannot silently reuse the same stable ID.

Material replacement uses a different requirement ID and an explicit
`replaces_requirement_id` reference to the direct predecessor Requirement.

Initial Requirement kinds are:

```text
section
selection
reflection
audience
approval
output
```

Initial obligation kinds are:

```text
required
optional
conditional
prohibited
```

The complete future condition/finding engine is outside #31. No Requirement may
execute arbitrary code.

## Binding

A Portfolio Profile Binding always references one exact activated Revision.

A Portfolio has at most one unresolved Binding head. Binding heads are resolved
from explicit predecessor relationships, never from `bound_at`, Profile revision
number, or Binding ID ordering.

If a Portfolio already has an active Binding to another Revision, ordinary bind
fails and explicit migration is required.

## Applicability

Binding and migration re-check the exact target Revision's modeled applicability.
Where a Revision constrains school year, institution, program, content area, or
effective dates, the supplied Binding context must match those values.

Missing context does not silently mean applicable.

## Migration

Migration requires an existing active Binding and an exact bindable target
Revision.

Requirement comparison is deterministic and classifies:

```text
unchanged
added
removed
replaced
materially_changed
unresolved_mapping
```

A title-only change may be `unchanged`. Materially changed stable-ID reuse is
invalid canonical Profile continuity. Explicit replacement is `replaced`.

Migration creates:

- one successor `PortfolioProfileBinding`;
- one `PortfolioProfileMigration` record;
- exact source and target Revision references;
- deterministic requirement impact;
- unresolved and reapproval requirement IDs.

The predecessor Binding remains immutable and historical.

Existing Selections, Placements, Arrangements, working Composition history,
future Reflections/approvals/findings, and issued Snapshots are not rewritten or
automatically declared sufficient under the target Profile.

## Local overlays and composition

Overlay Revisions are immutable, attributable local inputs. They reference exact
component Profile Revisions.

The initial runtime supports explicit Requirement additions/replacements plus
section and audience-rule additions. It does not implement dynamic inheritance.

Composition:

1. loads exact component Revisions;
2. verifies their explicit lifecycle state;
3. merges exact Requirement identities;
4. applies explicit Overlay changes;
5. rejects unresolved conflicts;
6. verifies the caller-provided effective Revision contains the flattened
   sections and audience rules;
7. writes a self-contained effective Revision and exact Requirement set;
8. records `PortfolioProfileComposition` provenance;
9. leaves the effective Revision inactive until separately activated.

Silent last-write-wins is prohibited.

A local Overlay cannot silently weaken a controlling `required` or `prohibited`
Requirement.

## Improvement and showcase

Purpose kind is classification only; it does not expand into hidden rules.

Improvement and showcase Revisions must explicitly contain their own sections,
requirements, audience rules, and authority context. Vitrine does not infer
baseline/current evidence, public review, highest ScoreForm attempt, latest work,
or any other policy merely from the purpose kind.

Audience rules describe policy but do not grant disclosure authorization.

## Canonical storage

All mutations use expected-state guarded canonical persistence. If canonical
state changes between review and commit, the operation fails with `state_conflict`.

Canonical Profile reads and operational decisions never require the derived
SQLite catalog.

## CLI

Power-user commands live under:

```text
vitrine profile ...
```

Complex immutable Revision and Overlay inputs may be supplied as exact JSON.
Direct commands are noninteractive.

## Teacher menu

The teacher menu exposes Portfolio Profile workflows using the same application
services. Standard navigation remains:

```text
H. Help
B. Back
M. Main Menu
Q. Quit
```

Screens clear after a teacher makes a choice by default. Each stage displays only
information required for the next action. Full Profile JSON and unrelated policy
history are not retained on screen.

## Boundaries

```text
Profile requirement
  != Requirement finding
  != source authorization
  != recipient authorization
  != approval record
  != Snapshot issuance
  != external acceptance
```

No Core or producer canonical record is mutated by these services.
