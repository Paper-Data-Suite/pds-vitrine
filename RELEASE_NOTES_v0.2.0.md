# pds-vitrine v0.2.0

Vitrine v0.2.0 is the first executable runtime release of the Paper Data Suite
portfolio module. It implements the audited v0.1 architecture for local,
fixture-backed Improvement and Showcase Portfolio workflows while preserving Core,
producer, grading, privacy, and immutable-custody boundaries.

Publication of these notes does not by itself authenticate a release asset. The
GitHub Release process must use the exact post-merge qualified wheel, sdist, and
`SHA256SUMS.txt`, followed by fresh-download verification.

## Runtime compatibility

```text
Python >=3.11
pds-core>=0.6,<0.7
```

Authoritative Core qualification artifact:

```text
pds_core-0.6.0-py3-none-any.whl
SHA-256:
be28c061b38463ef59ebc328ed1aa443767fe7f2c626babb769c2d8e5932f308
```

Vitrine declares only the `vitrine` console script. It does not declare
`paper_data_suite.modules` or `paper_data_suite.publication_producers` entry points,
and it has no unconditional runtime dependency on ScoreForm, Quillan, Concord,
Portia, or Meridian.

## What v0.2.0 provides

- Immutable foundational Portfolio, Portfolio Subject, Profile, Candidate,
  curation, Audience Context, and Snapshot records with exact canonical JSON.
- Guarded workspace-scoped canonical persistence, historical loading, explicit
  current pointers, expected-revision protection, diagnostics, and rebuildable
  derived indexes.
- Exact cross-class Portfolio Subject linking and correction/merge/split history.
- Immutable Profile revisions and exact Profile Bindings for the implemented
  Improvement and Showcase workflows.
- Explicit producer projection adapter contracts and deterministic adapter
  selection with structured fail-closed unsupported states.
- Core-backed Candidate discovery/evaluation using canonical Publication reload,
  exact manifest verification, and explicit source-read authorization.
- Proposal/Decision/Selection, Placement/Arrangement, Annotation, Reflection,
  Curation Review, and immutable Working Portfolio Composition workflows.
- Snapshot Series, Build Request, immutable Build Plan, Build Attempt, guarded
  materialization, deterministic Manifest/Seal, immutable Edition, explicit
  current pointer, and independently verified directory Export Artifact custody.
- Shared direct CLI and low-density teacher-facing workflows using the same
  application services and dependency context.
- Installed end-to-end acceptance from noneditable Vitrine/Core wheels, including
  source drift/removal, fresh-process historical reload, package/source write
  isolation, and a discriminating Current Edition pointer proof.

## Fixture-backed producer boundary

Vitrine v0.2.0 intentionally uses Vitrine-owned synthetic producer-shaped fixtures:

```text
vitrine_scoreform_fixture
vitrine_quillan_fixture
vitrine_concord_fixture
```

These are synthetic projections shaped to exercise reviewed producer semantics;
they are **not live producer integrations** and they do not masquerade as current
ScoreForm, Quillan, or Concord publication contracts.

The installed acceptance explicitly proves that live-contract-shaped support
requests cannot select these fixture adapters and that Core installed-producer
discovery does not expose Vitrine fixture identities.

## Important semantic boundaries

Vitrine v0.2.0 preserves, among others:

```text
Portfolio != Portfolio Subject
Candidate != Selection
Selection != Placement
Selection != disclosure authorization
Audience Context != Recipient Scope or consent
Group Membership != Artifact Author
Artifact Author != Artifact Subject
Group Score != individual Score
Composition != Snapshot
Build Request != Build Plan != Build Attempt != Edition
logical Edition != Export Artifact
Current Edition != greatest Edition number
```

ScoreForm-shaped attempts remain separate attempts; Vitrine does not choose the
latest, highest, best, official, Grade-bearing, or proficiency-bearing attempt.
Standards alignment is not converted into proficiency or mastery.

## Deliberately deferred

This release does not provide:

- live installed ScoreForm, Quillan, or Concord integration;
- production institutional authentication or authorization;
- recipient/guardian relationship verification or consent management;
- production redaction/de-identification or disclosure-event infrastructure;
- secure delivery, public hosting, or external submission automation;
- operational Parent/Guardian Conference or regulated Portfolio workflows;
- Meridian grading/proficiency policy or Grade calculation;
- ordinary Portia Portfolio exposure;
- or suite-wide archival/disposition orchestration.

Those surfaces remain follow-on work and are not release defects in v0.2.0.

## Qualification

The authoritative repository gate is:

```text
python scripts/validate_repository.py --core-wheel <authenticated-core-wheel>
```

The gate runs the full test/static-analysis/runtime-validation sequence once,
builds and checks the distributions, runs five narrow installed-wheel smokes, and
then runs the installed end-to-end acceptance exactly once. Final release
publication additionally requires exact-main qualification, final artifact hashes,
GitHub Release publication, and independent fresh-download verification.
