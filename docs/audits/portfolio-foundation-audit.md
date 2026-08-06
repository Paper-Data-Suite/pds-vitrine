# Portfolio Foundation Audit

- **Status:** Complete
- **Issue:** #13, “Conduct the portfolio foundation audit”
- **Audit date:** 2026-08-06
- **Verdict:** `ready_for_implementation`
- **Machine-readable record:** [portfolio-foundation-audit.json](portfolio-foundation-audit.json)
- **Findings:** [portfolio-foundation-findings.md](portfolio-foundation-findings.md)
- **Traceability:** [portfolio-foundation-traceability.md](portfolio-foundation-traceability.md)
- **Validation:** [issue-13-portfolio-foundation-validation.md](../validation/issue-13-portfolio-foundation-validation.md)

## Scope

This audit evaluates whether the Vitrine v0.1.0 foundation forms one coherent architecture across research, module boundaries, Portfolio identity, Profile policy, Core discovery, producer projections, curation, Snapshot integrity, privacy, regulated workflows, and the representative fixture corpus.

The audit is skeptical rather than ceremonial. A documentation claim is accepted only when its authority, examples, and executable fixtures agree. Correctable defects are fixed in this issue. Runtime work explicitly excluded from the foundation is classified as a nonblocking limitation rather than silently treated as implemented.

## Method

The review used five evidence layers:

1. current code and documentation in each relevant repository;
2. Vitrine research and module-boundary documents;
3. ADRs 0001 through 0009 and their paired designs;
4. isolated examples and the four complete synthetic Portfolio stories; and
5. standard-library validation of references, paths, bytes, digests, audience packages, findings, traceability, and ADR status.

Every finding records severity, exact evidence, disposition, resolution, and validation. No blocker or major finding remains unresolved.

## Current repository baselines

| Repository | Audited commit | Audited state |
| --- | --- | --- |
| `pds-vitrine` | `21a7e900de7c9247e05769c355f941a5e6fd58e3` | Foundation through the representative corpus; no production runtime. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Released v0.6 registration, publication, compatibility, audit, and rebuildable catalog infrastructure. |
| `pds-scoreform` | `c2fa06f1a4c33df01f3e0d9c8dd27702d4a06419` | Immutable manifest generation; producer profile, Core publication, and Vitrine reader remain later work. |
| `pds-quillan` | `05fecf23d29e56b45cba58ed97906f5353290033` | v0.8.9 submission, review, selected-evidence, and feedback workflow; Core publication remains later work. |
| `pds-concord` | `31b0efd2864cd7a0945ff29f5af99b2a00db52ae` | Native models and guarded persistence; routing, publication, and complete teacher workflow remain later work. |
| `pds-portia` | `d60966f8486bf93fb0185e3662b76d3b79ce9dcb` | Accepted lifecycle and coordinated persistence/recovery contracts; ordinary Portfolio exposure remains suppressed. |
| `pds-meridian` | `d55432f88848705cf9812586673db2bc81e01337` | Typed evidence inventory and exact adapter registry; real adapters, ingestion, policy, Grades, and reports remain later work. |

### Historical construction baseline policy

The representative corpus preserves the repository states used when it was constructed. Those references are historical evidence, not claims that the sibling repository remains at that commit.

The audit separately records current baselines. Historical references remain unchanged when they are reachable and accurately characterize the represented behavior. Invalid or inaccurate references are corrected.

The audit corrected one invalid ScoreForm SHA and narrowed its behavior claim to immutable manifest generation.

## Domain conclusions

### Module ownership and authority — pass

Vitrine remains a separate module. It owns Portfolio identity, Profile policy, Candidate evaluation, curation, Snapshot composition, audience-specific output, and regulated Portfolio workflow.

It does not own Core registration or publication, producer-native records, Meridian grading, Portia intervention records, Sunset archival orchestration, institutional identity, legal consent, or external compliance outcomes.

### Portfolio identity and cross-class linking — pass

Portfolio and Portfolio Subject remain distinct. Class-qualified references are exact and human-confirmed. Names, repeated local IDs, chronology, and filenames are not identity proof. Merge, split, correction, and historical resolution preserve prior state.

The negative corpus rejects name-only and repeated-ID matching.

### Profile versioning — pass

Purpose-specific Profiles are immutable and explicitly activated. Family, series, revision, Binding, cohort, school year, jurisdiction, program version, and local overlay remain distinct. Migration does not silently rewrite existing curation.

### Core compatibility and source authority — pass

The governing chain remains:

```text
catalog hint
  -> canonical Core reload
  -> exact compatibility evaluation
  -> path containment and manifest digest verification
  -> producer-owned reader or projection
  -> Vitrine Candidate evaluation
```

Catalog rows are nonauthoritative. Discovery is not authorization. Capabilities do not define document structure or educational meaning. Later publications and current pointers do not silently retarget historical Selections.

### Producer boundaries — pass

- **ScoreForm:** native attempts, points, and non-score states remain intact; no official-attempt, proficiency, or Grade inference occurs. The audited baseline implements immutable manifest generation, not Core publication or a Vitrine reader.
- **Quillan:** original work, selected evidence, feedback, reviews, and private notes remain distinct. Future public projections are labeled synthetic.
- **Concord:** Group Membership, authorship, subject identity, contribution, privacy, and Score target remain separate. Group Scores never become individual Scores.
- **Portia:** ordinary Portfolio discovery remains deny-by-default and no-leakage. New Portia persistence and derived-index contracts do not broaden Vitrine access.
- **Meridian:** the typed evidence inventory and exact adapter registry are current, but real adapters, ingestion, eligibility policy, proficiency, Grades, and reports remain later work. Meridian state is not Portfolio authority.

### Candidate and curation integrity — pass

Candidate eligibility, Selection, Placement, presentation, annotation, reflection, approval, and disclosure authorization remain separate. A Selection binds one exact Candidate and Evaluation. Current-pointer changes do not retarget historical curation.

Vitrine preserves a student Reflection but does not calculate improvement.

### Copied-file provenance — pass

Every committed byte-bearing fixture uses safe workspace-relative paths, exact size, lowercase SHA-256, and explicit source or generation identity. Source digests, copied-entry digests, logical inventory digests, manifest digests, and export inventories remain distinct.

Equal bytes do not collapse distinct business identity. Absolute paths, traversal, symlinks, and junctions are rejected.

### Snapshot and export immutability — pass

Build Request, immutable Plan, Attempt, Entry, Omission, Manifest, Seal, Edition, Export Artifact, Issuance, Submission, receipt, and external outcome remain distinct.

Issued Editions never silently refresh. Audience-visible changes require new Edition bytes and identity. Partial success preserves durable history.

### Privacy, audience, and redaction — pass

Metadata visibility, source access, curation, copying, internal-manifest access, issuance, delivery, submission, and historical access are independent authorization actions. Audience Context does not prove Recipient Scope. Indeterminate fails closed.

Portia existence, private Quillan material, ScoreForm secure material, and internal manifests remain absent from audience packages. Redaction is a verified transformation and never an in-place source or Edition edit.

### Regulated Profile integrity — pass

Regulated policy specializes the generic Profile model. Authority sources, case components, pathways, checklist definitions and findings, supporting records, attestations, approvals, readiness, batches, submissions, receipts, and outcomes remain separate.

The New Jersey-style fixture is synthetic, cohort-bound, research-only, and non-operational. ELA and mathematics remain independent.

### Representative corpus — pass

The corpus validates four positive Portfolios, 20 immutable Snapshot Entries, 20 declared negative cases, and 39 byte files. The only required corpus correction was baseline metadata and capability wording for ScoreForm.

## ADR dispositions

| Decision | Final status | Audit rationale |
| --- | --- | --- |
| ADR 0001 | Accepted | Confirms Vitrine ownership and dependency direction without absorbing Core, producer, Meridian, Portia, Sunset, or institutional authority. |
| ADR 0002 | Accepted | Preserves exact class-qualified identity and explicit cross-class confirmation without name-based inference. |
| ADR 0003 | Accepted | Provides immutable purpose-specific Profile revisions, explicit activation, overlays, and migration. |
| ADR 0004 | Accepted | Preserves staged Core discovery, canonical reload, exact compatibility, source authority, and Candidate evaluation. |
| ADR 0005 | Accepted | Keeps producer-owned projections, field allowlists, native meaning, and Portia suppression intact. |
| ADR 0006 | Accepted | Separates Candidate, Selection, Placement, presentation, annotation, reflection, approval, and exact Composition revisions. |
| ADR 0007 | Accepted | Defines exact bytes, digest layers, immutable Editions, exports, issuance, submission, and nondestructive history. |
| ADR 0008 | Accepted | Defines action-specific authorization, recipient scope, no-leakage behavior, redaction verification, and disclosure history. |
| ADR 0009 | Accepted | Specializes Profiles for authority sources, cases, components, checklists, attestations, deadlines, batches, and external outcomes. |

All nine ADRs are accepted as the governing Vitrine foundation. Unresolved serialization and runtime mechanics remain downstream work constrained by these decisions.

## Findings summary

- **Blockers:** 0
- **Major findings:** 3, all resolved
- **Minor findings:** 2, all resolved
- **Observations:** 5, closed without required architecture changes
- **Accepted limitations:** 2, nonblocking and assigned to later implementation

See the [findings register](portfolio-foundation-findings.md) for complete evidence and dispositions.

## Foundation exit conditions

| ID | Condition | Result | Evidence |
| --- | --- | --- | --- |
| EC-001 | Portfolio remains a separate module. | Satisfied | ADR 0001, module boundaries, PF-AUD-011 |
| EC-002 | Candidate discovery uses Core plus exact producer contracts. | Satisfied | ADR 0004, candidate design, negative stale-catalog and unsupported-contract cases |
| EC-003 | Cross-class identity is explicit and never guessed. | Satisfied | ADR 0002, identity design, name-only and repeated-ID negative cases |
| EC-004 | Purpose-specific Profiles are immutable and versioned. | Satisfied | ADR 0003, profile design, four purpose-specific portfolio fixtures |
| EC-005 | Source artifacts and copied Snapshot bytes preserve exact provenance. | Satisfied | ADR 0007, snapshot design, 39 verified byte files |
| EC-006 | Portia inclusion remains exceptional and privacy-governed. | Satisfied | ADR 0005, ADR 0008, Portia no-leakage scan |
| EC-007 | Issued Snapshot Editions never silently update. | Satisfied | ADR 0007, silent-refresh negative case |
| EC-008 | Audience and recipient authorization remain separate. | Satisfied | ADR 0008, parent Recipient Scope fixture, indeterminate-authorization negative case |
| EC-009 | Regulated examples remain versioned and non-operational. | Satisfied | ADR 0009, NJ research, NJ-style fixture |
| EC-010 | Producer-native meanings remain intact. | Satisfied | ADR 0005, ScoreForm non-score states, Concord Group Score boundary |
| EC-011 | Core, producer, Meridian, and Portia boundaries are current. | Satisfied | current audit baseline table, PF-AUD-006, PF-AUD-007 |
| EC-012 | Sibling commit references are valid and accurately characterized. | Satisfied | PF-AUD-001, known-invalid-SHA validator |
| EC-013 | No blocker or major finding remains unresolved. | Satisfied | findings register, foundation validator |
| EC-014 | ADR statuses are explicitly dispositioned. | Satisfied | ADRs 0001-0009 Accepted, decision index |
| EC-015 | Positive and negative corpus validation passes. | Satisfied | representative validator |
| EC-016 | Documentation and audit validation passes. | Satisfied | foundation validator, Markdown link and fence checks |
| EC-017 | No real or restricted student data is present. | Satisfied | synthetic data policy, Portia marker containment |
| EC-018 | No sibling repository is modified and no new Core kind is required. | Satisfied | ADR 0001, PF-AUD-011, repository diff scope |

## Remaining nonblocking implementation work

The foundation does not yet provide:

- final public serialization contracts;
- canonical persistence and transaction recovery;
- a Vitrine application or user interface;
- real producer readers and adapters;
- institutional identity or authorization integration;
- production Snapshot renderers;
- secure delivery;
- operational regulated Profiles;
- external submission automation; or
- Sunset archival and disposition integration.

These are implementation milestones, not foundation contradictions. They must preserve the accepted ADRs and audit invariants.

## Final verdict

```text
ready_for_implementation
```

The Vitrine foundation is coherent, traceable, and sufficiently constrained for serialized-contract and runtime implementation work. No blocker or major finding remains unresolved. No sibling repository change is required.
