# Released Producer Contract Audit v1

- **Issue:** #57 — Re-audit released producer contracts, verify Vitrine schema sufficiency, and freeze live adapter support keys
- **Milestone:** v0.3.0 — Consume released producer evidence and guide real improvement/showcase portfolios
- **Audit contract:** `vitrine_released_producer_contract_audit_v1`
- **Status:** frozen live-adapter planning baseline

## Purpose

Vitrine v0.2.0 deliberately shipped only Vitrine-owned development fixtures. The
ordinary adapter registry stayed empty until ScoreForm, Quillan, and Concord had
released their Phase 1 producer contracts.

Those producer releases now exist. This audit freezes the exact released artifacts,
Core compatibility envelope, public reader surfaces, artifact-access boundaries, and
Vitrine live support keys that downstream v0.3.0 adapter work must use.

The machine-readable companion is:

```text
vitrine/released_producer_contracts.py
```

That module records audited facts only. It does not register a live adapter, import a
producer package, authorize access, read a manifest, or resolve an artifact.

This document extends the fixture-era boundary defined in
[Producer Projection Adapter Boundary v1](producer-projection-adapters-v1.md). The
selection rule remains unchanged:

```text
all support-key scalar fields match exactly
AND
required_capabilities is a subset of request capabilities
```

There is no wildcard, nearest-version, distribution-version, newest-version, or
module-only fallback.

## Audited release artifacts

The release version and wheel digest are audit provenance. They identify the exact
released implementation inspected for this compatibility decision; they are not
adapter-selection fields.

| Component | Release | Wheel | SHA-256 |
|---|---|---|---|
| Core | `0.6.3` | `pds_core-0.6.3-py3-none-any.whl` | `98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5` |
| ScoreForm | `0.11.0` | `scoreform-0.11.0-py3-none-any.whl` | `8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44` |
| Quillan | `0.10.0` | `quillan-0.10.0-py3-none-any.whl` | `5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9` |
| Concord | `0.3.0` | `pds_concord-0.3.0-py3-none-any.whl` | `dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12` |

The audited producer requirements are:

```text
ScoreForm 0.11.0: pds-core>=0.6.2,<0.7
Quillan 0.10.0:   pds-core>=0.6.2,<0.7
Concord 0.3.0:    pds-core>=0.6.3,<0.7
```

Vitrine itself remains on the Core `0.6.x` compatibility line. This audit does not add
ScoreForm, Quillan, or Concord as hard Vitrine runtime dependencies.

## Public producer profile and reader boundaries

All three producers expose metadata-only Core producer Profiles through:

```text
paper_data_suite.publication_producers
```

The exact providers are:

```text
scoreform = scoreform.pds_publication:get_publication_producer_profile
quillan   = quillan.pds_publication:get_publication_producer_profile
concord   = concord.pds_publication:get_publication_producer_profile
```

The producer Profile declares compatibility metadata only. It is not a parser,
manifest-reader callback, authorization callback, workspace accessor, or producer
mutation surface.

The stable consumer-neutral manifest readers are ordinary installed package APIs:

```text
scoreform.academic_result_reader.read_academic_result_manifest
quillan.academic_result_reader.read_academic_result_manifest
concord.academic_result_reader.read_academic_result_manifest
```

Each consumes already-authorized, Core-verified immutable manifest bytes and delegates
semantic validation to the producer-owned manifest contract. Vitrine must not copy a
producer validator or interpret producer-private storage directly.

The intended live sequence remains:

```text
Core discovery
-> canonical Core reload
-> source authorization
-> Core path/digest verification
-> exact immutable manifest bytes
-> producer-owned public reader
-> producer-native public model
-> pure Vitrine projection
-> Vitrine Subject/Profile/Candidate policy
```

Installed package discovery/invocation and failure isolation belong to #58.

## Core source distinction

Academic Work Registration `source_records` and Publication Record `source_record` are
not interchangeable.

ScoreForm's registration identifies its assignment, but a compatible ScoreForm
Publication Record has no source record.

Quillan's registration identifies its assignment, but a compatible Quillan Publication
Record has no source record. Quillan registration source contract `2` must therefore
not appear in the Vitrine live adapter support key.

Concord is different: its compatible Publication Record requires the exact versioned
Activity source:

```text
module_id        = concord
record_kind      = activity
contract_version = concord_activity_v1
```

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

Concord advertises `criterion_scores`, `standards_ratings`, and `moderated_scores`, but
only `criterion_scores` is universal for a publishable v1 result manifest.
`standards_ratings` and `moderated_scores` are content-dependent capabilities.
Therefore one Concord key matches all of these valid capability sets:

```text
criterion_scores
criterion_scores + standards_ratings
criterion_scores + moderated_scores
criterion_scores + standards_ratings + moderated_scores
```

Separate overlapping Concord declarations would create an adapter conflict and are
forbidden.

## Distribution version is not semantic identity

The following values are deliberately absent from `ProducerAdapterSupportKey`:

```text
ScoreForm 0.11.0
Quillan 0.10.0
Concord 0.3.0
Core 0.6.3
wheel filename
wheel SHA-256
```

They identify the implementation audited here. They do not replace the producer,
manifest, source-record, capability, or Core publication contract namespaces.

A later package release that preserves the exact semantic contracts is not rejected
merely because its distribution version changed. Conversely, a familiar package name
or version never overrides a mismatching Core contract envelope.

Any genuinely changed producer/manifest/source contract requires an explicit future
Vitrine compatibility decision.

## Artifact access is separate from manifest support

A live manifest adapter match never implies that Vitrine may retrieve original work or
other producer artifacts.

### ScoreForm

The audited ScoreForm release exposes the pure academic-result manifest reader but no
consumer-neutral native artifact resolver comparable to Quillan or Concord.

`retained_source_path` is producer provenance metadata. It is not authorization to
open a retained scan and must not be converted into a Vitrine source locator.

Audit classification:

```text
artifact_access_mode = none
```

### Quillan

Quillan separately exposes:

```text
quillan.academic_result_artifacts
```

with closed artifact requests:

```text
student_work
feedback_pdf
feedback_markdown
```

Authorization outcomes are:

```text
allowed
denied
unresolved
```

The authorization request contains bounded manifest-derived identity and no artifact
path. Only `allowed` permits Quillan to inspect and verify native state. Quillan then
returns bounded immutable artifact bytes. `plain_paper_manual` work does not acquire a
fabricated digital artifact.

Audit classification:

```text
artifact_access_mode = producer_authorized_bytes
```

### Concord

Concord separately exposes:

```text
concord.academic_result_artifacts
```

for represented Concord-owned evidence:

```text
artifact_instance
artifact_page
```

with producer-approved representation:

```text
returned_artifact_pdf
```

The resolver accepts no arbitrary native path, filename, Scan Reference, or generic
record selector. After a separate external authorization decision, Concord binds the
read to the exact historical source snapshot and returns bounded deterministic PDF
bytes.

Audit classification:

```text
artifact_access_mode = producer_authorized_bytes
```

The current Vitrine Snapshot filesystem-source abstraction is therefore a known #57
schema hotspot. This slice records the mismatch but does not yet change Snapshot
materialization. The next schema-sufficiency slice must determine the narrowest
additive byte-returning provider contract without bypassing Quillan or Concord.

## Producer semantic crosswalk

The crosswalk below states what a live projection must preserve. It does not prescribe
one field-per-producer-field storage design; existing Vitrine extension points should
be preferred when they preserve meaning exactly.

### ScoreForm

Preserve:

- exact Core work and assignment identity;
- student identity;
- every represented attempt and exact attempt number;
- attempt origin, time, and producer provenance;
- native point totals;
- exact question identity/order;
- question standards alignment;
- response state as distinct `selected`, `blank`, or `ambiguous` state;
- selected-answer presence and native correctness evidence where policy permits;
- bounded manifest source/lineage metadata.

Do not collapse:

```text
attempt 1 != attempt 2
blank != ambiguous != selected
question alignment != producer-created standards rating
response correctness != proficiency
highest score != portfolio-worthy attempt
latest attempt != selected attempt
```

The adapter must not choose an official/latest/highest/best attempt, calculate Grade
or proficiency, infer answer keys, open retained scan paths, or infer Candidate worth.

### Quillan

Preserve:

- exact work/assignment and represented student identity;
- assignment/submission/review source snapshots;
- review-unit identity/order;
- observations and applicability/evidence state;
- overall and standard-specific native ratings;
- rating scale identity and ordinal semantics;
- standard feedback and safe published text state;
- selected PDS2 evidence references;
- review/source revision lineage needed for later authorized artifacts.

Do not collapse:

```text
absent != withheld
minimum native rating != missing rating
selected evidence != candidate evidence
selected evidence != duplicate evidence
selected evidence != excluded evidence
plain-paper work != missing digital file
native ordinal rating != percentage
native ordinal rating != Vitrine judgment
```

Private teacher notes, hidden text, unselected evidence, arbitrary routes, and other
producer-private state remain outside Vitrine projection.

### Concord

Preserve:

- Activity/work identity and scoring orientation;
- standards profile and ordered Focus Standards;
- exact Criterion Set and Criterion identity/revision;
- standard-backed versus local Criterion status;
- exact Scoring Scale revision, levels, and type-sensitive values;
- Score identity, target, disposition, value when applicable, basis, scorer/time, and
  native current/superseded state;
- Score Evidence Link and external lineage;
- Moderation status/permitted-use semantics required to interpret represented Scores;
- standards-result relationships;
- Group, Artifact, Artifact Page, Author, Subject, contribution, and represented-Group
  relationships;
- producer privacy classifications and historical source snapshot identity.

Do not collapse:

```text
Group Member != Artifact Author
Artifact Author != Artifact Subject
Artifact Author != documented contributor
Artifact Subject != Score target
Group Score != individual Score
represented Group != individual authorship
non-score disposition != numeric zero
1 != 1.0 != "1" != true
producer current Score != consumer-selected Score
```

The adapter must not normalize Concord values to percentage, letter grade, universal
proficiency, mastery, or portfolio quality.

## Vitrine schema-sufficiency status after slice 1

The released manifest-reader boundary and exact support-key model are sufficient
without changes to `ProducerAdapterSupportKey` or adapter selection.

The following existing Vitrine areas remain under active #57 audit before live adapter
implementation:

```text
CorePublicationSourceReference
ProducerSourceReference
SourceArtifactReference
SourcePrivacyMetadata
ProjectedProducerRelationship
Candidate provenance/display projection
SnapshotEntryPlan
SnapshotSourceProviderDescriptor
SnapshotSourceResult
```

Preliminary result:

- Core publication identity and support selection: **sufficient**;
- producer source/provenance extension points: **likely sufficient, verify per crosswalk**;
- privacy and relationship extension points: **likely sufficient, verify per crosswalk**;
- copied-source Snapshot acquisition: **sufficient after the narrow additive
  `SnapshotAuthorizedSourceBytesResult` runtime extension; no persisted wire-shape
  change is required**.

No generic Candidate/source model is to be redesigned merely to simplify a producer
adapter.

## Snapshot authorized-byte resolution

The released Quillan and Concord artifact APIs authorize and return bounded immutable
bytes; they do not grant Vitrine an arbitrary producer-native path selector. Issue #57
therefore extends only the Snapshot source-provider runtime boundary:

```text
filesystem-backed fixture/source provider
  -> SnapshotSourceResult
  -> exact locator + filesystem_reread_v1

producer-owned authorized artifact provider
  -> SnapshotAuthorizedSourceBytesResult
  -> exact immutable bytes + authorized_source_bytes_v1
```

The second form permits `SourceArtifactReference.source_locator=None`. Vitrine still
requires exact Publication, producer/projection, Artifact kind, representation, media
type, digest/size claims where supplied, and staged-byte verification. It does not
construct a temporary source path, reopen producer storage, or treat Snapshot build
authority as producer artifact authorization.

This resolves the only schema-sufficiency hotspot found by the released-contract audit
without redesigning Candidate, producer-source, relationship, privacy, or frozen
Snapshot record shapes. Live producer providers remain downstream work for #60 and
#61.

## Unsupported-contract behavior

A valid but unsupported support request remains:

```text
adapter.unsupported_contract
```

No fallback is allowed for:

- unknown producer module;
- wrong Core publication schema;
- wrong publication kind;
- wrong producer contract;
- wrong manifest contract;
- unexpected or missing Publication Record source;
- wrong source kind or source contract;
- missing required capability;
- development fixture presented as live identity;
- live identity presented to fixture support.

Near-future synthetic examples such as these must remain unsupported until explicitly
audited:

```text
scoreform_academic_result_manifest_v2
quillan_academic_work_v2
concord_activity_v2
Core Publication Record schema 2
```

Routine diagnostics contain contract metadata only and must not echo manifest bodies,
student data, ratings, responses, feedback, answer keys, or native filesystem paths.

## Fixture/live isolation

The development fixtures continue to use Vitrine-owned module and contract identities:

```text
vitrine_scoreform_fixture
vitrine_quillan_fixture
vitrine_concord_fixture
```

The live support catalog does not alter:

```python
build_adapter_registry()
```

The ordinary registry remains empty until the live adapter issues implement actual
reader/projector bindings. An audited support key therefore means only:

```text
Vitrine has frozen how this released contract will be selected
```

It does not mean:

```text
live adapter implemented
installed producer reader available
authorized publication selected
manifest verified
Candidate eligible
artifact authorized
portfolio disclosure authorized
```

## Downstream handoff

Issue #58 receives the frozen keys, released package identities, stable reader import
surfaces, and artifact-access classifications for installed-reader invocation and
failure isolation.

Issue #59 receives the exact ScoreForm key and semantic preservation requirements.

Issue #60 receives the exact Quillan key plus the pure-reader/separate-authorized-byte
artifact boundary.

Issue #61 receives the exact Concord key, conditional-capability policy, relationship
crosswalk, and separate authorized Artifact representation boundary.

Issue #62 receives the unsupported-contract rules and fixture/live separation needed
for cross-producer compatibility diagnostics.
