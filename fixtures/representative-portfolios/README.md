# Representative synthetic Portfolio corpus

This directory is the cross-contract fixture corpus for the Vitrine v0.1.0 foundation. It contains four coherent synthetic Portfolios, shared producer-shaped records, actual source and exported bytes, deterministic Snapshot manifests, expected outcomes, and deliberate negative cases.

The JSON shape is a development fixture contract only. It is not the final Vitrine public schema and does not imply executable integration with Core, ScoreForm, Quillan, Concord, Portia, or Meridian.

The improvement story's `improvement/runtime/*-manifest.json` files are minimal
execution descriptors for its dedicated vertical-slice validator. They publish
the existing representative bytes through the explicit
`vitrine_quillan_fixture` boundary and do not claim live Quillan integration.
The showcase story's `showcase/runtime/*-manifest.json` files likewise expose
the committed polished-work and collaborative text bytes through explicit
development-only Quillan- and Concord-shaped fixture boundaries. They are not
live producer readers or public interchange contracts.

## Portfolios

- `improvement/` — baseline and revised Quillan-shaped writing, separate feedback, student reflection, and immutable student-facing Edition.
- `showcase/` — polished writing plus a Concord-shaped Group Artifact with exact contribution and audience-safe attribution.
- `parent-conference/` — ScoreForm-shaped attempt summary, selected writing, family-safe feedback, exact Recipient Scope, and family-facing Edition.
- `nj-style-pathway/` — research-only regulated case with independent ELA/math components, local evidence, school batch, corrected resubmission, receipts, and outcome.

## Validation

From the repository root:

```powershell
python scripts/validate_representative_portfolios.py
python scripts/validate_portfolio_foundation.py
python scripts/validate_improvement_portfolio.py
python scripts/validate_showcase_portfolio.py
```

The validator uses only the Python standard library, performs no network access, imports no sibling package, mutates no fixture, and exits nonzero for any mismatch.

The corpus preserves its historical construction baselines. The issue #13 audit records current sibling baselines separately and corrects invalid or inaccurate historical references.
