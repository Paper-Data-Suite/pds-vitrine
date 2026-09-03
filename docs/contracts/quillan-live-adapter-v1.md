# Quillan Live Adapter v1

## Status

Issue #60, Slices 0-2 live Quillan projection contract for Vitrine v0.3.0.

Slice 0 reconciles Vitrine's post-#61 Snapshot runtime with released Quillan
0.10.0. Slice 1 adds the pure live Quillan review-summary projection. Slice 2
adds selected-evidence and feedback Artifact capabilities while keeping all
Artifact authorization and Artifact I/O outside the projection adapter.

## Released boundary

The supported producer baseline is Quillan 0.10.0 using:

```text
quillan_academic_result_manifest_v1
quillan_academic_work_v1
required capability: standards_ratings
```

Vitrine may use Quillan's public Academic Result reader for manifest semantics.
Artifact bytes remain behind Quillan's public authorization-gated Artifact API.
A manifest path, digest, Candidate selection, or Snapshot build-authority decision
is never Artifact authorization.

## Frozen representation identities

```text
review summary
  representation: quillan:review_summary
  artifact kind: assessment_summary

selected student work
  representation: quillan:selected_student_work
  artifact kind: original_student_work

feedback PDF
  representation: quillan:feedback_pdf
  artifact kind: rendered_feedback

feedback Markdown
  representation: quillan:feedback_markdown
  artifact kind: rendered_feedback
```

The live Candidate projection contract used by these representations is:

```text
vitrine_candidate_projection_v1
```

## Student-work media strategy

Released Quillan does not expose the routed-evidence filename, suffix, or MIME in
the public Academic Result manifest. After a deployment-owned authorization gate
allows the exact `student_work` request, Quillan may resolve the selected evidence
to exactly one of:

```text
image/jpeg
image/png
image/tiff
```

Vitrine therefore must not guess PNG, infer a suffix from an evidence ID or
digest, inspect native Quillan state before authorization, or label bytes with a
MIME type that was not returned by the producer API.

For an immutable Build Plan, selected Quillan student work uses:

```text
SourceArtifactReference.media_type = application/octet-stream
SnapshotEntryPlan.media_type       = application/octet-stream
```

`application/octet-stream` here means only that exact media is deliberately not
knowable at planning time. It is not a wildcard match and is never treated as the
sealed Entry's final MIME type.

The target Snapshot path must be suffix-neutral because a suffix would assert a
representation before authorization. Example:

```text
evidence/quillan-evidence-<opaque-id>
```

After authorization and producer-native verification, Vitrine accepts the exact
returned MIME only through:

```text
authorized_source_bytes_deferred_media_v1
```

The selected Snapshot source provider must declare a nonempty closed concrete
MIME allowlist. For Quillan selected student work that allowlist is exactly the
three image media types above. Returned bytes are rejected when the concrete MIME
is outside that list.

The acquired MIME is carried with the copied-byte runtime result and becomes the
existing persisted `SnapshotEntry.media_type`. The internal Snapshot manifest and
logical inventory also use that concrete MIME. The immutable Plan and source
Artifact continue to preserve their honest `application/octet-stream` planning
claim, so historical replay can distinguish what was knowable before
authorization from what Quillan established during authorized acquisition.

This requires no persistent Snapshot record-shape change.

## Existing authorized-byte behavior remains strict

The preexisting contract remains:

```text
authorized_source_bytes_v1
```

It still requires exact equality among:

```text
provider-returned media type
SnapshotEntryPlan.media_type
SourceArtifactReference.media_type
```

ScoreForm, Concord, filesystem providers, generated Vitrine Entries, and existing
historical Snapshot records are not weakened by the deferred-media extension.

## Frozen source-provider support keys

Recommended Quillan Artifact provider family:

```text
vitrine_quillan_authorized_artifact_source_provider
vitrine_quillan_authorized_artifact_source_provider_v1
```

Provider selection remains exact over:

```text
producer_module_id
projection_kind
projection_contract_version
artifact_kind
representation_kind
```

The frozen support keys are:

```text
selected student work
  quillan
  quillan:selected_student_work
  vitrine_candidate_projection_v1
  original_student_work
  quillan:selected_student_work

feedback PDF
  quillan
  quillan:feedback_pdf
  vitrine_candidate_projection_v1
  rendered_feedback
  quillan:feedback_pdf

feedback Markdown
  quillan
  quillan:feedback_markdown
  vitrine_candidate_projection_v1
  rendered_feedback
  quillan:feedback_markdown
```

Feedback media is already exact in released Quillan's public Artifact API:

```text
feedback_pdf      -> application/pdf
feedback_markdown -> text/markdown; charset=utf-8
```

Those representations therefore continue to use `authorized_source_bytes_v1`;
the deferred-media contract is only for selected student work.

## Deterministic Vitrine-owned source identity

Quillan does not expose a standalone Core record ID for every projected
review/evidence/feedback source. Vitrine-owned source IDs use the prefixes:

```text
quillan_review_<64 lowercase hex>
quillan_evidence_<64 lowercase hex>
quillan_feedback_<64 lowercase hex>
```

The digest construction is `vitrine_quillan_source_identity_v1`:

1. encode every identity field as UTF-8;
2. prepend each field with its unsigned 8-byte big-endian byte length;
3. concatenate the length-delimited fields in the fixed semantic order;
4. SHA-256 the concatenation;
5. append the lowercase hexadecimal digest to the source-kind prefix.

Every identity begins with the contract marker and `quillan`, then includes:

```text
class_id
work_id
student_id
projection/source kind
producer-native evidence ID or Artifact request kind when applicable
```

Thus native paths, display names, timestamps, filesystem enumeration, and mutable
current state never become identity authority.

## Live review-summary projection

Slice 1 registers `vitrine_quillan_live_adapter` against the exact frozen
`QUILLAN_LIVE_SUPPORT_KEY` and the installed audited Quillan reader. Importing
the adapter or listing it does not import Quillan; the producer contract module
is resolved lazily only when an already validated public model is projected.

Exactly one `quillan:review_summary` source is emitted for every represented
Quillan `StudentResult`. The source uses a Vitrine-owned opaque review identity,
an `assessment_summary` logical Artifact, and this Vitrine media type:

```text
application/vnd.pds.vitrine.quillan-review-summary+json
```

The logical summary has no producer `source_locator`, byte digest, or byte size.
It is not an Artifact-capability claim and causes no producer filesystem access.
The source carries one exact `core_student` / `submission_subject` relationship
and single-subject student-record privacy metadata.

The projection preserves the public Quillan semantics needed by later Candidate
and portfolio work, including:

- manifest, record-set, work, assignment, submission, and source-snapshot
  provenance;
- exact review and minimum-requirement states;
- assignment review-unit definition, basic requirements, and minimum-requirement
  policy;
- native rating-scale ID, level values, labels, descriptions, and ordering;
- Review Unit ordering;
- observation applicability, `evidence_present` nullability, native rating
  nullability, rationale state, feedback-inclusion flags, and timestamps;
- overall native standard ratings without percentage/Grade/proficiency/mastery
  conversion;
- all three `PublishedText` dispositions (`absent`, `withheld`, `included`) and
  exact included public text;
- standard-feedback inclusion metadata and public comments;
- PDS2 submission identity/provenance metadata excluding selected
  `EvidenceReference` records, which are Slice 2 sources; and
- plain-paper submission identity without fabricating digital evidence.

Vitrine's generic `ProjectionField` limits each individual string value to 1,000
characters, while Quillan permits substantially longer public `PublishedText`.
The adapter therefore serializes a deterministic canonical JSON review payload,
encodes those UTF-8 bytes as Base64, and splits the result into chunks of at most
900 characters. Joining and Base64-decoding the ordered
`review_payload_json_base64_chunks` reconstructs the exact represented Slice-1
semantic payload without truncation or whitespace/control-character ambiguity.
High-value native review/rating/null-state values
are also exposed as ordinary typed projection fields so consumers need not parse
the payload merely to distinguish native states.

The canonical Slice-1 payload deliberately excludes assignment `student_prompt`
and `DigitalSubmissionProvenance.evidence_references`: neither belongs to the
bounded review-summary context frozen for this slice. No private Quillan state is
substituted for omitted public fields.

## Slice boundary

Slices 0-1 intentionally do not implement:

- selected `EvidenceReference` source projection;
- Quillan student-work, feedback-PDF, or feedback-Markdown Artifact capability
  sources;
- Quillan Artifact authorization bridging or producer byte reads;
- Snapshot source-context revalidation for Quillan Artifacts;
- Candidate ranking, improvement inference, portfolio-worth inference, or UI
  selection policy.

Those remain later issue #60 slices.

## Slice 2 Artifact-capability projection

The live adapter now projects Artifact capabilities without invoking
`quillan.academic_result_artifacts`.

For a represented `pds2_response_pages` student, every public selected
`EvidenceReference` becomes one independent:

```text
projection kind:     quillan:selected_student_work
Artifact kind:       original_student_work
Artifact request:    student_work
planned media:       application/octet-stream
source_locator:      None
source_digest:       None
byte_size:           None
```

The capability preserves the public selected-evidence provenance:

```text
page_id
evidence_id
observation_id
route_id
issuance_id
generation_id
artifact_id
source_page_number
source_scan_id
source_sha256
routed_evidence_sha256
```

and records a one-based `evidence_sequence` so producer order survives Vitrine's
deterministic batch sorting. `routed_evidence_sha256` is producer provenance only;
it is not promoted to `SourceArtifactReference.source_digest` before authorized
Quillan acquisition returns exact bytes.

Candidate, duplicate, excluded, replacement, and otherwise unrepresented native
evidence is not widened into the projection. No routed-evidence path is exposed.

For every represented `StudentResult`, the adapter also emits two distinct
feedback capabilities:

```text
quillan:feedback_pdf
  Artifact kind: rendered_feedback
  media: application/pdf
  request: feedback_pdf

quillan:feedback_markdown
  Artifact kind: rendered_feedback
  media: text/markdown; charset=utf-8
  request: feedback_markdown
```

A feedback capability is not an existence claim. The adapter does not inspect
`review.json.exports`, producer paths, or current workspace state. Exact
availability remains the responsibility of Quillan's authorization-gated
Artifact API in the later source-provider slice.

Plain-paper results remain valid review results and may still have feedback
capabilities, but they never gain a fabricated `student_work` capability because
their public submission has no digital provenance.

All capability sources retain the exact `core_student` /
`submission_subject` relationship and link back to the student's opaque Quillan
review-summary identity. Their opaque source/Artifact identities depend only on
the frozen immutable producer-visible identity inputs from Slice 0, not rating
values, review state, timestamps, feedback text, or current Artifact existence.

