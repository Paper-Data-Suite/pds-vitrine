# pds-vitrine v0.4.0 — Release Candidate

**Preparation status (Issue #117): NOT PUBLISHED; NOT RELEASE-QUALIFIED.**

These notes describe the proposed v0.4.0 release. They do **not** establish that an
immutable `v0.4.0` tag, GitHub Release, official wheel, source distribution, or
fresh-download acceptance exists. The final release verdict belongs to the
[issue #117 audit](docs/v0.4.0-release-audit.md).

## What changed since v0.3.0

Vitrine remains a local-first, teacher-controlled way to curate authorized student
work into an immutable Portfolio. The post-v0.3.0 work adds and completes:

- **Paper-native student Reflection:** issue, print, route, retain, and review
  response pages through Core PDS2, with explicit student-author confirmation,
  separate adult-recorder provenance, and exact returned-paper evidence.
- **Guided teacher interactions:** retryable exact-phrase confirmation and clearer
  continuation after Candidate discovery, Selection, Placement, Profile choices,
  Composition, and Current Portfolio operations.
- **Working Composition v2:** requirement-backed Reflection content, explicit
  current/historical revision resolution, and clear separation of Reflection
  from evidence Placement.
- **Student Portfolio Presentation:** locally packaged human-readable evidence,
  offline HTML and optional PDF, safe technical/student-facing separation, exact
  source custody, verification, and presentation of reference-only material.
- **Completed Portfolio navigation:** verified edition history, safe local viewing
  and printing, historical Presentation access, updated builds, and post-build
  navigation.
- **Completion-aware Attention:** distinguish completed, update-ready, and
  actionable unfinished work instead of treating optional evidence as required.
- **Reader Contract v1 resilience:** compatible future ScoreForm, Quillan, and
  Concord releases can be consumed through their supported public reader
  contracts without a Vitrine release solely for a package-version increment.
  Unsupported/missing metadata fails closed; historical fallback stays bounded.

The last point has both fixture-backed journey coverage and an isolated installed
smoke using synthetic future-version producers (issue #104). Those synthetic
packages are **not official released producer wheels** and do not replace current
exact-release qualification.

## Installation and required runtime

```text
Distribution:       pds-vitrine 0.4.0
Import:             vitrine
Python:             >=3.11
Required dependency: pds-core>=0.6.5,<0.7
Console:            vitrine = vitrine.cli:main
```

ScoreForm, Quillan, Concord, Meridian, and Portia are **not** unconditional Vitrine
runtime dependencies. The `paper` optional extra supplies supported print/PDF
rendering libraries; do not assume base Vitrine installation has PDF tooling.

For source-checkout development, install an **authenticated Core 0.6.5 wheel**
first, then refresh Vitrine's editable metadata:

```powershell
python scripts/verify_core_wheel.py "$HOME\Downloads\pds_core-0.6.5-py3-none-any.whl"
python -m pip install "$HOME\Downloads\pds_core-0.6.5-py3-none-any.whl"
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
```

The above is a development workflow, **not a verified v0.4.0 released-wheel
installation instruction**. For actual release installation, use the official
wheel and SHA-256 authenticated during issue #117; the artifact identity remains
pending until post-merge qualification and publication.

## Compatibility boundary

Runtime producer acceptance is based on the supported Core Reader Contract v1
metadata, public reader and adapter semantics, source-read authorization, and
verified manifest bytes—not a nearest-version rule or producer wheel SHA-256.
Exact wheel filenames and hashes still govern **which released producer artifacts
were independently qualified**.

The proposed current qualification candidates are Core 0.6.5, ScoreForm 0.13.0,
Quillan 0.10.6, and Concord 0.3.1. These are not yet claimed as an authenticated
passing release matrix. See [v0.4.0 compatibility](docs/v0.4.0-release-compatibility.md).

The published Paper Data Suite launcher v0.1.0 has a separate exact-version
compatibility manifest qualifying Vitrine v0.2.0; it is **not automatically
qualified** for v0.4.0. Requalification of that Suite manifest is out of scope
for the independent Vitrine release.

## Data, privacy, and authority limits

Version promotion does not migrate or rewrite existing Portfolio records.
Candidate eligibility does not authorize Selection; Selection does not authorize
Snapshot construction or disclosure; actor attribution is not authorization.
Quillan/Concord Artifact bytes require separate producer authorization.
ScoreForm Snapshot evidence remains `reference_only`. A local Export or
Presentation is **not** external disclosure or delivery.

Vitrine does not provide institutional account authentication, guardian/recipient
identity verification, production consent/redaction, secure external delivery, or
public hosting. Release and test assets must contain no real student records.

## Qualification and publication

Issue #117 must independently pass focused and full tests, historical v0.3.0
release guards, authenticated current producer acceptance, immutable exact-main
build/hash checks, GitHub release publication, and fresh-download verification.
Until then the status is **PREPARATION — NOT RELEASED**.
