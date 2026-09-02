# Live ScoreForm Projection Adapter v1

- **Issue:** #59 — Implement the live ScoreForm projection adapter
- **Milestone:** v0.3.0 — Consume released producer evidence and guide real improvement/showcase portfolios
- **Status:** Operational live integration contract
- **Adapter ID:** `vitrine_scoreform_live_adapter`
- **Adapter contract:** `vitrine_scoreform_live_adapter_v1`
- **Projection contract:** `vitrine_candidate_projection_v1`
- **Reader contract:** `vitrine_installed_producer_reader_v1`

## Purpose

Issue #59 implements Vitrine's first live producer projection adapter. The
adapter consumes only the already validated public ScoreForm
`AcademicResultManifest` returned by the installed reader service.

The ownership sequence is:

```text
Core discovery
-> canonical Core Publication reload
-> exact historical Academic Work Registration
-> Core producer Profile compatibility
-> exact Vitrine adapter selection
-> source-read authorization
-> Core manifest verification
-> exact immutable manifest bytes
-> installed ScoreForm public reader
-> validated ScoreForm AcademicResultManifest
-> live ScoreForm Vitrine projection
-> Portfolio Subject resolution
-> Profile eligibility
-> Candidate Evaluation
```

ScoreForm owns ScoreForm semantic validation. Vitrine projection preserves
ScoreForm evidence. Vitrine Subject/Profile/Candidate layers own portfolio policy.

The adapter does not decode manifest JSON, duplicate ScoreForm validation, reopen
producer files, inspect ScoreForm workspace state, or generate publications.

## Qualification anchors

The implementation is qualified against:

```text
pds-core 0.6.3
pds_core-0.6.3-py3-none-any.whl
sha256:
98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5

ScoreForm 0.11.0
scoreform-0.11.0-py3-none-any.whl
sha256:
8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44
```

These release versions and digests are qualification anchors only. They are not
semantic adapter-selection fields.

Vitrine adds no hard ScoreForm runtime dependency.

## Frozen support key

The adapter reuses the one frozen ScoreForm live support key:

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

There is no package-version field, wildcard, nearest-version rule, source-record
substitution, or development-fixture fallback.

## Lazy reader binding

The declaration binds:

```text
public_reader_id:
vitrine_installed_scoreform_academic_result_reader

reader_contract_version:
vitrine_installed_producer_reader_v1

reader_package_identity:
scoreform

integration_kind:
live
```

Constructing the adapter declaration, ordinary registry, or adapter CLI
diagnostics does not import ScoreForm. ScoreForm resolution remains lazy until
the reader is invoked and/or the adapter validates the already returned
public-model type.

## Projection cardinality

The fundamental rule is:

```text
one represented ScoreForm student attempt
=
one ProjectedProducerSource
```

Every represented attempt survives independently.

```text
attempt 1 != attempt 2
latest attempt != selected attempt
highest score != portfolio-worthy attempt
```

The adapter never chooses an official, latest, highest, best, preferred,
replacement, Grade-bearing, or portfolio-worthy attempt.

## Deterministic attempt identity

ScoreForm does not publish a standalone native attempt record ID. Vitrine derives
an opaque projection identity using a length-delimited SHA-256 construction over:

```text
producer_module_id
class_id
assignment_id
student_id
attempt_number
projection_kind
```

The external form is:

```text
scoreform_attempt_<64 lowercase hexadecimal characters>
```

Plaintext student identity does not appear in the generated ID. Points,
correctness, selected-answer state, timestamp, and display values do not
determine identity.

The projected producer reference uses:

```text
producer_module_id              = scoreform
producer_contract_version       = scoreform_academic_work_v1
source_record_kind              = academic_result_attempt
source_record_contract_version  = None
native_revision                 = <attempt_number>
native_lifecycle                = recorded
native_disposition              = attempt
```

`source_record_contract_version=None` is deliberate because ScoreForm publishes
no separate native attempt-record contract through Core.

## Logical artifact boundary

Each attempt is represented as a logical assessment summary:

```text
artifact_kind        = assessment_summary
representation_kind  = scoreform:attempt_summary
source_locator       = None
source_digest        = None
byte_size            = None
```

The logical summary is not a retained scan. `retained_source_path` is never a
Vitrine source locator, and a retained-scan digest is not reused as a digest for
the logical summary.

ScoreForm 0.11.0 exposes no consumer-neutral Artifact resolver, so issue #59 does
not implement a ScoreForm Snapshot source provider.

## Student relationship

Each projected attempt carries the exact producer relationship:

```text
source_subject_kind       = core_student
source_subject_id         = <exact ScoreForm student_id>
relationship_kind         = attempt_subject
relationship_authority    = scoreform
```

The adapter does not query a roster or resolve Portfolio Subjects. Candidate
services perform that later using canonical Core class identity and Vitrine's
teacher-confirmed Subject links.

## Privacy metadata

Each attempt summary is single-subject student-record evidence:

```text
classification                         = student_record
subject_scope                          = single_subject
metadata_visibility                    = internal
collaborator_information_present       = false
third_party_information_present        = false
rights_review_required                 = false
redaction_review_required              = false
multi_subject_review_required          = false
minimum_necessary_projection_required  = true
```

This metadata does not authorize disclosure.

## Bounded semantic projection

The transient display projection preserves the relevant ScoreForm semantics
without expanding the durable Candidate wire schema.

Manifest and record-set metadata includes:

```text
record_set_id
record_set_revision
manifest_generated_at
assignment_source_sha256
results_history_source_sha256
results_history_schema_version
```

Assignment metadata includes:

```text
class_id
assignment_id
question_count
layout_id
total_points
standards_profile_id
question_numbers
question_points_possible
question_standard_alignments
```

Question standard IDs remain alignments only:

```text
question alignment != standards rating
```

Attempt metadata includes:

```text
attempt_number
result_origin
recorded_at
points_earned
points_possible
```

The adapter derives no percentage, letter Grade, rank, improvement score,
proficiency, or mastery.

Response metadata includes:

```text
response_states
selected_answer_presence
response_correctness
```

Exact selected-answer strings are deliberately excluded.

```text
selected != blank != ambiguous
response correctness != proficiency
points != Grade
```

## Provenance

For `pds2_scan`, bounded provenance preserves the represented issuance,
generation, artifact, page, route, logical-page, source-scan, source-page, and
source-digest identifiers.

`retained_source_path` is omitted.

For `plain_paper_manual`, no scan provenance is fabricated.

For `scan_review_manual`, the review failure identifier is preserved without
inventing PDS2 provenance.

## Candidate integration

Candidate services evaluate every projected attempt independently.

The live acceptance path proves that:

- two attempts for the same linked student both survive independently even when
  the later attempt has a lower score;
- an attempt for another represented student is still evaluated independently
  and can remain unresolved for that Portfolio Subject;
- Candidate discovery/evaluation creates no automatic `PortfolioSelection`.

```text
Candidate != Selection
```

## Registry and diagnostics

Issue #59 originally registered ScoreForm as the only live adapter. After
issue #61, the completed ordinary runtime registry contains:

```text
vitrine_concord_live_adapter
vitrine_scoreform_live_adapter
```

The three Vitrine-owned development fixture adapters remain isolated behind the
explicit development fixture registry.

Default adapter diagnostics can list/show either completed live declaration
without ScoreForm or Concord being installed. ScoreForm's frozen support key and
projection semantics are unchanged by the registry extension.

## Packaging and qualification

The runtime wheel includes:

```text
vitrine/scoreform_adapter.py
```

The source distribution includes this contract and the issue #59 validation
surface. Normal runtime requirements remain Core-only.

Exact released-wheel qualification is:

```powershell
python scripts/qualify_installed_producer_readers.py `
  --wheel-dir "$HOME\Downloads"
```

The qualification verifies the audited Core 0.6.3 and ScoreForm 0.11.0 artifacts
and three independent live ScoreForm attempt projections.

## Downstream handoff

Issue #61 now adds live Concord projection and Artifact support while leaving
ScoreForm's frozen support key and projection semantics unchanged.

Issue #60 may add live Quillan projection and Artifact support when implemented
or reconciled. Issue #62 may expose compatibility diagnostics over the stable
exact-match and privacy-safe failure boundaries.

No downstream integration may use a development fixture as a live fallback.
