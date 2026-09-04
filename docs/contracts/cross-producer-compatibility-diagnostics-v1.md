# Cross-Producer Compatibility Diagnostics v1

- **Issue:** #62 — Build cross-producer compatibility and unsupported-contract diagnostics
- **Milestone:** v0.3.0 — Consume released producer evidence and guide real improvement/showcase portfolios
- **Status:** Implemented transient diagnostic contract
- **Diagnostic contract:** `vitrine_cross_producer_compatibility_diagnostic_v1`

## Purpose

The issue #62 diagnostic layer explains whether released ScoreForm, Quillan, and
Concord evidence can be consumed by Vitrine without weakening the authority of
Core, producer public APIs, or existing Vitrine workflow contracts.

The authoritative layers remain separate:

```text
Core producer Profile compatibility
-> exact Vitrine live support key
-> installed audited producer reader
-> separately authorized producer Artifact API when applicable
-> Vitrine Candidate / Snapshot policy
```

Diagnostics explain those layers. They do not replace them.

## Transient contract

`CrossProducerCompatibilityDiagnostic` is non-persistent. It is never serialized
as a Candidate, Selection, Snapshot, Profile, or generic Vitrine source record.

Each diagnostic preserves:

```text
diagnostic_contract_version
scope
outcome
code
stage
producer_module_id
publication_id when applicable
adapter_id when applicable
reason_codes
safe_fields
summary
next_action
```

The supported scopes are:

```text
producer_readiness
contract_support
publication_compatibility
source_read
reader
projection
artifact
fixture_boundary
```

The supported outcomes are:

```text
ready
supported
not_applicable
unsupported
not_selectable
unavailable
denied
unresolved
integrity_failed
failed
not_checked
```

## Preserve existing technical authority

When an existing subsystem owns a stable code, the diagnostic preserves it.
Examples include:

```text
contracts.manifest_version_incompatible
adapter.unsupported_contract
reader.unavailable
reader.incompatible
reader.validation_failed
source_read.authorization_denied
source_read.authorization_unresolved
source_read.manifest_missing
source_read.manifest_integrity_failed
snapshot.source_unavailable
snapshot.source_integrity_failed
```

The diagnostic may add `compatibility.*` reason codes that explain the failure,
but it must not replace the originating code with a less precise generic status.

## Exact adapter support explanation

`explain_live_adapter_support(...)` explains the existing exact live-registry
selection rule without changing `ProducerAdapterSupportKey.matches()`.

For known producers it can distinguish:

```text
Core Publication schema mismatch
publication-kind mismatch
manifest-contract mismatch
producer-contract mismatch
Publication source-record presence mismatch
source-record kind mismatch
source-record contract mismatch
missing required capabilities
```

No nearest-version selection is performed. A diagnostic may show expected and
actual contract metadata, but it never selects another adapter, falls back to v1,
or substitutes a fixture adapter.

## Frozen producer-specific semantics

### ScoreForm

A compatible live ScoreForm Publication has no Core Publication source record and
requires:

```text
multiple_attempts
points
question_evidence
```

ScoreForm has no audited consumer-neutral Artifact resolver. Artifact readiness
is therefore `not_applicable`, not a missing-provider failure.

### Quillan

A compatible live Quillan Publication deliberately has no Core Publication
source record and requires `standards_ratings`.

Quillan Academic Work Registration assignment contract `2` is registration
provenance only. It does not expand the live Publication support key.

Quillan Artifact acquisition remains separately authorized for:

```text
student_work
feedback_pdf
feedback_markdown
```

### Concord

A compatible live Concord Publication requires the exact versioned Activity
source:

```text
source_record_kind = activity
source_record_contract_version = concord_activity_v1
```

`criterion_scores` is required. `standards_ratings` and `moderated_scores` remain
optional capabilities and must not be diagnosed as missing requirements.

## Installed readiness

`diagnose_installed_producer_readiness(...)` reports each audited producer
independently across:

```text
live adapter registration
Core producer Profile discovery
reader distribution availability
reader public API readiness
Artifact API applicability/readiness
```

The operation is explicitly observational. It may discover installed Core
producer Profiles and import audited producer public modules, but it performs no
workspace read, manifest read, authorization decision, repair, or persistence.

## Package version is not semantic compatibility

The audited release versions are qualification provenance:

```text
Core      0.6.3
ScoreForm 0.11.0
Quillan   0.10.0
Concord   0.3.0
```

**Package version is not semantic compatibility.**

An installed distribution version may appear in `safe_fields` as informational
metadata. It is not an adapter-selection key. A different package version is not
itself an unsupported contract, and an expected package version never overrides
a mismatching semantic Publication contract.

Semantic compatibility continues to depend on versioned contract fields such as:

```text
Core Publication schema version
Academic Work Registration producer contract version
manifest contract version
Publication source-record contract version
```

## Canonical Publication diagnostics

`diagnose_publication_compatibility(...)` reuses Core/Vitrine canonical-state
rules before protected source access:

```text
canonical Publication reload
-> exact referenced Academic Work Registration
-> unique publication-series head / withdrawal state
-> Core evaluate_publication_compatibility(...)
-> exact Vitrine live adapter support
-> audited reader readiness
```

A historical or withdrawn Publication is explained, not silently replaced by the
current head.

## Authorized read and projection probe

`diagnose_publication_read_probe(...)` extends the metadata preflight only when a
caller explicitly supplies source-read authorization context.

The protected sequence is:

```text
metadata preflight
-> source-read authorization
-> Core manifest containment/digest verification
-> exact immutable bytes
-> audited producer public reader
-> pure selected Vitrine projection
```

The diagnostic operation uses `compatibility_source_read` rather than pretending
to be Candidate evaluation.

If authorization is denied or unresolved, the probe stops before checking whether
the protected manifest exists.

## Artifact diagnostics

`diagnose_artifact_applicability(...)` and `explain_artifact_failure(...)` map
existing Snapshot/provider failures without changing Quillan or Concord Artifact
authority.

Producer-specific stages remain visible, including authorization, producer read,
and returned-result validation. `snapshot.source_unavailable` remains distinct
from `snapshot.source_integrity_failed`.

## Privacy boundary

Safe diagnostic metadata may include producer IDs, distribution names, installed
distribution versions, adapter/reader IDs, Publication IDs, semantic contract
versions, capabilities, selectability state, and stable codes.

Diagnostics must not expose:

```text
manifest bodies or bytes
student responses or selected answers
ratings or feedback bodies
private teacher notes
producer-native filesystem paths
Core absolute manifest paths
unauthorized Artifact bytes
raw producer exception messages
```

Teacher-readable summaries and next actions are Vitrine-owned bounded strings.
Raw producer exception text is never rendered by the compatibility CLI.

## Fixture separation

The development fixture identities remain:

```text
vitrine_scoreform_fixture
vitrine_quillan_fixture
vitrine_concord_fixture
```

A fixture identity encountered on a live diagnostic path is reported with
`adapter.fixture_not_enabled` at the `fixture_boundary`. It is never remapped to
a live producer identity.
