# Guided Working Composition v1

Issue #67 defines the teacher-facing preparation boundary for freezing Vitrine
curation into one immutable Working Portfolio Composition.

Contract identity:

```text
vitrine_guided_working_composition_v1
```

## Authority and canonical state

This contract is a transient orchestration and explanation layer over the
canonical curation contract. It does not add a second Composition model or a
durable preparation/session record.

Canonical durable records remain:

```text
WorkingPortfolioCompositionRevision
WorkingPortfolioCompositionInventory
WorkingPortfolioCompositionPointerRevision
```

The canonical write primitive remains `create_working_composition(...)`.
Preparation and canonical writes share the same
`WorkingCompositionDerivation` semantics.

## Governing distinctions

```text
working curation != Working Composition
Working Composition preparation != Working Composition
Working Composition != Audience Context
Working Composition != Snapshot

coherent != complete
coherent != approved
coherent_with_unresolved_obligations != invalid

Candidate stale != automatically invalid
Curation Review != disclosure authorization
teacher confirmation != obligation cleared
```

The workflow must not rank Candidates, select evidence automatically, infer
best/latest/highest evidence, claim improvement or proficiency, or authorize
disclosure.

## Read-only preparation

`prepare_working_composition(...)` loads one exact Vitrine state revision and
returns a transient `WorkingCompositionPreparation`.

Preparation exposes at least:

- exact Portfolio, Subject, Profile Binding, and Profile Revision;
- observed Vitrine state revision;
- observed Working Composition pointer revision;
- current and predicted Composition revisions;
- predicted create/reuse disposition;
- exact semantic Composition/Inventory payload;
- ordered Profile sections;
- exact current Arrangement identity/revision/pointer state;
- exact Arrangement-ordered Placements;
- active Selections, including unplaced Selections;
- structured Profile Requirement status;
- bounded Core Publication current-use observations;
- applicable exact curation Reviews;
- bound Profile audience constraints;
- deterministic preparation fingerprint.

Preparation writes no Vitrine record, requests no curation authority, invokes no
Candidate discovery, invokes no producer reader, and creates no Audience
Context or Snapshot state.

## Ordering

Section order is the explicit order stored by the bound Profile Revision.

Placement order is the exact `SectionArrangementRevision.placement_ids` order
for the current Arrangement.

Neither timestamps nor opaque Candidate, Selection, Placement, producer, or
Artifact identifiers are ranking or ordering authority.

An active Placement that is not covered by one exact current Arrangement is a
structural Composition error. Vitrine does not fabricate an order.

## Requirement explanation

Requirement explanation evaluates only explicit machine-readable Profile
semantics.

Supported explanatory states are:

```text
satisfied_current_curation
unresolved_missing
optional_absent
conditional_unresolved
prohibited_clear
audience_stage
not_machine_evaluable
```

Requirement prose is not parsed to invent executable policy.

Unresolved obligations remain frozen in the canonical Inventory. They are not
cleared by preparation, teacher review, authority approval, or Composition
creation.

## Source currentness

For each active Selection included by the Composition, preparation records
bounded current-use observations:

```text
Selection
Candidate
Publication
observed series head
observed series state
observed withdrawal state
derived current-use state
```

Historical, withdrawn, or unresolved source state does not automatically
withdraw, replace, or retarget a Selection.

Prepared freeze re-observes the same bounded Core Publication state. Material
source drift fails closed and requires a new preparation.

Producer readers are not invoked.

## Curation Reviews

Only Reviews applicable to the exact current curation targets/revisions are
included.

A Review of an old Annotation, Reflection, Arrangement, or other immutable
target does not silently satisfy a successor revision.

Review approval remains curation approval only. It is not disclosure
authorization.

## Audience constraints

Working Composition remains audience-neutral.

Preparation may display the exact bound Profile's audience rules, including
allowed/prohibited content classes and required review classes. It does not:

- choose an audience;
- create `AudienceContext`;
- perform Snapshot entry filtering;
- authorize a recipient;
- authorize disclosure.

Audience materialization belongs to the downstream Snapshot workflow.

## Fingerprint

The preparation fingerprint is deterministic SHA-256 over the semantic state
the teacher reviewed, including:

- contract identity;
- Portfolio/Subject/Profile identity;
- observed Vitrine state revision;
- observed Composition pointer/current revision;
- predicted Composition disposition/revisions;
- exact semantic Composition/Inventory payload;
- bounded Core Publication observations;
- a Composition note only when a new Composition would persist it.

The fingerprint is a replay/concurrency guard, not a signature or
authorization credential.

## Prepared freeze

`freeze_prepared_working_composition(...)` accepts one exact transient
preparation.

Before authority or persistence, it fails closed if:

- the Vitrine state revision changed;
- the Composition pointer changed;
- canonical Composition derivation changed;
- bounded Core Publication observations changed;
- the preparation fingerprint no longer matches.

The canonical service performs a second guarded derivation/source check before
commit.

No silent refresh, reprepare, retry, or last-write-wins behavior is permitted.

## Exact replay

If the semantic Composition/Inventory payload already equals the current
Composition, preparation reports `reuse_exact_current`.

Freezing that exact preparation reuses the current Composition and does not
create a duplicate successor revision or advance the Vitrine state.

A note-only change does not create a semantic successor Composition.

## Teacher workflow

Portfolio option 5 routes through the guided Working Composition menu.

The teacher may:

1. prepare current curation;
2. review section/order, requirements, sources, Reviews, audience constraints,
   and exact payload/change state;
3. inspect current or historical frozen Composition state;
4. explicitly confirm `FREEZE COMPOSITION`.

Unresolved obligations are shown before confirmation and remain unresolved
after freezing.

## Direct CLI

Task-level commands are:

```text
vitrine composition prepare PORTFOLIO_ID
vitrine composition freeze PORTFOLIO_ID \
  --preparation-fingerprint SHA256 \
  --expected-state-revision REVISION \
  --expected-composition-pointer-revision REVISION_OR_NONE \
  --actor-id ACTOR
```

The literal `none` is required to express an observed absence of an initial
Composition pointer.

The existing lower-level commands remain available:

```text
vitrine composition show
vitrine composition build
```

The prepared path does not silently infer stale expectations.

## Runtime dependency boundary

Guided Working Composition requires Vitrine and Core only.

It does not require installed ScoreForm, Quillan, Concord, Portia, or Meridian
packages and does not invoke sibling producer readers while preparing or
freezing persisted curation state.

## Downstream handoff

Issue #67 ends with exact Working Composition creation/reuse. Issue #68
consumes this handoff only when preparation reports:

```text
reuse_exact_current
```

If guided preparation predicts `create_initial` or `create_successor`, or
reports unplaced active Selections, Build and Export Current Portfolio stops
before downstream writes and sends the teacher back to Working Composition.

The downstream first-party bridge is documented in
[Build and Export Current Portfolio v1](build-export-current-portfolio-v1.md).
It creates/reuses the exact Audience Context and Snapshot Series, then
composes the existing Snapshot Request/Plan/Attempt/Seal/Edition/Export
services. Disclosure authorization and external delivery remain separate.
