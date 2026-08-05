# Producer Artifact Exposure Examples

## Purpose

These synthetic examples exercise the [producer artifact exposure design](../design/producer-artifact-exposure-boundaries.md) and [ADR 0005](../decisions/0005-producer-artifact-exposure-boundaries.md).

They are conceptual examples rather than final serialized contracts. Names, identifiers, classes, assignments, and records are synthetic.

Each example separates:

- producer source validity;
- projection exposure disposition;
- implementation readiness;
- required relationships and reviews;
- Candidate outcome;
- and later Selection or disclosure decisions.

## Common synthetic context

```text
workspace: synthetic_workspace
Portfolio: portfolio_aurora
Portfolio Subject: subject_aurora
Profile binding: profile_binding_showcase_r3
Profile revision: district_showcase / revision 3
```

A positive exposure decision does not create a Selection or snapshot.

## ScoreForm examples

### 1. Academic Result Manifest is source-only

**Source**

```text
producer: scoreform
manifest: scoreform_academic_result_manifest_v1
publication_id: pub_scoreform_ecology_r2
record_set_revision: 2
```

**Decision**

```text
projection: manifest itself
exposure: source_only
readiness: implemented
Candidate: none
```

**Reason**

The manifest supports verified parsing and provenance but is not a student-facing artifact.

### 2. One attempt summary is conditionally eligible

**Source**

```text
assignment: ecology_check
student: student_0042
attempt_number: 1
points_earned: 14
points_possible: 20
```

**Projection**

```text
scoreform:attempt_summary
```

**Decision**

```text
exposure: conditional_candidate
readiness: planned
condition: exact Profile permits result summaries
Candidate now: no, projection contract unavailable
```

The architecture permits the projection, but ScoreForm has not implemented that exact public representation.

### 3. Three attempts remain three projections

**Source**

```text
attempts: 1, 2, 3
scores: 12/20, 16/20, 15/20
```

**Decision**

Three attempt-summary evaluations are possible.

Vitrine does not select:

- attempt 2 because it is highest;
- attempt 3 because it is latest;
- or attempt 1 because it is first.

Selection belongs to issue #8. Formal grading-attempt policy remains outside Vitrine.

### 4. Ordinary attempt summary omits selected answers

**Source**

The manifest includes response-level selected answers.

**Projection allowlist**

```text
assignment identity
attempt number and origin
recorded time
points earned and possible
selected/blank/ambiguous counts
standard alignment summary
provenance
```

**Excluded**

```text
selected_answer
answer key
item text
detector details
```

The attempt summary remains a bounded result summary.

### 5. Restricted question-evidence projection

**Profile context**

A synthetic regulated Profile requires item-level evidence for standard `RL.CI.9-10.2`.

**Projection**

```text
scoreform:question_evidence_summary
question_number: 7
response_state: selected
correct: true
standard_ids: [RL.CI.9-10.2]
```

**Decision**

```text
exposure: conditional_candidate
required review: regulated-profile review
selected answer: omitted
answer key: prohibited
```

Correctness and alignment remain producer facts. Proficiency is not inferred.

### 6. Standard alignment is not proficiency

**Source**

Question 7 is aligned to `RL.CI.9-10.2` and the response is correct.

**Invalid conclusion**

```text
student is proficient in RL.CI.9-10.2
```

**Valid projection meaning**

```text
this exact question was aligned to RL.CI.9-10.2
this exact response was marked correct by ScoreForm
```

### 7. Raw answer-sheet scan is rejected

**Request**

Use the Core-retained scan at a ScoreForm retained-source path as the Candidate.

**Decision**

```text
exposure: prohibited
failure: raw_retained_scan_prohibited
```

Vitrine does not open or copy the retained path.

### 8. Future sanitized answer-sheet rendering

**Producer action required**

ScoreForm creates a projection that:

- isolates only the exact attempt pages;
- removes route and QR data where required;
- excludes unrelated pages;
- excludes detector overlays;
- binds exact source and rendered digests;
- and exposes the rendering through a public reader.

**Decision**

```text
projection: scoreform:sanitized_answer_sheet
exposure: conditional_candidate
readiness: planned
required review: sanitization and privacy
```

### 9. Answer key remains prohibited

**Source**

The assignment’s canonical answer key exists in ScoreForm.

**Decision**

```text
exposure: prohibited
```

Neither an attempt summary nor question-evidence summary may expose it.

### 10. Scan-review failure remains prohibited

**Source**

A manual review failure explains why one scan needed correction.

**Decision**

```text
exposure: prohibited
```

The eventual completed attempt may be projected. The failure record is operational provenance, not portfolio content.

### 11. Student absent from manifest

**Source**

The assignment exists, but `student_0042` has no published attempt.

**Decision**

No attempt projection exists.

Vitrine does not create:

- zero points;
- missing work;
- blank attempt;
- or incomplete Candidate.

### 12. Ambiguous response remains ambiguous

**Source**

```text
question_number: 12
response_state: ambiguous
selected_answer: null
correct: false
```

**Decision**

A restricted question summary preserves `ambiguous`. It does not select a likely answer or relabel the response as blank.

## Quillan examples

### 13. Selected original-work projection

**Source**

A four-page submission has one producer-selected evidence item for each page.

**Projection**

```text
quillan:student_work
pages: selected evidence only, in logical page order
```

**Decision**

```text
exposure: candidate_eligible
readiness: planned
```

Quillan must publish an exact public contract before Vitrine can create the Candidate.

### 14. Candidate evidence is excluded

**Source**

Page 2 has one selected image and one unreviewed candidate image.

**Projection**

Only the selected image is included.

The candidate image and its existence are omitted from student-facing output.

### 15. Duplicate evidence is excluded

**Source**

Two routed observations contain identical page content. Quillan marks one as duplicate.

**Decision**

The duplicate does not enter the original-work projection.

Digest equality alone does not cause Vitrine to choose between them; Quillan’s selected-evidence state is authoritative.

### 16. Excluded evidence remains excluded

**Source**

A page was explicitly excluded after teacher review.

**Decision**

It is not exposed in original work or feedback merely because the file remains retained.

### 17. Feedback PDF Candidate

**Source**

Quillan generated a student-facing PDF containing selected ratings, rationale, comments, and next steps.

**Decision**

```text
projection: quillan:student_feedback_pdf
exposure: candidate_eligible
readiness: unavailable to Vitrine
```

The export exists in Quillan, but no accepted Core publication and public reader currently expose it to Vitrine.

### 18. Feedback Markdown Candidate

The same approved feedback exists as Markdown.

It is a separate representation from the PDF and therefore receives a separate projection identity and Candidate evaluation.

### 19. Structured feedback summary

**Projection**

```text
quillan:student_feedback_summary
```

**Allowlist**

- assignment context;
- Focus Standards;
- selected ratings and labels;
- selected rationale and observations;
- selected comments;
- minimum-requirement notice;
- next steps.

**Decision**

```text
exposure: conditional_candidate
readiness: planned
```

The summary does not expose complete `review.json`.

### 20. Private notes remain absent without leakage

**Source**

The review includes a teacher-private note.

**Projection**

The PDF, Markdown, and structured summary contain no private-note content and no flag indicating that a private note exists.

### 21. Class report is not an individual artifact

**Source**

An assignment report includes aggregate ratings for the whole class and names the Portfolio Subject among many students.

**Decision**

```text
exposure: prohibited for individual Candidate use
```

The report is not isolated student work and may reveal other students.

### 22. Raw retained Quillan scan is rejected

**Request**

Use a retained source file because the public original-work projection is unavailable.

**Decision**

```text
exposure: prohibited
failure: raw_retained_scan_prohibited
```

No native-file fallback is allowed.

### 23. Feedback becomes stale

**Source history**

- feedback export revision 2 was generated;
- teacher later changed selected feedback;
- no revision 3 export exists yet.

**Decision**

The prior projection is `projection_representation_stale` for current working use.

Historical Candidate and snapshot references remain valid. Vitrine does not regenerate the export.

### 24. Bare rating is supporting metadata

**Source**

Quillan records a rating of `developing` under assignment-local scale revision 2.

**Decision**

The rating may accompany original work or feedback as supporting metadata.

It does not become a standalone Candidate or universal proficiency assertion.

## Concord examples

### 25. Confirmed individual Artifact

**Source**

```text
artifact_category: student_work
authorship_mode: individual_author
attribution_status: confirmed
privacy: teacher_and_subjects
```

**Decision**

```text
projection: concord:artifact
exposure: conditional_candidate
readiness: planned
```

Candidate creation still requires exact pages, subject relationship, access, Profile eligibility, and privacy review.

### 26. Confirmed co-authored Artifact

**Source**

Two confirmed co-authors produced one project record.

**Decision**

The Artifact may become a collaborative Candidate for either author, but the projection preserves both authors and requires collaborator review.

It is not presented as solely authored by the Portfolio Subject.

### 27. Group Artifact with confirmed collective authorship

**Source**

```text
authorship_mode: collective_group_author
represented_group: group_cedar
representation_status: unanimous_position
```

**Decision**

A collaborative projection may be conditionally eligible.

The Candidate preserves Group identity and does not create individual ownership or Score targeting.

### 28. Group Member without authorship

**Source**

The Portfolio Subject is a Group Member but has no Artifact Author record.

**Decision**

No individual Artifact Candidate is created from membership alone.

A carefully labeled Group-context projection may be possible only under a separate Profile and producer rule.

### 29. Recorder-for-Group representation

**Source**

```text
authorship_mode: recorder_for_group
representation_status: majority_position
```

**Decision**

The projection states that the student recorded a Group position.

It does not claim that the student authored the position individually or that the Group was unanimous.

### 30. Multiple named positions

**Source**

```text
representation_status: multiple_named_positions
```

**Decision**

The projection preserves the distinct positions and requires collaborator and multi-subject review.

Vitrine must not flatten the Artifact into one Group view.

### 31. Disputed authorship

**Source**

```text
attribution_status: disputed
```

**Decision**

No unqualified individual-authorship Candidate is created.

The source remains resolvable for review and historical provenance.

### 32. Primary and continuation pages

**Source**

An Artifact includes one primary page and two continuation pages.

**Decision**

The approved Artifact projection preserves all three in producer-defined order.

They are components of one Candidate rather than three standalone Candidates.

### 33. Instructional page is excluded

**Source**

An assignment packet includes an instructional page before the returned work.

**Decision**

The instructional page is supporting context or omitted. It is not student-authored work.

### 34. Rubric is separate feedback

**Source**

The returned Artifact contains a rubric page with teacher evaluation.

**Decision**

The rubric is represented as a separate feedback/evaluation projection rather than merged into the original-work representation automatically.

### 35. Standard-backed Score summary

**Source**

```text
score target: core_student student_0042
criterion: criterion_claim_evidence
scale revision: 3
value: meets
```

**Decision**

A Score summary may preserve the exact Criterion, scale, target, value, disposition, and provenance.

It does not become a Grade or universal proficiency level.

### 36. Group Score remains Group-targeted

**Source**

```text
score target: concord_group group_cedar
```

**Decision**

The Score summary remains Group-targeted.

The Artifact may be a collaborative Candidate, but the Group Score does not become an individual Score for the Portfolio Subject.

### 37. Non-score disposition

**Source**

A Score Record has disposition `insufficient_evidence` and no score value.

**Decision**

The summary preserves the non-score disposition and does not fabricate a numeric or categorical value.

### 38. Moderation record is source-only

**Source**

A moderation record explains why one Score was superseded.

**Decision**

```text
exposure: source_only
```

A later student-facing summary may preserve a bounded outcome, but the raw moderation record is not exposed.

### 39. Observation Artifact is not ordinary original work

**Source**

```text
artifact_category: observation
privacy: teacher_restricted
```

**Decision**

The raw Artifact remains source-only or prohibited.

A producer-approved observation summary would require explicit purpose and privacy review.

## Portia examples

### 40. Portia source is suppressed from ordinary discovery

**Source**

Core discovery technically matches an intervention publication associated with the Portfolio Subject.

**Decision**

```text
exposure: suppressed
ordinary results: zero visible Portia entries
```

The interface does not display:

- one hidden result;
- a title;
- a count;
- a facet;
- or a permission-error placeholder.

### 41. Student-selected reflection safe projection

**Source**

A student voluntarily selects a reflection for portfolio use.

**Projection requirements**

- explicit Portia portfolio-safe contract;
- exact subject;
- exact source and projection revision;
- purpose-specific opt-in;
- student review;
- no surrounding Event or intervention graph.

**Decision**

```text
exposure: conditional_candidate
readiness: planned
```

### 42. Documented-strength projection

**Source**

Portia contains a teacher-approved strength statement created specifically for portfolio use.

**Projection**

The statement includes the strength, date, bounded context, and approval provenance.

It excludes incident history, counts, tiers, allegations, and other participants.

### 43. Self-advocacy projection

**Source**

A student asks for a planned support and later approves a portfolio statement describing the self-advocacy.

**Decision**

The safe projection may be conditionally eligible without exposing the support plan, disability status, or intervention history.

### 44. Raw positive Observation is rejected

**Source**

A teacher recorded a positive Portia Observation.

**Decision**

The raw Observation remains suppressed.

Positive content does not make the native record portfolio-safe automatically.

### 45. Intervention plan is rejected

**Request**

Include the complete intervention plan as evidence of growth.

**Decision**

```text
exposure: suppressed/prohibited
```

A separate safe growth statement may be possible. The intervention plan itself remains outside the Portfolio.

### 46. Family communication is rejected

**Source**

A Portia Communication records a family conversation.

**Decision**

It cannot become a Candidate or supporting metadata.

### 47. Portia context linked to Quillan reflection

**Source**

A substantial student reflection is authored in Quillan and referenced by Portia for a support process.

**Decision**

- Quillan owns the reflection representation.
- Portia may expose only a bounded purpose-context projection.
- Vitrine preserves both references.
- Portia’s reference does not broaden Quillan access.

## Cross-producer and lifecycle examples

### 48. Original work and feedback remain separate Candidates

**Source**

One Quillan submission has:

- an original-work projection;
- a feedback PDF;
- and a structured feedback summary.

**Decision**

Each has separate projection identity and Candidate evaluation.

A later Selection may choose one, two, or all three according to Profile policy.

### 49. Multi-subject source is narrowed by the producer

**Source**

A Concord discussion record names four students.

**Producer projection**

Concord publishes a subject-isolated excerpt for `subject_aurora` with exact relationship and omission metadata.

**Decision**

The isolated projection may be conditionally eligible.

Vitrine does not construct the excerpt by deleting fields from the native record.

### 50. Collaborator review required

**Source**

A co-authored Artifact is otherwise eligible.

**Decision**

```text
exposure: conditional_candidate
remaining review: collaborator review
```

Candidate creation may remain conditional. Audience disclosure still requires issue #10 controls.

### 51. Rights review required

**Source**

A showcase Artifact contains a licensed image.

**Decision**

The producer projection is conditionally eligible, but rights review is required before a public edition.

Exposure permission does not decide public disclosure.

### 52. Contract exists but reader is unavailable

**Source**

A producer documents projection contract v1, but the installed producer package lacks its reader.

**Decision**

```text
exposure: candidate_eligible
readiness: unavailable
Candidate: none
failure: projection_reader_unavailable
```

### 53. Policy permits a planned projection

**Source**

The architecture permits `quillan:student_work`, but no public contract is accepted.

**Decision**

```text
exposure: candidate_eligible
readiness: planned
Candidate: none
```

Planned is not implemented.

### 54. Projection revision supersedes an earlier representation

**History**

- projection revision 1 contains pages 1–3;
- producer correction creates revision 2 with corrected page 2;
- revision 2 explicitly supersedes revision 1.

**Decision**

New candidate evaluation uses revision 2.

The revision 1 Candidate remains historically resolvable and is not retargeted.

### 55. Historical Candidate retains earlier projection

A Selection made before the correction continues to reference projection revision 1.

A teacher may replace it through issue #8’s later record model, but Vitrine does not rewrite it automatically.

### 56. Source and rendering digests differ

**Digests**

```text
manifest digest: digest_manifest_a
source artifact digest: digest_source_b
rendered PDF digest: digest_rendered_c
```

**Decision**

All three are valid because they bind different bytes.

The difference is not a digest mismatch.

### 57. Snapshot copy has a fourth digest

A later Vitrine snapshot copies the rendered PDF into an immutable package.

```text
copied representation digest: digest_snapshot_d
```

Issue #9 must preserve the source-to-copy relationship. The producer-rendered digest is not reused as the copied-byte digest unless the copied bytes are independently verified as identical.

### 58. Projection is withdrawn after Candidate creation

**History**

A producer withdraws a projection because it included an unsafe field.

**Decision**

- historical Candidate and Selection provenance remain preserved;
- current working use is blocked or reviewed;
- new Candidates are not created from the withdrawn projection;
- issued historical snapshots are not silently rewritten.

### 59. Audience disclosure remains unresolved

**Source**

A Quillan feedback PDF is Candidate-eligible and source access is authorized.

**Decision**

The Candidate may be considered for curation, but parent-facing or public disclosure remains unresolved under issue #10.

### 60. Exposure does not create Selection

**Source**

A Concord Artifact passes all exposure and Candidate checks.

**Decision**

The Portfolio Candidate exists.

No section placement, display title, ordering, reflection, or approval is created until issue #8’s Selection workflow records those actions.

## Summary matrix

| Producer | Ordinary positive projection | Source-only example | Prohibited or suppressed example | Readiness constraint |
| --- | --- | --- | --- | --- |
| ScoreForm | attempt summary; restricted question summary; future sanitized sheet | Academic Result Manifest | answer key, detector internals, raw scan | summary/rendering contracts are planned |
| Quillan | selected original work; feedback PDF/Markdown; structured feedback | submission and review | private notes, class reports, raw scan | Core publication and public reader unavailable |
| Concord | exact Artifact; exact Score summary | Review and Moderation | inferred authorship, route data, raw scan | public projection contracts planned |
| Portia | future explicit safe reflection/growth projection | none for ordinary Vitrine use | all ordinary records suppressed | safe projection contract planned |

## Example invariants

Across all examples:

- exact producer projection identity is preserved;
- no native-file fallback occurs;
- exposure and readiness are separate;
- no Candidate implies Selection;
- no exposure implies audience permission;
- no source reference implies copied bytes;
- relationships retain producer-native meaning;
- suppressed sources reveal no existence metadata;
- and historical revisions remain exact.
