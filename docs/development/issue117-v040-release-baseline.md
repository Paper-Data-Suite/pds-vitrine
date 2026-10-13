# Issue #117 — v0.4.0 release baseline and historical preservation

Status: **Release preparation only — not yet qualified or published**.

- Starting merged `main` commit: `95f29168f8b72007b606433da905a09faea3ca07`
- Starting Git tree SHA: `eb08c974d9af0ed72918416178e75332dbba13bd`
- Branch: `release/v0.4.0`
- Previous published release: `v0.3.0` (**RELEASED — VERIFIED**)
- Source version on entry: `0.3.0`
- Target: `v0.4.0`; current Core dependency: `pds-core>=0.6.5,<0.7`
- Issue #104 / PR #116: merged into this starting commit

## Frozen historical evidence

The SHA-256 inventory in `issue117-v040-release-baseline.json` protects
existing v0.3.0 audit documents and exact #71 replay contracts.
These records remain historical qualifications, not authority to change
v0.4.0 runtime compatibility or authenticate a future wheel.

## Release transition plan

1. Separate active version checks from frozen release assertions.
2. Promote version/tests to `0.4.0`; keep historic evidence frozen.
3. Add current v0.4.0 release records and current published-producer
   wheel acceptance with Core v0.6.5; avoid release coupling.
4. Qualify preparation PR; merge, then qualify exact clean `main`.
5. Publish immutable assets; verify fresh downloaded bytes.

## Boundaries

The Suite v0.1.0 exact manifest still qualifies Vitrine v0.2.0;
requalification belongs to a separate Suite integration issue.
Do not update Core, ScoreForm, Quillan, Concord, Meridian, or Portia
solely because Vitrine's package version changes.

A synthetic future-producer test is **not** authentic qualification
of a released producer wheel. No v0.4.0 wheel, tag, or GitHub Release
has been approved or published by this baseline slice.
