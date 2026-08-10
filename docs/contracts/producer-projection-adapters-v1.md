# Producer Projection Adapter Boundary v1

- **Issue:** #32 — Implement the producer projection adapter boundary
- **Milestone:** v0.2.0 — Runtime Foundations and Fixture-Backed Portfolio Slice
- **Status:** Operational runtime contract
- **Adapter contract:** `vitrine_fixture_adapter_v1` for issue #32 fixtures
- **Projection contract:** `vitrine_candidate_projection_v1`

## Purpose

This contract defines the boundary between already verified Core publication
metadata, exact producer readers, and transient Vitrine source projections.

```text
Core compatibility
  -> exact Vitrine adapter selection
  -> authorization                 # issue #33
  -> manifest verification         # issue #33
  -> exact producer public reader
  -> validated producer public model
  -> pure Vitrine projection
  -> Subject resolution            # issue #33
  -> Profile eligibility           # issue #33
  -> Candidate Evaluation          # issue #33
```

Issue #32 implements only adapter selection, immutable-byte reading, and pure
projection. It performs no Core catalog discovery, authorization, manifest path
or digest verification, Portfolio Subject resolution, Candidate evaluation,
persistence, Selection, or Snapshot work.

## Critical readiness statement

```text
development fixture adapter
!= installed producer integration
!= producer publication support
!= source authorization
!= Candidate eligibility
```

The ScoreForm-, Quillan-, and Concord-shaped adapters implemented by this issue
are all Vitrine development fixtures.

## Support request

`ProducerAdapterSupportRequest` is an immutable description of the exact Core
envelope metadata available before producer parsing:

```text
producer_module_id
core_publication_schema_version
publication_kind
manifest_contract_version
producer_contract_version
source_record_kind
source_record_contract_version
capabilities
```

Scalar fields match exactly. Capabilities are normalized into a deterministic
sorted tuple containing only Core publication capabilities.

`None` is exact absence, never a wildcard.

The source-record states remain distinguishable:

```text
source record absent
  source_record_kind = None
  source_record_contract_version = None

source record present and unversioned
  source_record_kind = <exact kind>
  source_record_contract_version = None

source record present and versioned
  source_record_kind = <exact kind>
  source_record_contract_version = <exact version>
```

A source-record version without a source-record kind is invalid.

## Support key

`ProducerAdapterSupportKey` contains the same exact scalar fields plus
`required_capabilities`.

An adapter matches only when:

```text
all scalar support fields match exactly
AND
required_capabilities is a subset of request capabilities
```

There is no wildcard contract, nearest version, highest version, newest version,
module-only fallback, or package-order rule.

## Adapter declaration

`ProducerProjectionAdapterDeclaration` preserves:

```text
adapter_id
adapter_contract_version
candidate_projection_contract_version
support_key
public_reader_id
reader_contract_version
reader_package_identity
supported_source_families
supported_representation_families
diagnostic_contract_version
integration_kind
```

Adapter identity is:

```text
adapter_id + adapter_contract_version
```

Support-key identity is separate from adapter identity.

## Reader boundary

`ProducerManifestReader` accepts only immutable `bytes` already obtained by the
caller.

It does not accept:

- paths;
- workspace roots;
- file handles;
- native producer directories;
- unresolved mappings.

Fixture readers require exact canonical JSON, reject duplicate keys, reject
unknown or missing fields, reject malformed primitive values, and return frozen
validated public-model objects.

The reader performs no filesystem or network access.

A future live ScoreForm adapter may delegate to ScoreForm's installed public
reader. Issue #32 does not do so and imports no sibling producer package.

## Projection boundary

`ProducerProjectionAdapter.project()` accepts only the validated public model
returned by its bound reader.

Projection is pure. It does not reopen a manifest, inspect Core or rosters,
resolve Portfolio Subjects, evaluate Profiles, authorize access, or persist
records.

The transient output is `ProducerProjectionBatch`, which preserves:

```text
adapter ID and version
reader ID and version
Vitrine projection contract version
exact support key
projected producer sources
deterministic diagnostic codes
```

Each `ProjectedProducerSource` contains:

```text
projection_kind
ProducerSourceReference
SourceArtifactReference
producer-native source relationships
SourcePrivacyMetadata
bounded display snapshot
```

The relationship value is deliberately producer-native. It is not a
`PortfolioSubjectRelationshipAssertion`. Issue #33 may create such an assertion
only after exact Portfolio Subject resolution.

## Registry

`ProducerProjectionAdapterRegistry` validates adapter/reader declaration binding,
rejects duplicate adapter identity, and canonicalizes diagnostic iteration order.

Selection outcomes are:

```text
0 matches -> adapter.unsupported_contract
1 match   -> exact adapter selected
2+ matches -> adapter.conflict
```

Conflict is never resolved by:

- insertion order;
- adapter ID order;
- package discovery order;
- version number;
- capability-count specificity;
- timestamp.

Overlapping capability claims that both match one request are conflicts.

## Ordinary versus fixture registry

`build_adapter_registry()` is the ordinary runtime construction surface. Issue
#32 performs no installed-reader discovery and the default registry is empty.

Passing a development fixture to that constructor fails with:

```text
adapter.fixture_not_enabled
```

`build_development_fixture_adapter_registry()` is the explicit test/development
surface. It contains exactly the three issue #32 fixture adapters.

## Fixture identities

Fixture selection uses Vitrine-owned identities rather than current or planned
producer publication contracts.

### ScoreForm-shaped

```text
producer_module_id: vitrine_scoreform_fixture
manifest_contract: vitrine_fixture_scoreform_manifest_v1
producer_contract: vitrine_fixture_scoreform_academic_work_v1
```

The fixture models ScoreForm's current public Academic Result Manifest semantics
while remaining unable to match the live ScoreForm contract:

```text
scoreform
scoreform_academic_work_v1
scoreform_academic_result_manifest_v1
```

It preserves exact class/assignment/student identity, every exact attempt, point
totals, attempt origin/time, response state, standard alignment, and bounded
provenance identity needed for later Vitrine policy. It does not choose an official/latest/highest attempt, calculate Grade,
proficiency, or mastery, or project answer keys, detector internals, routing data,
retained scan paths, or scan-review notes.

Projection kind:

```text
scoreform_fixture:attempt_summary
```

### Quillan-shaped

```text
producer_module_id: vitrine_quillan_fixture
manifest_contract: vitrine_fixture_quillan_manifest_v1
producer_contract: vitrine_fixture_quillan_academic_work_v1
```

Only explicitly `selected` or `approved` evidence can project as student work.
Candidate, duplicate, excluded, and unrelated-replacement evidence does not.
Only `student_facing` feedback projects. Private teacher feedback, teacher notes,
native paths, and route metadata remain absent from projection and diagnostics.

Projection kinds:

```text
quillan_fixture:student_work
quillan_fixture:student_feedback
```

No live Core 0.6 Quillan publication support is claimed.

### Concord-shaped

```text
producer_module_id: vitrine_concord_fixture
manifest_contract: vitrine_fixture_concord_manifest_v1
producer_contract: vitrine_fixture_concord_academic_work_v1
```

The fixture preserves:

```text
Group Membership != Artifact Author
Artifact Author != documented contribution
Group Score != individual Score
represented Group != individual authorship
```

A membership row produces only `group_member`. Authorship comes only from an
explicit Author row. Contribution remains separately typed. A Group-targeted
Score remains `group_score_target`; non-score dispositions do not acquire values.
No Grade, percentage, universal proficiency, or mastery is inferred.

Projection kinds:

```text
concord_fixture:artifact
concord_fixture:score_summary
```

Collaborative privacy remains multi-subject and requires later review rather than
ad hoc collaborator removal in the adapter.

## Structured failures

Stable codes include:

```text
adapter.invalid_support_request
adapter.invalid_declaration
adapter.duplicate_identity
adapter.unsupported_contract
adapter.conflict
adapter.fixture_not_enabled
reader.unavailable
reader.incompatible
reader.decode_failed
reader.validation_failed
projection.invalid_input
projection.failed
```

Failure objects contain privacy-safe contract metadata only. They never contain
manifest bodies, student names, response payloads, private notes, answer keys, or
absolute paths.

## CLI diagnostics

Power-user diagnostics are non-mutating:

```text
vitrine adapters list
vitrine adapters list --include-development-fixtures
vitrine adapters show <adapter_id> --include-development-fixtures
```

The default command reports no live adapter registrations. Fixture payloads are
never displayed. There is deliberately no teacher-facing adapter-management
menu.

## Packaging

Runtime adapter interfaces and fixture adapter implementations ship in the wheel
so explicit developer diagnostics work in an installed environment.

Synthetic JSON payloads remain repository/source-distribution assets under:

```text
fixtures/producer-adapters/
```

They are not packaged as runtime producer data in the wheel.

Vitrine retains only its Core runtime dependency and adds no ScoreForm, Quillan,
or Concord dependency or entry-point discovery.

## #33 handoff

Issue #33 receives this pure API:

```text
canonical Core publication metadata
  -> ProducerAdapterSupportRequest
  -> registry.select_adapter(...)
  -> exact adapter

verified immutable manifest bytes
  -> adapter.reader.read(...)
  -> validated producer public model
  -> adapter.project(...)
  -> ProducerProjectionBatch
```

Only then may #33 resolve exact Portfolio Subject relationships, evaluate exact
Profile policy, construct Candidate Evaluations, and persist positive Candidates.
