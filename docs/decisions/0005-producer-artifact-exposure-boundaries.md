# ADR 0005: Producer Artifact Exposure Boundaries

- **Status:** Proposed
- **Date:** 2026-08-05
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #7, “Define producer artifact exposure boundaries”

## Context

Vitrine can discover Core Publication Records and, after authorization and exact manifest verification, invoke producer-owned public readers. That capability does not determine which producer fields, native records, or files are appropriate Portfolio Candidate representations.

The current producers expose materially different domains:

- ScoreForm publishes structured academic results with every represented attempt and scan provenance;
- Quillan owns selected written evidence, teacher review, student-facing feedback exports, and private notes;
- Concord owns collaborative Artifacts, pages, authorship, subjects, Groups, Scores, moderation, and privacy;
- Portia owns sensitive behavior-support records that must not enter ordinary portfolio discovery.

Without a producer-specific projection boundary, Vitrine could incorrectly:

- treat manifests as student-facing artifacts;
- expose native producer files;
- copy raw retained scans;
- reveal private review data;
- infer individual authorship from Group Membership;
- convert Group Scores into individual results;
- or reveal the existence of sensitive Portia records.

The Candidate and source-reference architecture therefore requires a separate decision describing which exact producer-approved representations may enter candidate evaluation.

## Decision

Vitrine will recognize only exact, producer-owned, contract-versioned projections.

The architecture separates:

```text
producer manifest
producer-native record
producer-approved projection
Portfolio Candidate
Selection
copied Portfolio representation
```

A source becomes eligible for candidate evaluation only through:

```text
verified manifest
  -> producer public reader
  -> exact producer-approved projection
  -> Vitrine exposure decision
  -> Candidate Evaluation
```

Vitrine will not expose native files or arbitrary reader fields.

## Decision details

### Producers own projections

Each producer owns:

- projection kind;
- projection contract version;
- source compatibility;
- allowed fields;
- prohibited fields;
- representation identity;
- media types;
- source and projection revision behavior;
- producer privacy classification;
- and required source relationships.

Vitrine may evaluate or adapt a projection but may not broaden it.

### Manifests are normally source-only

A producer manifest supports verified interpretation and provenance.

It does not ordinarily become:

- a Candidate artifact;
- a displayed file;
- a public download;
- or a snapshot member.

An exceptional manifest-as-artifact contract would require an explicit producer decision and separate projection identity.

### Native records are not directly exposed

Vitrine will not expose:

- ScoreForm native result files;
- Quillan submissions or reviews;
- Concord native relationship or moderation records;
- Portia Events or intervention records;
- or undocumented files beneath producer work roots.

A missing projection results in an unsupported or unavailable outcome, not native-file fallback.

### Exposure disposition

The initial conceptual vocabulary is:

```text
candidate_eligible
conditional_candidate
supporting_metadata_only
source_only
prohibited
suppressed
unsupported
```

`Suppressed` prevents source-existence leakage through counts, titles, facets, previews, diagnostics, and placeholders.

### Implementation readiness

The initial readiness vocabulary is:

```text
implemented
contract_defined
planned
unavailable
retired
```

Readiness is independent of exposure policy.

### Projection Descriptor

One Producer Projection Descriptor identifies:

- exact producer and projection contract;
- compatible source manifest and record kinds;
- semantic artifact family;
- representation and media types;
- acquisition mode;
- standalone-Candidate eligibility;
- exposure disposition;
- field allowlist and critical exclusions;
- subject and source relationship requirements;
- multi-subject behavior;
- sensitivity and review requirements;
- revision behavior;
- availability semantics;
- and known limitations.

Descriptor identity is:

```text
producer_module_id
+ projection_kind
+ projection_contract_version
```

### Semantic families do not replace projection kinds

Broad families such as:

```text
original_work
feedback
result_summary
collaborative_work
reflection
growth_summary
context_summary
```

may support Portfolio Profile matching.

They do not replace exact producer-owned projection identity or native semantics.

### Acquisition modes remain explicit

The accepted conceptual modes are:

```text
structured_projection
producer_rendered_file
producer_authorized_source_file
```

Vitrine cannot convert a private native path into a producer-authorized source file.

### Field exposure is allowlist-based

Structured projections expose only declared fields.

Denylist-only exposure is rejected because new producer fields could otherwise become visible accidentally.

Operational and sensitive fields are excluded unless an explicit producer projection safely permits a minimum-necessary subset.

### Exposure does not authorize later actions

Projection exposure does not establish:

- source-access authorization;
- Profile eligibility;
- Selection;
- audience permission;
- consent;
- redaction completion;
- copied bytes;
- or snapshot issuance.

Those remain separate records and decisions.

### Raw retained scans are prohibited

Core retained scans are source custody and operational provenance, not ordinary Candidate representations.

A producer may later publish a sanitized rendering that:

- isolates exact subject pages;
- removes route or QR information where required;
- excludes unrelated content;
- has its own projection identity and digest;
- and is exposed through a public contract.

Vitrine must not manufacture such a rendering from retained-source paths.

### Multi-subject sources require explicit treatment

A projection must declare one of:

```text
single_subject
subject_isolated
collaborative_multi_subject
suppressed_multi_subject
```

Vitrine will not perform ad hoc redaction of native producer data to create an individual projection.

## Producer decisions

### ScoreForm

- Academic Result Manifest v1 is `source_only`.
- Each exact attempt may support a separate conditional attempt-summary projection.
- A restricted question-evidence summary may be permitted by an exact Profile and projection contract.
- Attempts remain separate; Vitrine selects no highest, latest, official, or Grade-bearing attempt automatically.
- Question alignments remain alignments, not proficiency.
- Answer keys, detector internals, scan-review details, private paths, and raw retained scans are prohibited.
- A completed answer-sheet Candidate requires a future sanitized ScoreForm rendering.

### Quillan

- Original-work projection uses producer-selected evidence only.
- Candidate, duplicate, replacement-only, and excluded evidence do not enter the ordinary original-work projection.
- PDF and Markdown feedback are appropriate conceptual Candidate representations after Core-compatible publication and public-reader support exists.
- Structured feedback follows the same student-facing allowlist.
- `submission.json` and `review.json` remain source-only.
- Private notes are prohibited without existence leakage.
- Class reports are not individual student artifacts.
- Raw retained scans and retained-source paths are prohibited.

### Concord

- Artifact projection is conditional on exact Artifact status, pages, relationships, and privacy.
- Artifact category and page kind affect exposure treatment.
- Group Membership is not authorship.
- Proposed, disputed, unknown, or superseded attribution is not confirmed individual authorship.
- Representation status remains explicit.
- Group Artifacts normally require collaborator and multi-subject review.
- Group Scores remain Group-targeted.
- Score summaries preserve exact Criterion, scale, target, disposition, moderation, and provenance without becoming Grade or universal proficiency.
- Raw Review and Moderation records remain source-only.
- Raw retained scans and route records are prohibited.

### Portia

- All ordinary Portia sources are suppressed.
- Ordinary discovery reveals no title, count, preview, filename, facet, diagnostic, or hidden-result indicator.
- Events, Accounts, Observations, Determinations, interventions, Communications, Outcomes, and complete manifests are not direct Candidates.
- A future portfolio-safe projection must be Portia-owned, explicit, opt-in, purpose-specific, student-reviewable, minimum-necessary, and separately permissioned.
- Safe projections may eventually cover student-selected reflection, documented strength, self-selected goal progress, successful replacement skill, self-advocacy, voluntary restorative artifact, or teacher-approved growth statement.
- Safe projections must exclude allegations, determinations, incident history, counts, tiers, disability, counseling, safety, family, demographic, and unrelated participant information.
- Linked Quillan or Concord artifacts retain their originating ownership and exposure rules.

## Revision and historical behavior

Projection references are exact and immutable in Candidate history.

A material projection change creates:

- a new projection contract or revision;
- a new Candidate Evaluation;
- and a new Candidate when the representation changes.

Vitrine will not silently refresh a Candidate or Selection.

Historical snapshots retain the exact projection used at issuance.

## Digest behavior

The architecture distinguishes:

```text
manifest digest
source-artifact digest
producer-rendered projection digest
Vitrine copied-representation digest
```

No digest is reused as proof of different bytes.

## Core impact

No blocking Core change is required.

Core compatibility and capability metadata remain useful for discovery and routing, but they do not become portfolio-exposure policy.

A future shared representation-capability vocabulary may be considered separately if several consumers need it. Any such Core vocabulary must remain metadata-only and must not authorize exposure.

## Consequences

### Positive

- Producer authority is preserved.
- New producer fields do not leak automatically.
- Manifests remain machine-readable interpretation sources.
- Original work and feedback remain distinct.
- Raw scan custody remains separate from portfolio presentation.
- Group and individual relationships remain honest.
- Portia suppression is enforceable without existence leakage.
- Profile matching can use broad families without flattening exact producer meaning.
- Historical Candidate and snapshot provenance remain reproducible.

### Costs

- Producers must define additional projection contracts before Vitrine can expose many useful representations.
- Vitrine requires producer-specific adapters and readiness handling.
- Some valid sources will produce no Candidate.
- Collaborator, rights, privacy, and sanitization reviews remain additional workflow obligations.
- Historical projection contracts and readers may need long-term support.

### Risks

- Projection catalogs may drift from producer contracts.
- Broad semantic families may be mistaken for exact contracts.
- Implementers may incorrectly treat `planned` as available.
- Sanitized renderings may accidentally omit necessary provenance or retain route data.
- Suppressed sources may leak through diagnostics if failure handling is careless.

These risks require exact versioning, allowlists, privacy-safe diagnostics, and adversarial tests in later implementation work.

## Rejected alternatives

### Treat every manifest as a Portfolio artifact

Rejected because manifests contain machine-oriented source data and may include sensitive or operational provenance.

### Expose every public-reader field

Rejected because reader validity does not establish portfolio suitability.

### Read native files when no projection exists

Rejected because it bypasses producer authority, privacy boundaries, and contract versioning.

### Use one universal producer artifact schema

Rejected because ScoreForm attempts, Quillan work and feedback, Concord collaborative Artifacts and Scores, and Portia safe projections have materially different semantics.

### Use one generic `file` projection

Rejected because source identity, representation meaning, relationships, privacy, and revision would be lost.

### Treat source files and rendered representations as identical

Rejected because they have different contracts, bytes, digests, and audiences.

### Treat raw retained scans as Candidates

Rejected because retained scans are operational source custody and may contain unrelated or sensitive data.

### Copy Core retained scans directly into Vitrine

Rejected because Vitrine must use a producer-approved isolated or sanitized representation.

### Treat supporting metadata as standalone work

Rejected because context labels and scale definitions are not student artifacts by themselves.

### Treat the ScoreForm manifest as one student artifact

Rejected because it contains several students and attempts and is not a student-facing rendering.

### Select ScoreForm’s highest or latest attempt

Rejected because ScoreForm does not establish that policy and Vitrine curation is separate from Meridian grading policy.

### Expose ScoreForm answer keys or detector data

Rejected because they are unnecessary, sensitive, or operational.

### Treat ScoreForm alignment as proficiency

Rejected because alignment is not a rating or cumulative judgment.

### Expose Quillan `review.json`

Rejected because the canonical review contains internal and potentially private material beyond the student-facing projection.

### Expose Quillan private notes

Rejected categorically, including existence leakage.

### Expose Quillan candidate, duplicate, or excluded evidence

Rejected because the producer-selected evidence state defines the approved original-work basis.

### Treat Quillan class reports as individual artifacts

Rejected because they contain aggregate or other-student context.

### Infer Concord authorship from Group Membership

Rejected because membership, authorship, contribution, representation, and Score targeting are separate records.

### Treat Group Score as individual Score

Rejected because target identity is producer authority.

### Flatten Concord representation status

Rejected because recorder summary, majority position, unanimous position, multiple positions, and no consensus have different meanings.

### Expose raw Concord Review or Moderation records

Rejected because those are canonical internal workflow records, not approved student-facing projections.

### Treat Portia records as ordinary Candidates

Rejected because behavior-support records require a much stronger purpose, permission, and minimum-necessary boundary.

### Reveal suppressed Portia result counts

Rejected because the existence of a sensitive record may itself be protected information.

### Allow a generic `allow_portia` switch

Rejected because exposure must name one exact safe projection and purpose.

### Copy the complete Portia record graph into a safe projection

Rejected because a safe projection must be bounded and independently reviewable.

### Treat exposure as authorization

Rejected because source access and audience disclosure remain separate institutional decisions.

### Treat exposure as Selection

Rejected because candidacy and curation are separate Vitrine records.

### Treat exposure as copied bytes

Rejected because copying and checksums belong to snapshot contracts.

### Infer current projection from timestamps

Rejected because current authority requires explicit producer revision or succession.

### Reuse manifest digest as copied-artifact digest

Rejected because the digests bind different byte sets.

## Required invariants

1. Producers own exact projection contracts.
2. Manifests are source-only unless an explicit exceptional projection says otherwise.
3. Native records are not directly exposed.
4. Missing projections never trigger native-file fallback.
5. Field exposure is allowlist-based.
6. Exposure disposition and readiness remain separate.
7. Projection identity is exact and versioned.
8. Broad families never replace exact projection identity.
9. Supporting metadata cannot stand alone as a Candidate.
10. Exposure does not grant access, Selection, disclosure, or copied-byte status.
11. Raw retained scans are prohibited.
12. Multi-subject sources require explicit producer treatment.
13. ScoreForm attempts remain separate and unranked by Vitrine.
14. ScoreForm alignment is not proficiency.
15. Quillan original work uses selected evidence only.
16. Quillan private notes never enter exposure.
17. Concord membership is not authorship.
18. Concord Group Scores remain Group-targeted.
19. Portia is suppressed by default without existence leakage.
20. Historical Candidates and snapshots retain exact projection provenance.
21. Digest layers remain distinct.
22. No sibling repository is modified by this decision.

## Follow-up

- Issue #8 defines Selection and curation records.
- Issue #9 defines representation copying, checksums, and snapshots.
- Issue #10 defines authorization, redaction, collaborator treatment, and audiences.
- Issue #11 instantiates regulated Profile requirements.
- Producer repositories must define and implement their accepted public projection contracts before runtime exposure.

## Related documents

- [Producer artifact exposure design](../design/producer-artifact-exposure-boundaries.md)
- [Representative producer exposure examples](../examples/producer-artifact-exposure-examples.md)
- [Candidate and source-reference design](../design/candidate-source-reference-contract.md)
- [ADR 0004: Candidate Discovery and Source References](0004-candidate-discovery-and-source-references.md)
- [Module boundaries and authority](../architecture/module-boundaries.md)
