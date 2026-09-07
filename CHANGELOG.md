# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- Create Portfolio for Student guided setup with exact Core roster selection,
  explicit cross-class Subject association, exact Improvement/Showcase Profile
  Revision choice, read-only planning, and one guarded atomic setup commit.
- Teacher menu and noninteractive `vitrine portfolio create-for-student`
  workflow with fully resolved `--dry-run`, dedicated validation, package
  guards, and isolated Core+Vitrine installed-wheel acceptance.
- Teacher Candidate Inbox with explicit append-preserving current-Evaluation
  pointers, workspace-wide positive/negative review, suppression-safe counts,
  bounded stale/attention signals, observational Selection state, and exact
  Profile/Core/producer/Artifact/Subject provenance.
- Read-only `vitrine candidate inbox` list/detail CLI, top-level Candidate Inbox
  teacher menu, Portfolio-filtered reuse, dedicated validation, package guards,
  and isolated Core+Vitrine installed-wheel acceptance.
- Optional packaged Improvement and Showcase starter Portfolio Profiles
  with deterministic Vitrine-authored policy, read-only validation/planning,
  explicit atomic activation, idempotent exact reuse, and no hidden purpose
  behavior or sibling producer dependency.
- Direct `vitrine profile starter` list/show/validate/plan/install commands,
  low-density teacher review/confirmation workflows, dedicated validation,
  package-content enforcement, and isolated Core+Vitrine wheel acceptance.
- Versioned transient cross-producer compatibility diagnostics for released
  ScoreForm, Quillan, and Concord integrations.
- Read-only installed producer readiness, exact semantic support explanation,
  canonical Publication preflight, and authorization-gated read/projection probes.
- Producer Artifact diagnostic mapping that preserves Snapshot failure codes while
  keeping ScoreForm Artifact readiness explicitly not applicable.
- Direct `vitrine compatibility` CLI commands, reusable repository validation,
  isolated wheel smoke coverage, and exact released-wheel readiness qualification.

## 0.2.0 - 2026-08-17

### Added

- First installable, typed `pds-vitrine` runtime release at `0.2.0`.
- Required `pds-core>=0.6,<0.7` runtime dependency.
- Side-effect-free help and version commands.
- Minimal teacher-facing menu and thin Core-owned workspace wrappers.
- Strict typing, linting, tests, cross-platform CI, distribution checks, and
  isolated installed-wheel smoke testing.
- Exact authentication tooling for the official Core v0.6.0 wheel.
- Immutable foundational Portfolio, Subject, Profile, source, Candidate,
  curation, audience, and Snapshot metadata models.
- Exact mapping conversion, strict canonical JSON, deterministic graph
  diagnostics, and canonical improvement and showcase runtime fixtures.
- Workspace-scoped canonical JSON persistence with immutable state revisions,
  explicit current selection, expected-revision protection, and strict loading.
- Deterministic storage diagnostics, conservative lock/partial-success handling,
  and a rebuildable nonauthoritative SQLite catalog.
- Portfolio Subject identity-history records, exact Core roster resolution,
  guarded cross-class linking, correction, merge, and split application services.
- Direct `vitrine subject` commands plus standardized low-density teacher menu
  workflows with H/B/M/Q navigation.
- Versioned Portfolio Profile services with explicit activation, exact Binding,
  stable Requirement identity, local overlays, explicit migration, direct CLI,
  teacher workflows, and validation.
- Exact immutable producer adapter support requests/keys, reader descriptors,
  declarations, transient source projections, structured failures, and a
  deterministic conflict-detecting registry.
- Explicit ScoreForm-, Quillan-, and Concord-shaped development fixture readers
  and adapters using Vitrine-owned fixture identities rather than live producer
  contracts.
- Non-mutating `vitrine adapters` diagnostics that exclude development fixtures
  unless explicitly requested.
- Producer-adapter fixture validation and isolated installed-wheel adapter smoke
  proving no ScoreForm, Quillan, or Concord runtime dependency is required.
- Core-backed fixture Candidate discovery/evaluation with bounded catalog use,
  canonical Publication/registration reload, explicit source-read authorization,
  exact manifest-byte verification, Subject/Profile evaluation, and guarded
  Evaluation/Candidate persistence.
- Explicit Vitrine-owned Core compatibility Profiles for ScoreForm-, Quillan-,
  and Concord-shaped development fixtures, plus Candidate discovery validation
  and isolated Candidate-service wheel smoke.
- Explicit Proposal/Decision/Selection curation workflows with injected
  curation-authority decisions and append-preserving Selection lifecycle.
- Guarded Placement, complete section Arrangement revisions, immutable
  Arrangement pointer history, curator Presentation replacement, revisioned
  Annotation and student Reflection, exact Curation Review Decisions, and
  nondestructive withdrawal/replacement behavior.
- Immutable Working Portfolio Composition creation plus one-to-one curation
  inventory and explicit Composition pointer revisions, preserving unresolved
  obligations without implying disclosure or Snapshot authority.
- Dedicated curation-state validation, fixture-backed curation workflow
  acceptance, and isolated installed-wheel curation smoke testing.
- Additive immutable Snapshot Series, Build Request, Plan, Attempt/Result,
  materialization provenance, Edition build provenance, directory Export, and
  current-pointer workflow records without changing frozen issue #28 Snapshot
  serialization.
- Dedicated Snapshot state projection and validation integrated with canonical
  guarded persistence.
- Safe Snapshot custody with portable relative-path policy, Unicode/case-fold
  collision rejection, exclusive staging, immutable Edition/Export roots, and
  privacy-minimal Series build locks that are never cleared by age.
- Explicit local Snapshot build authority, exact producer-source provider
  selection, deterministic renderer selection, exact-byte acquisition, staged
  output re-verification, independent SHA-256 layers, and source-stability
  checks.
- Immutable Build Plans that freeze exact Composition, curation, producer source,
  renderer, output-path, Review, obligation, and Export decisions with
  deterministic SHA-256 Plan fingerprints.
- Complete Attempt execution with explicit per-item dispositions, permitted
  source-backed Omissions, fail-closed blocking history, and explicit
  interrupted-Attempt recovery.
- Deterministic internal Snapshot Manifest bytes, independent logical-inventory
  hashing, final pre-seal verification, immutable Snapshot Seal/Edition
  publication, and partial-success/uncertain-durability preservation.
- Producer-independent historical Edition verification and independently
  verified `directory_package` Export Artifacts with deterministic directory
  inventory hashes and exact immutable replay.
- Explicit conflict-aware Snapshot current-Edition pointer revisions separate
  from sealing and Export creation.
- Development-only Snapshot acceptance fixtures covering copied Quillan-shaped
  student work and student-facing feedback, rendered structured ScoreForm-shaped
  attempt data, generated exact student Reflection, permitted Omission, blocking
  failure, sealed Edition, and verified directory Export.
- Dedicated Snapshot workflow validator, locked issue #28 fixture-hash checks,
  Snapshot runtime/development contracts, and isolated installed-wheel Snapshot
  smoke testing without sibling producer packages.
- Executable representative improvement Portfolio vertical slice spanning exact
  cross-class Subject links, Profile-bound Quillan-shaped fixture discovery,
  three explicit Selections, deterministic Arrangement, student comparison
  Reflection, immutable Composition, four-entry Snapshot/Export verification,
  and byte-for-byte source-drift immutability evidence.
- Executable representative showcase Portfolio vertical slice spanning exact
  Subject/Profile services, Quillan- and Concord-shaped Candidate discovery,
  distinct Group/Author/Subject/contribution/Score targets, explicit conditional
  Selection and collaborator-treatment review, immutable Composition, five-entry
  audience-safe Snapshot, reproducible directory Export, and producer-independent
  historical verification.
- Shared Portfolio-centered direct CLI and low-density teacher-facing workflows
  backed by one explicit fail-closed `VitrineWorkflowDependencies` context.
- Installed end-to-end acceptance from noneditable Vitrine/Core wheels covering
  exact cross-class Subject identity, fixture/live non-masquerading, Core-backed
  publication/discovery, Improvement and Showcase curation/Snapshots, actual
  Export privacy scanning, source drift/removal, fresh-process historical reload,
  discriminating Current Edition pointer resolution, and checkout/package write
  isolation.

Vitrine now persists foundational metadata, provides Portfolio Subject and
Profile workflows, implements the producer projection adapter boundary, executes
fixture-backed Core-to-Vitrine Candidate discovery/evaluation, supports explicit
byte-free working-Portfolio curation through immutable Composition revisions,
and can execute one exact Composition through verified immutable Snapshot
Edition and directory Export custody.

Live producer integrations, recipient/disclosure authorization, Issuance,
Submission, delivery, grading policy, and public hosting remain future work.
