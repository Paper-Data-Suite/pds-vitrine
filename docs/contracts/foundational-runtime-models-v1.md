# Foundational Runtime Models v1

- **Issue:** #28
- **Milestone:** v0.2.0 — Runtime Foundations and Fixture-Backed Portfolio Slice
- **Status:** Implemented in-memory contract
- **Record schema version:** `1`

## Purpose

Vitrine's foundational runtime layer represents the immutable semantic records
needed by the improvement and showcase Portfolio slices. It provides exact
mapping conversion, strict canonical JSON, and pure relationship validation.

The layer performs no workspace discovery, persistence, producer discovery,
source-byte access, authorization, Snapshot construction, export, or delivery.

## Public package

Supported records and value objects are imported through:

```python
from vitrine.models import ...
```

`vitrine.__init__` remains lightweight. The model package has no runtime
dependency beyond released Core 0.6.

## Shared conventions

All records and embedded values use frozen, slotted dataclasses. Caller
collections are converted to immutable tuples. Identifiers use Core's public
validation, and shared producer identities use Core `ModuleWorkRef` and
`ModuleRecordRef` values.

Positive integer fields reject Boolean values. Timestamps must be timezone-aware
and serialize in UTC. Relative paths use portable POSIX syntax and reject
absolute, drive-qualified, backslash, empty, `.` and `..` components.

Initial digest support is lowercase SHA-256. Source, output, manifest,
logical-inventory, and future export digests remain separate values.

Every top-level Vitrine record contains:

```text
schema_version
record_type
```

Unknown serialized fields are rejected.

## Record families

### Portfolio identity

- `Portfolio`
- `PortfolioSubject`
- `PortfolioSubjectClassLink`
- `ClassQualifiedStudentRef`

One Portfolio references one exact Portfolio Subject. A Subject is a
workspace-local Vitrine identity anchor, not an institutional identity record.
Student identity remains qualified by school year, Core class ID, and Core
student ID. Cross-class association requires an explicit attributable Subject
link; names never create identity.

### Portfolio Profiles

- `PortfolioProfileFamily`
- `PortfolioProfileRevision`
- `PortfolioProfileBinding`
- `ProfileApplicability`
- `ProfileSectionDefinition`
- `ProfileAudienceRule`

A Profile Revision is identified by Profile ID plus positive revision. Sections
have stable IDs and explicit unique order. Audience rules define intended-use
policy, not recipients or authorization. A Binding attaches one Portfolio to one
exact Revision; changing the Revision requires another Binding.

No Profile or Binding is selected as current from its highest revision,
timestamp, or identifier.

### Source provenance

- `AcademicWorkRegistrationSnapshot`
- `CorePublicationSourceReference`
- `ProducerSourceReference`
- `SourceArtifactReference`
- `SourcePrivacyMetadata`
- `PortfolioSubjectRelationshipAssertion`

Core Publication identity, producer-native identity, source Artifact identity,
Representation identity, privacy metadata, and Portfolio Subject relationship
are separate layers.

Academic publications preserve the exact referenced registration revision and
snapshot. Intervention publications prohibit fabricated registration state.
Historical and withdrawn publications remain representable as observations.

A relationship assertion preserves explicit producer meaning such as
`artifact_author`, `artifact_subject`, `group_member`,
`documented_contributor`, `recorder`, `represented_group`,
`individual_score_target`, or `group_score_target`. These values are not
interchangeable.

### Candidates

- `CandidateAvailabilityObservation`
- `CandidateSourceEndpoint`
- `CandidateEvaluation`
- `PortfolioCandidate`

Availability is multidimensional. Publication, registration, compatibility,
reader support, manifest integrity, source authorization, Subject relationship,
Profile eligibility, and disclosure review remain separate observations.

Candidate Evaluations preserve both positive and negative outcomes. Only
`eligible` and `conditionally_eligible` Evaluations may support a positive
Candidate. A Candidate retains the exact evaluated endpoint and Portfolio,
Subject, Binding, and Profile context.

A Candidate is not a Selection, authorization grant, disclosure approval, or
claim that Vitrine created the source evidence.

### Curation

- `PortfolioSelection`
- `PortfolioPlacement`
- `PlacementPresentation`
- `SectionArrangementRevision`
- `WorkingPortfolioCompositionRevision`

Selection, Placement, ordering, and Composition are separate immutable facts.
One Selection may have several explicit Placements when the Profile permits it.
Section order is declared through an Arrangement Revision rather than creation
time. A Composition Revision is a complete working state rather than a delta.

Annotations, Reflections, approvals, and workflow services remain deferred.

### Audience Context

`AudienceContext` binds one Portfolio context to one exact Profile audience
rule. Its copied rule values must agree with the Profile Revision.

Audience Context is intended-use policy. It is not a recipient, consent,
authorization, disclosure approval, or completed review.

### Foundational Snapshot metadata

- `SnapshotMaterializationRecord`
- `SnapshotEntry`
- `SnapshotOmission`
- `SnapshotManifest`
- `SnapshotSeal`
- `SnapshotEdition`

Materialization kinds distinguish copied source bytes, Vitrine-generated bytes,
and reference-only entries. Entries have safe relative paths and explicit
section ordinals. Omissions preserve why considered content was not included.
The Manifest is the logical inventory. The Seal preserves distinct manifest and
logical-inventory digests. The Edition binds the exact Portfolio, Subject,
Profile Binding, Profile Revision, Composition Revision, Audience Context,
Manifest, and Seal.

An Edition is not an Export Artifact, issuance, delivery, or submission.
Snapshot building and digest calculation remain deferred.

## Exact conversion

Public conversion includes:

```python
record_to_dict(record)
record_from_dict(data)
graph_to_dict(graph)
graph_from_dict(data)
```

Conversion requires exact key sets, reconstructs nested immutable values, uses
Core conversion for shared references, and rejects unknown or missing keys,
wrong primitive types, Boolean integers, and nonfinite numbers.

Optional fields are emitted explicitly as JSON `null`.

## Canonical JSON

Public canonical APIs include:

```python
record_to_canonical_json_bytes(record)
record_from_json_bytes(data)
graph_to_canonical_json_bytes(graph)
graph_from_json_bytes(data)
```

Canonical bytes use:

```text
UTF-8
no BOM
two-space indentation
sorted object keys
ensure_ascii = false
nonfinite numbers prohibited
exactly one trailing LF
```

Strict decoding rejects invalid UTF-8, duplicate object keys at any depth,
malformed JSON, nonfinite constants, unsupported record types or schema
versions, and unknown fields.

## Graph validation

`VitrineRecordGraph` is the immutable aggregate used for relationship validation.

```python
collect_record_graph_issues(graph)
validate_record_graph(graph)
```

The collector returns deterministically sorted, machine-testable
`ValidationIssue` values. The validator raises `VitrineRecordGraphError` with the
complete issue tuple.

Validation covers Portfolio and Subject resolution, Profile and Binding
agreement, source relationship assertions, Evaluation and Candidate context,
Selection and Placement context, Arrangement completeness, Composition
completeness, Audience rule agreement, and Snapshot inventory and Edition
agreement.

Diagnostics are privacy-minimized and never contain source document bodies,
manifest bytes, private notes, credentials, or absolute paths.

## Canonical fixtures

Canonical privacy-safe graphs are stored at:

```text
tests/fixtures/runtime-models/
  improvement-foundational-records-v1.json
  showcase-foundational-records-v1.json
```

The improvement graph preserves baseline and later work as distinct exact source
representations and includes a generated reflection entry. It does not claim
that Vitrine calculated educational improvement.

The showcase graph preserves individual work and collaborative evidence. It
keeps Group Membership, Artifact Author, Artifact Subject, contribution,
recorder, represented Group, individual Score target, and Group Score target
separate. It uses an audience-safe collaborative representation and records an
explicit omission for the unresolved original representation.

`scripts/validate_runtime_models.py` decodes, validates, reserializes, and
requires byte-exact equality for both fixtures.

## Deferred behavior

This contract does not implement persistence, current pointers, source discovery,
producer readers, Candidate discovery services, authorization, curation
workflows, Snapshot build operations, exports, issuance, delivery, regulated
workflows, or a new CLI surface.
