# Vitrine Architecture

Architecture documents define authority, boundaries, data flow, and constraints.
They do not replace Accepted ADRs or exact runtime contracts.

## Runtime status

The [package foundation](../development/package-foundation.md) establishes the
installable Core 0.6 baseline. The
[foundational runtime-model contract](../contracts/foundational-runtime-models-v1.md)
implements the first exact in-memory Portfolio contract. The
[canonical storage contract](../contracts/canonical-storage-v1.md) adds immutable
persistence and explicit current-state selection. The
[Portfolio Subject workflow contract](../contracts/portfolio-subject-workflows-v1.md)
adds exact Core roster linking and successor-based identity correction. The
[Portfolio Profile workflow contract](../contracts/portfolio-profile-workflows-v1.md)
adds explicit versioned policy, lifecycle, Binding, overlay, and migration. The
[producer projection adapter contract](../contracts/producer-projection-adapters-v1.md)
implements exact reader/adapter selection and strict development fixture
projections without live producer integration.

Core-backed Candidate discovery/evaluation, curation workflows, Snapshot
construction, authorization, and exports remain deferred.

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
5. Use the foundational runtime, storage, Subject, Profile, and producer-adapter contracts for exact implemented behavior.
6. Use the development guides for public APIs and validation.

## Authority order

1. Accepted ADR;
2. exact accepted contract;
3. current implementation documentation;
4. architecture;
5. conceptual design;
6. research.

## Producer adapter authority

Core metadata selects only an exact Vitrine adapter claim. The producer reader
owns producer validation and semantics; the Vitrine adapter performs a pure,
bounded translation. Adapter selection is not authorization, Subject resolution,
Profile eligibility, Candidate creation, Selection, or disclosure.

Development fixture adapters are explicit Vitrine test infrastructure. They do
not establish ScoreForm, Quillan, or Concord readiness.

## Candidate discovery runtime boundary

Issue #33 implements the accepted ADR 0004 trust sequence through explicit Core
and Vitrine application boundaries. The Core catalog proposes only publication
IDs; canonical Core reload, authorization, manifest verification, producer
reading, Subject resolution, and Profile eligibility remain separate stages.
Positive Candidate persistence does not create Selection or disclosure approval.

See [Candidate Discovery and Evaluation v1](../contracts/candidate-discovery-evaluation-v1.md).
