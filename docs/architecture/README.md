# Vitrine Architecture

Architecture documents define authority, boundaries, data flow, and constraints.
They do not replace Accepted ADRs or exact runtime contracts.

## Runtime status

The [package foundation](../development/package-foundation.md) establishes the
installable Core 0.6 baseline. The
[foundational runtime-model contract](../contracts/foundational-runtime-models-v1.md)
implements the first exact in-memory Portfolio contract with immutable models,
canonical JSON, and deterministic graph validation.

Persistence, current pointers, producer adapters, Candidate discovery services,
curation workflows, Snapshot construction, authorization, and exports remain
deferred.

## Current architecture

- [Module boundaries and authority](module-boundaries.md)
- [Portfolio Subject identity](../design/portfolio-subject-identity.md)
- [Versioned Portfolio Profiles](../design/portfolio-profile-contract.md)
- [Candidate and source references](../design/candidate-source-reference-contract.md)
- [Producer Artifact exposure](../design/producer-artifact-exposure-boundaries.md)
- [Selection and curation](../design/selection-curation-records.md)
- [Snapshot and immutability](../design/snapshot-export-immutability-contracts.md)
- [Privacy and audience controls](../design/privacy-redaction-audience-controls.md)
- [Regulated Portfolio Profiles](../design/regulated-portfolio-compliance-profiles.md)
- [Representative synthetic Portfolio corpus](../examples/representative-synthetic-portfolios.md)
- [Portfolio foundation audit](../audits/portfolio-foundation-audit.md)

## Reading order

1. Read the [module boundary architecture](module-boundaries.md).
2. Read the [Accepted ADRs](../decisions/README.md).
3. Review the conceptual designs in the order listed above.
4. Review the representative corpus and foundation audit.
5. Use the [foundational runtime contract](../contracts/foundational-runtime-models-v1.md) for exact implemented record shapes.
6. Use the [runtime-model guide](../development/runtime-models.md) for public APIs and validation.

## Authority order

1. Accepted ADR;
2. exact accepted contract;
3. current implementation documentation;
4. architecture;
5. conceptual design;
6. research.
