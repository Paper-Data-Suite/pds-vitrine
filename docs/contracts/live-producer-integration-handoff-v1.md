# Live Producer Integration Handoff v1

## Status

This document is the issue #57 downstream handoff for Vitrine v0.3.0.

Authoritative machine-readable contracts:

```text
vitrine.released_producer_contracts
  vitrine_released_producer_contract_audit_v1

vitrine.released_producer_schema_audit
  vitrine_released_producer_schema_audit_v1
```

Companion human-readable audits:

```text
docs/contracts/released-producer-contract-audit-v1.md
docs/contracts/released-producer-semantic-crosswalk-v1.md
docs/contracts/snapshot-build-workflows-v1.md
```

Issue #57 records the integration contract. Issues #59, #60, and #61 now
implement the completed live ScoreForm, Quillan, and Concord integrations.
After #60, `build_adapter_registry()` contains exactly those three live
declarations in deterministic identity order. Development fixtures remain
separate, and default workflow dependencies remain fail-closed rather than
auto-enabling producers.

The completed live registry is therefore:

```text
Concord + Quillan + ScoreForm
```

## Frozen release anchors

The audited release artifacts are:

| Producer | Release | Core range |
| --- | --- | --- |
| ScoreForm | 0.11.0 | `pds-core>=0.6.2,<0.7` |
| Quillan | 0.10.0 | `pds-core>=0.6.2,<0.7` |
| Concord | 0.3.0 | `pds-core>=0.6.3,<0.7` |
| Core audit baseline | 0.6.3 | n/a |

Package versions are reproducibility anchors for the audit. They are **not**
fields in semantic adapter-key identity.

A later package release remains compatible when the exact Core publication
schema, producer contract, manifest contract, Publication Record source
contract, publication kind, and required capabilities still match.

## Frozen live support keys

### ScoreForm

```text
producer_module_id              = scoreform
core_publication_schema_version = 1
publication_kind                = academic_result_set
manifest_contract_version       = scoreform_academic_result_manifest_v1
producer_contract_version       = scoreform_academic_work_v1
source_record_kind              = None
source_record_contract_version  = None
required_capabilities           = multiple_attempts
                                  points
                                  question_evidence
```

### Quillan

```text
producer_module_id              = quillan
core_publication_schema_version = 1
publication_kind                = academic_result_set
manifest_contract_version       = quillan_academic_result_manifest_v1
producer_contract_version       = quillan_academic_work_v1
source_record_kind              = None
source_record_contract_version  = None
required_capabilities           = standards_ratings
```

### Concord

```text
producer_module_id              = concord
core_publication_schema_version = 1
publication_kind                = academic_result_set
manifest_contract_version       = concord_academic_result_manifest_v1
producer_contract_version       = concord_academic_work_v1
source_record_kind              = activity
source_record_contract_version  = concord_activity_v1
required_capabilities           = criterion_scores
```

Concord `standards_ratings` and `moderated_scores` are conditional
per-publication capabilities. They must be preserved whenever represented but
must not be added to the support key's required capability set.

Exact scalar mismatch or a missing required capability is unsupported. The
stable selection failure remains:

```text
adapter.unsupported_contract
```

No distribution-version, insertion-order, package-discovery-order, or
"nearest version" fallback is permitted.

## Shared source-read sequence

All downstream live consumption starts from the same ownership sequence:

```text
Core discovery
-> canonical Core reload
-> source-read authorization
-> Core manifest path/digest verification
-> exact immutable manifest bytes
-> producer-owned public reader
-> validated producer-native public model
-> Vitrine projection
-> Candidate/Profile policy
```

Manifest authorization, producer Artifact authorization, and Vitrine Snapshot
build authority remain separate decisions.

Development fixture identities remain separate from live producer identities
and may never serve as a live fallback.

## Vitrine schema decision inherited by downstream issues

Issue #57 found the existing Candidate/source/privacy/relationship/projection
shapes sufficient.

No general persistent Candidate schema expansion is required.

The only prerequisite extensions are:

```text
copied_source_without_required_source_locator_v1
authorized_source_bytes_v1
```

`SourceArtifactReference.source_locator` may be absent when the producer owns
Artifact resolution. A live Quillan or Concord Snapshot source provider may
return `SnapshotAuthorizedSourceBytesResult` only after the producer-owned
authorization boundary has approved the exact requested Artifact.

Vitrine then independently verifies exact Publication identity, Artifact
identity, media type, digest/size claims, and the staged bytes.

Vitrine must not fabricate a temporary producer-native path to preserve the
older filesystem-provider interface.

## #58 — Installed producer-reader invocation and authorization

Issue #58 inherits:

- the three exact live `ProducerAdapterSupportKey` values above;
- exact-match selection with `adapter.unsupported_contract` for zero matches;
- conflict failure when more than one declaration matches;
- no fixture fallback;
- Core canonical reload before producer invocation;
- bounded source-read authorization before manifest bytes are exposed;
- Core manifest path/digest verification before reader invocation;
- immutable manifest bytes as the producer-reader input;
- producer semantic interpretation delegated to the producer public reader;
- sibling producer packages remaining optional rather than hard Vitrine
  dependencies;
- producer import/discovery/read failures isolated into privacy-safe Vitrine
  diagnostics.

Stable reader boundaries:

```text
scoreform.academic_result_reader.read_academic_result_manifest
quillan.academic_result_reader.read_academic_result_manifest
concord.academic_result_reader.read_academic_result_manifest
```

Issue #58 should resolve installed readers deliberately and fail closed when a
required installed reader is unavailable or incompatible. It must not copy a
producer validator into Vitrine.

Artifact APIs are not interchangeable with the manifest-reader invocation
service and remain separately authorized.

## #59 — Live ScoreForm projection adapter

Issue #59 inherits the ScoreForm support key and ScoreForm semantic crosswalk.

Required invariants include:

```text
attempt 1 != attempt 2
blank != ambiguous != selected
question alignment != standards rating
response correctness != proficiency
latest attempt != selected attempt
highest score != portfolio-worthy attempt
```

Issue #59 is implemented. Its operational contract is
[live-scoreform-projection-adapter-v1.md](live-scoreform-projection-adapter-v1.md).

The live adapter preserves exact assignment, student, attempt, question,
standards-alignment, response-state, points, and lineage evidence without:

- choosing latest/highest/best/official attempt;
- computing Grade, mastery, or proficiency;
- converting question `standard_ids` into standards ratings;
- inferring an answer key;
- inferring Candidate worth.

ScoreForm has no consumer-neutral Artifact resolver in the audited release.

```text
retained_source_path
```

remains provenance only and must never be opened by Vitrine as an inferred
Artifact capability.

## #60 — Live Quillan projection and Artifact adapter

Issue #60 inherits the Quillan support key, native-rating crosswalk, and the
separate Quillan Artifact boundary.

Issue #60 is implemented. Its operational contract is
[live-quillan-projection-artifact-adapter-v1.md](live-quillan-projection-artifact-adapter-v1.md).

Stable Artifact module:

```text
quillan.academic_result_artifacts
```

Audited request kinds:

```text
student_work
feedback_pdf
feedback_markdown
```

Authorization outcomes:

```text
allowed
denied
unresolved
```

The live projection must preserve review-unit order, applicability/evidence
states, observations, overall and standard-specific ratings, rating-scale
identity/ordinal semantics, feedback, `PublishedText` state, selected PDS2
evidence, and source/review lineage.

Required distinctions include:

```text
absent != withheld
minimum native rating != missing rating
selected evidence != candidate evidence
selected evidence != duplicate evidence
selected evidence != excluded evidence
plain-paper work != missing digital file
native ordinal rating != Vitrine judgment
```

Private teacher notes, hidden text, unselected evidence, and producer-private
paths remain outside Vitrine projection.

For Snapshot acquisition, the Quillan-owned Artifact API must authorize first.
Only `allowed` may produce immutable bytes for
`SnapshotAuthorizedSourceBytesResult`.

For `plain_paper_manual`, unavailable digital `student_work` remains
unavailable; Vitrine must not manufacture a digital Artifact.

## #61 — Live Concord projection and Artifact adapter

Issue #61 inherits the Concord support key, conditional capability rule,
type-sensitive Scale semantics, relationship crosswalk, and authorized Artifact
boundary.

Stable Artifact module:

```text
concord.academic_result_artifacts
```

Represented evidence request kinds:

```text
artifact_instance
artifact_page
```

Producer-approved representation:

```text
returned_artifact_pdf
```

The live adapter must preserve:

- Activity/work identity and scoring orientation;
- standards profile and ordered Focus Standards;
- Criterion Set/Criterion/Scale revision identity;
- standard-backed versus local Criterion status;
- ordered native Scale levels;
- type-sensitive native Scale values;
- exact Score identity, target, disposition, value, basis, scorer, and time;
- current/superseded Score state;
- Score Evidence Link and external-evidence lineage;
- Moderation identity/status/permitted-use semantics;
- standards-result relationships;
- Group, Author, Subject, contribution, recorder, and Score-target
  distinctions.

In particular:

```text
1 != 1.0 != "1" != true
Author != Subject by inference
group membership != authorship
Group Score target != individual Score target
non-score disposition != synthetic zero
```

Concord Artifact resolution remains producer-owned. Vitrine may consume
authorized immutable `returned_artifact_pdf` bytes but may not request or
reconstruct an arbitrary Concord path, filename, Scan Reference, or native
record selector.

Issue #61 is implemented. Its operational contract is
[live-concord-projection-artifact-adapter-v1.md](live-concord-projection-artifact-adapter-v1.md).
The implementation preserves every represented Score revision and Evidence Link,
uses the exact historical source snapshot for Artifact acquisition, and keeps
manifest authorization, Snapshot build authority, Concord Artifact
authorization, and disclosure authority separate.

## #62 — Compatibility and unsupported-contract diagnostics

Issue #62 inherits the exact support keys and failure boundaries rather than
inventing broader compatibility rules.

Diagnostics must distinguish, as applicable:

- missing installed reader distribution;
- incompatible installed reader/public API;
- unsupported Core/publication/manifest/producer/source-record contract;
- missing required publication capability;
- adapter conflict;
- withdrawn or non-selectable Core publication;
- manifest digest/source drift;
- source-read authorization denial or unresolved decision;
- producer Artifact authorization denial or unresolved decision;
- producer Artifact unavailability;
- fixture/live identity separation.

Diagnostics must be privacy-safe. They may identify contract versions,
producer/module identity, capability names, and bounded failure codes, but must
not expose:

- student response content;
- ratings/feedback bodies;
- answer keys;
- manifest bodies;
- producer-native filesystem paths;
- private teacher notes;
- unauthorized Artifact bytes.

A familiar package name/version is never evidence that an incompatible semantic
contract should be accepted.

## Validation contract

Repository validation now includes:

```text
python scripts/validate_released_producer_contracts.py
```

The validator freezes:

- audited release artifacts;
- exact live support keys;
- required semantic-crosswalk coverage;
- the two and only two #57 schema extensions;
- ordinary completed live-registry identity (Concord + Quillan + ScoreForm after #60);
- fixture/live identity separation;
- absence of hard ScoreForm/Quillan/Concord runtime dependencies;
- absence of eager sibling producer imports while validating #57;
- presence of the #58–#62 downstream handoff.

This validator is intentionally a contract guard. Downstream issues may extend
the integration implementation, but any deliberate change to a frozen #57
contract requires an explicit compatibility decision rather than accidental
drift.


## Issue #58 implementation status

Issue #58 is implemented.

The reusable runtime contract is documented in
`installed-producer-reader-services-v1.md`.

Implemented boundaries now available to #59-#62 are:

```text
vitrine_producer_reader_service_v1
vitrine_installed_producer_reader_v1
SourceReadAuthorizationRequest / Decision / Gate
read_verified_publication_manifest_bytes(...)
read_authorized_producer_manifest(...)
build_audited_installed_producer_reader(...)
build_audited_installed_producer_readers(...)
build_installed_producer_registry(...)
```

Reader bindings are derived only from the #57 audit, remain lazy, and do not
make package version part of semantic compatibility.

Candidate consumes the shared authorized-read operation directly. Issue #58
itself did not claim live projection support; issue #59 now supplies the exact
ScoreForm live projection declaration while preserving the same authorization
and reader boundary.

The remaining handoff is therefore narrow:

- #59 ScoreForm projection is implemented and frozen by its dedicated contract;
- #60 Quillan projection plus Quillan Artifact authorization is implemented
  and frozen by its dedicated operational contract;
- #61 Concord projection plus Concord Artifact authorization is implemented and
  frozen by its dedicated contract;
- #62 builds user-facing compatibility diagnostics over the stable failure
  distinctions.

Manifest source-read authorization, producer Artifact authorization, Snapshot
build authority, and disclosure authority remain separate.
