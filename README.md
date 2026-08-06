# pds-vitrine

A local-first portfolio module for curating authorized student work, preserving provenance, and producing purpose-specific, immutable portfolio snapshots.

## Current status

Vitrine has completed its v0.1.0 portfolio foundation audit with a `ready_for_implementation` verdict. The repository contains accepted architecture decisions, conceptual contracts, a deterministic representative fixture corpus, and offline validation. It does not yet contain a production application, package, persistence layer, producer readers, authorization engine, or snapshot renderer.

## Documentation

Documentation is indexed in [`docs/README.md`](docs/README.md).

Key entry points:

- [Portfolio-purpose research](docs/research/portfolio-purpose-workflows.md)
- [Module boundaries and authority](docs/architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](docs/design/portfolio-subject-identity.md)
- [Versioned Portfolio Profiles](docs/design/portfolio-profile-contract.md)
- [Candidate and source-reference contract](docs/design/candidate-source-reference-contract.md)
- [Producer artifact exposure boundaries](docs/design/producer-artifact-exposure-boundaries.md)
- [Selection, ordering, annotation, and reflection records](docs/design/selection-curation-records.md)
- [Snapshot, export, checksum, and immutability contracts](docs/design/snapshot-export-immutability-contracts.md)
- [Privacy, redaction, and audience controls](docs/design/privacy-redaction-audience-controls.md)
- [Regulated Portfolio and compliance profiles](docs/design/regulated-portfolio-compliance-profiles.md)
- [Representative synthetic Portfolio corpus](docs/examples/representative-synthetic-portfolios.md)
- [Portfolio foundation audit](docs/audits/portfolio-foundation-audit.md)
- [Portfolio foundation traceability](docs/audits/portfolio-foundation-traceability.md)
- [Architecture Decision Records](docs/decisions/README.md)
