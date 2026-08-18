# Vitrine Documentation

Vitrine completed its audited v0.1.0 foundation with a
`ready_for_implementation` verdict and has completed the v0.2.0 runtime
implementation through installed end-to-end acceptance. Issue #40 has promoted
the source release identity to `0.2.0`; qualification, publication, and fresh-download
verification remain pending. Documents distinguish accepted architecture, exact
runtime contracts, validated fixtures, release-audit evidence, and deferred workflows.

## Runtime implementation

- [Foundational runtime models v1](contracts/foundational-runtime-models-v1.md) — exact immutable record/value-object contract, conversion, canonical JSON, and graph validation implemented by issue #28.
- [Canonical storage v1](contracts/canonical-storage-v1.md) — workspace-scoped canonical paths, immutable record/state history, current-pointer publication, concurrency, strict loading, recovery boundaries, and catalog nonauthority implemented by issue #29.
- [Portfolio Subject workflows v1](contracts/portfolio-subject-workflows-v1.md) — exact Core roster linking, attributable identity decisions, correction, merge/split history, CLI, and low-density teacher workflows implemented by issue #30.
- [Portfolio Profile workflows v1](contracts/portfolio-profile-workflows-v1.md) — explicit Profile lifecycle, Requirement identity, exact Binding, overlays, composition, and migration implemented by issue #31.
- [Producer projection adapter boundary v1](contracts/producer-projection-adapters-v1.md) — exact support requests/keys, immutable reader/adapter declarations, deterministic conflict-detecting registry, strict development fixtures, transient projections, and structured failures implemented by issue #32.
- [Candidate discovery and evaluation v1](contracts/candidate-discovery-evaluation-v1.md) — bounded Core catalog discovery, canonical reload, explicit authorization, verified reader bytes, Subject/Profile evaluation, and guarded Candidate persistence implemented by issue #33.
- [Curation workflows v1](contracts/curation-workflows-v1.md) — explicit Proposal/Decision/Selection provenance, lifecycle, Placement/Arrangement pointers, Annotation, Reflection, Review, and immutable Composition state implemented by issue #34.
- [Snapshot build workflows v1](contracts/snapshot-build-workflows-v1.md) — exact Composition-bound Request/Plan/Attempt execution, guarded byte custody, Series locks, exact source/render boundaries, deterministic Manifest/Seal/Edition creation, directory Export, verification, current pointer, and recovery implemented by issue #35.
- [Runtime-model development](development/runtime-models.md) — public imports, construction, conversion, fixtures, and validation commands.
- [Canonical-storage development](development/canonical-storage.md) — persistence, historical reads, audits, catalogs, locks, and focused validation.
- [Portfolio Subject workflow development](development/portfolio-subject-workflows.md) — application services, direct CLI, teacher menu, and workflow validation.
- [Portfolio Profile workflow development](development/portfolio-profile-workflows.md) — Profile service, CLI/menu, and migration guidance.
- [Producer-adapter development](development/producer-adapters.md) — exact selection, fixture isolation, reader purity, and adapter validation.
- [Candidate-discovery development](development/candidate-discovery.md) — runtime construction, authorization gate, exact Subject/Profile evaluation, and focused validation.
- [Curation workflow development](development/curation-workflows.md) — guarded curation services, authority gate, pointer concurrency, revisioning, and Composition guidance.
- [Snapshot build workflow development](development/snapshot-build-workflows.md) — Plan construction, exact provider/renderer boundaries, Series locking, sealing, Export verification, recovery, and validation.
- [Package foundation](development/package-foundation.md) — installable package, Core 0.6 dependency, CLI/menu shell, workspace delegation, packaging, and CI.
- [Synthetic data policy](development/synthetic-data.md) — repository-wide test and fixture privacy rules.

Producer-adapter configuration and projections remain transient. Issue #33
consumes them through a fixture-backed Core discovery/Evaluation service, issue
#34 consumes positive Candidates through explicit byte-free curation, and issue
#35 consumes one exact immutable Composition through explicit Snapshot
construction.

Development fixture adapters, Snapshot fixture providers, and fixture renderers
are not installed producer integrations. Candidate, Selection, curation
approval, Snapshot build authority, disclosure authorization, and external
Issuance remain distinct.

## v0.2.0 release audit

- [v0.2.0 release notes](../RELEASE_NOTES_v0.2.0.md) — reviewed release notes and explicit deferred/live-integration boundary.
- [v0.2.0 release audit](v0.2.0-release-audit.md) — ADR conformance, preserved v0.1 findings, #26 exit conditions, privacy/persistence/Snapshot audit, and release-preparation verdict.
- [v0.2.0 release compatibility boundary](v0.2.0-release-compatibility.md) — frozen target package/runtime contract, fixture/live producer boundary, fail-closed defaults, and deferred scope.
- [Release checklist](release_checklist.md) — separate release-preparation PR, exact-main qualification, immutable GitHub Release publication, and fresh-download verification phases.

These documents describe release preparation until an authenticated `v0.2.0` tag and
GitHub Release are actually published and independently reverified.

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

Issue #32 producer-shaped fixtures are stored under:

```text
fixtures/producer-adapters/
```

Issue #35 deterministic Snapshot build fixtures are stored under:

```text
fixtures/snapshot-workflows/
```

The first executable cross-service Portfolio acceptance slice is documented in
[Executable improvement Portfolio vertical slice](development/improvement-portfolio-vertical-slice.md).
The collaborative audience-safe slice is documented in
[Executable showcase Portfolio vertical slice](development/showcase-portfolio-vertical-slice.md).

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
