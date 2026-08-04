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

## Architecture decisions

- [ADR index](decisions/README.md)
- [ADR 0001: Vitrine Module Boundaries and Authority](decisions/0001-vitrine-module-boundaries-and-authority.md) — currently **Proposed** pending explicit maintainer acceptance.
- [ADR 0002: Portfolio Subject Identity and Roster Linking](decisions/0002-portfolio-subject-identity-and-roster-linking.md) — currently **Proposed** pending explicit maintainer acceptance.

## Document status and authority

- Research documents provide evidence and design inputs. They do not define final schemas or certify compliance.
- Architecture documents consolidate system context and constraints.
- Conceptual design documents translate architecture into record responsibilities and invariants without finalizing serialization or runtime behavior.
- A Proposed ADR records a recommendation under review.
- An Accepted ADR governs later contracts and implementation unless superseded.
- Future accepted contracts will define exact record shapes and validation while remaining subordinate to accepted ADRs.
- Implementation documentation will describe behavior that actually exists.

No document in this repository provides legal advice, activates an operational New Jersey profile, or makes Vitrine an external compliance authority.
