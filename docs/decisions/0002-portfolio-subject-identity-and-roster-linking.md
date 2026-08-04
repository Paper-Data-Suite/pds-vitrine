# ADR 0002: Portfolio Subject Identity and Roster Linking

- **Status:** Proposed
- **Date:** 2026-08-04
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #4, “Define portfolio identity, subject identity, and cross-class linking”

## Context

Vitrine must support student portfolios that may span several classes and school years.

Core currently owns canonical class folders, class metadata, and rosters. A Core roster makes `student_id` canonical within one roster, while names are display values. Class metadata supplies school-year context. Core does not provide a workspace-global or institution-global person identity or an authoritative cross-roster identity crosswalk.

Producer modules also preserve class and work context:

- ScoreForm student attempts are meaningful within complete ScoreForm work identity.
- Quillan submissions are class-, assignment-, and student-qualified.
- Concord separates roster identity from Group Membership, Artifact Authors, Artifact Subjects, contribution, and Score targets.
- Portia uses explicit `class_id + student_id` references and rejects matching names or repeated IDs as identity proof.

Vitrine needs a limited, local identity layer that can connect several exact roster identities to one longitudinal portfolio subject. It must not become an SIS, legal-identity registry, or institution-wide person service.

The design must prevent both:

1. treating each class enrollment as a permanently different person; and
2. automatically merging different people because names or IDs match.

## Decision

### Separate Portfolio and Portfolio Subject

Vitrine will model Portfolio and Portfolio Subject as separate durable concepts.

A Portfolio represents one independently managed portfolio workflow.

A Portfolio Subject represents one person for local Vitrine portfolio purposes.

For v0.1.0:

```text
one Portfolio -> exactly one Portfolio Subject
one Portfolio Subject -> zero or many Portfolios
```

Group, cohort, class, organization, and multi-subject portfolios are deferred.

### Use a separate immutable Portfolio Subject Binding

The relationship between a Portfolio and its subject will be a durable binding record with its own identity and immutable endpoints.

A Portfolio must never be silently rebound.

When the subject endpoint is wrong, Vitrine will preserve the original Portfolio and create an explicit successor Portfolio bound to the corrected subject.

### Use workspace-scoped Portfolio Subject identity

Each subject receives an opaque `portfolio_subject_id` unique within one Vitrine workspace.

The identifier:

- is not derived from a roster entry;
- contains no direct PII;
- remains stable across class and school-year changes;
- is not automatically portable across workspaces;
- and must not be represented as a district, state, or legal identity.

### Use exact class-qualified roster references

Vitrine will serialize a roster-student reference as:

```text
school_year + class_id + student_id
```

Core lookup continues to use `class_id + student_id`. Vitrine includes school year in its historical reference because class IDs and student IDs may be reused and Core class metadata may change later.

At confirmation time:

- the Core class folder must resolve;
- class metadata must validate;
- its school year must match the proposed reference;
- the roster must validate;
- and the exact student ID must exist in that roster.

A bare `student_id` is never a valid Vitrine person reference.

### Make Subject Roster Association a durable record

A Subject Roster Association will connect one Portfolio Subject to one exact class-qualified roster reference.

The association will carry:

- opaque association identity;
- immutable endpoints;
- proposal and confirmation provenance;
- nonauthoritative display snapshot;
- basis and authority information;
- lifecycle status;
- and explicit correction or supersession history.

### Require explicit teacher confirmation

For the initial local-first foundation, cross-class and cross-year associations require attributable teacher confirmation. Automatic confirmation is prohibited.

Matching names, preferred names, initials, repeated student IDs, optional roster columns, producer histories, filenames, directories, handwriting, writing style, or other similarity signals may not confirm identity automatically.

A future UI may propose a match. A proposal grants no cross-class authority and cannot unlock records.

### Preserve names only as display snapshots

Names and preferred names remain nonauthoritative display data.

Historical display snapshots may be retained for readability, but they never:

- establish identity;
- repair an unresolved reference;
- merge subjects;
- or override Core roster state.

### Separate historical identity from current source resolution

A confirmed association remains part of history when a student is removed from a roster or a class becomes unavailable.

Current resolution will be reported separately. It will not silently rewrite or erase the historical association.

### Use nondestructive correction

Confirmed association endpoints are immutable.

A wrong endpoint creates a new association and explicit invalidation or supersession history.

A Portfolio bound to the wrong subject creates a successor Portfolio rather than an in-place subject swap.

### Use successor-based subject merge and split

Duplicate Portfolio Subjects will not be deleted or rewritten.

A merge creates one new successor subject and preserves every predecessor. Valid roster links are carried forward through new successor associations that explicitly supersede the predecessor associations; duplicate exact links are consolidated through the merge decision.

An incorrectly combined subject is split by creating two or more successor subjects and preserving the erroneous predecessor. New successor associations allocate each valid roster link to the correct successor and explicitly supersede the old associations.

Existing Portfolio bindings remain historical. Continued active work uses explicit successor Portfolios.

Merge, split, and supersession graphs must be acyclic and must not derive current identity from timestamps or identifier ordering.

### Use a Vitrine-owned workspace namespace

Portfolio and subject identity will be conceptually scoped beneath a Vitrine-owned workspace namespace rather than duplicated under every class.

Representative conceptual layout:

```text
<PDS workspace>/vitrine/
  portfolios/
  subjects/
  bindings/
  roster-associations/
  identity-decisions/
  subject-transitions/
  derived/
```

This ADR does not finalize filesystem paths.

### Require no blocking Core change

The foundation can use existing Core class, metadata, roster, workspace, and identifier contracts.

Vitrine will not create a Core global person registry solely for its own convenience.

A generalized Core workspace-module path may be proposed later only if several independent modules require the same abstraction.

## Authority and non-implications

A confirmed Vitrine association means only:

> An attributable authorized actor determined that the exact roster reference and the Portfolio Subject represent the same person for the documented local portfolio context.

It does not establish:

- institutional or legal identity;
- current enrollment;
- source access authorization;
- disclosure permission;
- artifact ownership;
- Artifact Author or Subject status;
- contribution;
- Score target;
- Grade-item membership;
- proficiency;
- or graduation eligibility.

## Consequences

### Positive consequences

- Longitudinal portfolios can span classes and years.
- Reused IDs and matching names cannot silently combine students.
- Core remains the roster authority.
- Vitrine remains a local portfolio identity layer rather than a competing SIS.
- Historical decisions remain auditable.
- Name changes do not change identity.
- Roster removal does not erase portfolio history.
- Duplicate subjects can be reconciled without deleting evidence.
- Incorrectly combined subjects can be split without rewriting issued snapshots.
- Later candidate discovery can use exact confirmed subject scope.

### Costs and limitations

- Teachers must confirm cross-class and cross-year links.
- The same person may temporarily have duplicate Portfolio Subjects.
- Current source resolution may become unavailable for historical references.
- Merge and split workflows require explicit successor handling.
- Existing Portfolios cannot be rebound silently, so correction may create additional records.
- Workspace-scoped subject IDs are not institution-wide identity.
- Multi-teacher and cross-workspace reconciliation remain future work.

### Security and privacy consequences

- Cross-class matching interfaces require authorization and data minimization.
- Optional roster columns cannot be copied indiscriminately.
- Identity decisions require attributable actors and authority context.
- Opaque IDs must avoid direct PII.
- Sensitive identity documents should remain in authoritative external systems.
- Portia records remain deny-by-default even when roster identity matches.

## Rejected alternatives

### Use bare `student_id` as workspace-global identity

Rejected because Core guarantees uniqueness only within one roster, and IDs may repeat across classes or years.

### Use student name as identity

Rejected because names change, collide, vary in spelling, and are display data rather than durable identifiers.

### Automatically merge matching IDs across rosters

Rejected because repeated IDs do not prove that two roster rows represent one person.

### Automatically merge matching names

Rejected because exact and fuzzy name matches produce both false positives and false negatives.

### Use optional roster fields as hidden automatic identity keys

Rejected because optional columns are not guaranteed, may be stale or sensitive, and do not become institutionally authoritative merely by appearing in a roster.

### Use one class enrollment as permanent Portfolio identity

Rejected because portfolios may span classes and years, and one class should not own longitudinal person identity.

### Store a separate canonical Portfolio beneath every linked class

Rejected because duplication creates conflicting authority and correction problems. Class indexes should be derived.

### Treat Portfolio as the person identity

Rejected because one person may need several purpose-specific Portfolios and each Portfolio has an independent lifecycle.

### Create a generic Core global person registry solely for Vitrine

Rejected because Core does not currently own institution-wide identity and Vitrine can satisfy its foundation with a local subject layer.

### Reuse Portia Actor identity for roster students

Rejected because Portia explicitly keeps roster students as roster-qualified references and reserves Actor records for recurring non-roster people.

### Rewrite association endpoints in place

Rejected because it destroys historical meaning and makes issued or audited records impossible to interpret reliably.

### Delete duplicate subjects during merge

Rejected because deletion loses provenance and can corrupt historical Portfolio and snapshot references.

### Reassign existing Portfolios directly during merge or split

Rejected because hidden foreign-key rewrites would change historical identity. Continued work uses explicit successor Portfolios.

### Allow unrestricted many-subject Portfolios in v0.1.0

Rejected because group, cohort, and multi-subject portfolios require separate authority, privacy, authorship, and snapshot semantics.

## Validation requirements

Later serialized contracts and implementation must verify:

- one active binding per Portfolio;
- exact school-year, class, and student reference validation;
- leading-zero preservation;
- no bare-ID or name-based identity;
- proposal/confirmation separation;
- attributable confirmation;
- no duplicate active roster reference across subjects;
- immutable endpoints;
- legal lifecycle transitions;
- explicit nondestructive correction;
- acyclic subject transitions;
- derived-index nonauthority;
- and no upstream Core mutation.

## Required follow-up

- Define final serialized identity schemas and persistence behavior.
- Define local actor references and authorization integration.
- Define candidate discovery using confirmed associations.
- Define selection records that preserve the relied-upon subject relationship.
- Define snapshot identity capture and identity-correction findings.
- Define cross-workspace migration only when a concrete use case exists.
- Revisit a shared Core workspace-module path only if multiple modules require it.

## References

- [Portfolio Subject identity design](../design/portfolio-subject-identity.md)
- [Representative identity examples](../examples/portfolio-subject-identity-examples.md)
- [Vitrine module boundaries](../architecture/module-boundaries.md)
- [ADR 0001: Vitrine Module Boundaries and Authority](0001-vitrine-module-boundaries-and-authority.md)
- [Core roster and workspace contract](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/docs/roster_workspace_contract.md)
- [Portia shared identity and cross-class model](https://github.com/Paper-Data-Suite/pds-portia/blob/8cd4b1f2ca80cc240693184c87e5df463ba375cf/README.md)
- [Concord ADR 0005: Separate Artifact Authors and Subjects](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0005-separate-artifact-authors-and-subjects.md)
