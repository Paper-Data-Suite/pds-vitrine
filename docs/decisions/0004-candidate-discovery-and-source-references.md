# ADR 0004: Candidate Discovery and Source References

- **Status:** Proposed
- **Date:** 2026-08-05
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #6, “Define candidate and source-reference contracts”

## Context

Vitrine must discover potentially useful student work without taking ownership of Core registry records or producer-native records.

Core v0.6 provides:

- a disposable publication catalog for bounded discovery;
- canonical Academic Work Registration revisions;
- canonical immutable Publication Records and Withdrawals;
- explicit publication-series identity and predecessor links;
- safe manifest paths;
- exact SHA-256 binding;
- and metadata-only producer compatibility Profiles.

Producer modules remain authoritative for:

- native work and record identity;
- manifests;
- source-record contracts;
- educational semantics;
- artifact relationships;
- attempts;
- revisions;
- scales;
- privacy projections;
- and public readers.

Vitrine additionally needs to determine, under one exact Portfolio, Portfolio Subject, and Portfolio Profile revision:

- whether the actor may inspect a source;
- whether the source relates to the Portfolio Subject;
- whether one producer representation is permitted;
- whether it may be considered for one section or requirement;
- and which later reviews remain necessary.

Those concerns do not belong in Core and are not equivalent to Meridian’s grading-evidence inventory.

The architecture must prevent a derived catalog hit from becoming a trusted Candidate without canonical and producer verification.

## Decision

Vitrine will use a staged, layered candidate architecture with separate records for:

1. Publication Discovery Runs;
2. Publication Discovery Findings;
3. exact Core Publication Source References;
4. exact registration and series-state observations;
5. Manifest Verification Observations;
6. producer compatibility and Vitrine adapter support;
7. Producer Reader Observations;
8. Producer Source References;
9. Source Artifact and Representation References;
10. typed Native Attempt, Standard, and Portfolio Subject relationship references;
11. multidimensional privacy and availability metadata;
12. immutable Candidate Evaluations;
13. positive Portfolio Candidates;
14. and explicit Candidate Current Pointers.

The required trust sequence is:

```text
bounded catalog discovery
  -> canonical Core reload
  -> registration and series verification
  -> compatibility
  -> exact Vitrine adapter selection
  -> authorization
  -> manifest verification
  -> producer-owned public reader
  -> source projection
  -> subject relationship
  -> Profile eligibility
  -> positive Candidate
```

A failure at any stage is recorded at that stage.

A negative or unresolved result is a Candidate Evaluation, not a malformed positive Candidate.

## Decision details

### Discovery Findings and Candidates are distinct

A catalog row can create only a Publication Discovery Finding.

The row is nonauthoritative and may be:

- stale;
- missing;
- inconsistent with canonical state;
- or unavailable because the catalog itself is missing or corrupt.

A positive Candidate requires canonical and producer verification.

### Candidate Evaluation and positive Candidate are distinct

A Candidate Evaluation records the full pipeline, including:

- ineligible;
- unresolved;
- suppressed;
- and positive outcomes.

A Portfolio Candidate exists only for an eligible or permitted conditional source representation.

This separation prevents invalid placeholder Candidates from being stored merely to preserve diagnostics.

### Exact Core Publication reference

Vitrine preserves every canonical Publication Record field relevant to provenance:

```text
schema version
publication_id
ModuleWorkRef
optional source_record
publication_kind
capabilities
record_set_id
record_set_revision
manifest_contract_version
manifest_path
manifest digest algorithm and digest
published_at
registration revision
predecessor publication ID
```

For academic publications, Vitrine also preserves the exact referenced Academic Work Registration revision and relevant immutable metadata.

Intervention publications have no fabricated registration.

### Publication lifecycle is an observation

Vitrine records explicit canonical states such as:

- current selectable head;
- current withdrawn head;
- historical predecessor;
- superseded;
- withdrawn;
- conflict;
- and cycle.

It never selects “current” using greatest revision, newest timestamp, filename, or identifier ordering.

### Authorization precedes parsing

Vitrine may use privacy-minimized Core envelope metadata to request authorization.

It must not open and parse a student-level manifest before authorization for the requested source, subject scope, operation, and purpose.

### Manifest verification precedes producer parsing

Vitrine verifies:

- exact path;
- work-root containment;
- regular nonsymlink status;
- digest algorithm;
- and exact digest bytes

before invoking a producer reader.

A digest mismatch blocks parsing and Candidate creation.

### Core producer Profiles remain metadata-only

A Core `PublicationProducerProfile` identifies compatibility.

It does not contain a parser callback and does not become a Vitrine adapter registry.

### Vitrine adapters are consumer-side

A Vitrine adapter declares exact support for:

- producer module;
- publication kind;
- manifest contract version;
- producer contract version where applicable;
- source-record contract where relevant;
- and required capabilities where relevant.

The adapter invokes a producer-owned public reader and projects validated public models into Vitrine references.

Unknown versions have no fallback.

### Source-reference layering

The model separates:

```text
Core Publication Source Reference
Producer Source Reference
Source Artifact Reference
Source Representation Reference
Native Attempt Reference
Candidate Standard Reference
Portfolio Subject Relationship Assertion
```

This avoids flattening all producer output into one generic source or score.

### One Candidate identifies one representation

One Candidate is scoped to:

```text
Portfolio
+ Portfolio Subject
+ exact Profile binding/revision
+ exact verified publication
+ exact producer source
+ exact representation
+ authorized purpose context
```

An original file and rendered feedback are separate Candidates.

### Candidate IDs are Vitrine identities

Candidate IDs are opaque, stable, never reused, and do not encode PII or source semantics.

Exact source endpoints define Candidate meaning but do not have to be embedded in the ID.

### Current Evaluation is explicit

Successive Evaluations for the same Candidate are linked explicitly.

A Candidate Current Pointer identifies the Evaluation governing current working use.

Currency is not inferred from timestamps or greatest revisions.

### Source changes create new Candidates

A new publication, producer source item, representation, attempt endpoint, Portfolio, Portfolio Subject, or Profile binding creates a new Candidate.

An old Candidate is not retargeted in place.

### Subject relationships are typed

The relationship between a source and the Portfolio Subject is explicit and attributable.

The model preserves producer distinctions such as:

- attempt subject;
- submission subject;
- Artifact Author;
- Artifact Subject;
- Group Member;
- documented contributor;
- individual Score target;
- Group Score target;
- Event Participant;
- and report subject.

No relationship is inferred from another unless the producer contract defines that implication.

### Attempt status remains producer-owned

Vitrine preserves exact attempt identity and producer-native origin.

It does not automatically create:

- official;
- best;
- latest for grading;
- replacement;
- or Grade-bearing status.

### Standards references preserve relationship kind

The Candidate model preserves whether a standard is:

- a focus;
- an alignment;
- governing;
- or contextual.

A standard reference is not a proficiency result.

### Privacy is multidimensional

Privacy metadata includes sensitivity, multi-subject scope, metadata visibility, minimum-necessary treatment, rights review, and redaction review.

It is not one Boolean.

### Availability is multidimensional

Availability separately records:

- catalog;
- canonical publication;
- registration;
- series;
- compatibility;
- adapter;
- reader;
- manifest;
- producer parse;
- source;
- artifact;
- authorization;
- subject relationship;
- Profile eligibility;
- and disclosure review.

A derived summary may be displayed but does not replace those facts.

### Portia is suppressed by default

Portia catalog matches do not become ordinary visible discovery findings.

Default suppression reveals no:

- count;
- title;
- filename;
- Candidate;
- preview;
- facet;
- or hidden-source diagnostic.

A future permitted Portia projection requires explicit Profile, authorization, minimum-necessary producer projection, and privacy review.

### Candidate state is canonical; indexes are derived

Retained Candidate Evaluations, positive Candidates, current pointers, and correction links are canonical Vitrine state.

Candidate indexes, lists, facets, thumbnails, and duplicate suggestions are derived and rebuildable.

### Duplicate handling uses exact identity and lineage

Vitrine does not deduplicate by title, filename, timestamp, or digest alone.

Producer-declared lineage and exact identities govern equivalence.

Distinct provenance remains preserved even when two records are declared equivalent.

### No blocking Core change

Core v0.6 already supplies the shared publication envelope, verification, and compatibility metadata needed for the conceptual design.

Vitrine owns Candidate policy and requires no Core global Candidate or parser callback.

A future Core enhancement may improve bounded canonical enumeration, but this ADR does not require or invent one.

## Consequences

### Positive consequences

- Catalog staleness cannot silently create source authority.
- Candidate failures remain attributable to the correct layer.
- Producer-native meaning is preserved.
- New producers can integrate without a universal manifest schema.
- Historical Candidates remain reproducible.
- Attempt and standard semantics are not prematurely normalized.
- Sensitive sources can be suppressed without metadata leakage.
- Selection and snapshot contracts receive exact source provenance.
- Current working status is explicit and auditable.
- Candidate indexes remain disposable.

### Costs

- The data model contains several explicit references and observations.
- Adapter support must be maintained per exact producer contract.
- Authorization must be available before student-level parsing.
- Candidate refresh creates additional immutable records.
- Duplicate detection cannot rely on one convenient digest.
- Producer readiness differences must remain visible.
- Some potentially useful sources remain unavailable until producers publish public readers.

### Risks

- Implementers may be tempted to collapse layered references.
- A consumer adapter could accidentally duplicate producer validation.
- Privacy-safe diagnostics require discipline.
- Candidate Current Pointer updates will need concurrency controls.
- Broad Profile rules could attempt to expose sensitive source families.
- A future UI may obscure the difference between unresolved and ineligible.

The final schemas and runtime tests must preserve the distinctions in this ADR.

## Alternatives considered

### 1. Treat a catalog row as a Candidate

Rejected.

The catalog is derived, disposable, and potentially stale.

### 2. Parse the producer manifest before authorization

Rejected.

The manifest may contain student-level educational information. Filesystem readability is not access authority.

### 3. Parse arbitrary producer JSON in Vitrine

Rejected.

Vitrine would duplicate validation, couple to private structure, and risk semantic drift.

### 4. Put producer parser callbacks into Core Profiles

Rejected.

Core Profiles are compatibility metadata. Parser callbacks would transfer producer semantics into Core and couple Core to producer runtime code.

### 5. Use one universal producer manifest schema

Rejected.

ScoreForm attempts, Quillan reviews, Concord artifacts and Scores, Portia interventions, and Meridian reports have materially different meaning.

### 6. Use filenames or titles as source identity

Rejected.

They are mutable display data and may collide.

### 7. Use manifest array position as durable identity

Rejected.

Ordering may be contract-significant but position alone is not stable item identity.

### 8. Treat the whole manifest as one student artifact automatically

Rejected.

A manifest can contain several students, attempts, artifacts, results, and internal provenance.

### 9. Flatten all producer results into a generic score

Rejected.

This would erase native scales, response states, non-score dispositions, group targets, and source relationships.

### 10. Select ScoreForm’s highest or latest attempt automatically

Rejected.

ScoreForm preserves all attempts and does not define one official or Grade-bearing attempt.

### 11. Treat standard alignment as proficiency

Rejected.

Alignment says what a source addresses, not what the student has demonstrated.

### 12. Infer Concord authorship from Group Membership

Rejected.

Concord explicitly separates membership, authorship, subject, contribution, recorder, and Score target.

### 13. Treat Portia publications as ordinary Candidates

Rejected.

Intervention data requires purpose-specific authorization, minimum-necessary projection, and no-existence-leakage defaults.

### 14. Use one privacy Boolean

Rejected.

Sensitivity, access, eligibility, disclosure, collaborators, rights, and redaction are separate dimensions.

### 15. Use one availability Boolean

Rejected.

A valid publication may have a missing artifact; a compatible source may have denied authorization; a historical source may remain valid for provenance.

### 16. Deduplicate by digest alone

Rejected.

Identical bytes can represent distinct student issuances, artifacts, or relationships.

### 17. Retarget a Candidate to a successor publication in place

Rejected.

That destroys historical source identity and makes issued provenance unstable.

### 18. Rewrite a Candidate after subject correction

Rejected.

Corrections require new records and preserved impact history.

### 19. Treat a source reference as copied bytes

Rejected.

A source may remain producer-controlled and unavailable for copying.

### 20. Store Candidate history only in a derived index

Rejected.

Indexes may be deleted or rebuilt and cannot carry authoritative curation provenance.

### 21. Use adapter fallback for unknown versions

Rejected.

Nearest-version assumptions can misparse contracts and expose unintended data.

### 22. Require producer packages to depend on Vitrine

Rejected.

The dependency direction remains consumer to producer public reader where installed; producers remain independent.

### 23. Require Core to implement Portfolio eligibility

Rejected.

Portfolio purpose, Profile requirements, Subject relationships, and candidate policy belong to Vitrine.

### 24. Use Meridian’s evidence inventory as the Vitrine Candidate model

Rejected.

Meridian’s inventory serves grading and reporting. Vitrine requires artifacts, representations, audience/privacy context, and Portfolio-specific relationships.

## Required follow-up

Issue #7 must define producer-specific exposed source and representation families.

Issue #8 must define Selection and curation records that reference exact Candidates.

Issue #9 must define copied-byte and issued-snapshot provenance.

Issue #10 must define authorization, recipient, consent, redaction, and disclosure behavior.

Later implementation work must define:

- final schemas;
- adapter registry;
- source-reference validation;
- persistence;
- Candidate Current Pointer concurrency;
- CLI or service behavior;
- and synthetic integration fixtures.

## Validation expectations

Review of later work should reject:

- catalog-as-authority behavior;
- parsing before authorization;
- Core parser callbacks;
- private producer file access;
- generic fallback readers;
- timestamp-derived currency;
- digest-only deduplication;
- flattened subject relationships;
- standard-to-proficiency inference;
- attempt auto-selection;
- Portia existence leakage;
- in-place Candidate retargeting;
- and source references that claim copied bytes.

## Related documents

- [Candidate and Source-Reference Contract](../design/candidate-source-reference-contract.md)
- [Representative Candidate and Source-Reference Examples](../examples/candidate-source-reference-examples.md)
- [Module boundaries and authority](../architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](../design/portfolio-subject-identity.md)
- [Versioned Portfolio Profile Contract](../design/portfolio-profile-contract.md)
- [ADR index](README.md)
