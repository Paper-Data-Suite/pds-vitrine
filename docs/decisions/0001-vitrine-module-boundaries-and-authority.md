# ADR 0001: Vitrine Module Boundaries and Authority

- **Status:** Accepted
- **Date:** 2026-08-04
- **Accepted:** 2026-08-06 — approved by issue #13 portfolio foundation audit
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` foundation architecture and all later Vitrine contracts and implementation
- **Issue:** #3, “Define module boundaries and ownership”

## Context

Vitrine is intended to discover authorized student work through Paper Data Suite Core, allow deliberate teacher or student curation, preserve exact provenance, and produce purpose-specific immutable portfolio snapshots.

The suite already assigns authority across several modules:

- Core owns shared identity, registration, publication, compatibility, and discovery infrastructure.
- Producer modules own their native records and educational semantics.
- Meridian owns grading, standards proficiency, Grade-item membership, and formal academic reporting.
- Portia owns behavior-support and intervention records.
- Concord owns collaborative Artifacts, Authors, Subjects, contributions, Review, Moderation, and Scores.
- sibling documentation identifies a future Sunset module as the owner of suite-wide archival orchestration.
- institutional and external systems retain authority over identity, consent, official submission, records administration, and final decisions.

Without an explicit boundary, Vitrine could accidentally become a competing registry, universal producer schema, gradebook, intervention dossier, archive system, or external compliance authority. It could also create false individual ownership by assigning Concord group Artifacts to every member or expose Portia material merely because an intervention publication is technically discoverable.

Foundation research established that discovery, authorization, eligibility, selection, copying, disclosure, profile satisfaction, institutional approval, external submission, and external outcome are separate decisions.

## Decision

Vitrine will be a separate portfolio domain module.

Vitrine owns portfolio-purpose aggregates, candidate findings, curation decisions, portfolio annotations and reflections, profile findings, portfolio review and approval records, copied portfolio representations, immutable snapshot inventories, portfolio issuance history, and references to external submissions and outcomes.

Vitrine does not own Core canonical records, producer-native records, grading or proficiency, intervention case management, institutional identity or authorization, suite-wide archival disposition, official external submission, or external decisions.

### 1. Source semantic authority

The module or external system that creates a canonical source record remains authoritative for its meaning, identity, revision, correction, supersession, and withdrawal.

Vitrine may reference a source, interpret it for a portfolio purpose, and copy an authorized representation. It must not rewrite the source or make the copied representation a competing canonical producer record.

### 2. Core boundary

Vitrine may use Core to discover publications and verify canonical Publication Records, Academic Work Registration references, withdrawal state, safe manifest paths, SHA-256 binding, capabilities, and producer compatibility.

Core publication does not authorize portfolio access, selection, copying, disclosure, or approval.

Vitrine must not:

- use the disposable Core catalog as canonical authority;
- mutate Core registrations, publications, or withdrawals;
- add Vitrine workflow fields to neutral Core records;
- require Core to parse producer semantics;
- or require a new Core publication kind merely to represent portfolios.

Core must not depend on Vitrine workflow code.

### 3. Producer boundary

ScoreForm, Quillan, Concord, Portia, and future producers remain authoritative for their native records and public projection contracts.

Vitrine will consume supported public readers or explicit adapters. It will not crawl producer directories, parse undocumented files, infer semantics from filenames, mutate producer records, or flatten all producer outputs into one universal result meaning.

Producers must not require Vitrine as a runtime dependency to perform their own work or publication.

### 4. ScoreForm boundary

ScoreForm remains authoritative for attempts, responses, points, response states, alignment, provenance, manifests, and producer revision history.

Vitrine may select an attempt for a portfolio narrative. It must not claim that the attempt is official, best, latest for grading, or Grade-bearing unless an authoritative grading source says so. Vitrine does not calculate proficiency or Grades from ScoreForm data.

### 5. Quillan boundary

Quillan remains authoritative for written-work submissions, evidence, teacher review, Focus Standard observations and ratings, feedback composition, private notes, review state, and Quillan exports.

Vitrine must use a privacy-safe public projection. It must not change Quillan review state, expose private notes through ordinary portfolio access, or treat a Vitrine annotation as a Quillan amendment.

### 6. Concord boundary

Concord remains authoritative for Activities, Groups, Memberships, Artifact Authors, Artifact Subjects, contribution records, Review, Moderation, Score targets, Scores, and evidence relationships.

Vitrine must preserve these distinctions:

```text
Group Member
!= Artifact Author
!= Artifact Subject
!= contributor
!= recorder
!= represented Group
!= Score target
!= portfolio subject
```

A group Artifact is not automatically owned by every member. Inclusion in an individual portfolio does not establish individual authorship, contribution, or proficiency. Every individual relationship to a group Artifact must be explicit.

### 7. Portia boundary

Portia remains authoritative for behavior-support and intervention records.

Portia material is excluded from ordinary Vitrine discovery and candidate presentation by default. Vitrine must prevent sensitive-source existence leakage through counts, titles, search facets, filenames, previews, diagnostics, or indexes.

Any future inclusion requires:

- explicit profile permission;
- explicit actor and audience authorization;
- deliberate opt-in;
- a minimum-necessary producer-approved projection;
- and preservation of Portia's contextual meaning.

Vitrine must not reinterpret Portia material as academic evidence, a Grade, or a permanent student trait.

### 8. Meridian boundary

Meridian remains authoritative for grading-evidence selection, standards proficiency, Grade-item membership, reassessment, Grade calculation, Academic Period aggregation, overrides, and formal report snapshots.

Portfolio selection is not grading selection.

Vitrine may later include an authorized Meridian report as a source artifact. It must not calculate or rewrite Meridian results, and an issued Vitrine snapshot must not silently refresh when Meridian recalculates.

Meridian must not become Vitrine's artifact manager or curation engine.

### 9. Sunset and records-management boundary

No public Sunset repository or runtime contract exists at the time of this decision.

Vitrine owns semantic portfolio lifecycle and may later produce an archive handoff descriptor. A future Sunset module or institutional records system will own suite-wide archival orchestration, storage movement, legal-hold coordination, records-schedule execution, and authorized disposition.

Vitrine must not delete upstream records, infer destruction authority from lifecycle state, or apply a universal retention period.

Archive movement must not rewrite issued snapshot bytes, checksums, provenance, or historical meaning.

### 10. External-system boundary

External institutional systems remain authoritative for official identity, institutional role, parent/guardian relationship, consent, signatures, records classification, legal hold, official transmission, receipt, regulated outcome, graduation, diploma status, and authorized disposition.

Vitrine may prepare packages and record external references. It must distinguish:

```text
prepared
locally approved
transmitted
receipt acknowledged
correction requested
resubmitted
externally accepted or rejected
outcome recorded
```

Vitrine must not claim external submission, receipt, approval, compliance, graduation, or diploma status without authoritative external evidence.

### 11. Human authority

Vitrine records actions by actors under an identified role, institution, purpose, scope, policy/profile, and time. A role label alone does not establish authority.

Authentication and full authorization mechanics remain later work, but the architecture requires authorization to be explicit and separate from discovery.

### 12. Working and issued state

Working portfolios are mutable and preserve history.

Issued Vitrine snapshots are immutable. They are authoritative for exactly what Vitrine issued at a particular time and audience. They are not authoritative for current upstream source state.

Corrections create successor editions. Access may later be restricted without rewriting historical bytes.

### 13. Dependency direction

Permitted directions are:

```text
pds-vitrine -> pds-core public contracts
pds-vitrine -> producer public reader contracts or Vitrine-owned adapters
pds-vitrine -> optional Meridian public output contracts
pds-vitrine -> future Sunset handoff contract
pds-vitrine -> explicit external-system adapters
```

Circular dependencies and required producer-to-Vitrine dependencies are prohibited.

### 14. Conservative behavior when contracts are unavailable

Producer and sibling runtime contracts are at different implementation stages. When a required public contract is absent, incompatible, or unavailable, Vitrine will report an explicit unsupported or unavailable state.

It will not fall back to private-file parsing or semantic inference.

## Authority hierarchy

| Concern | Authoritative owner |
| --- | --- |
| Shared class/module/work identity | Core |
| Academic Work Registration | Core |
| Publication identity, manifest binding, supersession, withdrawal | Core |
| Producer manifest and native record meaning | Originating producer |
| Source artifact content and revision | Originating producer or identified external source |
| ScoreForm attempt facts | ScoreForm |
| Quillan submission and review facts | Quillan |
| Concord authorship, subject, contribution, and Score relationships | Concord |
| Portia intervention facts | Portia |
| Grade and proficiency derivation | Meridian |
| Portfolio purpose, curation, annotation, reflection, and portfolio review | Vitrine |
| Exact historical content of an issued Vitrine edition | Immutable Vitrine snapshot |
| Institutional authorization, consent, and official signatures | Responsible institution/system |
| Suite-wide archive/disposition execution | Future Sunset or institutional records authority |
| Official submission receipt and regulated outcome | Receiving external authority |

Authority is layered. Core may be authoritative for publication identity while the producer is authoritative for manifest meaning and Vitrine is authoritative for the later selection. No layer erases another.

## Consequences

### Positive consequences

- Vitrine has a clear, independent product role.
- Source authority and provenance remain intact.
- Core stays module-neutral.
- Producers remain independently operable.
- Portfolio selection cannot silently affect Grades.
- Portia material receives deny-by-default treatment.
- Concord group Artifacts retain truthful authorship and subject scope.
- Issued snapshots remain historical records rather than mutable live views.
- External approval and institutional authority are not impersonated.
- Future archive integration can move custody without changing meaning.
- Missing runtime contracts produce explicit capability gaps rather than unsafe fallback parsing.

### Negative consequences

- Vitrine requires explicit adapters and multiple source relationships rather than one universal artifact object.
- Authorization cannot be inferred from Core discovery.
- Multi-student and group Artifacts require more complex handling.
- Some producer integrations cannot be implemented until public readers exist.
- External submission workflows require separate connectors or human-recorded events.
- Archive and retention behavior cannot be completed until an institutional or Sunset contract exists.
- Interfaces must explain several distinct concepts that simpler systems often collapse.

### Implementation consequences

Later implementation must:

- preserve source-module identity;
- validate Core canonical state and manifest digests;
- use public producer readers;
- record source facts separately from portfolio interpretations;
- implement deny-by-default source classes;
- preserve explicit Concord relationships;
- distinguish portfolio and grading selection;
- create immutable snapshot records;
- support external-reference provenance;
- and fail closed or report unsupported states when authority or contracts are missing.

## Alternatives considered

### Alternative 1: Implement portfolios inside Meridian

Rejected.

Meridian owns grading, proficiency, Grade-item membership, and formal reporting. Portfolio curation includes original artifacts, reflections, annotations, audience-specific editions, rights review, and external presentation that are not grading responsibilities. Combining the modules would turn Meridian into an artifact manager and blur portfolio selection with grading-evidence selection.

### Alternative 2: Treat Core publications as portfolio records

Rejected.

Core publications are neutral discovery envelopes bound to producer manifests. They do not contain Vitrine purpose, selection, audience, reflection, approval, or snapshot semantics. Adding those fields would make Core portfolio-aware and would still not solve access authorization.

### Alternative 3: Copy all producer records into one Vitrine-native universal artifact schema

Rejected.

Producer domains contain non-interchangeable meanings: attempts, writing reviews, collaborative Scores, group authorship, and intervention records. A universal copy would lose semantics, create competing canonical records, and make corrections or withdrawals ambiguous.

### Alternative 4: Make every producer depend on Vitrine

Rejected.

Producer modules must remain independently operable and publish through Core without Vitrine. Reverse dependencies would create installation coupling and circular architecture.

### Alternative 5: Automatically include all discoverable work

Rejected.

Discovery is not authorization, eligibility, selection, disclosure permission, or audience approval. Automatic inclusion would violate the intentional nature of portfolios and expose sensitive or unsuitable records.

### Alternative 6: Automatically include Portia records

Rejected.

Portia records are contextual, sensitive intervention records. Automatic inclusion would create privacy leakage, risk stigmatizing students, and conflate support information with academic evidence.

### Alternative 7: Assign every Concord group Artifact to every member

Rejected.

Group Membership does not prove authorship, contribution, subject status, or individual proficiency. Automatic assignment would create false provenance and violate Concord's accepted architecture.

### Alternative 8: Make Vitrine responsible for archival destruction

Rejected.

Retention and disposition are institutionally governed across modules. Vitrine cannot classify every upstream record, coordinate legal holds suite-wide, or delete producer/Core records. It may provide portfolio lifecycle and handoff metadata only.

### Alternative 9: Make Vitrine the external compliance decision-maker

Rejected.

Vitrine may evaluate profile completeness and preserve evidence, but institutional and government authorities own attestations, submissions, acceptance, graduation, and diploma decisions. A software finding is not legal approval.

### Alternative 10: Parse private producer files until readers exist

Rejected.

This would make Vitrine depend on unstable implementation details, bypass privacy projections, and encourage semantic guessing. Unsupported integrations must remain explicit.

## Required follow-up

The following v0.1.0 issues must apply this decision:

- #4: portfolio identity and explicit cross-class subject linking;
- #5: versioned profiles and external rule authority;
- #6: candidate and source-reference contracts;
- #7: producer artifact exposure boundaries;
- #8: selection, ordering, annotation, and reflection records;
- #9: snapshot, checksum, and immutability contracts;
- #10: privacy, redaction, and audience controls;
- #11: regulated compliance profiles.

Cross-repository implementation issues may be required for:

- ScoreForm's consumer-neutral reader;
- Quillan's publication and consumer-neutral reader;
- Concord's publication and artifact reader;
- Portia's intervention publication and privacy-safe projection;
- Meridian's public report-output contract;
- and a future Sunset archival handoff contract.

## References

### Vitrine

- [Portfolio purposes and workflows](../research/portfolio-purpose-workflows.md)
- [Compliance and policy constraints](../research/compliance-constraints.md)
- [New Jersey Graduation Portfolio Appeal](../research/new-jersey-graduation-portfolio-appeal.md)
- [Module-boundary architecture](../architecture/module-boundaries.md)

### Sibling repositories

- [PDS Core academic registry integration](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/docs/academic_registry_integration.md)
- [ScoreForm Academic Result Manifest v1](https://github.com/Paper-Data-Suite/pds-scoreform/blob/10459751476f6d48d3c3a908a26d76732f00e340/docs/academic_result_manifest_v1.md)
- [Quillan workspace lifecycle](https://github.com/Paper-Data-Suite/pds-quillan/blob/05fecf23d29e56b45cba58ed97906f5353290033/docs/workspace_lifecycle.md)
- [Concord ADR 0005: Separate Artifact Authors and Subjects](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0005-separate-artifact-authors-and-subjects.md)
- [Portia README](https://github.com/Paper-Data-Suite/pds-portia/blob/8cd4b1f2ca80cc240693184c87e5df463ba375cf/README.md)
- [Meridian README](https://github.com/Paper-Data-Suite/pds-meridian/blob/e6be420c1ad650fa801cd16867fa18a30cb1050c/README.md)
