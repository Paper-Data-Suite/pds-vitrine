# Selection, Ordering, Annotation, and Reflection Records

## Status and boundary

This document defines a conceptual Vitrine curation model for issue #8, **Define selection, ordering, annotation, and reflection records**.

It is a foundation design, not a final serialized contract or runtime implementation.

The design defines Vitrine-owned records for:

- proposing and deciding whether a Portfolio Candidate should be curated;
- creating positive Portfolio Selections;
- placing one Selection in one or more Profile sections;
- preserving deterministic section-item order;
- recording curator display metadata;
- recording rationale, annotation, and reflection without conflating their meanings;
- reviewing and approving exact curation revisions;
- assembling immutable working-Portfolio composition revisions;
- and preserving withdrawal, invalidation, replacement, correction, and supersession history.

The design does not:

- discover Candidates;
- change producer-native records;
- choose grading evidence;
- copy source bytes;
- issue snapshots;
- authorize audiences;
- verify consent or signatures;
- apply redaction;
- calculate proficiency or Grades;
- or activate a regulated Profile.

Those responsibilities remain with the contracts and issues identified below.

## Governing separation

The curation model preserves this sequence:

```text
verified producer projection
  -> positive Portfolio Candidate
  -> Selection Proposal
  -> Selection Decision
  -> positive Portfolio Selection
  -> Section Placement
  -> Section Arrangement Revision
  -> Presentation / Annotation / Reflection revisions
  -> Curation Review Decision
  -> Working Portfolio Composition Revision
  -> later snapshot request
```

No arrow is implicit.

The following concepts remain distinct:

```text
Candidate
  != Proposal
  != Decision
  != Selection
  != Placement
  != Arrangement
  != Presentation
  != Rationale
  != Annotation
  != Reflection
  != Approval
  != Composition Revision
  != Snapshot
```

Likewise:

```text
selected for a Portfolio
  != selected for grading
  != approved for disclosure
  != copied into a snapshot
  != submitted externally
  != externally accepted
```

## Reviewed repository baseline

The design was reconciled against these repository states.

| Repository | Reviewed baseline | Relevant authority and readiness |
| --- | --- | --- |
| `pds-vitrine` | `70c130322d619bf86817791b3b01ca2d2ec18dee` | Profiles, Candidate/source references, producer projection boundaries, and Proposed ADRs 0001–0005 are documented; no runtime curation implementation exists. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Core owns canonical work, publication, registration, identity, exact manifest verification, and derived discovery infrastructure; it does not own Portfolio curation. |
| `pds-scoreform` | `c2fa06f1a4c33df01f3e0d9c8dd27702d4a06419` | Immutable Academic Result Manifest generation is implemented; all represented attempts remain distinct and no official, best, latest-for-grading, or Grade-bearing attempt is selected. |
| `pds-quillan` | `05fecf23d29e56b45cba58ed97906f5353290033` | Quillan owns selected submission evidence, evidence roles and states, teacher review, private notes, feedback, and assignment-local reports. |
| `pds-concord` | `87a8165845bc61ad188e78817ccb2415af3701e1` | Immutable native Artifact, Page, Author, Subject, Group, Score, Review, Moderation, and correction models exist; storage and publication workflows remain pending. |
| `pds-portia` | `8cd4b1f2ca80cc240693184c87e5df463ba375cf` | Exact scope-specific references, targets, and nondestructive correction patterns are accepted; ordinary Portia sources remain inappropriate for general Portfolio curation. |
| `pds-meridian` | `c7e9129f6547bca9953f8ae5c8718ce358341172` | Meridian owns grading evidence eligibility, attempt policy, Grade-item membership, proficiency, Grades, and report composition; it does not own Portfolio Selection. |

### Reusable cross-repository patterns

The design reuses these suite-wide patterns:

- opaque durable IDs rather than semantic IDs;
- exact references rather than search-based repair;
- immutable operational records;
- explicit predecessors and successors;
- append-preserving lifecycle events;
- explicit current pointers;
- three-valued or unresolved states where facts are incomplete;
- source authority preserved by module;
- nondestructive correction;
- and derived indexes that can be rebuilt.

### Incompatible assumptions rejected

The design rejects these assumptions from adjacent domains:

- a ScoreForm attempt chosen for a Portfolio is the attempt Meridian must grade;
- Quillan's selected evidence can be reopened or reclassified by Vitrine;
- Concord Group Membership proves authorship or individual Score ownership;
- a Portia-safe projection permits access to its underlying source graph;
- a Core publication or Candidate authorizes Selection;
- or a Selection authorizes later audience disclosure.

## Authority model

### Vitrine owns

Vitrine owns the canonical curation records defined here:

- Selection Proposal;
- Selection Decision;
- Portfolio Selection;
- Selection Lifecycle Event;
- Section Placement;
- Section Arrangement Revision;
- arrangement current pointer;
- Selection Presentation;
- Selection Rationale;
- Annotation;
- Reflection Record;
- Curation Review Decision;
- Working Portfolio Composition Revision;
- composition current pointer;
- and curation correction and replacement relationships.

### Portfolio Profile owns policy definitions

The exact bound Portfolio Profile revision defines:

- who may propose or select;
- whether student participation is required;
- permitted section placement;
- minimum, maximum, and exact counts;
- repeated-placement policy;
- required rationale;
- reflection rules;
- approval rules;
- reapproval triggers;
- and prohibited content.

The Profile describes policy. It does not create actor-authored records.

### Candidate records own source endpoints

A Selection references one exact positive Candidate and the exact Candidate Evaluation relied upon.

A Selection does not reinterpret or retarget the Candidate.

### Producers retain source authority

Producer modules remain authoritative for:

- source identity;
- attempt identity;
- source revision;
- artifact authorship;
- Group and subject relationships;
- native ratings and Scores;
- producer feedback;
- and producer privacy metadata.

Curator-authored text may describe why a source was selected, but it must not replace producer facts.

### Institutions and issue #10 own authorization

Actor identity, institutional authorization, recipient authorization, consent, public-release permission, redaction completion, and disclosure logging remain external or later Vitrine concerns.

A curation record may preserve an asserted role and an authorization reference. It does not authenticate either by itself.

### Issue #9 owns copied bytes and issuance

A Working Portfolio Composition Revision identifies exact curation state.

It contains no producer bytes and is not an issued snapshot.

## Terminology

### Selection Proposal

An actor-authored request to include one exact Candidate in a Portfolio.

A Proposal may later be accepted, rejected, returned for changes, withdrawn, or expire.

### Selection Decision

An immutable decision about one exact Proposal revision.

### Portfolio Selection

A positive durable Vitrine record stating that one exact Candidate is part of the working Portfolio under one exact Portfolio, Subject, and Profile binding.

### Section Placement

A relationship placing one Selection in one Profile section.

Selection identity and Placement identity are separate so one selected source may appear in several permitted sections without duplicate Selections.

### Section Arrangement Revision

A complete immutable ordered list of active Placement IDs for one section.

### Selection Presentation

Curator-authored display metadata, such as a title or caption, for one Selection or Placement.

### Selection Rationale

The actor-authored reason for a Proposal, Decision, withdrawal, or replacement.

Rationale normally supports process provenance rather than audience presentation.

### Annotation

Curator-authored explanatory context attached to curation state.

Annotation is not producer feedback or source fact.

### Reflection

Actor-authored interpretation responding to one exact Profile reflection rule and one exact curation target.

### Curation Review Decision

An immutable review or approval decision scoped to one exact record revision.

### Working Portfolio Composition Revision

One immutable, coherent, byte-free representation of the active curated Portfolio state.

## Conceptual graph

```text
Portfolio
  -> Portfolio Profile Binding
  -> Portfolio Subject

Portfolio Candidate
  -> Candidate Evaluation
  -> exact producer projection

Selection Proposal
  -> Candidate
  -> proposed section(s)
  -> proposed rationale

Selection Decision
  -> exact Proposal

Portfolio Selection
  -> exact Candidate
  -> accepted Proposal / Decision or equivalent direct authority

Portfolio Selection
  -> one or more Section Placements

Profile Section
  -> Section Arrangement Revision
  -> ordered Placement IDs

Selection / Placement / Section / comparison set / Composition Revision
  -> Annotation revisions
  -> Reflection revisions

Exact curation record revision
  -> Curation Review Decisions

Working Portfolio Composition Revision
  -> active Selections
  -> active Placements
  -> exact Arrangement revisions
  -> exact Presentation revisions
  -> exact Annotation revisions
  -> exact Reflection revisions
  -> unresolved obligations
```

## Record overview

| Record | Canonical? | Mutable? | Primary role |
| --- | --- | --- | --- |
| Selection Proposal | Yes | No | Preserve proposal intent, including unsuccessful proposals. |
| Selection Decision | Yes | No | Preserve an actor's decision about one exact Proposal. |
| Portfolio Selection | Yes | No | Bind an exact Candidate into one working Portfolio context. |
| Selection Lifecycle Event | Yes | No | Preserve activation, withdrawal, replacement, invalidation, or supersession. |
| Section Placement | Yes | No | Connect one Selection to one Profile section. |
| Section Arrangement Revision | Yes | No | Define complete item order for one section. |
| Arrangement Current Pointer | Yes | Conflict-aware update | Identify the arrangement governing current working use. |
| Selection Presentation | Yes | No | Preserve curator display metadata independently of source metadata. |
| Selection Rationale | Yes | No | Explain a curation action or decision. |
| Annotation | Yes | No | Add curator-authored explanatory context. |
| Reflection Record | Yes | No | Preserve actor-authored reflection against an exact rule and target. |
| Curation Review Decision | Yes | No | Approve, reject, request changes, acknowledge, or waive an exact revision. |
| Working Portfolio Composition Revision | Yes | No | Freeze one exact byte-free curation state. |
| Composition Current Pointer | Yes | Conflict-aware update | Identify the composition governing current working use. |
| Curation search indexes and dashboards | No | Rebuildable | Support discovery and workflow views. |

## Identity conventions

Every canonical curation record receives an opaque, non-PII, never-reused ID.

IDs must not encode:

- student name;
- student ID;
- class ID;
- source title;
- producer module;
- section label;
- attempt number;
- decision outcome;
- or lifecycle state.

Human-readable labels are snapshots or display metadata, never identity.

The same source may receive different Selection IDs when selected into:

- different Portfolios;
- different Portfolio Subjects;
- different Profile bindings;
- or a corrected successor Selection.

## Selection Proposal

### Purpose

A Selection Proposal preserves curation intent before a positive Selection exists.

Keeping Proposals separate from Selections allows Vitrine to retain:

- rejected student proposals;
- teacher-requested revisions;
- withdrawn suggestions;
- expired proposals;
- and system-generated recommendations that no human accepted.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_proposal_id` | Required | Opaque durable Proposal identity. |
| `contract_version` | Required | Proposal contract version. |
| `portfolio_id` | Required | Exact Portfolio. |
| `portfolio_subject_id` | Required | Exact Portfolio Subject. |
| `profile_binding_id` | Required | Exact operational Profile Binding. |
| `portfolio_profile_id` | Required | Stable Profile series identity snapshot. |
| `profile_revision` | Required | Exact Profile revision. |
| `candidate_id` | Required | Exact positive Candidate. |
| `candidate_evaluation_id` | Required | Exact Candidate Evaluation relied upon. |
| `proposer` | Required | Exact actor reference or permitted system-process reference. |
| `asserted_role` | Required | Actor's curation role for this action. |
| `proposal_source` | Required | `student`, `teacher`, `authorized_reviewer`, `imported_prior_curation`, or `system_suggestion`. |
| `proposed_section_ids` | Optional | Ordered unique section IDs proposed for placement. |
| `proposed_requirement_ids` | Optional | Requirement-intent IDs; not satisfaction claims. |
| `rationale_id` | Conditional | Required where the Profile requires proposal rationale. |
| `known_condition_ids` | Optional | Candidate or Profile conditions known at proposal time. |
| `predecessor_proposal_id` | Optional | Earlier Proposal revised or resubmitted. |
| `created_at` | Required | Aware timestamp. |
| `authorization_reference` | Conditional | External or later Vitrine authorization reference where available. |

### Forbidden fields

A Proposal must not contain:

- copied source bytes;
- mutable `approved` Boolean;
- inferred Grade status;
- inferred proficiency;
- public-release consent;
- recipient identity;
- producer-private fields;
- or a mutable list of later Decisions.

### Validation

A Proposal is structurally valid only when:

- Portfolio, Subject, Profile Binding, Candidate, and Candidate Evaluation all match;
- the Candidate existed and was positive at proposal time;
- the proposed sections exist in the exact Profile revision;
- the proposer role is syntactically valid;
- the proposal source is explicit;
- requirement-intent IDs exist in the Profile revision;
- and predecessor relationships are acyclic.

Profile authority evaluation may still produce an unauthorized or unresolved Proposal outcome. Structural retention of an unauthorized attempt does not turn it into a valid Selection.

### Lifecycle

A Proposal itself is immutable.

Later proposal state is derived from exact Selection Decisions and successor Proposals.

No Decision rewrites the Proposal.

## Selection Decision

### Purpose

A Selection Decision records what an authorized actor decided about one exact Proposal.

### Decision vocabulary

```text
accepted
rejected
changes_requested
withdrawn
expired
```

`Withdrawn` normally records proposer-authorized withdrawal where the Profile permits it.

`Expired` records policy-based expiration and must identify the governing rule or authority.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_decision_id` | Required | Opaque durable Decision identity. |
| `contract_version` | Required | Decision contract version. |
| `selection_proposal_id` | Required | Exact Proposal revision decided. |
| `decision` | Required | Closed decision vocabulary. |
| `decision_actor` | Required | Exact actor or authorized system process. |
| `asserted_role` | Required | Role used to make the decision. |
| `selection_rule_id` | Conditional | Exact Profile rule granting or constraining authority. |
| `decided_at` | Required | Aware timestamp. |
| `reason_id` | Conditional | Required for rejection, changes requested, withdrawal, expiration, or Profile policy. |
| `conditions_imposed` | Optional | Explicit obligations attached to acceptance. |
| `expected_successor_proposal` | Optional | Whether changes require a new Proposal. |
| `authorization_reference` | Conditional | External authorization basis where required. |

### Decision uniqueness

One Proposal may have at most one terminal Decision.

A `changes_requested` Decision is terminal for that Proposal revision; a revised Proposal receives a new ID and predecessor reference.

The model must not append multiple contradictory mutable statuses to one Proposal.

### Accepted Decision and Selection creation

An accepted Decision authorizes creation of a Portfolio Selection only when all current gates remain satisfied, including:

- Candidate remains selectable under the exact Profile;
- actor authority is valid;
- duplicate-active-Selection policy passes;
- conditional obligations are preserved;
- and no source or Profile state invalidates the action.

An accepted Decision may therefore exist without a positive Selection if later creation fails. The failure remains explicit.

## Portfolio Selection

### Purpose

A Portfolio Selection is the positive canonical curation record that binds one exact Candidate into one exact Portfolio context.

### Conceptual identity

```text
selection_id
  -> portfolio_id
  -> portfolio_subject_id
  -> profile_binding_id
  -> candidate_id
  -> candidate_evaluation_id relied upon
```

The ID is opaque. The endpoint fields define meaning.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_id` | Required | Opaque durable Selection identity. |
| `contract_version` | Required | Selection contract version. |
| `portfolio_id` | Required | Exact Portfolio. |
| `portfolio_subject_id` | Required | Exact Subject. |
| `profile_binding_id` | Required | Exact Profile Binding. |
| `portfolio_profile_id` | Required | Profile series snapshot. |
| `profile_revision` | Required | Exact Profile revision. |
| `candidate_id` | Required | Exact selected Candidate. |
| `candidate_evaluation_id` | Required | Exact Evaluation relied upon at activation. |
| `selection_proposal_id` | Optional | Accepted Proposal. |
| `selection_decision_id` | Optional | Accepted Decision. |
| `direct_selection_authority` | Conditional | Required only for an explicitly permitted direct workflow. |
| `selected_by` | Required | Exact actor. |
| `asserted_role` | Required | Role used for activation. |
| `selected_at` | Required | Aware timestamp. |
| `selection_rationale_id` | Conditional | Required when Profile policy requires it. |
| `condition_snapshot` | Optional | Candidate and Profile conditions preserved at activation. |
| `required_review_ids` | Optional | Outstanding review requirements, not completed approvals. |
| `source_relationship_snapshot` | Required | Exact Candidate subject/source relationship summary needed to preserve meaning. |
| `native_semantic_references` | Optional | Attempt, standard, Group, authorship, Score-target, or equivalent exact references. |
| `predecessor_selection_id` | Optional | Corrected or superseded predecessor where applicable. |
| `replaces_selection_ids` | Optional | Explicit replacement targets. |

### Direct Selection

A direct teacher or authorized-curator Selection may be allowed only when the exact Profile permits it.

The direct workflow must produce equivalent provenance:

- actor;
- authority rule;
- rationale where required;
- Candidate Evaluation;
- selection time;
- and outstanding obligations.

It must not create an unattributed Selection merely because a UI button was pressed.

### Duplicate active Selection policy

For v0.1.0, the recommended invariant is:

```text
one Candidate
  -> at most one active Selection
  within one Portfolio + Portfolio Subject + Profile Binding
```

A repeated appearance in several sections uses multiple Placements.

A corrected successor Candidate or materially different representation receives a new Candidate and may receive a new Selection.

### Forbidden interpretations

A Selection does not mean:

- the source was selected for grading;
- the source is the student's sole or best work;
- an attempt is official;
- a standard was mastered;
- a Group artifact was individually authored;
- a source is authorized for public release;
- a snapshot contains the bytes;
- or an institution approved the Portfolio.

## Selection lifecycle

### Event vocabulary

```text
activated
withdrawn
replaced
invalidated
superseded
```

### Selection Lifecycle Event fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_lifecycle_event_id` | Required | Opaque event identity. |
| `selection_id` | Required | Exact Selection. |
| `event_kind` | Required | Closed lifecycle vocabulary. |
| `actor` | Required | Actor or authorized process. |
| `asserted_role` | Required | Role used for the lifecycle action. |
| `recorded_at` | Required | Event-recording time. |
| `effective_at` | Required | Effective time where distinct. |
| `reason_id` | Conditional | Required for withdrawal, replacement, invalidation, or supersession. |
| `successor_selection_ids` | Conditional | Required for replacement or supersession. |
| `authority_reference` | Conditional | Governing Profile or institutional authority. |

### Current lifecycle resolution

Current lifecycle is resolved from a validated event graph and explicit current-state policy.

It must not be selected from:

- the newest timestamp;
- lexical event ID;
- greatest Selection revision;
- or filesystem order.

### Withdrawal

Withdrawal removes a Selection from future active compositions without a successor.

Historical Placement, Reflection, approval, and composition references remain valid for their exact historical state.

### Replacement

Replacement links one or more old Selections to one or more explicit successor Selections.

Replacement is not in-place endpoint mutation.

### Invalidation

Invalidation records that a Selection should not have been operational because of a material defect such as:

- wrong Portfolio;
- wrong Subject;
- wrong Profile Binding;
- wrong Candidate;
- invalid authority;
- or source relationship error.

Invalidation does not erase the historical record or downstream impact.

### Supersession

Supersession represents a corrected successor that preserves the same broad curation intent.

The distinction between `replaced` and `superseded` must be documented in the eventual contract and UI. Neither may retarget the original Selection.

## Section Placement

### Purpose

A Section Placement states where one selected source appears in the working Portfolio.

Selection and Placement are distinct because:

- one source may satisfy several presentation purposes;
- section movement should not replace source Selection identity;
- and repeated display must preserve one underlying Selection rather than duplicate provenance.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `placement_id` | Required | Opaque durable Placement identity. |
| `contract_version` | Required | Placement contract version. |
| `selection_id` | Required | Exact active or historically active Selection. |
| `portfolio_id` | Required | Exact Portfolio, repeated for validation. |
| `profile_binding_id` | Required | Exact Profile Binding. |
| `section_id` | Required | Exact stable Profile section ID. |
| `requirement_intent_ids` | Optional | Requirements the curator intends the Placement to address. |
| `placement_purpose` | Optional | Bounded purpose such as primary evidence, comparison evidence, context, or appendix. |
| `placed_by` | Required | Actor. |
| `asserted_role` | Required | Role used. |
| `placed_at` | Required | Aware timestamp. |
| `presentation_id` | Optional | Exact current-at-composition Presentation revision reference. |
| `annotation_ids` | Optional | Exact Annotation revision references. |
| `predecessor_placement_id` | Optional | Earlier Placement corrected or moved. |

### Requirement intent

`requirement_intent_ids` records curation intent only.

A Profile requirement finding separately decides whether the complete Portfolio state satisfies the requirement.

This preserves:

```text
curator intended this as baseline evidence
  != baseline requirement satisfied
```

### Multiple Placements

A Selection may have several active Placements only when:

- the exact Profile permits repeated use;
- the Placement purposes are valid;
- cardinality and duplication rules pass;
- and the arrangement revisions include each Placement explicitly.

### Section movement

Moving an item from one section to another creates:

1. a successor Placement for the new section;
2. lifecycle treatment for the old Placement;
3. new Arrangement revisions for affected sections;
4. and a new Composition Revision.

The old Placement is not edited in place.

## Placement lifecycle

Placements should use append-preserving events or an equivalent immutable predecessor/successor model.

Suggested states include:

```text
active
withdrawn
replaced
invalidated
```

A Placement may become inactive while the underlying Selection remains active elsewhere.

## Section Arrangement Revision

### Purpose

A Section Arrangement Revision is the canonical ordering authority for one section.

It stores the complete ordered Placement sequence rather than scattering mutable position integers across Placement records.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `section_arrangement_id` | Required | Stable logical arrangement series identity for Portfolio + Profile Binding + section. |
| `arrangement_revision` | Required | Positive immutable revision. |
| `contract_version` | Required | Arrangement contract version. |
| `portfolio_id` | Required | Exact Portfolio. |
| `profile_binding_id` | Required | Exact Profile Binding. |
| `section_id` | Required | Exact Profile section. |
| `ordered_placement_ids` | Required | Complete ordered list of unique active Placements intended for the section. |
| `predecessor_revision` | Optional | Exact predecessor revision. |
| `created_by` | Required | Actor. |
| `asserted_role` | Required | Curation role. |
| `created_at` | Required | Aware timestamp. |
| `reason_id` | Optional | Reorder, insertion, removal, migration, or correction reason. |
| `expected_current_revision` | Conditional | Optimistic concurrency precondition used during creation. |

### Arrangement invariants

An Arrangement Revision must:

- reference each Placement at most once;
- contain only Placements for the exact Portfolio, Profile Binding, and section;
- include only Placements valid for that composition context;
- preserve complete order;
- and use an acyclic predecessor chain.

### Empty arrangements

An empty section may have an explicit empty Arrangement Revision.

Absence of an arrangement is not automatically equivalent to an intentionally empty section.

### Profile section order versus item order

The Profile defines the order of sections.

The Arrangement defines the order of items within one section.

Vitrine must not flatten both into one generic integer ordering system.

## Section Arrangement Current Pointer

### Purpose

A current pointer identifies which Arrangement Revision governs the current working section.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `section_arrangement_id` | Required | Logical arrangement series. |
| `current_revision` | Required | Exact current Arrangement Revision. |
| `previous_revision` | Optional | Prior pointer target. |
| `updated_by` | Required | Actor or authorized process. |
| `updated_at` | Required | Aware timestamp. |
| `reason_id` | Optional | Reorder, migration, correction, or composition update. |
| `expected_previous_revision` | Required for update | Conflict-detection precondition. |

### Concurrency

Two actors reordering the same section from the same predecessor must not silently overwrite each other.

The second conflicting update must fail with a revision conflict and preserve both proposed Arrangement Revisions for review if they were durably created.

No last-write-wins behavior is permitted.

## Selection Presentation

### Purpose

Selection Presentation records curator-controlled display metadata without changing producer-owned metadata.

### Scope

A Presentation may target:

- a Selection generally;
- one Placement;
- or an explicitly named presentation context.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_presentation_id` | Required | Stable logical Presentation series identity. |
| `presentation_revision` | Required | Positive immutable revision. |
| `contract_version` | Required | Presentation contract version. |
| `target_type` | Required | `selection` or `placement`. |
| `target_id` | Required | Exact target. |
| `display_title` | Optional | Curator title. |
| `short_caption` | Optional | Bounded caption. |
| `context_label` | Optional | Bounded contextual label. |
| `language` | Optional | Language tag. |
| `presentation_class` | Required | Intended class such as working, teacher-internal, family, reviewer, or public. |
| `source_title_snapshot_reference` | Optional | Reference to producer title snapshot used for comparison. |
| `created_by` | Required | Curator. |
| `created_at` | Required | Aware timestamp. |
| `predecessor_revision` | Optional | Exact prior Presentation revision. |

### Title separation

The model preserves:

```text
producer source title
curator display title
snapshot-rendered title
```

A curator title never overwrites the Candidate's source-title snapshot.

### Presentation class is not authorization

A `public` or `family` presentation class means only that the curator drafted text for that intended context.

It does not authorize the audience, recipient, or disclosure.

## Selection Rationale

### Purpose

Rationale explains why an actor proposed, accepted, rejected, withdrew, replaced, or superseded a Candidate or Selection.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_rationale_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Rationale contract version. |
| `action_type` | Required | Proposal, acceptance, rejection, withdrawal, replacement, supersession, or migration. |
| `target_type` | Required | Exact record class. |
| `target_id` | Required | Exact record. |
| `reason_kind` | Required | Bounded reason vocabulary or explicit other. |
| `text` | Conditional | Actor-authored explanation where required. |
| `structured_reason` | Optional | Policy-safe structured values. |
| `profile_rule_id` | Optional | Governing Profile rule. |
| `author` | Required | Actor. |
| `asserted_role` | Required | Role. |
| `created_at` | Required | Aware timestamp. |

### Rationale is not audience-facing by default

A rationale may contain workflow context inappropriate for a family, public, or external audience.

Later snapshot and audience policy decides whether any portion is rendered.

## Annotation

### Purpose

Annotation adds curator-authored context without claiming to be producer fact or learner reflection.

### Suggested purpose vocabulary

```text
curator_context
source_context
comparison_note
standards_context
caption
accessibility_description
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `annotation_id` | Required | Stable logical Annotation series identity. |
| `annotation_revision` | Required | Positive immutable revision. |
| `contract_version` | Required | Annotation contract version. |
| `purpose` | Required | Closed or versioned purpose vocabulary. |
| `target_type` | Required | Selection, Placement, section, comparison set, or Composition Revision. |
| `target_ids` | Required | Exact target set with declared cardinality and ordering semantics. |
| `content` | Required | Actor-authored text or structured value. |
| `language` | Optional | Language tag. |
| `author` | Required | Actor. |
| `asserted_role` | Required | Role. |
| `created_at` | Required | Aware timestamp. |
| `predecessor_revision` | Optional | Earlier Annotation revision. |
| `intended_visibility_class` | Optional | Working, internal, family, reviewer, public, or regulated. |

### Annotation boundaries

An Annotation must not:

- overwrite producer metadata;
- declare an attempt official;
- declare a standard mastered;
- invent Concord authorship;
- expose Portia source history;
- or create audience authorization.

A statement such as “This shows strong growth” remains curator interpretation unless an authoritative external record separately establishes that conclusion.

## Reflection Record

### Purpose

Reflection preserves actor-authored interpretation under one exact Profile reflection rule.

### Supported scope vocabulary

```text
selection
placement
comparison_set
section
checkpoint
portfolio
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `reflection_id` | Required | Stable logical Reflection series identity. |
| `reflection_revision` | Required | Positive immutable revision. |
| `contract_version` | Required | Reflection contract version. |
| `portfolio_id` | Required | Exact Portfolio. |
| `portfolio_subject_id` | Required | Exact Subject. |
| `profile_binding_id` | Required | Exact Profile Binding. |
| `reflection_rule_id` | Required | Exact Profile reflection rule. |
| `prompt_id` | Required | Exact prompt or prompt-set identity. |
| `prompt_version` | Required | Exact immutable prompt version. |
| `prompt_snapshot_digest` | Conditional | Digest or bounded snapshot where needed for historical reproducibility. |
| `author` | Required | Actor. |
| `asserted_role` | Required | Student, teacher, or other Profile-permitted role. |
| `scope` | Required | Closed scope vocabulary. |
| `target_ids` | Required | Exact Selection, Placement, section, checkpoint, or composition target set. |
| `target_order_semantics` | Conditional | Required for comparison sets or ordered targets. |
| `content_mode` | Required | `inline_text`, `structured_response`, or `external_artifact_reference`. |
| `inline_content` | Conditional | Reflection content for inline or structured modes. |
| `external_reference` | Conditional | Exact Candidate or Selection reference for artifact-backed reflection. |
| `language` | Optional | Language tag. |
| `created_at` | Required | Aware timestamp. |
| `predecessor_revision` | Optional | Exact prior Reflection revision. |
| `review_state_summary` | Optional | Derived convenience only; exact review records remain separate. |

### Prompt identity

A prompt's display text may change across versions.

The Reflection must preserve exact prompt identity and version, and enough bounded prompt evidence to explain what the actor answered historically.

A mutable current prompt pointer is insufficient.

### Comparison Reflection

A comparison Reflection must identify:

- every compared Selection explicitly;
- whether target order is meaningful;
- the comparison role of each target where required, such as baseline, intermediate, or current;
- and the exact Profile rule.

A replaced Selection remains historically valid as a comparison target for the old Reflection.

A new Reflection revision is required to compare a successor Selection.

### External-artifact Reflection

An external-artifact Reflection references one exact eligible Candidate or Selection.

It does not:

- copy the bytes;
- make the external artifact student-authored automatically;
- or bypass producer exposure policy.

### Reflection correction

A revised Reflection receives a new revision with an exact predecessor.

The earlier revision remains preserved.

Approvals attached to the earlier revision do not automatically apply to the successor.

### Reflection boundaries

Reflection is not automatically:

- proof of growth;
- proof of proficiency;
- consent;
- remorse;
- confession;
- compliance certification;
- or external attestation.

## Curation Review Decision

### Purpose

A Curation Review Decision preserves one actor's review of one exact curation record revision.

### Target types

The initial conceptual targets are:

```text
selection_proposal
selection
section_placement
section_arrangement_revision
selection_presentation_revision
annotation_revision
reflection_revision
working_portfolio_composition_revision
```

### Decision vocabulary

```text
approved
rejected
changes_requested
acknowledged
waived
```

`Waived` is valid only when:

- the exact Profile approval rule permits waiver;
- the actor has waiver authority;
- the reason is preserved;
- and the waiver scope is exact.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `curation_review_decision_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Review contract version. |
| `profile_binding_id` | Required | Exact Profile Binding. |
| `approval_rule_id` | Required | Exact Profile approval rule. |
| `target_type` | Required | Supported exact target class. |
| `target_id` | Required | Exact target identity. |
| `target_revision` | Conditional | Required for revisioned targets. |
| `decision` | Required | Closed review vocabulary. |
| `actor` | Required | Exact reviewer. |
| `asserted_role` | Required | Reviewer role. |
| `authority_reference` | Conditional | Institutional or Profile authority. |
| `decided_at` | Required | Aware timestamp. |
| `reason_id` | Conditional | Required for rejection, changes requested, or waiver. |
| `required_follow_up` | Optional | Explicit required next action. |
| `predecessor_review_id` | Optional | Earlier review in a governed sequence. |

### Approval scope

An approval applies only to the exact target and revision.

For example:

```text
approval of reflection revision 1
  != approval of reflection revision 2
```

```text
approval of working composition revision 4
  != approval of composition revision 5
```

```text
approval for teacher-internal curation review
  != parent-facing disclosure approval
```

### Approval does not fabricate external authority

A Curation Review Decision does not by itself prove:

- authenticated signature;
- legal consent;
- guardian relationship;
- source authorization;
- recipient authorization;
- redaction completion;
- snapshot issuance;
- external submission;
- or external acceptance.

## Working Portfolio Composition Revision

### Purpose

A Working Portfolio Composition Revision freezes one exact, coherent, byte-free curation state.

It is the primary whole-Portfolio target for review and the input contract that issue #9 will use for snapshot construction.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `working_composition_id` | Required | Stable logical composition series for one Portfolio and Profile Binding. |
| `composition_revision` | Required | Positive immutable revision. |
| `contract_version` | Required | Composition contract version. |
| `portfolio_id` | Required | Exact Portfolio. |
| `portfolio_subject_id` | Required | Exact Subject. |
| `profile_binding_id` | Required | Exact Profile Binding. |
| `portfolio_profile_id` | Required | Profile series snapshot. |
| `profile_revision` | Required | Exact Profile revision. |
| `active_selection_ids` | Required | Complete set of active Selections included. |
| `active_placement_ids` | Required | Complete set of active Placements included. |
| `section_arrangement_revisions` | Required | Exact Arrangement revision for each represented Profile section. |
| `presentation_revisions` | Optional | Exact Presentation revisions used. |
| `annotation_revisions` | Optional | Exact Annotation revisions included in curation state. |
| `reflection_revisions` | Optional | Exact Reflection revisions included in curation state. |
| `unresolved_obligations` | Optional | Explicit Profile, Candidate, collaborator, rights, privacy, or approval obligations. |
| `validation_findings` | Required | Exact validation-result references or bounded summary. |
| `predecessor_revision` | Optional | Exact prior Composition Revision. |
| `created_by` | Required | Actor or authorized composition service. |
| `asserted_role` | Required | Role or process authority. |
| `created_at` | Required | Aware timestamp. |
| `reason_id` | Optional | Curation update, migration, correction, or review reason. |
| `expected_current_revision` | Conditional | Optimistic concurrency precondition. |

### Composition completeness

The Composition Revision must be internally complete:

- every included Placement references an included Selection;
- every arrangement references only included Placements;
- every included Presentation, Annotation, and Reflection revision resolves;
- exact Profile section and rule IDs resolve;
- selection and placement lifecycle is valid for the composition point;
- duplicate rules pass;
- and unresolved obligations are preserved rather than hidden.

### Composition validity versus Profile completeness

A structurally valid Composition Revision may remain incomplete under Profile policy.

For example, it may preserve:

- a missing required Reflection;
- pending collaborator review;
- unresolved rights review;
- insufficient item count;
- or stale approval.

The composition record must not fabricate completeness merely to become serializable.

### No producer bytes

A Composition Revision contains references and curation metadata only.

It contains no:

- original-work bytes;
- feedback PDF bytes;
- scan bytes;
- rendered snapshot bytes;
- or copied-file digests.

## Composition Current Pointer

### Purpose

The Composition Current Pointer identifies which Composition Revision governs current working use.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `working_composition_id` | Required | Logical composition series. |
| `current_revision` | Required | Exact current Composition Revision. |
| `previous_revision` | Optional | Prior pointer target. |
| `updated_by` | Required | Actor or authorized process. |
| `updated_at` | Required | Aware timestamp. |
| `reason_id` | Optional | Curation change, migration, correction, or rollback. |
| `expected_previous_revision` | Required for update | Conflict-detection precondition. |

### Pointer invariants

Current composition must not be inferred from:

- greatest revision;
- newest timestamp;
- directory order;
- newest Selection;
- or newest arrangement.

A pointer transition must reference an existing, valid Composition Revision in the same series.

### Rollback

A pointer may deliberately return to an earlier Composition Revision where policy permits.

Rollback does not delete later revisions and must record actor, time, and reason.

## Actor and authority treatment

The design preserves separate concepts:

```text
actor identity
asserted curation role
Profile-granted action authority
institutional authorization
source-access authorization
audience authorization
```

### Actor identity

Actor identity must use an authoritative reference appropriate to the deployment.

A display name is not actor identity.

### Asserted role

Every actor-authored curation record preserves the role under which the actor acted.

Examples include:

```text
student
teacher
curator
institutional_reviewer
external_reviewer
system_process
```

The vocabulary must be Profile- and deployment-aware rather than inferred from UI location.

### Profile-granted authority

The exact Profile may permit different actions by role:

| Role example | Possible authority |
| --- | --- |
| Student | Propose, annotate, reflect, acknowledge, or withdraw own Proposal. |
| Teacher | Propose, accept, directly select where allowed, arrange, annotate, request changes, or approve instructional curation. |
| Curator | Arrange, caption, annotate, and assemble Composition Revisions. |
| Institutional reviewer | Approve exact Composition Revisions or waive specific permitted stages. |
| System process | Suggest Candidates, validate structure, or create composition drafts; never silently approve human decisions. |

### Authorization references

Where institutional authorization is required, the curation record stores an exact reference or unresolved state.

It must not embed credentials, tokens, or raw signature material.

## Profile-driven validation

All curation validation uses the exact bound Profile revision.

### Selection rules

Validate:

- actor proposal and selection authority;
- required student participation;
- direct-selection allowance;
- permitted producer projection kinds and semantic families;
- conditional Candidate policy;
- duplicate-source policy;
- and required rationale.

### Section rules

Validate:

- section existence;
- Selection eligibility for the section;
- minimum, maximum, and exact counts;
- repeated-placement rules;
- diversity requirements;
- and section-specific reflection or approval obligations.

### Reflection rules

Validate:

- rule identity;
- author role;
- prompt and prompt version;
- scope;
- target count;
- timing;
- content mode;
- and review requirements.

### Approval rules

Validate:

- target type;
- reviewer role;
- sequence;
- quorum where applicable;
- waiver authority;
- and reapproval triggers.

### Requirement intent versus findings

Selections and Placements may point to requirement-intent IDs.

Requirement findings remain separate derived records.

A curation record must not mark its own requirement as satisfied.

## Conditional Candidates and unresolved obligations

A conditional Candidate may be selected only when the exact Profile permits selection before all conditions are resolved.

Outstanding obligations remain explicit, such as:

- collaborator review;
- student confirmation;
- rights review;
- accessibility alternative;
- privacy review;
- sanitized rendering;
- or teacher confirmation.

A conditional Selection must not be silently promoted to unconditional by later composition assembly.

## Producer-specific curation boundaries

### ScoreForm

A ScoreForm Candidate may identify one exact attempt summary or restricted question-evidence projection.

A Vitrine Selection must preserve:

- exact work;
- exact student context;
- exact attempt identity;
- exact producer manifest and projection revision;
- and producer-native result semantics.

Vitrine must not:

- select an attempt automatically because it is highest, latest, first, or most recent;
- label it official or Grade-bearing;
- modify attempt history;
- convert points into a Grade;
- infer proficiency from standard alignment;
- or change Meridian's attempt-selection policy.

When a Profile permits one ScoreForm attempt, the curator must make one explicit choice among separate Candidate records.

### Quillan

Quillan's submission evidence selection remains producer-owned.

A Quillan original-work Candidate already represents producer-approved selected evidence.

Vitrine must not:

- reopen Quillan candidate evidence;
- include duplicate or excluded evidence;
- change `selected_evidence_id`;
- modify review state;
- expose private notes;
- or merge original work and rendered feedback into one Selection.

Original-work and feedback representations are separate Candidates and require separate Selections.

If Quillan later publishes a successor original-work projection after selected evidence changes, the old Selection remains attached to the old Candidate. The curator must explicitly select the successor if desired.

### Concord

A Concord Artifact Selection must preserve exact producer relationships, including:

- Artifact identity;
- Artifact category;
- relevant Page identity;
- Artifact Author records;
- Artifact Subject records;
- authorship mode;
- attribution status;
- represented Group;
- representation status;
- documented contribution where available;
- privacy policy;
- and correction lineage.

A Vitrine Proposal, Selection, Presentation, Annotation, or Reflection must not convert:

```text
Group Membership -> Artifact Author
Group Score -> individual Score
recorder_for_group -> sole authorship
Artifact Subject -> Artifact Author
Portfolio inclusion -> proficiency
```

If attribution is proposed, disputed, unknown, or superseded, the Selection must preserve that state and apply the Profile's conditional or prohibited behavior.

A Group-targeted Score summary may be selected as Group context. It must not be relabeled as an individual result.

### Portia

Only an exact, producer-approved portfolio-safe Portia projection may become a Candidate and then a Selection.

Vitrine must preserve:

- safe projection identity and revision;
- exact opt-in or permission reference where supplied;
- purpose limitation;
- Portfolio Subject relationship;
- and sensitivity obligations.

Vitrine must not:

- reveal suppressed Portia source existence;
- expose the source Event or intervention graph;
- include allegations, determinations, disability, safety, family, or unrelated participant information;
- or treat Selection as broad disclosure consent.

If a safe projection is revoked, withdrawn, corrected, or replaced, the old Selection remains historical and current working use requires explicit review.

### Meridian

Vitrine Selection has no effect on:

- Meridian publication eligibility;
- evidence inventory;
- attempt-selection policy;
- Grade-item membership;
- proficiency;
- Grades;
- overrides;
- or reports.

The same Candidate source may be selected for a showcase Portfolio and excluded from grading, or used in grading and omitted from a Portfolio.

## Profile migration

A Portfolio migration to a successor Profile Binding must not silently carry curation forward.

### Migration analysis

Migration must compare:

- Candidate eligibility;
- section IDs;
- selection rules;
- repeated-placement rules;
- requirement IDs;
- reflection rules and prompts;
- approval rules;
- and reapproval triggers.

### Migration outcomes

Each existing curation record may be classified as:

```text
retained_without_change
retained_with_new_placement
requires_new_selection
requires_new_reflection
requires_reapproval
prohibited_in_successor
unresolved
historical_only
```

### Successor composition

Migration creates:

- a new Profile Binding;
- any required successor Selections and Placements;
- new Arrangement revisions;
- new or revised Reflections where required;
- a new Composition series or explicitly linked successor composition under the new binding;
- and preserved predecessor references.

An old Composition Revision remains reproducible under the old Profile.

## Correction, withdrawal, replacement, and supersession

### Material endpoint correction

An error in any of these fields requires invalidation and a new record rather than in-place editing:

- Portfolio;
- Portfolio Subject;
- Profile Binding;
- Candidate;
- Candidate Evaluation;
- section;
- reflection rule;
- approval target;
- or exact source representation.

### Nonmaterial display correction

A spelling or wording correction in curator display metadata creates a new Presentation or Annotation revision.

The source title remains unchanged.

### Selection replacement

Replacement must preserve:

- old Selection;
- new Selection;
- explicit reason;
- old and new Candidate identities;
- affected Placements;
- whether Placements were recreated;
- Reflection impact;
- approval impact;
- and Composition transition.

### Replacement cycles

Replacement and supersession relationships must be acyclic.

One old Selection may be replaced by several successors, and several old Selections may be consolidated into one successor only when the eventual contract explicitly supports and validates that cardinality.

### Approval staleness

A changed target revision does not delete the prior approval.

The prior approval remains historically true for its exact target and becomes insufficient for the successor where policy requires reapproval.

## Candidate state changes after Selection

### Candidate Current Pointer advances

A Candidate Current Pointer change does not retarget an existing Selection.

Vitrine creates a new Candidate Evaluation for current-use diagnostics and may require a new Candidate and Selection where the source endpoint changed.

### Source becomes unavailable

The Selection remains historical.

A new availability observation or Candidate Evaluation may make current composition invalid or unresolved.

The Composition Revision must preserve the unavailable state rather than pretend the source was never selected.

### Source publication is withdrawn

Withdrawal does not erase historical Selection provenance.

The exact Profile and later snapshot policy decide whether the source may remain in working use, requires review, or is prohibited from new snapshots.

## Canonical, derived, and transient state

### Canonical Vitrine state

The following are canonical:

- Proposals;
- Decisions;
- Selections;
- lifecycle events;
- Placements;
- Arrangement Revisions and pointer transitions;
- Presentations;
- Rationales;
- Annotations;
- Reflections;
- Curation Review Decisions;
- Composition Revisions and pointer transitions;
- and correction or replacement links.

### Derived state

The following are derived and rebuildable:

- selected-item lists;
- section views;
- order previews;
- incomplete-reflection queues;
- approval dashboards;
- requirement-intent summaries;
- duplicate warnings;
- migration previews;
- replacement timelines;
- and curation search indexes.

### Transient state

The following may be transient:

- an unsaved reorder drag state;
- a draft editor buffer;
- a validation preview;
- a temporary diff;
- or a pending composition plan.

Transient state becomes canonical only through an explicit immutable record creation operation.

## Failure taxonomy

### Proposal and Decision failures

```text
selection_proposal_not_found
selection_proposal_already_decided
selection_proposal_predecessor_cycle
selection_actor_unauthorized
selection_candidate_not_eligible
selection_candidate_condition_unresolved
selection_candidate_evaluation_stale
selection_profile_binding_mismatch
selection_required_student_participation_missing
selection_direct_workflow_not_permitted
```

### Selection lifecycle failures

```text
selection_duplicate_active
selection_invalidated
selection_withdrawn
selection_already_replaced
selection_replacement_cycle
selection_successor_mismatch
selection_source_unavailable
selection_source_withdrawn
selection_projection_retired
selection_requires_reapproval
```

### Placement and arrangement failures

```text
section_not_found
section_prohibited
section_cardinality_exceeded
section_repeated_use_not_permitted
placement_duplicate
placement_profile_mismatch
placement_selection_inactive
placement_predecessor_cycle
arrangement_missing_placement
arrangement_duplicate_placement
arrangement_foreign_placement
arrangement_revision_conflict
arrangement_current_pointer_conflict
```

### Presentation and Annotation failures

```text
presentation_target_invalid
presentation_revision_conflict
presentation_source_title_overwritten
presentation_class_unknown
annotation_scope_invalid
annotation_target_cardinality_invalid
annotation_revision_conflict
annotation_claims_source_authority
```

### Reflection failures

```text
reflection_rule_not_found
reflection_prompt_version_unknown
reflection_author_role_mismatch
reflection_target_invalid
reflection_target_cardinality_invalid
reflection_comparison_incomplete
reflection_external_reference_invalid
reflection_revision_conflict
reflection_profile_binding_mismatch
```

### Approval failures

```text
approval_rule_not_found
approval_actor_unauthorized
approval_target_stale
approval_scope_mismatch
approval_sequence_invalid
approval_quorum_unmet
approval_waiver_not_permitted
approval_requires_reapproval
```

### Composition failures

```text
composition_inconsistent
composition_missing_selection
composition_missing_placement
composition_arrangement_mismatch
composition_profile_mismatch
composition_unresolved_obligation_hidden
composition_revision_conflict
composition_current_pointer_conflict
composition_predecessor_cycle
```

These failures remain distinct from:

- Candidate evaluation failures;
- source-access denial;
- disclosure denial;
- snapshot-generation failure;
- external-submission failure;
- and external rejection.

## Edge-case decisions

### Student Proposal accepted by teacher

- Student Proposal remains canonical.
- Teacher Decision records acceptance.
- Selection references both.
- Student participation does not imply public consent.

### Student Proposal rejected

- Rejection and rationale remain historical.
- No positive Selection is created.
- A revised Proposal receives a new ID.

### Teacher Proposal when student participation is required

- Proposal may be structurally valid.
- Activation remains blocked or conditional until the exact student-participation requirement is satisfied.

### System suggestion

- System may create a Proposal marked `system_suggestion` only where policy permits.
- It cannot create an active Selection without an authorized human or explicitly permitted institutional process.

### Same Candidate in two sections

- Create one Selection.
- Create two distinct Placements.
- Include each Placement in its section Arrangement.
- Validate repeated-use policy.

### Duplicate active Selection

- Reject a second active Selection for the same Candidate within the same Portfolio, Subject, and Profile Binding.
- Offer a Placement workflow instead.

### Concurrent reorder

- Each curator may create an Arrangement Revision from the same predecessor.
- Only one pointer update may succeed against the expected predecessor.
- The conflict is preserved for deliberate resolution.

### Source title changes

- Existing Presentation remains unchanged.
- Candidate source-title history remains exact.
- A curator may create a successor Presentation after reviewing the source change.

### Candidate Current Pointer advances

- Existing Selection remains bound to the Evaluation it relied upon.
- New current-use evaluation does not retarget it.

### Candidate becomes unavailable

- Historical Selection remains.
- New compositions must preserve the unavailable finding.
- Issue #9 later decides omission and snapshot behavior.

### ScoreForm has several attempts

- Each attempt Candidate requires a distinct Proposal or direct Selection.
- No automatic highest or latest policy exists.

### Profile permits one ScoreForm attempt

- Cardinality validation prevents more than one active permitted Placement or Selection contribution according to the exact Profile rule.
- The curator must explicitly replace or withdraw the prior choice.

### Quillan original work and feedback

- Two Candidates.
- Two Selections.
- Potentially separate sections or Placement purposes.
- Feedback Selection never stands in for original work.

### Quillan selected evidence changes

- Producer creates a successor projection and Candidate.
- Old Selection remains historical.
- Curator explicitly replaces it if desired.

### Concord Group Member lacks authorship

- Membership cannot support an individual-authorship Selection.
- Group-context Selection may be conditional only if the projection and Profile allow it.

### Concord attribution is disputed

- Preserve disputed status.
- Do not present unqualified authorship.
- Apply conditional, Group-context, or prohibited policy.

### Concord Group Score

- May be selected only as Group-targeted context where permitted.
- Annotation and Presentation must not state individual achievement.

### Portia-safe projection

- Selection references only the safe projection.
- No source graph, hidden count, or underlying event identifier is exposed beyond the approved projection contract.

### Portia-safe projection later revoked

- Historical Selection remains.
- Current composition requires explicit review and may become invalid or unresolved.
- Revocation does not erase prior curation history.

### Selection withdrawal

- Selection receives a withdrawal event.
- Placements become inactive through explicit lifecycle actions.
- Arrangements and Composition Revision are replaced, not edited.

### Selection replacement with Placement migration

- New Selection is created.
- New Placements reference the new Selection.
- Old Placements remain historical.
- New Arrangement and Composition revisions preserve the transition.

### Wrong Portfolio Subject

- Invalidate the erroneous Selection.
- Create a new Candidate evaluation and Candidate under the correct Subject if appropriate.
- Create a new Selection.
- Do not retarget the old Selection.

### Public caption without audience authorization

- Presentation may exist as a draft for intended `public` class.
- It cannot establish disclosure permission.

### Reflection revised after approval

- Reflection revision 1 and its approval remain historical.
- Reflection revision 2 requires new review where the Profile says so.

### Comparison Reflection references replaced Selection

- Existing Reflection remains historically valid.
- A new comparison using the successor requires a new Reflection revision.

### Profile migration changes section IDs

- Preserve old Placements.
- Create new Placements against successor section IDs.
- Record mapping or unresolved migration.

### Profile migration adds student approval

- Existing teacher approval remains historically scoped.
- Successor composition remains incomplete until the new student stage is satisfied.

### Approval targets earlier Composition Revision

- Approval remains exact.
- A later Composition Revision is not approved automatically.

### Derived index deleted

- Rebuild from canonical curation records and current pointers.
- No curation decision is lost.

## Security and privacy

### Data minimization

Curation records should store only metadata necessary to explain and reproduce curation.

They must not duplicate complete producer manifests or native records.

### IDs and paths

Do not place:

- names;
- student IDs;
- source titles;
- Portia semantics;
- or rationale text

in record IDs or filenames.

### Free text

Rationale, Annotation, Presentation, and Reflection are potential sources of sensitive or third-party information.

Later contracts and UI should support:

- bounded lengths;
- clear author attribution;
- intended visibility classification;
- privacy review flags;
- and safe export decisions.

They should not silently scan, classify, or rewrite actor-authored content without explicit policy.

### Diagnostics

Diagnostics must avoid revealing:

- suppressed Portia source existence;
- Quillan private notes;
- ScoreForm answers or detector details;
- Concord unrelated participants;
- or confidential institutional authorization data.

### Signatures and credentials

This design stores references to approval or authorization records, not credentials, tokens, cryptographic private keys, or raw biometric signatures.

## Downstream issue boundaries

### Issue #9 — snapshot, export, checksum, and immutability

Issue #9 will define:

- exact Composition Revision input;
- source-representation retrieval;
- copied bytes;
- producer-rendered and Vitrine-rendered derivatives;
- source and copied digests;
- snapshot manifests;
- omissions and unavailable-source handling;
- issuance;
- and snapshot supersession.

This issue defines no copied bytes.

### Issue #10 — privacy, redaction, and audience controls

Issue #10 will define:

- authenticated actors;
- authorization decisions;
- recipient identity;
- guardian verification;
- consent;
- collaborator review;
- redaction;
- metadata suppression;
- audience permission;
- and disclosure logs.

This issue may record intended presentation class and required review, but it grants no disclosure authority.

### Issue #11 — regulated Profiles

Issue #11 will define concrete regulated:

- checklists;
- documents;
- attestations;
- signatures;
- deadlines;
- review stages;
- and external outcomes.

The generic records here may represent those actor decisions without inventing their exact regulated meaning.

## Core impact

No blocking Core change is required.

Core remains authoritative for shared identity, work, publication, and manifest verification.

Vitrine can own curation records within its module namespace.

A new Core Selection registry, annotation registry, reflection registry, or approval registry would incorrectly centralize consumer-specific policy and is not recommended.

## Unresolved questions

The following questions remain intentionally open for final contracts or implementation issues:

1. Whether direct Selection should create an implicit Proposal/Decision pair or a separately typed equivalent provenance envelope.
2. Exact actor-reference contract and integration with institutional identity systems.
3. Exact curation-role vocabulary and whether Profile revisions may extend it.
4. Whether rationale, annotation, and reflection text use plain text, a restricted Markdown subset, or structured rich text.
5. Exact maximum lengths and language-tag requirements.
6. Whether one Selection may be placed in several sections by default or only through an explicit Profile flag.
7. Exact difference between `replaced` and `superseded` in final lifecycle schemas.
8. Whether Section Arrangement Current Pointer transitions are separate canonical events or versioned pointer records.
9. Whether Composition Revision uses sets sorted canonically or preserves explicit ordering for nonsection collections.
10. Exact contract for comparison-set roles such as baseline, intermediate, and current.
11. Whether a Profile may permit anonymous or pseudonymous external reviewers while preserving internal authoritative identity.
12. How institutional signature and consent references integrate without storing protected secrets.
13. How offline concurrent edits are reconciled beyond fail-closed optimistic concurrency.
14. Whether draft text buffers are stored by Vitrine or remain application-local transient state.
15. Exact archival and retention classifications for unsuccessful Proposals and superseded drafts.

## Validation invariants

The final contracts and implementation must preserve at least these invariants:

1. Candidate and Selection are distinct.
2. Proposal and positive Selection are distinct.
3. Rejected, withdrawn, expired, and changes-requested Proposals do not create positive Selections.
4. Automated suggestions cannot silently activate Selections.
5. One Selection binds one exact Candidate.
6. Selection preserves the exact Candidate Evaluation relied upon.
7. Candidate Current Pointer changes do not retarget Selection.
8. One Candidate has at most one active Selection per Portfolio, Subject, and Profile Binding in v0.1.0.
9. Repeated section appearance uses Placements rather than duplicate Selections.
10. Placement and Selection are distinct.
11. Profile section order and curator item order are distinct.
12. Item order is explicit and revisioned.
13. Current arrangement is identified explicitly.
14. Requirement intent is not requirement satisfaction.
15. Curator display title is not producer title.
16. Presentation class is not audience authorization.
17. Rationale, Annotation, Reflection, and Approval remain distinct.
18. Reflection is actor-authored interpretation.
19. Reflection preserves exact prompt identity and version.
20. Reflection revisions preserve history.
21. Approval binds one exact target revision.
22. Approval does not authorize source access, disclosure, issuance, or external acceptance.
23. Material changes do not silently inherit approval.
24. Composition Revision contains no copied producer bytes.
25. Composition current state is explicit.
26. No current curation state is inferred solely from timestamps or greatest revision.
27. Selection withdrawal preserves history.
28. Selection replacement creates a new Selection.
29. Correction never retargets an operational Selection in place.
30. ScoreForm Portfolio Selection does not choose the grading attempt.
31. Quillan producer evidence selection remains producer-owned.
32. Concord authorship, Group, representation, and Score-target semantics remain unchanged.
33. Portia suppression and safe-projection limits remain intact.
34. Meridian grading policy remains independent.
35. Derived indexes are rebuildable.
36. No canonical curation record is hard-deleted through ordinary workflow.
37. Concurrent arrangement and composition updates fail closed rather than silently overwriting.
38. Profile migration does not silently migrate curation.
39. Historical Composition Revisions remain usable as exact inputs to later snapshot provenance.
40. No sibling repository is modified.

## Related documents

- [Module boundaries and authority](../architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](portfolio-subject-identity.md)
- [Versioned Portfolio Profiles](portfolio-profile-contract.md)
- [Candidate and source-reference contract](candidate-source-reference-contract.md)
- [Producer artifact exposure boundaries](producer-artifact-exposure-boundaries.md)
- [ADR 0006: Selection, Ordering, Annotation, and Reflection](../decisions/0006-selection-ordering-annotation-and-reflection.md)
- [Representative selection and curation examples](../examples/selection-curation-examples.md)
