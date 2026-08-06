# ADR 0007: Snapshot, Export, Checksum, and Immutability

- **Status:** Proposed
- **Date:** 2026-08-05
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #9, “Define snapshot, export, checksum, and immutability contracts”
- **Related design:** [`../design/snapshot-export-immutability-contracts.md`](../design/snapshot-export-immutability-contracts.md)
- **Related examples:** [`../examples/snapshot-export-examples.md`](../examples/snapshot-export-examples.md)

## Context

Vitrine now has conceptual contracts for:

- Portfolio and Portfolio Subject identity;
- immutable versioned Portfolio Profiles;
- Candidate discovery and exact source references;
- producer-approved artifact exposure;
- Selection, Placement, ordering, Presentation, Annotation, and Reflection;
- exact-revision curation approval;
- and immutable byte-free Working Portfolio Composition Revisions.

Those contracts establish the exact curation state that should become a snapshot, but not:

- how producer representations are acquired;
- which bytes Vitrine copies or generates;
- how unavailable content is represented;
- how Entry and package checksums differ;
- how a logical Edition differs from a ZIP, PDF, or HTML export;
- when a build becomes immutable;
- how issuance differs from submission;
- or how a successor snapshot affects an already issued Edition.

The surrounding suite has also advanced:

- Core implements immutable publication envelopes, exact producer-manifest SHA-256 binding, explicit current pointers, supersession, and withdrawal;
- ScoreForm implements exact-byte immutable manifest generation, replay, source stability checks, exclusive creation, and post-durability partial success;
- Concord implements immutable canonical record revisions, complete work snapshots, optimistic concurrency, guarded publication, and derived catalogs;
- Portia has accepted append-only lifecycle, correction, migration, integrity-finding, and exceptional-removal contracts;
- Quillan already preserves immutable Artifact and issuance identity within its producer workflow;
- and Meridian plans frozen report snapshots distinct from refreshable report views.

Vitrine needs to reuse these patterns without confusing any producer-owned snapshot, manifest, or issuance concept with Vitrine's own Portfolio Snapshot identity.

A mutable directory of copied files would be insufficient because it could not reliably explain:

- which exact Composition was used;
- which source revision each file came from;
- whether bytes were copied or rendered;
- which expected items were omitted;
- which renderer and policy produced generated documents;
- which exact bytes were issued or submitted;
- whether a later source update changed the package;
- or whether a later Edition superseded rather than overwrote the original.

## Decision

Vitrine will use separate, immutable, append-preserving records for:

1. Snapshot Build Requests;
2. immutable Snapshot Build Plans;
3. append-preserving Snapshot Build Attempts;
4. stable Snapshot Series;
5. immutable Snapshot Editions;
6. Snapshot Entries;
7. Materialization Records;
8. explicit Snapshot Omissions;
9. canonical internal Snapshot Manifests;
10. Snapshot Seals;
11. format-specific Snapshot Export Artifacts;
12. Snapshot Issuances;
13. Snapshot Submissions;
14. append-preserving lifecycle events;
15. explicit guarded Snapshot Current Pointers;
16. and a narrow Exceptional Removal Certificate boundary.

The governing sequence is:

```text
exact Working Portfolio Composition Revision
  -> Build Request
  -> immutable Build Plan
  -> Build Attempt in staging
  -> Entries / Omissions / Materialization Records
  -> canonical Snapshot Manifest
  -> final verification and Snapshot Seal
  -> immutable Snapshot Edition
  -> one or more Export Artifacts
  -> optional Issuance
  -> optional Submission
  -> optional external Receipt / Outcome reference
```

No stage is implied by the preceding stage.

## Decision details

### One exact Composition Revision is the sole curation input

Every Build Request and Plan binds one exact Working Portfolio Composition Revision.

The builder must not build from a mutable current view or repeatedly dereference the Composition Current Pointer.

If the working Portfolio changes during construction, the existing Plan remains bound to the original Composition.

A new Composition requires a new Request or successor Plan and ultimately a new Snapshot Edition.

### Build Request, Plan, Attempt, and Edition are separate

A Request records actor intent.

A Plan freezes exact source endpoints, renderers, expected output, and omission policy.

An Attempt records one execution, including failures that create no Edition.

An Edition exists only after durable final verification and sealing.

This separation permits safe retry, conflict reporting, audit, and recovery without representing partial staging output as an issued snapshot.

### Snapshot Series and Edition provide business identity

A Snapshot Series identifies a logical stream for one Portfolio, Subject, purpose, and audience-content policy.

A Snapshot Edition is identified by:

```text
snapshot_series_id + snapshot_edition
```

Edition identity is not a content hash.

Two Editions may have identical bytes while representing separate approvals, reissuance, migration, or historical events.

### Logical Edition and Export Artifact are separate

A Snapshot Edition is the logical content and omission inventory.

An Export Artifact is one format-specific immutable realization, such as:

```text
directory_package
zip_archive
pdf_bundle
html_package
```

One Edition may have several Export Artifacts when their substantive logical content is the same.

Different audience-visible content requires a different Edition, not merely another Export Artifact.

### Every logical item receives an explicit disposition

Every Entry planned from the Composition receives one terminal outcome:

```text
included
reference_only
omitted_permitted
failed_blocking
```

A sealed Edition represents included, reference-only, and policy-permitted omitted items through exact canonical records.

A required item that cannot be included and is not covered by an exact permitted-omission rule blocks sealing.

Silent absence is rejected.

### Snapshot Entries preserve exact source and output provenance

A producer-source Entry binds exact:

- Selection and Placement where relevant;
- Candidate and Candidate Evaluation;
- Core Publication and producer manifest provenance;
- producer projection kind, contract, and revision;
- source Artifact and representation identity;
- source digest claim where available;
- Materialization Record;
- normalized output path;
- media type;
- byte size;
- and copied or generated output digest.

A generated Entry binds exact structured inputs, renderer, template, configuration, transformation policy, and output digest.

### Materialization is explicit

The initial materialization kinds are:

```text
exact_byte_copy
producer_render
vitrine_render
authorized_transformation
prior_snapshot_copy
```

Vitrine never treats the presence of a source path as sufficient provenance.

Every byte-bearing Entry has one exact Materialization Record.

### Prior-snapshot reuse is explicit

Prior Snapshot Entry bytes may be carried forward only where the exact Profile and audience-content policy permit it.

The Plan names the exact prior Entry, and the Materialization Record states `prior_snapshot_copy`.

The new Edition preserves the original producer provenance and does not claim fresh source verification.

Silent cache fallback is rejected.

### Source successors never silently replace planned sources

A Build Plan never automatically follows:

- a Candidate Current Pointer;
- a successor Candidate;
- a newer Core Publication;
- a later ScoreForm attempt;
- a newer Quillan feedback revision;
- a corrected Concord Artifact;
- a revised Portia safe projection;
- or a current producer work snapshot.

Source change causes conflict, a successor Plan, a policy-permitted Omission, or explicit prior-snapshot reuse.

### Source copying uses guarded exact-byte acquisition

An eventual implementation must:

- resolve the exact producer-approved representation;
- reject absolute paths, containment escape, URLs where local files are required, symlinks, junctions, and nonregular files;
- open and read exact binary bytes;
- independently hash acquired bytes;
- verify producer digest claims where available;
- write to exclusive staging output;
- reload and independently hash staged bytes;
- verify source stability under the source contract;
- and fail closed on concurrent mutation.

Filesystem metadata equality alone is insufficient.

### Structured projections require explicit rendering

A structured producer projection is not a file merely because it can be serialized.

Snapshot bytes require an exact renderer contract and provenance for:

- canonical input identity or digest;
- renderer and version;
- template and configuration digests;
- transformation policy;
- language;
- output media type;
- byte size;
- and output digest.

### Internal Snapshot Manifest is canonical

Each Edition has one deterministic internal Snapshot Manifest containing the exact:

- Portfolio, Subject, Profile Binding, and Composition Revision;
- audience-content policy;
- ordered Entry inventory;
- internal Omission inventory;
- generated-index references;
- builder contract;
- path policy;
- and digest policy.

The manifest uses deterministic canonical serialization.

It does not contain its own digest field.

### Snapshot Seal binds exact canonical bytes

After complete staging verification, a Snapshot Seal binds:

- exact manifest digest;
- optional logical inventory digest;
- Entry and Omission counts;
- builder identity;
- verification result;
- sealed time;
- and any post-seal durability warnings.

The initial required digest algorithm is lowercase SHA-256.

The Seal never reuses a producer manifest digest.

### Digest layers remain semantically distinct

The architecture preserves separate claims for:

1. Core producer-manifest digest;
2. producer source-artifact digest;
3. acquired-source digest;
4. copied Snapshot Entry digest;
5. generated-entry digest;
6. Snapshot Manifest digest;
7. logical inventory digest where used;
8. Export Artifact digest;
9. and imported external receipt or decision digest.

Equal values do not merge their authority or meaning.

A checksum is not a signature, authorization decision, encryption mechanism, or proof of lawful disclosure.

### Audience-safe indexes are ordinary generated Entries

Cover pages, tables of contents, artifact indexes, provenance appendices, accessibility guides, omission notices, and submission checklists are byte-bearing generated Entries.

They have renderer provenance and output digests.

They do not replace the canonical internal manifest.

The internal manifest is not automatically included in an audience package because it may contain restricted IDs and provenance.

### Audience policy and authorization remain separate

A versioned audience-content policy determines what the package would contain for a class of use.

It does not prove that a requester or recipient is authorized.

Issue #10 remains responsible for actor authentication, recipient scope, consent, collaborator treatment, redaction approval, disclosure authorization, and delivery logging.

### Content differences create new Editions

A new Edition is required when any audience-visible content changes, including:

- included or omitted items;
- copied bytes;
- captions, titles, Annotations, or Reflections;
- provenance detail;
- collaborator names;
- redaction;
- accessibility transformations;
- language;
- or omission notices.

A container-only change may create another Export Artifact of the same Edition.

### Sealing uses staging and exclusive publication

Builds occur in noncanonical staging storage.

Before sealing, Vitrine reloads and validates every Entry, Materialization Record, Omission, path, size, digest, manifest reference, and Composition binding.

The final Edition target is created exclusively and published atomically or through an equivalently guarded commit protocol.

Existing sealed paths are never overwritten or merged.

### Current Edition is explicit

A guarded Snapshot Current Pointer identifies the Edition recommended for current use within one Series.

The current Edition is never inferred from:

- largest Edition number;
- newest seal time;
- latest Issuance;
- latest Submission;
- filename;
- or directory order.

Pointer updates use expected-predecessor protection and fail closed on concurrency conflicts.

### Sealing and pointer publication are separate

A newly sealed Edition may exist without becoming current when:

- pointer update fails;
- review requires explicit promotion;
- the Edition is a historical reconstruction;
- or the Series permits several concurrently valid Editions.

Pointer failure does not invalidate or delete the Edition.

### Partial success after durability preserves the Edition

When durable sealing succeeds but a later operation fails, Vitrine preserves the Edition and reports structured partial success.

Examples include failure to:

- clear a lock;
- remove staging;
- update the current pointer;
- rebuild a derived catalog;
- produce an optional Export Artifact;
- or generate an optional preview.

No post-seal cleanup failure may trigger deletion or rewriting of the Edition.

### Uncertain durability fails conservatively

When the implementation cannot determine whether an Edition target became durable, it must:

- not reuse the Edition number;
- not declare success;
- preserve or quarantine the uncertain target;
- and require explicit recovery.

### Export Artifacts have independent integrity

Each Export Artifact binds:

- exact Edition;
- exact included Entry set;
- export format and contract;
- packager or renderer identity;
- configuration and template digest;
- generation time;
- size;
- artifact digest or directory-inventory digest;
- and validation result.

A ZIP digest authenticates the exact ZIP bytes, not the logical Edition identity.

### Issuance and Submission are separate immutable events

Issuance records that exact Export Artifacts were designated for a purpose and audience-policy context under an authorization reference.

Submission records handoff to an external destination or process.

Neither event mutates the Edition or artifact.

The following remain separate:

```text
build time
seal time
export generation time
issuance time
submission time
external receipt time
external decision time
```

### Submission does not establish receipt or acceptance

Successful local upload or handoff does not prove:

- destination receipt;
- processing;
- review;
- or external approval.

External receipt and decision records remain separate and preserve the external authority's native vocabulary.

### Lifecycle is append-preserving

The initial Snapshot lifecycle vocabulary is:

```text
sealed
superseded
withdrawn
invalidated
revoked_for_future_use
exceptionally_removed
```

Lifecycle events never rewrite the Edition.

Supersession preserves predecessor history. Withdrawal may have no replacement. Invalidation records a material defect. Revocation restricts future reliance without claiming external recall.

### Exceptional removal is narrow and authorization-bearing

Ordinary workflow never hard-deletes sealed Editions.

A future Exceptional Removal Certificate may support local removal where retaining substantive bytes is prohibited.

It preserves only minimum lawful evidence:

- Edition identity;
- manifest digest;
- affected local storage scope;
- authorizing authority;
- reason class;
- operator;
- time;
- and verification result.

It must not retain prohibited substantive payload, and it must state that external copies are not claimed removed.

### Canonical records and derived views remain distinct

Canonical state includes Requests, Plans, Attempts, Series, Editions, Entries, Materialization Records, Omissions, Manifests, Seals, Export Artifacts, Issuances, Submissions, lifecycle events, current pointers, and removal certificates.

Search indexes, dashboards, previews, thumbnails, export caches, and submission queues are derived and rebuildable.

A derived catalog cannot be required to reconstruct an Edition.

## Producer-specific decisions

### ScoreForm

- Academic Result Manifests remain source provenance rather than default Portfolio Entries.
- Only exact producer-approved attempt-summary, question-evidence, or sanitized-sheet projections may be materialized.
- Attempts remain independently selected; Vitrine never chooses the grading attempt.
- Raw retained scans, `results.csv`, answer keys, detector data, and scan-review records remain prohibited.
- ScoreForm manifest digest and Snapshot Entry digest remain distinct.
- Exact replay, source stability, exclusive immutable creation, and post-durability partial success are reusable patterns.

### Quillan

- Only exact public selected-work and student-facing feedback projections may be copied.
- Original work and feedback remain separate Entries.
- Quillan Artifact, issuance, evidence, and feedback revision provenance is preserved.
- Native submissions, reviews, private notes, unselected evidence, and retained scans remain inaccessible.
- Until public Core 0.6 projections exist, operational Vitrine copying is unavailable rather than implemented through private-file fallback.

### Concord

- Concord canonical Work Snapshots are producer storage records, not Vitrine Snapshot Editions.
- Vitrine copies only exact public Artifact or Score-summary projections when implemented.
- The complete Concord graph is never copied as a Portfolio Entry.
- Artifact, Page, Author, Subject, Group, representation, Score target, native scale, and correction provenance remain distinct.
- Concord guarded persistence, complete snapshot chain, optimistic concurrency, and derived catalogs are reusable implementation patterns.

### Portia

- Only exact Portia-owned portfolio-safe projections may create Snapshot bytes.
- Underlying Events, Accounts, Determinations, interventions, Communications, and other sensitive graphs remain prohibited.
- Suppressed source existence must not leak through internal content distributed to audiences, filenames, counts, or omission wording.
- Source correction, migration, revocation, and safe-projection replacement never rewrite issued Vitrine Editions.
- Portia append-only lifecycle, exact references, integrity findings, and exceptional-removal model are reusable patterns.

### Meridian

- Meridian report snapshots remain Meridian-owned canonical report objects.
- A future public report projection may be copied as an exact source Entry.
- Vitrine preserves Meridian report snapshot and policy provenance without importing private grading state.
- Similar snapshot vocabulary does not imply shared IDs, pointers, or lifecycle.

## Consequences

### Positive consequences

- Issued Portfolio history can be reproduced and audited without consulting mutable current state.
- Exact source, renderer, and output provenance survives producer evolution.
- One logical Edition can support several formats without equating snapshot identity to one ZIP or PDF.
- Every absent item is explainable without leaking suppressed sources.
- Byte integrity can be validated at Entry, manifest, inventory, and export levels.
- Concurrency and partial-success behavior are explicit.
- Later privacy, regulated submission, and archival work can reuse stable generic records.
- Producer modules retain authority over source meaning and lifecycle.

### Costs and complexity

- More record types are required than a mutable export directory.
- Every generated document requires provenance and digesting.
- Builds must stage and verify all outputs before sealing.
- Audience-content changes require separate Editions.
- Export containers require their own validation and integrity records.
- Exceptional removal and external submission require careful institutional integration.
- Bit-reproducible rendering may be difficult and cannot be claimed casually.

### Risks

- A future implementation may expose restricted internal provenance unless audience manifests are separated rigorously.
- Overly broad omission notices may leak suppressed sources.
- Renderer nondeterminism may complicate replay and reproduction.
- Large media snapshots may require transaction and storage limits not yet defined.
- Institutions may incorrectly treat checksums as signatures or export success as submission acceptance.

These risks require explicit validation and user-facing terminology rather than weakening immutability.

## Alternatives considered and rejected

### 1. Use a mutable snapshot directory

Rejected because source refresh, manual edits, and partial copies could change issued history without a new identity.

### 2. Build from live current state

Rejected because a long build could combine several Composition, Candidate, or producer revisions.

### 3. Silently refresh from producer sources

Rejected because an Edition must represent the exact source state selected and approved, not whatever is current later.

### 4. Follow source successors automatically

Rejected because successor Publications, Candidates, Artifacts, or projections are different source endpoints requiring new curation and planning.

### 5. Use a content hash as Snapshot Edition identity

Rejected because identity, purpose, lifecycle, audience policy, and separate historical events are not reducible to byte equality.

### 6. Keep only one package-wide checksum

Rejected because it cannot explain or independently validate individual files, generated outputs, or omissions.

### 7. Reuse producer manifest digest as copied-file digest

Rejected because the producer manifest and copied Portfolio representation are different byte layers and authority claims.

### 8. Use a ZIP digest as logical Edition identity

Rejected because ZIP metadata and compression can change while logical content remains the same, and one Edition may have several formats.

### 9. Treat one PDF as the entire snapshot model

Rejected because portfolios may contain original files, accessible alternatives, HTML, media, generated indexes, and omission records not faithfully represented by one PDF.

### 10. Omit unavailable content silently

Rejected because completeness and historical accuracy require an explicit policy-based Omission or a blocking failure.

### 11. Seal partial packages without Omission records

Rejected because file absence would be indistinguishable from build failure, policy exclusion, or later deletion.

### 12. Automatically include the internal manifest in audience exports

Rejected because exact IDs, producer provenance, and restricted omission details may exceed minimum-necessary disclosure.

### 13. Treat audience labels as authorization

Rejected because a content policy does not authenticate recipients or establish consent and disclosure permission.

### 14. Use one timestamp for build, seal, issue, and submit

Rejected because each event has different authority and operational meaning.

### 15. Treat export success as delivery or external acceptance

Rejected because local package creation says nothing about external receipt, processing, review, or decision.

### 16. Overwrite a sealed Edition

Rejected because immutability and historical issuance provenance require a successor Edition.

### 17. Regenerate an existing Edition under a newer renderer

Rejected because changed renderer output creates new bytes and may change audience-visible meaning.

### 18. Select current Edition by greatest number or newest time

Rejected because current use is an explicit policy decision and may legitimately roll back.

### 19. Copy private producer files or raw retained scans

Rejected because Vitrine may use only producer-approved projections and must not bypass source privacy or evidence-selection boundaries.

### 20. Copy complete Concord or Portia record graphs

Rejected because those graphs contain producer-owned relationships and sensitive context broader than an approved Portfolio representation.

### 21. Fall back silently to cached prior bytes

Rejected because historical bytes must be an explicit `prior_snapshot_copy` with exact provenance and policy permission.

### 22. Hard-delete sealed history through ordinary workflow

Rejected because supersession, withdrawal, invalidation, and revocation require append-preserving history.

### 23. Claim external copies were recalled after local removal

Rejected because Vitrine cannot prove or control independently held copies.

### 24. Add a Core Portfolio Snapshot registry

Rejected because Portfolio Editions, curation, audience policy, and Issuance are Vitrine-owned rather than shared publication infrastructure.

## Core impact

No Core change is required.

Vitrine uses Core's existing publication and manifest-verification authority for producer sources, then owns its own Snapshot Series, Editions, Entries, Seals, Export Artifacts, Issuances, and Submissions.

A shared contract should move to Core only after multiple modules demonstrate the same authority and serialization requirement.

## Implementation constraints

Later implementation must:

- use exact opaque IDs;
- use deterministic canonical serialization;
- hash exact bytes with lowercase SHA-256 initially;
- reject path traversal, aliases, symlinks, junctions, and nonregular files;
- separate staging from sealed storage;
- create Edition targets exclusively;
- guard current-pointer updates;
- preserve post-seal partial success;
- never reuse uncertain Edition numbers;
- keep internal and audience-safe manifests separate;
- preserve every permitted Omission;
- prevent producer-private fallback;
- and maintain privacy-safe diagnostics.

## Follow-up work

- Issue #10 defines authorization, recipient scope, consent, redaction, disclosure, and delivery logging.
- Issue #11 defines concrete regulated package, signature, destination, omission, and submission requirements.
- Runtime contract work must define exact schemas, storage, transaction journals, canonical JSON, path policy, and export formats.
- Producer modules must implement their public projections and readers before operational snapshot copying.
- Future Sunset integration must define archival transfer, legal holds, retention execution, and disposition.

## Status rationale

This ADR remains **Proposed** because the repository is still in foundation design and maintainers have not explicitly accepted the decision.
