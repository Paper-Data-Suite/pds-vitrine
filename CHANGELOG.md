# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- Installable, typed `pds-vitrine` package baseline at `0.2.0.dev0`.
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

Vitrine now persists foundational metadata, provides Portfolio Subject and
Profile workflows, implements the producer projection adapter boundary, and
executes the first fixture-backed Core-to-Vitrine Candidate discovery/evaluation
slice. Live producer integrations, curation, Snapshot construction, recipient
authorization, export, and delivery remain future work.
