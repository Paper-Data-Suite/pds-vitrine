# Portfolio Foundation Audit Findings

- **Audit date:** 2026-08-06
- **Preservation rule:** Resolved findings remain in this register.
- **Machine-readable source:** [portfolio-foundation-audit.json](portfolio-foundation-audit.json)

## PF-AUD-001: The representative corpus recorded an unreachable ScoreForm commit and overstated implemented publication behavior.

- **Domain:** `cross_repository_baselines`
- **Severity:** `major`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Evidence:**
  - `docs/examples/representative-synthetic-portfolios.md`
  - `fixtures/representative-portfolios/corpus.json`
  - `fixtures/representative-portfolios/shared/producers/scoreform.json`
  - `docs/decisions/0005-producer-artifact-exposure-boundaries.md`
- **Resolution:** Replaced the invalid SHA with c2fa06f..., limited current ScoreForm behavior to immutable manifest generation, corrected the accepted producer-boundary ADR, and recorded Core publication and the Vitrine reader as future work.
- **Validation:
  - known invalid SHA absent
  - foundation validator baseline check

## PF-AUD-002: All nine load-bearing ADRs remained Proposed at the planned foundation exit.

- **Domain:** `architecture_decisions`
- **Severity:** `major`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Evidence:**
  - `docs/decisions/0001-vitrine-module-boundaries-and-authority.md`
  - `docs/decisions/0002-portfolio-subject-identity-and-roster-linking.md`
  - `docs/decisions/0003-versioned-portfolio-profiles.md`
  - `docs/decisions/0004-candidate-discovery-and-source-references.md`
  - `docs/decisions/0005-producer-artifact-exposure-boundaries.md`
  - `docs/decisions/0006-selection-ordering-annotation-and-reflection.md`
  - `docs/decisions/0007-snapshot-export-checksum-and-immutability.md`
  - `docs/decisions/0008-privacy-redaction-and-audience-controls.md`
  - `docs/decisions/0009-regulated-portfolio-and-compliance-profiles.md`
- **Resolution:** Reviewed each ADR against the final designs and corpus, accepted ADRs 0001-0009, and recorded the audit acceptance date.
- **Validation:
  - ADR headers and index agree
  - all accepted ADRs are represented in traceability

## PF-AUD-003: Documentation indexes and design status notes described the governing ADR set as Proposed.

- **Domain:** `documentation_authority`
- **Severity:** `minor`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Evidence:**
  - `docs/README.md`
  - `docs/decisions/README.md`
  - `docs/design/portfolio-subject-identity.md`
  - `docs/design/portfolio-profile-contract.md`
  - `docs/design/candidate-source-reference-contract.md`
  - `docs/design/privacy-redaction-audience-controls.md`
  - `docs/design/regulated-portfolio-compliance-profiles.md`
- **Resolution:** Reconciled index tables, authority language, and design status notes with the accepted ADR set.
- **Validation:
  - status text scan
  - ADR index/status agreement

## PF-AUD-004: The corpus did not explicitly distinguish its historical construction baseline from later audit baselines.

- **Domain:** `fixture_baselines`
- **Severity:** `minor`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Evidence:**
  - `fixtures/representative-portfolios/corpus.json`
  - `docs/examples/representative-synthetic-portfolios.md`
- **Resolution:** Added explicit historical-construction baseline policy and an audited-at Vitrine commit.
- **Validation:
  - audit manifest baseline policy check

## PF-AUD-005: The corpus validator did not provide milestone-wide ADR, traceability, findings, Markdown, or known-invalid-baseline checks.

- **Domain:** `validation`
- **Severity:** `major`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Evidence:**
  - `scripts/validate_representative_portfolios.py`
- **Resolution:** Added scripts/validate_portfolio_foundation.py and machine-readable audit metadata.
- **Validation:
  - foundation validator passes
  - representative validator invoked by foundation validator

## PF-AUD-006: Meridian advanced from typed evidence inventory to an exact adapter interface and registry after corpus construction.

- **Domain:** `meridian_boundary`
- **Severity:** `observation`
- **Status:** `closed`
- **Disposition:** `not_a_defect`
- **Evidence:**
  - current audit baseline d55432f...
- **Resolution:** Retained the valid historical corpus baseline and documented the current no-real-adapter, no-ingestion, no-grading boundary.
- **Validation:
  - current baseline recorded in audit report

## PF-AUD-007: Portia added coordinated persistence, recovery, Quarantine, and derived-index contracts after corpus construction.

- **Domain:** `portia_boundary`
- **Severity:** `observation`
- **Status:** `closed`
- **Disposition:** `not_a_defect`
- **Evidence:**
  - current audit baseline d60966f...
- **Resolution:** Confirmed that Vitrine still consumes no Portia-private state and that deny-by-default/no-leakage rules remain unchanged.
- **Validation:
  - Portia marker scan
  - audience package exclusion checks

## PF-AUD-008: Most producer-specific Vitrine readers and projections remain future implementation work.

- **Domain:** `producer_runtime`
- **Severity:** `accepted_limitation`
- **Status:** `open_nonblocking`
- **Disposition:** `accepted_limitation`
- **Evidence:**
  - producer exposure design
  - current sibling baselines
- **Resolution:** The foundation defines exact fail-closed boundaries and labels future-facing fixtures accurately; runtime readers belong to implementation milestones.
- **Validation:
  - no fixture claims executable sibling integration

## PF-AUD-009: Exact serialization, persistence, transaction, renderer, authorization-provider, and retention mechanics remain unresolved.

- **Domain:** `runtime_contracts`
- **Severity:** `accepted_limitation`
- **Status:** `open_nonblocking`
- **Disposition:** `accepted_limitation`
- **Evidence:**
  - unresolved implementation question sections in the design documents
- **Resolution:** Confirmed these questions are downstream mechanics constrained by accepted invariants and do not alter the foundation architecture.
- **Validation:
  - no unresolved question authorizes broad fallback or weakens a settled invariant

## PF-AUD-010: The New Jersey-style fixture is research-only and cannot be used as an operational or later-cohort Profile.

- **Domain:** `regulated_profiles`
- **Severity:** `observation`
- **Status:** `closed`
- **Disposition:** `not_a_defect`
- **Evidence:**
  - regulated design
  - NJ research
  - NJ-style fixture
- **Resolution:** Verified cohort binding, separate ELA/mathematics components, local-versus-batch separation, and explicit non-operational status.
- **Validation:
  - regulated fixture checks
  - documentation terminology scan

## PF-AUD-011: Vitrine does not need a new Core publication kind to close the foundation.

- **Domain:** `core_compatibility`
- **Severity:** `observation`
- **Status:** `closed`
- **Disposition:** `not_a_defect`
- **Evidence:**
  - module boundaries
  - candidate contract
  - producer exposure contract
- **Resolution:** Confirmed that Core publication identity, exact manifest binding, compatibility metadata, and the producer-owned reader/projection boundary are sufficient architectural primitives.
- **Validation:
  - traceability exit condition EC-018

## PF-AUD-012: The representative corpus passes all positive and negative integrity, path, digest, audience, and no-leakage checks.

- **Domain:** `corpus_integrity`
- **Severity:** `observation`
- **Status:** `closed`
- **Disposition:** `not_a_defect`
- **Evidence:**
  - `fixtures/representative-portfolios`
  - `scripts/validate_representative_portfolios.py`
- **Resolution:** No corpus byte or semantic correction was required beyond the ScoreForm baseline metadata and capability boundary.
- **Validation:
  - 4 portfolios, 20 entries, 20 negative cases, 39 byte files
