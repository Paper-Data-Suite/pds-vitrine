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

## Reading order

1. Review the [foundation research](../research/portfolio-purpose-workflows.md).
2. Read [module boundaries and authority](module-boundaries.md).
3. Read the related [Architecture Decision Records](../decisions/README.md).
4. Read the [Portfolio Subject identity design](../design/portfolio-subject-identity.md).
5. Read the [Versioned Portfolio Profile design](../design/portfolio-profile-contract.md).
6. Read the [Candidate and source-reference design](../design/candidate-source-reference-contract.md).
7. Use later contract documents for exact serialized structures once they are added.

## Document authority

When documents disagree:

1. an **Accepted** ADR governs the architectural decision;
2. a final accepted contract governs detailed record shape and validation while remaining subordinate to ADRs;
3. implementation documentation describes current behavior;
4. architecture documents provide consolidated context and constraints;
5. conceptual design documents provide reviewed record-level recommendations;
6. research documents provide evidence and design inputs but do not establish final contracts.

The current ADRs are **Proposed**. Until explicitly accepted, they record reviewed recommendations and must not be represented as accepted decisions.
