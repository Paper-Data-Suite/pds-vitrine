# Vitrine Architecture

This directory contains system-level Vitrine architecture documents. Architecture documents explain boundaries, authority, data flow, and constraints in more detail than an ADR, but they do not replace accepted decisions or final contracts.

## Current documents

- [Module boundaries and authority](module-boundaries.md) — defines Vitrine's ownership, authority hierarchy, dependency directions, sibling-module boundaries, prohibited behavior, edge cases, and downstream implications.

## Related conceptual designs

- [Portfolio Subject identity and cross-class linking](../design/portfolio-subject-identity.md) — applies the module-boundary architecture to Portfolio identity, workspace-scoped subject identity, exact roster references, confirmation, and nondestructive correction.
- [Representative identity examples](../examples/portfolio-subject-identity-examples.md) — exercises the identity design with synthetic cases.
- [Versioned Portfolio Profiles](../design/portfolio-profile-contract.md) — applies the architecture to purpose-specific policy, immutable revisions, requirement identity, audience rules, retention references, and migration.
- [Representative Portfolio Profile examples](../examples/portfolio-profile-examples.md) — exercises the Profile design with synthetic policy families, revisions, conditions, overlays, and failure states.
- [Candidate and source-reference contract](../design/candidate-source-reference-contract.md) — applies the trust architecture to catalog discovery, canonical publication verification, producer readers, source identity, subject relationships, privacy, availability, and Candidate evaluation.
- [Representative Candidate and source-reference examples](../examples/candidate-source-reference-examples.md) — exercises the Candidate design across discovery, integrity, support, producer, privacy, lifecycle, duplicate, and correction cases.
- [Producer artifact exposure boundaries](../design/producer-artifact-exposure-boundaries.md) — applies the Candidate architecture to exact producer-owned projection kinds, allowlists, retained-scan restrictions, readiness, and sensitive-source suppression.
- [Representative producer artifact exposure examples](../examples/producer-artifact-exposure-examples.md) — exercises ScoreForm, Quillan, Concord, Portia, multi-subject, revision, and digest boundaries.
- [Selection, ordering, annotation, and reflection records](../design/selection-curation-records.md) — applies Profiles and Candidates to explicit proposals, decisions, Selections, Placements, ordering, presentation, reflection, approval, and working-composition revisions.
- [Representative selection and curation examples](../examples/selection-curation-examples.md) — exercises student and teacher curation, ordering conflicts, producer boundaries, reflection, approval, replacement, migration, and exact composition history.
- [Snapshot, export, checksum, and immutability contracts](../design/snapshot-export-immutability-contracts.md) — applies exact Composition state to guarded source acquisition, copied/generated Entries, explicit omissions, canonical manifests, layered digests, immutable Editions, exports, issuance, submission, and lifecycle.
- [Representative snapshot and export examples](../examples/snapshot-export-examples.md) — exercises source changes, rendering, checksum layers, omission policy, format differences, concurrency, partial success, external handoff, and historical preservation.
- [Privacy, redaction, and audience controls](../design/privacy-redaction-audience-controls.md) — applies Profiles, source boundaries, curation, and immutable Editions to exact authorization gates, audience and recipient scope, no-leakage discovery, redaction, de-identification, disclosure, and revocation.
- [Representative privacy, redaction, and audience examples](../examples/privacy-redaction-audience-examples.md) — exercises student, family, teacher, reviewer, regulated, public, producer, collaborator, transformation, consent, logging, and historical-access cases.
- [Regulated Portfolio and compliance profiles](../design/regulated-portfolio-compliance-profiles.md) — specializes immutable Profiles for authority sources, cases, independent components, pathways, checklists, records, attestations, deadlines, approvals, batches, submissions, receipts, outcomes, migration, and a researched New Jersey reference family.
- [Representative regulated Portfolio and compliance examples](../examples/regulated-portfolio-compliance-examples.md) — exercises source activation, components, pathways, missing and defective evidence, signer authority, deadlines, approvals, rolling submissions, external outcomes, producer boundaries, and replay.
- [Representative synthetic Portfolio corpus](../examples/representative-synthetic-portfolios.md) — composes the identity, Profile, source, exposure, curation, Snapshot, privacy, and regulated-workflow contracts into validated improvement, showcase, conference, and NJ-style fixtures.
- [Portfolio foundation audit](../audits/portfolio-foundation-audit.md) — evaluates the complete foundation, reconciles sibling drift, accepts ADRs 0001-0009, and records the readiness verdict.

## Reading order

1. Review the [foundation research](../research/portfolio-purpose-workflows.md).
2. Read [module boundaries and authority](module-boundaries.md).
3. Read the related [Architecture Decision Records](../decisions/README.md).
4. Read the [Portfolio Subject identity design](../design/portfolio-subject-identity.md).
5. Read the [Versioned Portfolio Profile design](../design/portfolio-profile-contract.md).
6. Read the [Candidate and source-reference design](../design/candidate-source-reference-contract.md).
7. Read the [producer artifact exposure design](../design/producer-artifact-exposure-boundaries.md).
8. Read the [selection and curation design](../design/selection-curation-records.md).
9. Read the [snapshot, export, checksum, and immutability design](../design/snapshot-export-immutability-contracts.md).
10. Read the [privacy, redaction, and audience-control design](../design/privacy-redaction-audience-controls.md).
11. Read the [regulated Portfolio and compliance-profile design](../design/regulated-portfolio-compliance-profiles.md).
12. Review and validate the [representative synthetic Portfolio corpus](../examples/representative-synthetic-portfolios.md).
13. Read the [portfolio foundation audit](../audits/portfolio-foundation-audit.md) and [traceability matrix](../audits/portfolio-foundation-traceability.md).
14. Use later contract documents for exact serialized structures once they are added.

## Document authority

When documents disagree:

1. an **Accepted** ADR governs the architectural decision;
2. a final accepted contract governs detailed record shape and validation while remaining subordinate to ADRs;
3. implementation documentation describes current behavior;
4. architecture documents provide consolidated context and constraints;
5. conceptual design documents provide reviewed record-level recommendations;
6. research documents provide evidence and design inputs but do not establish final contracts.

ADRs 0001 through 0009 are **Accepted** following the issue #13 portfolio foundation audit.

## Runtime baseline

The [package foundation](../development/package-foundation.md) establishes the installable v0.2.0 shell and released Core 0.6 dependency without adding Portfolio runtime records, producer readers, persistence, or Snapshot behavior.
