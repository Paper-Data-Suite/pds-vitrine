# Portfolio Subject Identity and Cross-Class Linking

- **Issue:** #4, “Define portfolio identity, subject identity, and cross-class linking”
- **Design date:** 2026-08-04
- **Status:** Foundation design paired with proposed ADR 0002; not a final serialized schema or runtime implementation
- **Applies to:** `pds-vitrine` v0.1.0 foundation work

## 1. Purpose

This document defines the conceptual identity model that Vitrine will use to manage student portfolios across classes and school years without claiming institution-wide identity authority.

It defines:

- Portfolio identity;
- Portfolio Subject identity;
- one-subject Portfolio cardinality for v0.1.0;
- exact class-qualified roster-student references;
- school-year context;
- historical person display snapshots;
- teacher-confirmed Subject Roster Associations;
- current versus historical source resolution;
- identity correction, merge, split, invalidation, and supersession;
- canonical workspace scope;
- derived reverse indexes;
- and downstream constraints for later Vitrine contracts.

The paired architectural decision is [ADR 0002: Portfolio Subject Identity and Roster Linking](../decisions/0002-portfolio-subject-identity-and-roster-linking.md). It remains **Proposed** until maintainers explicitly accept it.

## 2. Governing boundary

The module-boundary architecture establishes that Core owns shared class and roster records while Vitrine owns only its portfolio-specific subject associations. Vitrine is not an institutional identity provider, student information system, legal-identity registry, or roster authority.

The identity foundation therefore begins with these non-equivalences:

```text
same name
  != same student_id
  != same class-qualified roster identity
  != same Portfolio Subject
```

```text
same student_id in two rosters
  != confirmed same person
```

```text
confirmed same Portfolio Subject
  != authorized to access every source record
  != author of every related artifact
  != owner of every group artifact
  != subject of every producer record
  != evidence of proficiency
```

The central rule is:

> Vitrine may group exact roster-qualified identities only through explicit, attributable confirmation. Names, repeated IDs, optional roster fields, and source similarity may assist human review but never create identity authority.

## 3. Scope and non-goals

This document is conceptual. It does not define:

- final JSON Schema;
- Python classes;
- filesystem writers;
- transaction mechanics;
- a teacher-facing interface;
- automated matching;
- SIS or identity-provider integration;
- parent or guardian identity;
- institution-wide user accounts;
- portfolio profiles;
- source-candidate contracts;
- artifact projections;
- selection or annotation records;
- snapshot packages;
- authorization or disclosure policy;
- grading or proficiency;
- or regulated compliance-profile behavior.

Those responsibilities belong to later issues or external systems. This document constrains them.

## 4. Cross-repository review baseline

The following repository state was reviewed on 2026-08-04. Commit links are immutable review anchors.

| Repository | Reviewed state and implementation status | Authoritative documents reviewed | Reusable pattern | Incompatible assumption | Unresolved dependency |
| --- | --- | --- | --- | --- | --- |
| `pds-vitrine` | [`6f65a36`](https://github.com/Paper-Data-Suite/pds-vitrine/commit/6f65a3635e337d95ac96d9ee73fb351c6466449c); documentation-only foundation | [Module boundaries and authority](../architecture/module-boundaries.md), proposed [ADR 0001](../decisions/0001-vitrine-module-boundaries-and-authority.md) | Vitrine owns portfolio-specific subject associations while source identity remains upstream. | Vitrine must not become an SIS, roster authority, or institution-global person registry. | Final serialized records, persistence, and actor authorization remain future work. |
| `pds-core` | [`6c50721`](https://github.com/Paper-Data-Suite/pds-core/commit/6c507213618b68a6dd3ea096e1a898201ff029e6), released v0.6.0 shared infrastructure | [Roster and workspace contract](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/docs/roster_workspace_contract.md), [`rosters.py`](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/pds_core/rosters.py), [`class_metadata.py`](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/pds_core/class_metadata.py) | Exact roster lookup, string-preserved IDs, class metadata school year, identifier validation, and workspace/class helpers. | Core `student_id` is not workspace-global, and names are not identity. | Core has no roster revision ID or cross-roster person service; Vitrine must preserve historical context itself. |
| `pds-portia` | [`8cd4b1f`](https://github.com/Paper-Data-Suite/pds-portia/commit/8cd4b1f2ca80cc240693184c87e5df463ba375cf); accepted schemas and architecture, no complete executable app | [Portia README and identity model](https://github.com/Paper-Data-Suite/pds-portia/blob/8cd4b1f2ca80cc240693184c87e5df463ba375cf/README.md), accepted shared-reference decision and schemas | Exact `class_id + student_id` references, nonauthoritative display snapshots, explicit cross-class links, exact resolution, and append-preserving correction. | A class-owned Event or Support Process is not a longitudinal Portfolio Subject, and Portia Actor IDs must not be reused for roster students. | Future Portia publication and privacy-safe readers remain unavailable and deny-by-default. |
| `pds-concord` | [`e86e520`](https://github.com/Paper-Data-Suite/pds-concord/commit/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721); installable package baseline with accepted conceptual ADRs, domain runtime incomplete | [ADR 0005: Separate Artifact Authors and Subjects](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0005-separate-artifact-authors-and-subjects.md), [initial conceptual contracts](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/design/initial-conceptual-data-contracts.md) | Durable association records and strict separation among membership, authorship, subject, contribution, and Score targeting. | A roster identity or Portfolio Subject does not establish any Concord educational relationship. | Consumer-neutral artifact readers and production publication remain later Concord work. |
| `pds-scoreform` | [`1045975`](https://github.com/Paper-Data-Suite/pds-scoreform/commit/10459751476f6d48d3c3a908a26d76732f00e340); executable producer with Academic Result Manifest v1 and revision policy, full Core 0.6 workflow incomplete | [Academic Result Manifest v1](https://github.com/Paper-Data-Suite/pds-scoreform/blob/10459751476f6d48d3c3a908a26d76732f00e340/docs/academic_result_manifest_v1.md), [publication revision policy](https://github.com/Paper-Data-Suite/pds-scoreform/blob/10459751476f6d48d3c3a908a26d76732f00e340/docs/publication_revision_policy.md) | Student attempts remain exact producer facts within complete class/work context; append-preserved history. | A manifest `student_id` is not a global person key and does not select the official or Grade-bearing attempt. | Consumer reader and complete publication workflow must exist before production Vitrine ingestion. |
| `pds-quillan` | [`05fecf2`](https://github.com/Paper-Data-Suite/pds-quillan/commit/05fecf23d29e56b45cba58ed97906f5353290033), executable v0.8.9 on the prior Core line | [Data contracts](https://github.com/Paper-Data-Suite/pds-quillan/blob/05fecf23d29e56b45cba58ed97906f5353290033/docs/data_contracts.md), [workspace lifecycle](https://github.com/Paper-Data-Suite/pds-quillan/blob/05fecf23d29e56b45cba58ed97906f5353290033/docs/workspace_lifecycle.md) | Class-, assignment-, and student-qualified source paths; private versus student-facing projection boundaries. | A submission path or producer student field is not an institution-global identity and cannot create a Vitrine crosswalk. | Core 0.6 publication projection and consumer-neutral reader remain future work. |
| `pds-meridian` | [`e6be420`](https://github.com/Paper-Data-Suite/pds-meridian/commit/e6be420c1ad650fa801cd16867fa18a30cb1050c); architecture-only | [ADR 0001: Policy-Driven Standards Proficiency and Grade Calculation](https://github.com/Paper-Data-Suite/pds-meridian/blob/e6be420c1ad650fa801cd16867fa18a30cb1050c/docs/decisions/0001-policy-driven-standards-proficiency-and-grade-calculation.md), [ADR 0002: Provenance-Bound Report Snapshots](https://github.com/Paper-Data-Suite/pds-meridian/blob/e6be420c1ad650fa801cd16867fa18a30cb1050c/docs/decisions/0002-provenance-bound-report-snapshots-and-subscriptions.md) | Report identity and evidence must remain provenance-bound. | Meridian is not an artifact manager or a current global person registry for Vitrine. | No runtime subject or identity adapter exists. |
### 4.1 Core findings

The active Core roster contract defines required fields:

```text
class_id, student_id, last_name, first_name, period
```

Core preserves identifiers as strings, including leading zeros. It requires one exact class ID throughout a roster and rejects duplicate student IDs within that roster.

Core explicitly treats:

```text
student_id
```

as canonical for lookup **within one Roster**. Names and preferred names are display values only.

Core class metadata separately binds:

```text
class_id + school_year
```

Core does not currently provide:

- a roster revision ID;
- a workspace-global student ID;
- a district-global person ID;
- a cross-roster identity association;
- or a subject merge/split service.

### 4.2 Portia findings

Portia already uses a durable roster-student reference consisting of:

```text
class_id + student_id
```

It does not assume repeated IDs or matching names establish identity. Cross-class participants use complete explicit references, and historical display snapshots remain outside identity.

Portia also establishes useful rules that Vitrine adopts:

- exact references resolve without name-based repair;
- reverse histories are derived;
- canonical records are not duplicated under every related class;
- roster students are not duplicated as generic Actor records;
- and cross-year continuity uses explicit linked records.

Vitrine differs because a Portfolio Subject is intentionally longitudinal and may aggregate several confirmed roster identities. Portia Event ownership remains class-based; Vitrine Portfolio Subject identity is workspace-scoped.

### 4.3 Concord findings

Concord distinguishes student identity from educational relationships. The following remain separate:

- Group Membership;
- Artifact Author;
- Artifact Subject;
- contribution claim;
- recorder;
- represented Group;
- individual Score target;
- and Group Score target.

A Vitrine Portfolio Subject association cannot replace any of those Concord facts.

### 4.4 ScoreForm and Quillan findings

ScoreForm identifies a published attempt through complete work context plus student and attempt values. Quillan uses class-, assignment-, and student-qualified storage. Neither producer supplies an institution-global person identity.

Producer student values may support exact source linkage after the corresponding roster association is confirmed. They must not create a Portfolio Subject or cross-class link automatically.

## 5. Terms

### 5.1 Portfolio

A **Portfolio** is one durable Vitrine aggregate created for one portfolio workflow. It may later own curation, review, and issuance history.

A Portfolio is not a person, roster row, class, profile, source work, or snapshot.

### 5.2 Portfolio Subject

A **Portfolio Subject** is one Vitrine-owned, workspace-scoped identity anchor representing one person for portfolio purposes.

It groups confirmed roster-qualified identities without replacing their source rosters.

### 5.3 Portfolio Subject Binding

A **Portfolio Subject Binding** is the durable relationship connecting one Portfolio to exactly one Portfolio Subject.

The binding has its own identity and immutable endpoints so a Portfolio cannot be silently rebound.

### 5.4 Class-Qualified Roster Student Reference

A **Class-Qualified Roster Student Reference** identifies one exact student row through:

```text
school_year + class_id + student_id
```

Core lookup uses `class_id + student_id`; Vitrine preserves `school_year` in the serialized historical reference because class IDs and student IDs may be reused over time.

### 5.5 Person Display Snapshot

A **Person Display Snapshot** is historical, nonauthoritative presentation metadata copied from a confirmed roster row.

It improves readability but never functions as identity.

### 5.6 Subject Roster Association

A **Subject Roster Association** is a durable Vitrine record linking one Portfolio Subject to one exact class-qualified roster-student reference.

### 5.7 Identity Decision

An **Identity Decision** is an attributable event that proposes, confirms, rejects, invalidates, or supersedes a Subject Roster Association, or that records a subject merge, split, or Portfolio correction.

### 5.8 Current resolution

**Current resolution** answers whether an upstream Core class, metadata record, roster, and student row can be loaded and validated now.

Current resolution is distinct from the historical fact that an association was confirmed earlier.

## 6. Identity graph

The conceptual graph is:

```text
Portfolio
  -> Portfolio Subject Binding
      -> Portfolio Subject
          -> Subject Roster Association [0..*]
              -> Class-Qualified Roster Student Reference
              -> Person Display Snapshot
              -> Identity Decisions [1..*]
```

Subject correction may add:

```text
Portfolio Subject [predecessor 1..*]
  -> Subject Identity Transition
      -> Portfolio Subject [successor 1..*]
```

No edge in this graph grants artifact access by itself.

## 7. Portfolio conceptual contract

### 7.1 Purpose and ownership

Vitrine owns the Portfolio record. It identifies one independently managed portfolio aggregate.

### 7.2 Cardinality decision

For v0.1.0:

```text
one Portfolio -> exactly one Portfolio Subject
one Portfolio Subject -> zero or many Portfolios
```

Group, class, cohort, organization, and multi-subject portfolios are outside this foundation.

### 7.3 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `portfolio_id` | Required | Opaque, stable, collision-resistant Vitrine identity. |
| `contract_version` | Required | Portfolio identity contract version. |
| `created_at` | Required | Aware creation timestamp. |
| `created_by` | Required | Attributable actor reference or creation provenance. |
| `identity_status` | Required | `active`, `invalidated`, or `superseded` for identity purposes. |
| `subject_binding_id` | Required | Exact active or historical Portfolio Subject Binding. |
| `supersedes_portfolio_id` | Conditional | Direct predecessor when this Portfolio corrects an identity error. |
| `superseded_by_portfolio_id` | Derived or recorded by transition | Direct successor when established. |
| `identity_reason` | Conditional | Reason for invalidation or successor creation. |
| purpose/profile fields | Deferred | Defined by later profile contracts, not this identity record. |

### 7.4 Identifier rules

`portfolio_id` must:

- be nonempty and opaque;
- contain no direct PII;
- remain stable when display labels or source associations change;
- never be reused;
- not encode a student, class, year, purpose, or profile;
- and remain distinct from subject, binding, association, profile, selection, and snapshot IDs.

### 7.5 Correction rule

The subject endpoint of a Portfolio is not edited in place.

When a Portfolio was created for the wrong person:

1. preserve the original Portfolio and binding;
2. record an identity-invalidating decision;
3. create a successor Portfolio with a new ID;
4. bind the successor to the correct subject;
5. link the successor to its direct predecessor;
6. review any working selections explicitly;
7. and preserve issued snapshots without byte mutation.

## 8. Portfolio Subject conceptual contract

### 8.1 Purpose and ownership

Vitrine owns Portfolio Subject identity only inside one Vitrine workspace.

It does not become authoritative for legal or institutional identity.

### 8.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `portfolio_subject_id` | Required | Opaque, workspace-scoped, stable identity. |
| `contract_version` | Required | Subject identity contract version. |
| `created_at` | Required | Aware creation timestamp. |
| `created_by` | Required | Attributable actor or import/migration provenance. |
| `identity_status` | Required | `active`, `invalidated`, `merged`, `split`, or `superseded`. |
| `current_display_snapshot_id` | Optional | Convenience reference to a current presentation snapshot; not identity. |
| `identity_transition_ids` | Derived | Reverse view of canonical transitions involving the subject. |
| `association_ids` | Derived | Reverse view of Subject Roster Associations. |
| `portfolio_ids` | Derived | Reverse view of Portfolios bound to the subject. |
| demographic or academic fields | Forbidden | Grades, birth date, guardians, interventions, addresses, and general dossier fields do not belong here. |

### 8.3 Scope

The initial identity namespace is:

```text
one Vitrine workspace
```

Consequences:

- another workspace may independently generate the same opaque value;
- copying a record does not establish cross-workspace identity;
- subject IDs must not be advertised as district or state IDs;
- workspace merge requires an authorized reconciliation process;
- and multi-teacher or institution-wide identity remains future work.

### 8.4 Subject without a currently resolvable roster

A subject may remain valid when:

- all classes are historical;
- a student was removed from an active roster;
- a class folder is archived;
- or current source resolution is temporarily unavailable.

At least one historical confirmed association should normally support a subject. A subject created in error without any valid association may be invalidated rather than deleted.

## 9. Portfolio Subject Binding conceptual contract

### 9.1 Purpose

A separate binding record prevents silent rebinding and allows exact audit history.

### 9.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `portfolio_subject_binding_id` | Required | Opaque durable binding identity. |
| `contract_version` | Required | Binding contract version. |
| `portfolio_id` | Required | Exact Portfolio endpoint. |
| `portfolio_subject_id` | Required | Exact Portfolio Subject endpoint. |
| `created_at` | Required | Aware timestamp. |
| `created_by` | Required | Attributable actor or migration provenance. |
| `status` | Required | `active`, `invalidated`, or `superseded`. |
| `decision_id` | Required | Identity Decision authorizing creation or state change. |
| `supersedes_binding_id` | Conditional | Direct predecessor binding, used only with a successor Portfolio identity correction. |
| `reason` | Conditional | Correction or invalidation rationale. |

### 9.3 Invariants

- One Portfolio has exactly one active binding.
- A binding has exactly one Portfolio and one Portfolio Subject endpoint.
- Endpoints are immutable.
- A Portfolio cannot acquire a second active binding.
- A wrong endpoint requires a successor Portfolio, not a binding swap.
- Multiple Portfolios may bind to the same subject.

## 10. Class-Qualified Roster Student Reference

### 10.1 Serialized shape

The Vitrine conceptual value is:

```yaml
school_year: "2026-2027"
class_id: "english10_p2"
student_id: "00107"
```

`school_year` is included in the serialized Vitrine reference rather than left only as transient lookup context.

### 10.2 Why school year is serialized

Core class metadata is mutable and separately stored. Vitrine must preserve the school-year context that an authorized actor confirmed at the time of association.

This protects against:

- class folder reuse;
- accidental metadata replacement;
- student ID reuse in later years;
- and loss of historical context after archival movement.

The serialized school year does not override Core. At confirmation time it must equal validated Core class metadata.

### 10.3 Validation at confirmation

Confirmation requires all of the following:

1. `school_year`, `class_id`, and `student_id` pass applicable validation.
2. The exact Core class folder exists.
3. Class metadata loads successfully.
4. Metadata `class_id` matches the folder.
5. Metadata `school_year` equals the proposed Vitrine reference.
6. The canonical class roster loads successfully.
7. The roster class ID matches the class folder.
8. The exact student ID exists once in the roster.
9. Student identifiers remain strings and preserve leading zeros.
10. No conflicting active confirmed association already claims the same reference.

### 10.4 Reference identity key

Within one Vitrine workspace, the complete historical key is:

```text
school_year + class_id + student_id
```

A bare `student_id` is invalid as a Vitrine identity endpoint.

### 10.5 Source evidence

A later serialized contract may preserve confirmation evidence such as:

- class metadata SHA-256;
- roster SHA-256;
- source paths relative to the workspace;
- Core contract versions;
- or a roster-row snapshot.

These values support audit but do not become identity. Exact digest fields should be finalized with persistence and security review.

## 11. Person Display Snapshot

### 11.1 Purpose

A Person Display Snapshot preserves the human-readable label observed when an association was proposed or confirmed.

### 11.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `person_display_snapshot_id` | Required | Opaque snapshot identity. |
| `association_id` | Required | Association whose source row was captured. |
| `captured_at` | Required | Aware timestamp. |
| `first_name` | Required | Source display value at capture. |
| `last_name` | Required | Source display value at capture. |
| `preferred_name` | Optional | Optional roster display value. |
| `display_name` | Required | Deterministically rendered convenience value. |
| `class_id` | Required | Display context; duplicates exact reference context. |
| `school_year` | Required | Display context. |
| `source_kind` | Required | `core_roster`. |
| identity authority | Forbidden | The snapshot must never assert that names prove identity. |

### 11.3 Rules

- Snapshots are immutable.
- A name change creates a later snapshot if a current display update is needed.
- Old snapshots remain attached to historical decisions and editions.
- Current UI may prefer the newest authorized snapshot.
- Snapshot differences neither confirm nor invalidate identity automatically.
- Snapshots must not be searched to repair an unresolved exact reference.

## 12. Subject Roster Association conceptual contract

### 12.1 Purpose

The association records that an exact roster-student reference has been considered in relation to one Portfolio Subject.

### 12.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `subject_roster_association_id` | Required | Opaque durable association identity. |
| `contract_version` | Required | Association contract version. |
| `portfolio_subject_id` | Required | Exact subject endpoint. |
| `roster_student_ref` | Required | Exact `school_year + class_id + student_id` value. |
| `display_snapshot_id` | Required | Nonauthoritative historical display snapshot. |
| `created_at` | Required | Proposal or direct-creation time. |
| `created_by` | Required | Proposing actor or migration source. |
| `status` | Required | `proposed`, `confirmed`, `rejected`, `invalidated`, or `superseded`. |
| `confirmation_decision_id` | Conditional | Required in confirmed state. |
| `terminal_decision_id` | Conditional | Required for rejected, invalidated, or superseded state. |
| `supersedes_association_ids` | Conditional | One or more direct predecessors when correcting, consolidating, merging, or splitting associations. |
| `basis_summary` | Required for confirmation | Concise human-readable reason. |
| `basis_type` | Required for confirmation | Controlled basis category. |
| `external_basis_ref` | Optional | Reference to an authoritative record stored elsewhere. |
| current resolution fields | Derived | Must not overwrite historical confirmation. |

### 12.3 Endpoint immutability

The following never change after creation:

- association ID;
- Portfolio Subject endpoint;
- school year;
- class ID;
- student ID;
- creation attribution;
- and initial display snapshot.

A wrong endpoint requires a new association.

Lifecycle changes are append-preserving. A final serialized contract may store immutable association revisions or derive current `status` from Identity Decisions, but it must not overwrite or erase the decision history that produced the current projection.

### 12.4 Lifecycle

Allowed conceptual transitions are:

```text
proposed -> confirmed
proposed -> rejected
confirmed -> invalidated
confirmed -> superseded
```

A confirmed association does not become rejected retroactively. If it was wrong, it is invalidated or superseded with explicit history.

Terminal states do not return to confirmed. A later valid relationship uses a new association. When a subject merge or split changes the operational subject endpoint, successor associations are created on the successor subject and explicitly supersede the predecessor associations.

### 12.5 Confirmation effect

Confirmation establishes only that the exact roster reference and Portfolio Subject represent the same person for the documented local Vitrine context.

Confirmation does not:

- modify the Core roster;
- authorize source access;
- authorize cross-class disclosure;
- select artifacts;
- establish producer authorship;
- establish Concord contribution;
- establish Grade eligibility;
- or establish institutional identity.

## 13. Identity Decision conceptual contract

### 13.1 Purpose

An Identity Decision records an attributable human or authorized external decision affecting identity state.

### 13.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `identity_decision_id` | Required | Opaque durable decision identity. |
| `contract_version` | Required | Decision contract version. |
| `decision_type` | Required | Controlled decision vocabulary. |
| `subject_ids` | Conditional | Subjects affected by subject-level decisions. |
| `association_ids` | Conditional | Associations affected by association decisions. |
| `portfolio_ids` | Conditional | Portfolios affected by correction decisions. |
| `decided_at` | Required | Aware timestamp. |
| `decided_by` | Required | Attributable actor reference. |
| `role_at_decision` | Required | Role claimed under the applicable local policy. |
| `authority_source` | Required | Workspace policy, institutional reference, or migration authority. |
| `basis_type` | Required | Basis category. |
| `basis_summary` | Required | Concise rationale. |
| `external_basis_ref` | Optional | Reference to supporting source stored outside Vitrine. |
| `supersedes_decision_id` | Optional | Corrects a prior decision without deleting it. |

### 13.3 Decision types

The initial conceptual vocabulary includes:

```text
propose_association
confirm_association
reject_association
invalidate_association
supersede_association
create_subject
invalidate_subject
merge_subjects
split_subject
invalidate_portfolio_identity
create_successor_portfolio
```

Final serialized vocabulary may refine these names but must preserve the distinctions.

### 13.4 Initial confirmation authority

In the v0.1.0 local-first workflow, cross-class and cross-year confirmation requires attributable teacher action.

A generic string such as:

```text
teacher
```

is insufficient. The decision must preserve an actor reference or local identity value supplied by the deployment, the actor's role at decision time, and the authority source.

Complete authentication and authorization remain later work.

### 13.5 Confirmation bases

Suggested basis categories are:

```text
direct_teacher_knowledge
authorized_institutional_crosswalk
verified_sis_information
student_confirmation
parent_or_guardian_confirmation
transfer_or_enrollment_record
migration_from_reviewed_source
other_authorized_basis
```

A basis category does not itself prove authority. `authority_source` and actor attribution remain required.

Sensitive identity documents should normally remain in their authoritative system. Vitrine should store a reference and concise rationale rather than copies.

## 14. Automated suggestion boundary

A later UI may offer candidate matches for teacher review, but the output is never more than a proposal.

Automatic confirmation is prohibited from any single signal or combination of signals, including:

- exact name;
- fuzzy name;
- preferred name;
- initials;
- repeated student ID;
- matching email-like optional field;
- class period;
- course sequence;
- school year;
- assignment history;
- producer work history;
- handwriting;
- writing style;
- file metadata;
- directory ownership;
- device identity;
- or statistical similarity.

A proposal must not unlock cross-class discovery, show protected records, or merge histories.

## 15. Cross-class rules

A Portfolio Subject may have several confirmed associations in one school year.

Examples include:

- concurrent English and computer science enrollment;
- a midyear schedule change;
- an interdisciplinary portfolio;
- or transfer between class periods.

Required rules:

1. Every endpoint is an exact roster-student reference.
2. Each additional class requires explicit confirmation.
3. No Core roster is modified.
4. No synthetic roster row is created.
5. No Portfolio or subject root is duplicated under each class.
6. No class becomes the permanent owner of person identity.
7. Producer work remains in its owning class and module.
8. Authorization remains class- and purpose-sensitive.
9. One invalid association does not invalidate unrelated associations automatically.
10. Current enrollment state remains separate from historical identity.

## 16. Cross-year rules

A Portfolio Subject may have several confirmed associations across school years.

Each association preserves its own:

- school year;
- class ID;
- student ID;
- display snapshot;
- confirmation decision;
- and current-resolution state.

A later roster entry is not linked automatically even when the student ID repeats.

A new year does not:

- create a new Portfolio Subject automatically;
- merge subjects automatically;
- replace prior associations;
- move old producer records;
- or rewrite issued snapshots.

Longitudinal continuity is represented by multiple confirmed associations to one stable Portfolio Subject.

## 17. Current versus historical resolution

### 17.1 Historical confirmation

Historical confirmation records what an attributable actor decided using the source context available at that time.

### 17.2 Current resolution states

A derived resolver should distinguish at least:

```text
resolvable
class_not_found
class_metadata_missing
class_metadata_invalid
class_school_year_mismatch
roster_missing
roster_invalid
student_not_found
student_id_conflict
historical_reference_only
source_unavailable
```

### 17.3 Resolution does not rewrite identity

When a source no longer resolves:

- preserve the association;
- preserve its historical decision;
- report the current state;
- block operations that require live source access;
- and do not substitute a similarly named roster row.

### 17.4 Roster removal

Removal from an active roster means only that the current roster no longer contains the row. It does not prove that the historical association was wrong.

## 18. Duplicate active-association invariant

Within one Vitrine workspace, one exact reference:

```text
school_year + class_id + student_id
```

may have at most one active confirmed Portfolio Subject.

If the same reference is confirmed against two subjects:

- report an integrity conflict;
- stop ordinary current-subject resolution;
- do not select one by timestamp, identifier, name, or portfolio count;
- require explicit merge, split, invalidation, or supersession;
- and preserve both prior records for audit.

## 19. Subject merge

### 19.1 Use case

Two Portfolio Subjects are later confirmed to represent the same person.

### 19.2 Decision

A merge is nondestructive and successor-based.

Conceptually:

```text
subject A ----\
               -> merge transition -> subject C
subject B ----/
```

### 19.3 Rules

- Create a new successor subject C.
- Preserve subjects A and B.
- Mark A and B as merged or superseded through an explicit transition.
- Preserve all predecessor associations and decisions on their original subjects.
- Create successor associations on C for every roster reference that remains valid.
- Each successor association identifies the predecessor association or associations it supersedes.
- Mark predecessor associations noncurrent through explicit supersession decisions.
- Consolidate duplicate exact references deliberately rather than copying two active claims.
- New operational use resolves prospectively through C and its successor associations.
- Do not rewrite issued snapshots.
- Do not delete duplicate records.
- Do not move producer data.
- Validate that successor relationships are acyclic.

### 19.4 Portfolio handling

Existing Portfolios retain their original subject bindings as historical facts.

For an active working Portfolio that must continue under C:

- create an explicit successor Portfolio;
- bind it to C;
- preserve predecessor linkage;
- and migrate or reconsider working selections through a later authorized workflow.

This prevents hidden rebinding.

## 20. Subject split

### 20.1 Use case

One Portfolio Subject incorrectly combines associations belonging to different people.

### 20.2 Decision

A split is nondestructive and successor-based.

```text
subject A
  -> split transition
      -> subject B
      -> subject C
```

### 20.3 Rules

- Preserve erroneous subject A.
- Create corrected successor subjects.
- Record exactly which predecessor associations allocate to each successor subject.
- Create new successor associations on the corrected subjects and supersede the predecessor associations explicitly.
- Do not change old association endpoints in place.
- Identify affected Portfolios and candidate histories.
- Require explicit successor Portfolios where continued work is needed.
- Preserve issued snapshots.
- Do not infer artifact ownership from the corrected roster grouping.

## 21. Subject Identity Transition conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `subject_identity_transition_id` | Required | Opaque transition identity. |
| `transition_type` | Required | `merge`, `split`, `invalidate`, or `supersede`. |
| `predecessor_subject_ids` | Required | One or more exact predecessors. |
| `successor_subject_ids` | Conditional | Required for merge, split, or supersede. |
| `decided_at` | Required | Aware decision time. |
| `decided_by` | Required | Attributable actor. |
| `authority_source` | Required | Policy or institutional authority context. |
| `basis_summary` | Required | Human-readable reason. |
| `association_allocation` | Conditional | For merge or split, explicit mapping from predecessor associations to successor subjects and successor association IDs. |
| `affected_portfolio_ids` | Required, possibly empty | Portfolios requiring review. |
| `supersedes_transition_id` | Optional | Correction of a prior transition. |

### 21.1 Validation

- A subject cannot be its own successor.
- Transition chains must be acyclic.
- One predecessor cannot have contradictory active terminal transitions.
- A merge has two or more predecessors and exactly one successor.
- A split has one predecessor and two or more successors.
- A successor subject must be newly created for the transition.
- Current resolution follows explicit transitions, never identifier order or timestamp alone.

## 22. Canonical namespace and storage scope

### 22.1 Decision

Portfolio and Portfolio Subject identity are Vitrine-owned and workspace-scoped.

A representative conceptual namespace is:

```text
<PDS workspace>/
  vitrine/
    portfolios/
      <portfolio_id>/
    subjects/
      <portfolio_subject_id>/
    bindings/
    roster-associations/
    identity-decisions/
    subject-transitions/
    derived/
```

This is a conceptual storage decision, not an implemented filesystem contract.

### 22.2 Rejected class duplication

Canonical Portfolio and subject records are not copied beneath every linked class. Class-level indexes may be derived.

### 22.3 Core impact

No blocking Core change is required for the conceptual model.

Vitrine can use existing Core:

- identifier validation;
- workspace root;
- class folders;
- class metadata;
- roster loading;
- and class-qualified source context.

A generalized Core workspace-module path should be proposed only if several independent modules require the same abstraction. Vitrine should not add a global person registry to Core merely for convenience.

## 23. Canonical and derived data

### 23.1 Canonical Vitrine identity records

Canonical records are:

- Portfolio;
- Portfolio Subject;
- Portfolio Subject Binding;
- Subject Roster Association;
- Person Display Snapshot;
- Identity Decision;
- and Subject Identity Transition.

### 23.2 Derived views

Derived and rebuildable views may include:

- subject by roster reference;
- subjects by class;
- subjects by school year;
- Portfolios by subject;
- associations by status;
- current display name;
- merge/split resolution graph;
- unresolved identity work queue;
- and cross-class candidate scope.

A derived index must not:

- create confirmation;
- override canonical records;
- repair references by name;
- or become the only history of a decision.

## 24. Privacy and data minimization

The identity layer must:

- use opaque IDs;
- avoid direct PII in paths and identifiers;
- store only necessary display snapshots;
- avoid copying whole rosters;
- avoid copying identity documents by default;
- preserve references to authoritative external evidence rather than duplicate it;
- restrict cross-class matching interfaces to authorized contexts;
- avoid exposing one class roster merely because another class is visible;
- avoid Portia existence leakage;
- and support retention and disclosure policy without pretending to decide it.

The identity layer must not store:

- birth dates;
- addresses;
- guardian records;
- disability details;
- intervention summaries;
- biometric-like identifiers;
- writing-style fingerprints;
- device fingerprints;
- or broad demographic profiles.

## 25. Interaction with later Vitrine contracts

### 25.1 Portfolio profiles

A later profile identifies purpose, audience, requirements, and policy. It must reference Portfolio and subject identity rather than redefine them.

### 25.2 Candidate and source references

Candidate discovery may use only confirmed, currently permitted associations. It must preserve the exact roster context through which a source is related to the subject.

Identity confirmation remains separate from source authorization.

### 25.3 Producer artifact exposure

Producer readers remain authoritative for whether a roster student is an author, subject, score target, or other participant in one source record.

### 25.4 Selections and annotations

A selection must record the subject relationship relied on. An annotation may describe participation but cannot rewrite source authorship.

### 25.5 Snapshots

Issued snapshots must preserve:

- Portfolio ID;
- Portfolio Subject ID;
- binding ID;
- relevant roster association IDs;
- display snapshots used;
- and identity-transition state at issuance.

Later identity correction does not silently change issued bytes.

### 25.6 Privacy controls

Identity confirmation does not grant Portia access, family disclosure, public sharing, or cross-class source access. Later authorization must evaluate those separately.

## 26. Failure-state vocabulary

Later contracts should distinguish at least:

```text
subject_not_found
subject_invalidated
subject_superseded
subject_merge_required
subject_split_required
portfolio_subject_mismatch
portfolio_identity_invalidated
roster_reference_not_found
roster_reference_conflict
roster_student_removed
class_metadata_missing
class_metadata_invalid
class_school_year_mismatch
roster_missing
roster_invalid
association_proposed
association_confirmation_required
association_rejected
association_invalidated
association_superseded
duplicate_active_association
actor_not_authorized_to_confirm
source_context_unavailable
display_snapshot_stale
historical_reference_only
current_resolution_unavailable
identity_transition_cycle
```

“Not found,” “historical,” “invalidated,” “unauthorized,” and “conflicted” are not interchangeable.

## 27. Edge-case decisions

### 27.1 Same student ID, different classes, different people

Do not link automatically. Create separate subjects unless an authorized actor explicitly confirms one person.

### 27.2 Same person, different student IDs

Allow both exact references on one subject after independent confirmation.

### 27.3 Midyear class-period change

Preserve both class-qualified associations and their source work. Enrollment status may change without invalidating historical identity.

### 27.4 Name change

Keep subject identity unchanged. Create a later display snapshot when needed.

### 27.5 Preferred-name disagreement

Treat as display variation only.

### 27.6 Student removed from roster

Preserve the confirmed historical association and report current nonresolution.

### 27.7 Class metadata school-year change

Report a mismatch. Do not rewrite the association's historical school year.

### 27.8 Corrected roster student ID

Create and confirm a new association. Supersede or invalidate the old association explicitly.

### 27.9 One roster reference claimed by two subjects

Block ordinary resolution and require explicit reconciliation.

### 27.10 Same person represented in two workspaces

Treat as separate local identities until an authorized migration or cross-workspace reconciliation contract exists.

### 27.11 Portfolio bound to wrong person

Invalidate identity use and create a successor Portfolio. Never swap the subject endpoint silently.

### 27.12 Association invalidated after issuance

Preserve snapshot bytes and audit history. Later access restriction, withdrawal, or corrected reissue is explicit.

### 27.13 Concord group artifact

Subject identity does not establish individual authorship, contribution, ownership, or proficiency.

### 27.14 Portia record

Matching roster identity does not authorize discovery or inclusion. Portia remains deny-by-default.

## 28. Foundational invariants

1. `portfolio_id` is opaque, stable, unique within its scope, and never reused.
2. `portfolio_subject_id` is opaque, stable, workspace-scoped, and never reused.
3. One v0.1.0 Portfolio has exactly one Portfolio Subject.
4. Multiple Portfolios may reference one Portfolio Subject.
5. Portfolio-to-subject binding has immutable endpoints.
6. A wrong Portfolio subject requires explicit successor history.
7. A bare `student_id` is never a complete Vitrine roster reference.
8. The complete historical roster key is `school_year + class_id + student_id`.
9. Names and preferred names are display data only.
10. Display snapshots are immutable and nonauthoritative.
11. Proposed associations grant no cross-class authority.
12. Confirmation requires attributable teacher action in v0.1.0.
13. Automated matching never confirms identity.
14. One exact roster reference has at most one active confirmed subject.
15. One subject may have several confirmed roster references.
16. Association endpoints are immutable.
17. Endpoint correction, merge, and split create explicit successor associations.
18. Roster removal does not erase historical confirmation.
19. Current resolution is separate from historical identity.
20. Merge and split preserve predecessors.
21. Merge and split create explicit successor subjects.
22. Subject transition graphs are acyclic.
23. Reverse indexes are derived and nonauthoritative.
24. Vitrine identity operations never modify Core rosters or class metadata.
25. Identity confirmation does not grant source access.
26. Identity confirmation does not establish producer authorship or proficiency.
27. Issued snapshots are never silently rewritten after identity correction.
28. No real student data is required to validate this model.

## 29. Unresolved implementation questions

The conceptual decisions are sufficient for later serialized-contract work, but implementation must still decide:

- exact identifier prefixes and generation method;
- exact JSON Schema versioning strategy;
- whether canonical records use immutable revisions or append-only event logs;
- atomic write and recovery behavior;
- whether roster and metadata SHA-256 values are required at confirmation;
- the local actor-reference contract used before institutional authentication exists;
- how current-resolution caches are rebuilt;
- how subject transition resolution is exposed safely;
- how archived class sources are loaded;
- and whether a later Core workspace-module path becomes shared infrastructure.

These questions must not weaken the settled identity invariants.

## 30. Validation checklist for later contracts

A serialized implementation must prove at least:

- exact endpoint validation;
- preservation of leading-zero IDs;
- school-year agreement with Core metadata at confirmation;
- rejection of bare IDs and name-only references;
- proposal versus confirmation separation;
- duplicate active-reference detection;
- immutable endpoints;
- legal lifecycle transitions;
- nondestructive merge and split;
- acyclic transition graphs;
- one active subject binding per Portfolio;
- no hidden rebinding;
- current/historical resolution distinction;
- derived-index rebuildability;
- privacy-safe diagnostics;
- and no upstream mutation.

## 31. Conclusion

Vitrine needs a durable identity anchor because a portfolio may span classes and years, but it must not pretend that local roster values are globally unique or that Vitrine is an institutional identity authority.

The foundation therefore separates:

```text
Portfolio
Portfolio Subject
Portfolio-to-Subject Binding
exact roster identity
human confirmation
current source resolution
historical display
producer relationship
source authorization
```

That separation makes longitudinal portfolios possible without unsafe name matching, destructive merges, or hidden reassignment of student work.
