# Live Quillan Projection and Artifact Adapter v1

- **Issue:** #60 — Implement the live Quillan projection and artifact adapter
- **Milestone:** v0.3.0 — Consume released producer evidence and guide real improvement/showcase portfolios
- **Status:** Operational live integration contract
- **Adapter ID:** `vitrine_quillan_live_adapter`
- **Adapter contract:** `vitrine_quillan_live_adapter_v1`
- **Projection contract:** `vitrine_candidate_projection_v1`
- **Reader contract:** `vitrine_installed_producer_reader_v1`
- **Artifact provider family:** `vitrine_quillan_authorized_artifact_source_provider`
- **Artifact provider version:** `vitrine_quillan_authorized_artifact_source_provider_v1`

## Purpose

Issue #60 implements Vitrine's live Quillan Academic Result projection and the
separately authorized Quillan Artifact acquisition path used by copied-source
Snapshots.

The production ownership sequence is:

```text
Core Publication discovery
-> canonical Core reload
-> exact Academic Work Registration reload
-> Quillan compatibility
-> source-read authorization
-> Core manifest verification
-> installed Quillan public reader
-> validated Quillan AcademicResultManifest
-> live Quillan projection
-> Portfolio Subject resolution
-> Profile/Candidate evaluation
-> explicit Selection
-> Snapshot planning
-> Snapshot build authority
-> Candidate/Evaluation/Selection/Core revalidation
-> separate Quillan Artifact authorization
-> quillan.academic_result_artifacts
-> exact immutable Artifact bytes
-> Vitrine staging and digest verification
```

Quillan owns Quillan semantic validation, native source integrity, Artifact
availability, and Artifact bytes. Vitrine owns bounded projection, portfolio
policy, explicit curation, immutable Snapshot planning, revalidation, and staging.
Deployment/application policy owns the Quillan Artifact authorization decision.

The integration does not calculate Grades, proficiency, mastery, improvement,
portfolio quality, or automatic selection. It does not inspect Quillan native
storage directly.

## Qualification anchors

The implementation is qualified against:

```text
pds-core 0.6.3
pds_core-0.6.3-py3-none-any.whl
sha256:
98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5

Quillan 0.10.0
quillan-0.10.0-py3-none-any.whl
sha256:
5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9
```

Release versions and wheel digests are qualification provenance only. They are
not semantic adapter-selection fields.

Vitrine retains no hard `quillan` runtime dependency.

## Frozen live support key

The adapter reuses exactly:

```text
QUILLAN_LIVE_SUPPORT_KEY
```

with:

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

The compatible Core Publication deliberately has no Publication `source_record`.
Quillan's Academic Work Registration separately identifies the assignment source
at contract `2`; registration source provenance is not part of the live adapter
support key.

No wildcard, nearest-version rule, package-version match, source-record
substitution, insertion-order fallback, or fixture fallback is permitted.
Unsupported exact contracts continue to fail with:

```text
adapter.unsupported_contract
```

## Installed reader and lazy loading

The live declaration binds only to:

```text
public_reader_id:
vitrine_installed_quillan_academic_result_reader

reader_contract_version:
vitrine_installed_producer_reader_v1

reader_package_identity:
quillan

integration_kind:
live
```

Constructing Vitrine, importing the adapter/provider modules, building the
ordinary registry, or running `vitrine adapters list/show` does not import
Quillan. Producer discovery/import occurs only when the installed reader or
public Artifact API is explicitly invoked.

The live projection consumes only the validated public model produced by:

```python
quillan.academic_result_reader.read_academic_result_manifest(...)
```

Vitrine does not parse the producer JSON itself, duplicate Quillan validators,
open `assignment.json`, `submission.json`, or `review.json`, reconstruct work
paths, query current Quillan workflow state, or regenerate feedback.

## Review projection cardinality and identity

The primary cardinality rule is:

```text
one represented Quillan StudentResult
=
one independently projected quillan:review_summary
```

Every represented student survives independently. Vitrine does not select a
student by array position, filename, roster inference, current producer state, or
rating value.

The logical review summary is:

```text
artifact_kind        = assessment_summary
representation_kind  = quillan:review_summary
source_locator       = None
source_digest        = None
byte_size            = None
```

Quillan does not publish a standalone Core record ID for every projected source,
so Vitrine derives deterministic opaque IDs using the frozen
`vitrine_quillan_source_identity_v1` length-delimited SHA-256 construction.
Prefixes remain:

```text
quillan_review_<64 lowercase hex>
quillan_evidence_<64 lowercase hex>
quillan_feedback_<64 lowercase hex>
```

Identity includes immutable producer-visible work/student/source identity and,
where applicable, the producer-native evidence ID or Artifact request kind. It
never depends on rating value, feedback text, timestamps, display labels,
Candidate status, or current Artifact existence.

## Exact student relationship and privacy

Every represented student source carries:

```text
source_subject_kind       = core_student
source_subject_id         = <exact Quillan student_id>
relationship_kind         = submission_subject
relationship_authority    = quillan
```

The adapter does not infer a Portfolio Subject ID. Canonical Vitrine Subject
linking happens later.

Projected student evidence remains conservatively classified as single-subject
student-record material with minimum-necessary projection required. Privacy
metadata is not disclosure authorization.

## Assignment, submission, and lineage semantics

The projection preserves bounded public manifest/work/assignment semantics,
including:

```text
record_type
contract_version
producer_module_id
generated_at
record_set.record_set_id
record_set.revision
work.module_id
work.class_id
work.work_id
assignment source snapshot
assignment_id
title
writing_type
standards_profile_id
ordered focus_standard_ids
review-unit definition
native Rating Scale
basic requirements
minimum-requirement policy
```

Assignment writing requirements remain Quillan requirements, not Vitrine Profile
requirements.

For every represented student, the adapter preserves exact submission semantics:

```text
class_id
assignment_id
student_id
submission_state
entry_method
expected_pages
```

and exact public source snapshots for submission and review. Those relative paths
and digests are producer lineage; they are not generic Vitrine filesystem
locators.

Entry methods remain distinct:

```text
pds2_response_pages
!=
plain_paper_manual
```

A valid plain-paper result is not a missing digital submission.

## Review states and minimum requirements

Quillan review states remain exact:

```text
not_started
requirements_checked
returned_without_full_review
observations_in_progress
observations_complete
ratings_complete
feedback_composed
ready_for_export
exported
```

They are not collapsed into pass/fail or ready/not-ready Vitrine judgments.

Minimum-requirement outcomes preserve:

```text
status
returned_without_full_review
updated_at
teacher_note PublishedText
```

with native statuses:

```text
not_checked
met
unmet_continue_review
returned_without_full_review
```

`unmet_continue_review` is not portfolio ineligibility, and
`returned_without_full_review` is not a zero, failure Grade, or inferred missing
submission.

## PublishedText

Quillan's public text state remains three-way:

```text
absent != withheld != included
```

For `included`, bounded public text may be projected. For `withheld` or `absent`,
text remains `None` and the disposition is preserved exactly.

Vitrine never recovers withheld text from producer storage, substitutes private
teacher notes, or equates absent/withheld with an empty string.

The rule applies to minimum-requirement notes, observation rationales,
overall-rating rationales, and feedback comment text.

## Review units, observations, ratings, and feedback

Review Units survive independently and in producer order. Standard Observations
preserve:

```text
observation_id
standard_id
applicable
evidence_present
rating
rationale
include_in_feedback
updated_at
```

The native distinctions remain:

```text
applicable = false
!=
applicable = true and evidence_present = false
!=
applicable = true and evidence_present = true
```

A missing rating is not converted to `0` or to the minimum Scale value.

Overall standard ratings preserve exact native integer values, rationale state,
feedback-inclusion state, and timestamps. Rating Scale identity, level order,
labels, and descriptions are preserved without percentage, Grade, mastery,
proficiency, universal-scale, or Candidate-score normalization.

Standard Feedback preserves the public composition structure, ordered included
observation IDs, comment identity, PublishedText state, inclusion state, and
creation time. Quillan feedback inclusion is not Vitrine Selection or disclosure
permission.

Because generic `ProjectionField` strings are bounded while public Quillan text
may be longer, the exact review payload is serialized deterministically, UTF-8
encoded, Base64 encoded, and stored in ordered bounded
`review_payload_json_base64_chunks`. This avoids truncating represented public
semantics without expanding the persistent Candidate wire model.

## Selected PDS2 evidence

For `pds2_response_pages`, only selected EvidenceReference values already present
in the public manifest become selected-work sources.

The cardinality rule is:

```text
one represented selected EvidenceReference
=
one independently projected quillan:selected_student_work source
```

Public evidence order is preserved explicitly. The projection preserves bounded
public provenance such as page/evidence/observation/route/issuance/generation/
artifact identity, source page/scan identity, and public SHA-256 values.

Candidate, duplicate, excluded, replacement, or otherwise unselected evidence is
not widened into Vitrine.

Producer-private paths are never projected as Vitrine source locators. The public
`routed_evidence_sha256` remains provenance only before authorization; it is not
borrowed as `SourceArtifactReference.source_digest`.

For `plain_paper_manual`, no `quillan:selected_student_work` source is fabricated.

## Artifact capabilities

The live projection exposes three closed Artifact-capability representations:

```text
quillan:selected_student_work
quillan:feedback_pdf
quillan:feedback_markdown
```

with Quillan public request kinds exactly:

```text
student_work
feedback_pdf
feedback_markdown
```

A projected capability does not authorize producer I/O. A feedback capability
also does not prove that the current export exists; final availability belongs to
Quillan after authorization.

Before authorization every capability has:

```text
source_locator = None
source_digest  = None
byte_size      = None
```

## Student-work media reconciliation

The public Academic Result manifest does not expose the selected routed-evidence
suffix or MIME. The released Artifact API may resolve selected work to exactly:

```text
image/jpeg
image/png
image/tiff
```

The immutable source and Snapshot plan therefore use:

```text
application/octet-stream
```

as an explicit "exact media not knowable yet" planning value. It is not a
wildcard.

Selected student work uses the additive acquisition contract:

```text
authorized_source_bytes_deferred_media_v1
```

The provider declares the closed concrete media allowlist above. The target path
is suffix-neutral. After authorization, the exact producer-returned concrete MIME
must be in that allowlist and becomes the sealed Snapshot Entry media type.

Existing exact-media behavior remains strict through:

```text
authorized_source_bytes_v1
```

Feedback uses exact media from planning through sealing:

```text
feedback_pdf      -> application/pdf
feedback_markdown -> text/markdown; charset=utf-8
```

## Exact Snapshot provider support keys

The provider family/version is:

```text
vitrine_quillan_authorized_artifact_source_provider
vitrine_quillan_authorized_artifact_source_provider_v1
```

The registry uses three exact provider descriptors so provider IDs remain unique.
Support selection is exact over producer, representation/projection contract,
Artifact kind, and representation kind.

```text
selected student work
  producer:              quillan
  projection:            quillan:selected_student_work
  projection contract:   vitrine_candidate_projection_v1
  artifact kind:         original_student_work
  representation:        quillan:selected_student_work

feedback PDF
  producer:              quillan
  projection:            quillan:feedback_pdf
  projection contract:   vitrine_candidate_projection_v1
  artifact kind:         rendered_feedback
  representation:        quillan:feedback_pdf

feedback Markdown
  producer:              quillan
  projection:            quillan:feedback_markdown
  projection contract:   vitrine_candidate_projection_v1
  artifact kind:         rendered_feedback
  representation:        quillan:feedback_markdown
```

## Canonical revalidation before Artifact access

The production Quillan source-context resolver revalidates an immutable selected
Snapshot source in this order:

```text
Snapshot Entry Plan
-> Candidate Evaluation
-> PortfolioCandidate
-> explicit PortfolioSelection
-> Placement when represented
-> frozen Candidate source endpoint
-> canonical Core Publication
-> withdrawal state
-> exact historical Academic Work Registration
-> frozen Quillan live contract
-> separate manifest source-read authorization
-> Core manifest verification
-> installed Quillan reader
-> exact live Quillan reprojection
-> frozen Candidate/source/Artifact equality
```

For selected student work, exact reprojection must reproduce the same public
EvidenceReference and opaque Vitrine source identity. For feedback, it must
reproduce the same exact PDF or Markdown capability identity.

A withdrawn Publication, registration drift, manifest-read denial, or
reprojection mismatch fails before Quillan Artifact authorization and producer
native I/O.

## Separate Quillan Artifact authorization

Artifact access uses only:

```text
quillan.academic_result_artifacts
```

The producer API's authorization outcomes remain:

```text
allowed
denied
unresolved
```

Manifest source-read authorization is not Artifact authorization. Candidate
eligibility is not Artifact authorization. Selection is not Artifact
authorization. Snapshot build authority is not Artifact authorization.

Only an explicit `allowed` Artifact decision may permit Quillan native I/O.
Denied, unresolved, invalid, or exceptional deployment decisions fail closed.

The Vitrine deployment request binds the immutable Snapshot/Candidate source,
Publication, student, Artifact request kind, purpose, and—only for selected
student work—the exact public evidence ID. It contains no producer-native path.

## Authorized result verification

Quillan's `student_work` request is student-scoped and returns the represented
selected-work tuple for that student. Vitrine verifies every returned result and
then selects the one whose public `EvidenceReference` is exactly the planned
reference.

Vitrine verifies exact work, record-set revision, student, Artifact kind,
immutable bytes, producer SHA-256, producer byte size, evidence provenance, and
concrete media. The selected-work digest must agree with the public
`routed_evidence_sha256`.

For feedback, Vitrine requires exactly one returned result of the requested kind
with exact work/revision/student identity, media type, bytes, digest, and size.

Vitrine never reopens Quillan's returned `relative_path`.

Producer historical/native source drift maps to Snapshot source-integrity
failure rather than bypass, retry through a private path, or current-state
substitution.

## Snapshot materialization

Successful producer acquisition returns:

```text
SnapshotAuthorizedSourceBytesResult
```

The Snapshot materializer independently verifies producer digest/size claims,
stages immutable bytes, rereads staged bytes, and recomputes the output digest.
Authorized-byte sources do not enter the generic filesystem stability path.

Selected student work resolves deferred media only from the producer-returned
closed allowlist. PDF/Markdown remain exact-media acquisitions.

## Candidate, Selection, and inference boundary

Every represented Quillan source flows through ordinary Portfolio Subject and
Profile/Candidate policy. Candidate discovery does not select evidence.

```text
Candidate != Selection
```

Snapshot acquisition begins only after explicit Selection.

Quillan ratings, feedback, review state, minimum requirements, and selected
producer evidence are evidence only. They do not prove:

```text
improvement
mastery
proficiency
Grade
portfolio worth
showcase quality
```

Those judgments, where supported at all, belong to later Vitrine consumer policy
and teacher-controlled curation.

## Ordinary registry and CLI

After #60, the completed ordinary live registry is:

```text
Concord + Quillan + ScoreForm
```

with deterministic adapter IDs:

```text
vitrine_concord_live_adapter
vitrine_quillan_live_adapter
vitrine_scoreform_live_adapter
```

The three development fixture adapters remain isolated behind explicit fixture
opt-in. Default workflow dependencies remain fail-closed rather than discovering
or enabling producer integrations automatically.

`vitrine adapters list` and `vitrine adapters show
vitrine_quillan_live_adapter` work without Quillan installed.

## Packaging and exact-wheel qualification

The runtime wheel includes:

```text
vitrine/quillan_adapter.py
vitrine/quillan_contract.py
vitrine/quillan_artifact_context.py
vitrine/quillan_artifact_source.py
```

Normal runtime requirements remain Core-only.

The source distribution includes the dedicated validator and exact-wheel Artifact
qualification harness:

```text
scripts/validate_quillan_adapter.py
scripts/qualify_quillan_artifact_source.py
```

Exact release qualification uses:

```powershell
python scripts/qualify_installed_producer_readers.py `
  --wheel-dir "$HOME\Downloads"
```

The gate authenticates the audited release wheels, invokes the released Quillan
reader and producer Profile, qualifies the live projection, creates genuine
producer-native selected PDS2 evidence and feedback exports through installed
Quillan production APIs, and exercises all three Vitrine Artifact provider
representations.

The denied-authorization case is required to fail before producer-native
workspace access.

## Validation

Focused validation includes:

```powershell
python scripts/validate_quillan_adapter.py
python scripts/validate_producer_adapters.py
python scripts/check_documentation.py
python -m pytest `
  tests/test_quillan_adapter.py `
  tests/test_quillan_artifact_source.py `
  tests/test_quillan_artifact_context.py `
  tests/test_snapshot_deferred_media.py
```

The final repository gate is:

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```

## Supporting implementation notes

The earlier Slice contracts remain useful as focused implementation notes:

- [Quillan Live Adapter v1](quillan-live-adapter-v1.md)
- [Quillan authorized Artifact Snapshot source provider v1](quillan-artifact-source-provider-v1.md)

This document is the final issue #60 operational contract and supersedes their
slice-status language for current implementation status.
