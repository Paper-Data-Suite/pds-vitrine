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

The package baseline does not yet implement Portfolio records, producer adapters,
Candidate discovery, Vitrine persistence, curation, or Snapshot construction.
