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
- Portfolio Subject identity-history records, exact Core roster resolution, guarded
  cross-class linking, correction, merge, and split application services.
- Direct `vitrine subject` commands plus standardized low-density teacher menu
  workflows with H/B/M/Q navigation.

Vitrine now persists foundational metadata and provides Portfolio Subject identity
workflows, but does not yet discover live producer sources, curate artifacts, build
Snapshot bytes, authorize disclosure, or export and deliver portfolios.
