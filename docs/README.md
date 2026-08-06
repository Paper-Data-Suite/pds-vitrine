# Vitrine Documentation

Vitrine has completed its v0.1.0 foundation audit with a `ready_for_implementation` verdict. The documents in this repository distinguish accepted architecture, conceptual designs, validated fixtures, later data contracts, and eventual implementation behavior.

## Foundation research

- [Portfolio purposes and workflows](research/portfolio-purpose-workflows.md) — compares improvement, showcase, parent/guardian conference, and regulated alternate-graduation-pathway portfolios.
- [New Jersey Graduation Portfolio Appeal](research/new-jersey-graduation-portfolio-appeal.md) — revalidated 2025-2026/Class of 2026 regulated-workflow case study and non-operational reference Profile family.
- [Compliance and policy constraints](research/compliance-constraints.md) — privacy, retention, accessibility, accommodations, intellectual property, and local-policy boundaries.
- [Source register](research/source-register.md) — reviewable inventory of authorities, temporal scope, source status, and known gaps.

## Foundation architecture

- [Architecture index](architecture/README.md)
- [Module boundaries and authority](architecture/module-boundaries.md) — Vitrine ownership, source authority, dependency directions, sibling-module boundaries, external-system limits, and edge-case behavior.

## Conceptual design

- [Portfolio Subject identity and cross-class linking](design/portfolio-subject-identity.md) — Portfolio and subject identity, exact roster references, teacher-confirmed associations, historical resolution, correction, merge, and split.
- [Representative identity examples](examples/portfolio-subject-identity-examples.md) — privacy-safe scenarios exercising cross-class, cross-year, correction, merge, split, Concord, and Portia boundaries.
- [Versioned Portfolio Profiles](design/portfolio-profile-contract.md) — Profile families, immutable revisions, requirements, audience rules, approvals, retention references, composition, and migration.
- [Representative Portfolio Profile examples](examples/portfolio-profile-examples.md) — synthetic improvement, showcase, conference, regulated, migration, composition, and failure scenarios.
- [Candidate and source-reference contract](design/candidate-source-reference-contract.md) — staged Core discovery, canonical verification, producer-reader projection, exact source references, subject relationships, privacy, availability, and Candidate evaluation.
- [Representative Candidate and source-reference examples](examples/candidate-source-reference-examples.md) — synthetic discovery, integrity, adapter, producer, privacy, lifecycle, and correction scenarios.
- [Producer artifact exposure boundaries](design/producer-artifact-exposure-boundaries.md) — producer-owned projection kinds, exposure and readiness states, field allowlists, retained-scan policy, and ScoreForm, Quillan, Concord, and Portia matrices.
- [Representative producer artifact exposure examples](examples/producer-artifact-exposure-examples.md) — synthetic source-only, eligible, conditional, prohibited, suppressed, group, privacy, revision, and digest scenarios.
- [Selection, ordering, annotation, and reflection records](design/selection-curation-records.md) — proposals, decisions, Selections, Placements, immutable ordering, presentation, rationale, annotation, reflection, approval, composition revisions, and replacement history.
- [Representative selection and curation examples](examples/selection-curation-examples.md) — synthetic proposal, ordering, reflection, approval, producer-boundary, migration, correction, and composition scenarios.
- [Snapshot, export, checksum, and immutability contracts](design/snapshot-export-immutability-contracts.md) — exact Composition input, source acquisition, copied and generated Entries, omissions, manifests, checksums, immutable Editions, exports, issuance, submission, and lifecycle.
- [Representative snapshot and export examples](examples/snapshot-export-examples.md) — synthetic copy, render, digest, omission, export, concurrency, partial-success, issuance, submission, lifecycle, and exceptional-removal scenarios.
- [Privacy, redaction, and audience controls](design/privacy-redaction-audience-controls.md) — separate authorization gates, audience and recipient scope, authority evidence, no-leakage discovery, redaction, de-identification, collaborator treatment, disclosure authorization, events, and revocation.
- [Representative privacy, redaction, and audience examples](examples/privacy-redaction-audience-examples.md) — synthetic student, family, teacher, reviewer, regulated, public, producer, redaction, de-identification, delivery, and historical-authorization scenarios.
- [Regulated Portfolio and compliance profiles](design/regulated-portfolio-compliance-profiles.md) — authority sources, regulated cases and components, pathways, checklists, supporting records, attestations, deadlines, approvals, batches, submissions, receipts, outcomes, migration, and the New Jersey reference family.
- [Representative regulated Portfolio and compliance examples](examples/regulated-portfolio-compliance-examples.md) — synthetic Profile activation, component, pathway, evidence, checklist, attestation, deadline, batch, resubmission, external-outcome, privacy, producer, and historical-replay scenarios.
- [Representative synthetic Portfolio corpus](examples/representative-synthetic-portfolios.md) — executable cross-contract fixtures for improvement, showcase, parent/guardian conference, and research-only NJ-style regulated Portfolios, with actual bytes, checksums, producer boundaries, expected outcomes, and negative cases.

## Foundation audit

- [Audit index](audits/README.md)
- [Portfolio foundation audit](audits/portfolio-foundation-audit.md) — skeptical closure review and final `ready_for_implementation` verdict.
- [Portfolio foundation traceability](audits/portfolio-foundation-traceability.md) — maps every foundation issue and exit condition to direct evidence.
- [Portfolio foundation findings](audits/portfolio-foundation-findings.md) — preserved finding register and dispositions.
- [Issue #13 validation](validation/issue-13-portfolio-foundation-validation.md) — offline validation commands and results.

## Architecture decisions

- [ADR index](decisions/README.md)
- [ADR 0001: Vitrine Module Boundaries and Authority](decisions/0001-vitrine-module-boundaries-and-authority.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0002: Portfolio Subject Identity and Roster Linking](decisions/0002-portfolio-subject-identity-and-roster-linking.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0003: Versioned Portfolio Profiles](decisions/0003-versioned-portfolio-profiles.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0004: Candidate Discovery and Source References](decisions/0004-candidate-discovery-and-source-references.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0005: Producer Artifact Exposure Boundaries](decisions/0005-producer-artifact-exposure-boundaries.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0006: Selection, Ordering, Annotation, and Reflection](decisions/0006-selection-ordering-annotation-and-reflection.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0007: Snapshot, Export, Checksum, and Immutability](decisions/0007-snapshot-export-checksum-and-immutability.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0008: Privacy, Redaction, and Audience Controls](decisions/0008-privacy-redaction-and-audience-controls.md) — accepted by the issue #13 portfolio foundation audit.
- [ADR 0009: Regulated Portfolio and Compliance Profiles](decisions/0009-regulated-portfolio-and-compliance-profiles.md) — accepted by the issue #13 portfolio foundation audit.

## Document status and authority

- Research documents provide evidence and design inputs. They do not define final schemas or certify compliance.
- Architecture documents consolidate system context and constraints.
- Conceptual design documents translate architecture into record responsibilities and invariants without finalizing serialization or runtime behavior.
- A Proposed ADR records a recommendation under review.
- An Accepted ADR governs later contracts and implementation unless superseded.
- Future accepted contracts will define exact record shapes and validation while remaining subordinate to accepted ADRs.
- Implementation documentation will describe behavior that actually exists.

No document in this repository provides legal advice, activates an operational New Jersey profile, or makes Vitrine an external compliance authority.
