# Vitrine Documentation

Vitrine is in its foundation-design phase. The documents in this repository distinguish research findings, architecture decisions, conceptual designs, later data contracts, and eventual implementation behavior.

## Foundation research

- [Portfolio purposes and workflows](research/portfolio-purpose-workflows.md) — compares improvement, showcase, parent/guardian conference, and regulated alternate-graduation-pathway portfolios.
- [New Jersey Graduation Portfolio Appeal](research/new-jersey-graduation-portfolio-appeal.md) — versioned 2025-2026/Class of 2026 regulated-workflow case study.
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

## Architecture decisions

- [ADR index](decisions/README.md)
- [ADR 0001: Vitrine Module Boundaries and Authority](decisions/0001-vitrine-module-boundaries-and-authority.md) — currently **Proposed** pending explicit maintainer acceptance.
- [ADR 0002: Portfolio Subject Identity and Roster Linking](decisions/0002-portfolio-subject-identity-and-roster-linking.md) — currently **Proposed** pending explicit maintainer acceptance.
- [ADR 0003: Versioned Portfolio Profiles](decisions/0003-versioned-portfolio-profiles.md) — currently **Proposed** pending explicit maintainer acceptance.
- [ADR 0004: Candidate Discovery and Source References](decisions/0004-candidate-discovery-and-source-references.md) — currently **Proposed** pending explicit maintainer acceptance.
- [ADR 0005: Producer Artifact Exposure Boundaries](decisions/0005-producer-artifact-exposure-boundaries.md) — currently **Proposed** pending explicit maintainer acceptance.
- [ADR 0006: Selection, Ordering, Annotation, and Reflection](decisions/0006-selection-ordering-annotation-and-reflection.md) — currently **Proposed** pending explicit maintainer acceptance.

## Document status and authority

- Research documents provide evidence and design inputs. They do not define final schemas or certify compliance.
- Architecture documents consolidate system context and constraints.
- Conceptual design documents translate architecture into record responsibilities and invariants without finalizing serialization or runtime behavior.
- A Proposed ADR records a recommendation under review.
- An Accepted ADR governs later contracts and implementation unless superseded.
- Future accepted contracts will define exact record shapes and validation while remaining subordinate to accepted ADRs.
- Implementation documentation will describe behavior that actually exists.

No document in this repository provides legal advice, activates an operational New Jersey profile, or makes Vitrine an external compliance authority.
