# Vitrine Documentation

Vitrine has completed the merged v0.3.0 implementation through issue #71 and is now
in issue #72 release audit/preparation. The source release identity is promoted to
`0.3.0` during this work, but publication and fresh-download verification remain
separate release phases.

The v0.3 implementation consumes exact released ScoreForm, Quillan, and Concord
contracts through public producer boundaries, adds guided teacher Portfolio workflows,
immutable local Snapshot/Export custody, bounded attention, and Core module-operations
integration while preserving Vitrine's privacy/provenance/authority boundaries.

Documents distinguish accepted architecture, exact runtime contracts, development
fixtures, live installed acceptance, release-audit evidence, and intentionally deferred
production authorization/delivery surfaces.

## Runtime implementation

- [Foundational runtime models v1](contracts/foundational-runtime-models-v1.md) — exact immutable record/value-object contract, conversion, canonical JSON, and graph validation implemented by issue #28.
- [Canonical storage v1](contracts/canonical-storage-v1.md) — workspace-scoped canonical paths, immutable record/state history, current-pointer publication, concurrency, strict loading, recovery boundaries, and catalog nonauthority implemented by issue #29.
- [Portfolio Subject workflows v1](contracts/portfolio-subject-workflows-v1.md) — exact Core roster linking, attributable identity decisions, correction, merge/split history, CLI, and low-density teacher workflows implemented by issue #30.
- [Portfolio Profile workflows v1](contracts/portfolio-profile-workflows-v1.md) — explicit Profile lifecycle, Requirement identity, exact Binding, overlays, composition, and migration implemented by issue #31.
- [Starter Portfolio Profiles v1](contracts/starter-portfolio-profiles-v1.md) — optional packaged Improvement/Showcase Profiles, read-only planning, explicit atomic activation, and producer-neutral policy implemented by issue #63.
- [Producer projection adapter boundary v1](contracts/producer-projection-adapters-v1.md) — exact support requests/keys, immutable reader/adapter declarations, deterministic conflict-detecting registry, strict development fixtures, transient projections, and structured failures implemented by issue #32.
- [Candidate discovery and evaluation v1](contracts/candidate-discovery-evaluation-v1.md) — bounded Core catalog discovery, canonical reload, explicit authorization, verified reader bytes, Subject/Profile evaluation, and guarded Candidate persistence implemented by issue #33.
- [Candidate Inbox v1](contracts/candidate-inbox-v1.md) — explicit Candidate current-Evaluation pointers, workspace-wide positive/negative review, bounded staleness/attention, provenance, CLI/menu, and suppression-safe read behavior implemented by issue #64.
- [Guided Candidate review and Selection v1](contracts/guided-candidate-review-selection-v1.md) — Candidate Inbox-backed teacher review, explicit select/decline/Placement/lifecycle/content/review orchestration, exact concurrency, menu/CLI reuse, and producer-independent curation implemented by issue #66.
- [Guided Working Composition v1](contracts/guided-working-composition-v1.md) — read-only exact curation preparation, ordered section/Placement explanation, Requirement/source/Review/audience constraints, deterministic fingerprints, prepared fail-closed freeze, menu/CLI reuse, and producer-independent Composition creation implemented by issue #67.
- [Build and Export Current Portfolio v1](contracts/build-export-current-portfolio-v1.md) — exact current-Composition handoff, audience/materialization/export preparation, canonical Snapshot execution, verified directory Export, menu/CLI parity, and explicit non-delivery/current-pointer boundaries implemented by issue #68.
- [Attention and Next Actions v1](contracts/attention-next-actions-v1.md) — deterministic read-only Candidate/curation/Composition/Snapshot/omission/Export attention projection, bounded owner actions, privacy-minimal summaries, and explicit issue #70 handoff implemented by issue #69.
- [Teacher Information Architecture v1](contracts/teacher-information-architecture-v1.md) — teacher-first presentation hierarchy, explicit Technical Details / Provenance drill-down, and display-versus-authority boundary introduced by issue #95.
- [Candidate Evidence Review v1](contracts/candidate-evidence-review-v1.md) — instructional Candidate naming, discovery summaries, exact preview revalidation, fail-closed Artifact access, structured metadata preview, and transient viewer handling implemented by issue #96.
- [Guided Menu Interactions v1](contracts/guided-menu-interactions-v1.md) — shared controlled confirmations, required zero/one/many choice handling, clear/redraw transitions, and contextual next actions implemented by issue #98.
- [Vitrine Suite Operations Integration v1](contracts/suite-operations-integration-v1.md) â€” Core 0.6.3 module-operations provider, workspace readiness, #69 attention adaptation, exact unsupported class-scope rule, and opaque workspace relocation boundary implemented by issue #70.
- [Create Portfolio for Student v1](contracts/create-portfolio-for-student-v1.md) — exact Core roster selection, explicit cross-class Subject association, exact Profile choice, read-only planning, and one-batch guarded setup implemented by issue #65.
- [Curation workflows v1](contracts/curation-workflows-v1.md) — explicit Proposal/Decision/Selection provenance, lifecycle, Placement/Arrangement pointers, Annotation, Reflection, Review, and immutable Composition state implemented by issue #34.
- [Snapshot build workflows v1](contracts/snapshot-build-workflows-v1.md) — exact Composition-bound Request/Plan/Attempt execution, guarded byte custody, Series locks, exact source/render boundaries, deterministic Manifest/Seal/Edition creation, directory Export, verification, current pointer, and recovery implemented by issue #35.
- [Runtime-model development](development/runtime-models.md) — public imports, construction, conversion, fixtures, and validation commands.
- [Canonical-storage development](development/canonical-storage.md) — persistence, historical reads, audits, catalogs, locks, and focused validation.
- [Portfolio Subject workflow development](development/portfolio-subject-workflows.md) — application services, direct CLI, teacher menu, and workflow validation.
- [Portfolio Profile workflow development](development/portfolio-profile-workflows.md) — Profile service, CLI/menu, and migration guidance.
- [Starter Portfolio Profile development](development/starter-portfolio-profiles.md) — catalog, validation, planning, installation, CLI/menu, customization, and wheel acceptance guidance.
- [Producer-adapter development](development/producer-adapters.md) — exact selection, fixture isolation, reader purity, and adapter validation.
- [Candidate-discovery development](development/candidate-discovery.md) — runtime construction, authorization gate, exact Subject/Profile evaluation, and focused validation.
- [Candidate Inbox development](development/candidate-inbox.md) — current-Evaluation pointer rules, read-only projection, Portfolio reuse, focused validation, and installed-wheel acceptance.
- [Guided Candidate review and Selection development](development/guided-candidate-review-selection.md) — planner/executor boundaries, exact Evaluation provenance, explicit section/Placement intent, lifecycle/content/review orchestration, menu/CLI integration, and validation.
- [Guided Working Composition development](development/guided-working-composition.md) — shared derivation, read-only preparation, exact replay/concurrency/source guards, audience-neutral boundaries, menu/CLI integration, and wheel qualification.
- [Build and Export Current Portfolio development](development/build-export-current-portfolio.md) — shared preparation/view orchestration, deterministic first-party planning, canonical execution, recovery, menu/CLI integration, and installed-wheel validation.
- [Attention and Next Actions development](development/attention-next-actions.md) — semantic-source delegation, current build-chain rules, deterministic aggregation, read-only menu/CLI surfaces, and Core 0.6.3 qualification guidance.
- [Teacher Information Architecture development](development/teacher-information-architecture.md) — transient teacher presentation projections, Portfolio overview/drill-down behavior, and extension rules for issue #95.
- [Candidate Evidence Review development](development/candidate-evidence-review.md) — #96 evidence-presentation, preview-authority, producer Artifact bridge, transient viewer, and focused qualification boundaries.
- [Guided menu interaction development](development/guided-menu-interactions.md) — shared confirmation/cardinality helpers, redraw rules, contextual continuation, navigation, and active-versus-dormant workflow boundaries for issue #98.
- [Suite operations integration development](development/suite-operations-integration.md) â€” installed Core provider discovery, readiness/attention adapter boundaries, opaque relocation validation, package wiring, and complete qualification guidance.
- [Create Portfolio for Student development](development/create-portfolio-for-student.md) — planner-first orchestration, exact identity/Profile boundaries, atomic commit, teacher menu, CLI, and installed-wheel acceptance.
- [Curation workflow development](development/curation-workflows.md) — guarded curation services, authority gate, pointer concurrency, revisioning, and Composition guidance.
- [Snapshot build workflow development](development/snapshot-build-workflows.md) — Plan construction, exact provider/renderer boundaries, Series locking, sealing, Export verification, recovery, and validation.
- [Package foundation](development/package-foundation.md) — installable package, Core 0.6 dependency, CLI/menu shell, workspace delegation, packaging, and CI.
- [Synthetic data policy](development/synthetic-data.md) — repository-wide test and fixture privacy rules.

Live adapter declarations and producer projections remain transient. Current production
Candidate discovery consumes Core-governed canonical Publications only after exact
compatibility and source-read authorization, then invokes installed public producer
readers. Quillan/Concord copied Artifact bytes use separate producer Artifact
authorization; ScoreForm Snapshot evidence remains `reference_only`.

Development fixture adapters and fixture renderers remain explicit opt-in test
infrastructure. They are not installed producer integrations and cannot satisfy the
released live support keys. Issue #71 separately authenticates exact released
Core/ScoreForm/Quillan/Concord wheels and qualifies the complete live workflow,
negative matrix, immutable custody, historical reload, and Core+Vitrine-only sealed
verification.

Candidate, Selection, curation approval, Snapshot build authority, disclosure
authorization, and external delivery remain distinct.

## v0.3.0 release audit

- [v0.3.0 release notes](../RELEASE_NOTES_v0.3.0.md) — teacher-facing release value,
  exact compatibility anchors, and explicit authorization/delivery boundaries.
- [v0.3.0 release audit](v0.3.0-release-audit.md) — issue #72 audit ledger and final
  privacy/provenance/usability/architecture/package disposition.
- [v0.3.0 release compatibility boundary](v0.3.0-release-compatibility.md) — frozen
  package, released producer, authority, custody, and suite-operations boundaries.
- [Release checklist](release_checklist.md) — four-phase release preparation,
  exact-main qualification, immutable publication, and fresh-download verification.

Historical v0.2.0 records remain preserved:

- [v0.2.0 release notes](../RELEASE_NOTES_v0.2.0.md)
- [v0.2.0 release audit](v0.2.0-release-audit.md)
- [v0.2.0 release compatibility boundary](v0.2.0-release-compatibility.md)

During issue #72 these documents describe a release candidate until the exact
`v0.3.0` tag/GitHub Release is published and independently reverified.

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

## Issue validation

- [Issue #63 starter Profile validation](validation/issue-63-starter-profile-validation.md) — focused, package, isolated-wheel, and complete repository acceptance evidence.
- [Issue #64 Candidate Inbox validation](validation/issue-64-candidate-inbox-validation.md) — current-Evaluation, positive/negative, staleness/attention, privacy, package, and isolated-wheel acceptance evidence.
- [Issue #65 Create Portfolio for Student validation](validation/issue-65-create-portfolio-for-student-validation.md) — exact roster identity, Profile selection, atomic setup, interface, package, and isolated-wheel acceptance evidence.
- [Issue #66 guided Candidate review and Selection validation](validation/issue-66-guided-candidate-review-selection-validation.md) — cross-workflow history, concurrency/authority negatives, menu/CLI parity, package guards, isolated Core+Vitrine wheel smoke, and complete qualification commands.
- [Issue #67 guided Working Composition validation](validation/issue-67-guided-working-composition-validation.md) — shared derivation, exact ordering/Requirement/source/Review/audience explanation, prepared concurrency/authority negatives, package guards, isolated Core+Vitrine wheel smoke, and complete qualification commands.
- [Issue #68 Build and Export Current Portfolio validation](validation/issue-68-build-export-current-portfolio-validation.md) — cross-workflow acceptance matrix, contract validator, package guards, isolated Core+Vitrine byte-bearing Export smoke, and complete repository qualification.
- [Issue #69 Attention and Next Actions validation](validation/issue-69-attention-next-actions-validation.md) — cross-workflow acceptance matrix, contract validator, package/current-release guards, isolated Core+Vitrine attention smoke, and complete repository qualification.
- [Issue #70 Suite Operations Integration validation](validation/issue-70-suite-operations-integration-validation.md) â€” Core provider/readiness/attention contract, class-scope boundary, opaque workspace relocation, package guards, isolated Core+Vitrine operations smoke, and complete repository qualification.
- [Issue #95 Teacher Information Architecture validation](validation/issue-95-teacher-information-architecture-validation.md) — acceptance matrix, display-versus-authority/read-only/privacy guards, successful-build result hierarchy, package wiring, and isolated Core+Vitrine presentation smoke.
- [Issue #96 Candidate Evidence Review validation](validation/issue-96-candidate-evidence-review-validation.md) — A-N focused acceptance, suppressed-preview privacy regression, exact preview/public-API guards, package/repository wiring, and the handoff to installed acceptance.
- [Issue #98 Guided Menu Interactions validation](validation/issue-98-guided-menu-interactions-validation.md) — controlled confirmation/cardinality acceptance, cross-menu transition coverage, package guards, isolated Core+Vitrine wheel smoke, and complete repository qualification.

- [Issue #71 live installed cross-producer acceptance validation](validation/issue-71-live-installed-cross-producer-acceptance-validation.md) — exact released-wheel authentication, live producer/Candidate/curation/Snapshot acceptance, negative currentness/authorization matrix, custody/tamper/historical verification, and producer-independent sealed verification.

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
