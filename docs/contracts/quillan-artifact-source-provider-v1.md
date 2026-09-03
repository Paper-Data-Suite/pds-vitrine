# Quillan authorized Artifact Snapshot source provider v1

Issue #60 Slice 3 implements the runtime bridge from a frozen Vitrine Snapshot
Entry Plan to Quillan 0.10.0's public authorization-gated Artifact API.

This boundary is separate from the live semantic projection. A projected
`SourceArtifactReference` describes an Artifact capability; it does not authorize
producer I/O, prove current Artifact availability, or expose a producer path.

## Exact provider family

The provider family is:

```text
vitrine_quillan_authorized_artifact_source_provider
```

with version:

```text
vitrine_quillan_authorized_artifact_source_provider_v1
```

The Snapshot provider registry requires unique provider IDs, so the family is
instantiated as three exact descriptors:

```text
..._student_work
..._feedback_pdf
..._feedback_markdown
```

Their support keys remain exactly the Slice-0 frozen Quillan support keys.

Selected student work advertises only the released concrete media set:

```text
image/jpeg
image/png
image/tiff
```

Its immutable Plan media remains `application/octet-stream` because exact media
is unknowable before authorized producer resolution. The provider returns
`authorized_source_bytes_deferred_media_v1` with Quillan's exact concrete media.

Feedback representations remain exact before authorization:

```text
feedback_pdf      -> application/pdf
feedback_markdown -> text/markdown; charset=utf-8
```

They return `authorized_source_bytes_v1`.

## Authorization sequence

The provider enforces:

```text
immutable Snapshot Entry Plan validation
-> canonical Vitrine/Core source-context resolution
-> lazy import of quillan.academic_result_artifacts
-> Quillan producer authorization request
-> Vitrine deployment authorization bridge
-> explicit allowed decision
-> Quillan native verification and Artifact read
-> Vitrine returned-result verification
-> SnapshotAuthorizedSourceBytesResult
```

Snapshot build authority is not Quillan Artifact authorization. Manifest-read
authorization is not Quillan Artifact authorization. Only an explicit `allowed`
Artifact decision is translated to Quillan's producer gate.

A deployment decision is scoped to the immutable Vitrine source. It includes the
Snapshot plan/attempt identity, Publication identity, opaque source Artifact ID,
student ID, Artifact request kind, purpose, and—only for selected student
work—the exact public `evidence_id`.

The producer request contains no Vitrine-invented native path. Vitrine does not
read or reconstruct `submission.json`, `review.json`, routed-evidence paths, or
feedback export paths.

Gate exceptions, invalid decisions, and `unresolved` decisions are translated to
producer `unresolved`. `denied` remains denied. In every non-allowed case,
Quillan's public API fails before producer-native I/O.

## Selected student-work tuple

Quillan's released API authorizes `student_work` at student scope and returns all
represented selected student-work Artifacts for that student. Vitrine therefore:

1. validates the planned opaque source ID against the exact public `evidence_id`;
2. confirms that evidence is represented in the published StudentResult;
3. invokes Quillan's student-level public Artifact operation;
4. verifies every returned result's work, record-set revision, student, kind,
   immutable bytes, size, and SHA-256;
5. selects exactly one result whose public `EvidenceReference` equals the planned
   reference;
6. requires its SHA-256 to equal the public `routed_evidence_sha256`;
7. requires its concrete media type to be one of the frozen released media types.

No returned `relative_path` is reopened by Vitrine.

Plain-paper results cannot satisfy this selected-work context because they have
no represented digital evidence reference. They fail before Quillan import/I/O
rather than gaining fabricated digital work.

## Feedback results

PDF and Markdown remain separate exact request kinds. The provider requires one
returned result of the requested kind, exact work/revision/student identity, the
exact frozen media type, immutable bytes, valid byte size, and valid SHA-256.

A projected feedback capability does not guarantee that an export exists. Final
availability remains Quillan-owned and is checked only after authorization.

## Failure model

Expected failures use the existing Snapshot materialization codes:

```text
snapshot.invalid_request
snapshot.source_unavailable
snapshot.source_integrity_failed
```

Authorization denial/unresolved is `source_unavailable`. Historical manifest or
native-source drift reported by Quillan is `source_integrity_failed`. Returned
bytes or identity that disagree with the immutable public source also fail
integrity verification.

## Production canonical context

Slice 4 adds the production source-context resolver used before the provider may
invoke Quillan's Artifact API. The resolver revalidates the immutable Snapshot
Entry against canonical Vitrine and Core state in this order:

```text
Snapshot Entry Plan
-> Candidate Evaluation / Candidate / explicit Selection / Placement
-> frozen Core Publication reference
-> canonical Core Publication and withdrawal state
-> exact Academic Work Registration revision
-> live Quillan Publication/Registration contract
-> separate manifest source-read authorization
-> Core manifest digest verification
-> audited installed Quillan public reader
-> live Quillan reprojection
-> exact Candidate source reproduction
-> QuillanArtifactSourceContext
```

The Core Publication remains intentionally source-record-free for live adapter
selection. The resolver separately verifies the frozen Academic Work
Registration's one Quillan assignment source at contract `2`; this is registration
provenance and is not added to `QUILLAN_LIVE_SUPPORT_KEY`.

For selected work, exact reprojection must reproduce one represented
`submission_subject` relationship and one public selected `EvidenceReference`
whose deterministic opaque Vitrine source identity equals the frozen Candidate
Artifact ID. The resulting context carries the exact public `evidence_id` but no
producer-native path.

For feedback, exact reprojection must reproduce the requested PDF or Markdown
capability identity. The context still makes no claim that the export currently
exists; availability remains producer-owned after separate Artifact
authorization.

Snapshot build authority, manifest source-read authorization, and Quillan
Artifact authorization remain three independent decisions. A withdrawn or drifted
Publication, registration mismatch, manifest-read denial, or reprojection mismatch
fails before Artifact authorization and producer-native I/O.
