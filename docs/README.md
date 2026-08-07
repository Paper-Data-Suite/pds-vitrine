# Vitrine Documentation

Vitrine completed its audited v0.1.0 foundation with a
`ready_for_implementation` verdict and is implementing the v0.2.0 runtime
foundation. Documents distinguish accepted architecture, conceptual designs,
exact runtime contracts, validated fixtures, and deferred workflows.

## Runtime implementation

- [Foundational runtime models v1](contracts/foundational-runtime-models-v1.md) — exact immutable record and value-object contract, conversion, canonical JSON, and graph validation implemented by issue #28.
- [Runtime-model development](development/runtime-models.md) — public imports, construction, conversion, fixtures, and validation commands.
- [Package foundation](development/package-foundation.md) — installable package, Core 0.6 dependency, CLI/menu shell, workspace delegation, packaging, and CI.
- [Synthetic data policy](development/synthetic-data.md) — repository-wide test and fixture privacy rules.

The runtime model layer does not provide persistence, producer discovery,
source-byte access, curation services, Snapshot construction, authorization,
export, or delivery.

## Foundation research

- [Portfolio purposes and workflows](research/portfolio-purpose-workflows.md)
- [New Jersey Graduation Portfolio Appeal](research/new-jersey-graduation-portfolio-appeal.md)
- [Compliance and policy constraints](research/compliance-constraints.md)
- [Source register](research/source-register.md)

## Architecture and conceptual design

- [Architecture index](architecture/README.md)
- [Module boundaries and authority](architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](design/portfolio-subject-identity.md)
- [Versioned Portfolio Profiles](design/portfolio-profile-contract.md)
- [Candidate and source-reference contract](design/candidate-source-reference-contract.md)
- [Producer Artifact exposure boundaries](design/producer-artifact-exposure-boundaries.md)
- [Selection, ordering, annotation, and reflection](design/selection-curation-records.md)
- [Snapshot, export, checksum, and immutability](design/snapshot-export-immutability-contracts.md)
- [Privacy, redaction, and audience controls](design/privacy-redaction-audience-controls.md)
- [Regulated Portfolio and compliance Profiles](design/regulated-portfolio-compliance-profiles.md)

## Representative examples and fixtures

- [Portfolio Subject examples](examples/portfolio-subject-identity-examples.md)
- [Portfolio Profile examples](examples/portfolio-profile-examples.md)
- [Candidate and source-reference examples](examples/candidate-source-reference-examples.md)
- [Producer Artifact exposure examples](examples/producer-artifact-exposure-examples.md)
- [Selection and curation examples](examples/selection-curation-examples.md)
- [Snapshot and export examples](examples/snapshot-export-examples.md)
- [Privacy and audience examples](examples/privacy-redaction-audience-examples.md)
- [Regulated Portfolio examples](examples/regulated-portfolio-compliance-examples.md)
- [Representative synthetic Portfolio corpus](examples/representative-synthetic-portfolios.md)

Canonical runtime-model fixtures are stored under:

```text
tests/fixtures/runtime-models/
```

The earlier representative corpus remains under:

```text
fixtures/representative-portfolios/
```

## Foundation audit

- [Audit index](audits/README.md)
- [Portfolio foundation audit](audits/portfolio-foundation-audit.md)
- [Portfolio foundation traceability](audits/portfolio-foundation-traceability.md)
- [Portfolio foundation findings](audits/portfolio-foundation-findings.md)
- [Issue #13 validation](validation/issue-13-portfolio-foundation-validation.md)

## Architecture decisions

- [ADR index](decisions/README.md)
- [ADR 0001: Module Boundaries and Authority](decisions/0001-vitrine-module-boundaries-and-authority.md)
- [ADR 0002: Portfolio Subject Identity](decisions/0002-portfolio-subject-identity-and-roster-linking.md)
- [ADR 0003: Versioned Portfolio Profiles](decisions/0003-versioned-portfolio-profiles.md)
- [ADR 0004: Candidate Discovery and Source References](decisions/0004-candidate-discovery-and-source-references.md)
- [ADR 0005: Producer Artifact Exposure](decisions/0005-producer-artifact-exposure-boundaries.md)
- [ADR 0006: Selection and Curation](decisions/0006-selection-ordering-annotation-and-reflection.md)
- [ADR 0007: Snapshot and Immutability](decisions/0007-snapshot-export-checksum-and-immutability.md)
- [ADR 0008: Privacy and Audience Controls](decisions/0008-privacy-redaction-and-audience-controls.md)
- [ADR 0009: Regulated Portfolio Profiles](decisions/0009-regulated-portfolio-and-compliance-profiles.md)

## Authority

When documents disagree:

1. an Accepted ADR governs the architectural decision;
2. an exact accepted runtime contract governs detailed shape and validation;
3. implementation documentation describes current behavior;
4. architecture documents consolidate context and constraints;
5. conceptual designs provide reviewed recommendations;
6. research provides evidence but does not establish executable contracts.

No document in this repository provides legal advice, activates an operational
regulated Profile, or makes Vitrine an external compliance authority.
