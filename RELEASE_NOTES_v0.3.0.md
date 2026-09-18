# pds-vitrine v0.3.0

Vitrine v0.3.0 moves the portfolio workflow from fixture-backed producer exercises to
released ScoreForm, Quillan, and Concord evidence while keeping Vitrine local-first,
teacher-controlled, provenance-preserving, and Core-only as an installed runtime
dependency.

These notes describe the v0.3.0 release candidate during release preparation. They do
not by themselves establish that a `v0.3.0` tag or GitHub Release has been published.
Publication requires exact-main qualification, immutable release artifacts, and
fresh-download verification.

## Teacher-facing value

Through explicit Vitrine workflows, a teacher can now:

- work from released ScoreForm 0.11.0, Quillan 0.10.0, and Concord 0.3.0 evidence;
- review a Candidate inbox without silently selecting evidence;
- create a Portfolio for one exact student identity and choose packaged Improvement
  or Showcase Profile policy;
- review, select, place, annotate, reflect on, and review evidence through explicit
  curation records;
- prepare an exact Working Portfolio Composition;
- build and verify a local immutable Portfolio Edition;
- create and independently verify a local `directory_package` Export;
- review bounded Vitrine attention and next-action summaries; and
- participate in the released Core module-operations boundary used by suite
  doctor/launcher/backup/attention workflows.

Vitrine does not rank attempts or silently choose the newest, highest, or "best"
evidence. ScoreForm attempts remain separate attempts. Producer standards/rating
evidence is not converted by Vitrine into proficiency, mastery, or a Grade.

## Runtime compatibility

```text
Python >=3.11
pds-core>=0.6.3,<0.7
```

Vitrine declares:

```text
console:
  vitrine = vitrine.cli:main

Core module operations:
  paper_data_suite.module_operations
    vitrine = vitrine.pds_operations:get_module_operations_profile
```

It does **not** declare `paper_data_suite.modules` or
`paper_data_suite.publication_producers`, and it has no unconditional runtime
dependency on ScoreForm, Quillan, Concord, Portia, or Meridian.

## Exact producer qualification anchors

The release audit reuses the exact released artifacts authenticated by issues #57
and #71:

```text
pds-core 0.6.3
pds_core-0.6.3-py3-none-any.whl
SHA-256 98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5

ScoreForm 0.11.0
scoreform-0.11.0-py3-none-any.whl
SHA-256 8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44

Quillan 0.10.0
quillan-0.10.0-py3-none-any.whl
SHA-256 5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9

Concord 0.3.0
pds_concord-0.3.0-py3-none-any.whl
SHA-256 dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12
```

Package versions are qualification anchors, not compatibility heuristics. Runtime
adapter selection still uses the exact released semantic support keys and never
falls back to a nearest/latest/best producer contract.

## Privacy and authorization boundary

Vitrine v0.3.0 consumes producer evidence only through public released boundaries.
The accepted source-read sequence remains:

```text
Core discovery
-> canonical Publication reload
-> canonical producer registration
-> series / withdrawal state
-> compatibility
-> source-read authorization
-> Core path/digest verification
-> immutable manifest bytes
-> installed public producer reader
-> pure Vitrine projection
```

Quillan and Concord source bytes require a **separate** producer Artifact
authorization before copied-source materialization. ScoreForm remains
`reference_only` for Snapshot materialization and Vitrine does not invent a
ScoreForm Artifact-byte API.

The following remain separate decisions:

```text
Candidate eligibility != Selection authority
actor attribution != authorization
Selection != Snapshot build authority
Snapshot build authority != disclosure authorization
Audience Context != recipient identity / relationship / consent
local Export != external delivery
```

Vitrine v0.3.0 does not implement production institutional authentication,
recipient/guardian relationship verification, consent management, production
redaction/de-identification, disclosure authorization, secure delivery, public
hosting, or external submission.

## Immutable custody

A successful local build freezes exact curation and source provenance into Vitrine
custody. Issue #71 acceptance proves:

- currentness drift and exact-source drift/removal fail closed;
- denied/unresolved source and Artifact authorization does not cross protected
  persistence/materialization boundaries;
- Export tampering is detected;
- exact historical state reload works;
- sealed Edition/Export verification remains valid after producer source roots
  disappear; and
- a Core+Vitrine-only verifier can independently verify sealed custody without
  importing producer packages.

A Vitrine `directory_package` Export is a verified local artifact. It is not a
claim that the Portfolio was sent, shared, submitted, delivered, published, or
authorized for disclosure.

## Release qualification

The release remains open through all four ceremony phases:

```text
1. release-preparation branch and PR qualification
2. post-merge exact-main qualification
3. immutable tag and GitHub Release publication
4. fresh-download post-release verification
```

See `docs/release_checklist.md` for the authoritative ceremony.
