# Representative Candidate and Source-Reference Examples

- **Issue:** #6, “Define candidate and source-reference contracts”
- **Date:** 2026-08-05
- **Status:** Synthetic conceptual examples; not final serialized fixtures
- **Related design:** [Candidate and Source-Reference Contract](../design/candidate-source-reference-contract.md)
- **Related decision:** [ADR 0004](../decisions/0004-candidate-discovery-and-source-references.md)

## 1. Purpose and conventions

These examples exercise the candidate trust pipeline and its failure boundaries.

All people, classes, works, records, publications, digests, and institutions are synthetic.

The examples use abbreviated YAML-like shapes to emphasize meaning. They are not final schemas.

Shared synthetic context:

```yaml
portfolio:
  portfolio_id: port_61d86c97907b4f7fa675865f2330d1ae
  portfolio_subject_id: ps_920589c7710848d6bde79db8b348267a
  profile_binding_id: ppb_3ee80c32755d4a7a8c295cfffc9628b7
  portfolio_profile_id: showcase_english
  profile_revision: 2

subject_roster_association:
  school_year: 2026-2027
  class_id: english10_p2
  student_id: "0017"
```

A Candidate ID identifies one exact source representation under this context unless a scenario explicitly changes it.

## 2. Successful ScoreForm attempt Candidate

### Source

```yaml
catalog_row:
  publication_id: pub_11111111111111111111111111111111

canonical_publication:
  publication_id: pub_11111111111111111111111111111111
  work:
    module_id: scoreform
    class_id: english10_p2
    work_id: unit1_assessment
  publication_kind: academic_result_set
  capabilities:
    - points
    - question_evidence
    - multiple_attempts
  record_set_id: academic_results
  record_set_revision: 3
  manifest_contract_version: scoreform_academic_result_manifest_v1
  manifest_digest: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  academic_work_registration_revision: 2
```

The exact manifest verifies, the ScoreForm reader parses it, and student `"0017"` has attempt `2`.

### Result

```yaml
producer_source:
  source_record_kind: attempt
  manifest_local_item_id: student_0017_attempt_2
  native_revision: 2

native_attempt:
  attempt_identity_kind: attempt_number
  attempt_id_or_number: 2
  origin_or_kind: pds2_scan

subject_relationship:
  relationship_kind: attempt_subject
  relationship_authority: producer_native

candidate_evaluation:
  outcome: eligible
  matched_requirement_ids:
    - showcase_selected_response_result
  eligible_section_ids:
    - assessment_evidence

candidate:
  candidate_id: cand_57f0b1c9e2504d5991822e1f8fdd2115
  representation_kind: result_projection
```

### Preserved boundary

The Candidate is not selected and attempt `2` is not declared official or Grade-bearing.

## 3. Stale catalog row

The catalog proposes:

```yaml
publication_id: pub_22222222222222222222222222222222
```

Canonical reload returns no Publication Record.

### Result

```yaml
discovery_finding:
  finding_kind: catalog_candidate_drifted
  canonical_reload_outcome: canonical_publication_missing

candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - candidate_drift
    - publication_missing
```

No Core Publication Source Reference and no Candidate are created.

## 4. Missing catalog with canonical data not judged invalid

The catalog database does not exist.

### Result

```yaml
discovery_run:
  catalog_observation: missing

discovery_finding:
  finding_kind: catalog_unavailable
  reason_codes:
    - catalog_missing
```

The system does not claim that canonical publications are absent or invalid.

No unbounded filesystem crawl occurs.

## 5. Manifest digest mismatch

The canonical Publication Record expects:

```yaml
manifest_digest: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

The observed digest differs.

### Result

```yaml
manifest_verification:
  outcome: digest_mismatch

candidate_evaluation:
  outcome: ineligible
  reason_codes:
    - manifest_digest_mismatch
```

The producer reader is not called. No Candidate is created. Vitrine does not overwrite the file.

## 6. Missing producer Profile

Core reload succeeds, but no installed `PublicationProducerProfile` exists for the producer.

### Result

```yaml
availability:
  producer_profile: missing
  adapter: not_evaluated
  reader: not_evaluated

candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - producer_profile_missing
```

This differs from an incompatible Profile and from a missing Vitrine adapter.

## 7. Compatible Profile with missing Vitrine adapter

The Core producer Profile supports the publication exactly.

No Vitrine adapter claims the support key.

### Result

```yaml
availability:
  producer_profile: compatible
  adapter: missing

candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - adapter_missing
```

Vitrine does not use a generic JSON parser.

## 8. Adapter installed, producer reader missing

The Vitrine adapter is installed, but its producer public reader dependency is unavailable.

### Result

```yaml
availability:
  adapter: selected
  reader: missing

candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - reader_missing
```

The source is not labeled invalid. The deployment lacks the required reader.

## 9. Unsupported manifest contract version

The publication identifies:

```yaml
manifest_contract_version: scoreform_academic_result_manifest_v2
```

Only v1 is supported.

### Result

```yaml
availability:
  producer_profile: incompatible
  adapter: missing

candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - manifest_contract_unsupported
```

The system does not select v1 as “closest.”

## 10. Several ScoreForm attempts remain separate

The manifest contains:

```yaml
students:
  - student_id: "0017"
    attempts:
      - attempt_number: 1
        points_earned: 12
      - attempt_number: 2
        points_earned: 16
      - attempt_number: 3
        points_earned: 14
```

### Result

Three exact attempt source references may be evaluated:

```text
student_0017_attempt_1
student_0017_attempt_2
student_0017_attempt_3
```

No Candidate is automatically called:

- highest;
- latest for grading;
- replacement;
- official;
- or Grade-bearing.

A later Vitrine Selection may deliberately choose one representation. Meridian grading policy remains separate.

## 11. ScoreForm blank and ambiguous responses

Attempt `2` contains:

```yaml
responses:
  - question_number: 7
    response_state: blank
    selected_answer: null
    correct: false
  - question_number: 8
    response_state: ambiguous
    selected_answer: null
    correct: false
```

### Result

The result projection preserves both states.

It does not transform either response into an arbitrary answer or generic “wrong mark.”

## 12. ScoreForm standards remain alignments

Question `4` contains:

```yaml
standard_ids:
  - RL.CR.9-10.1
```

### Candidate standard reference

```yaml
standard_id: RL.CR.9-10.1
relationship_kind: alignment
source_authority: producer_native
```

The Candidate does not claim proficiency, mastery, or a standard rating.

## 13. ScoreForm student absent from manifest

Student `"0017"` does not appear in the exact manifest.

### Result

```yaml
candidate_evaluation:
  outcome: ineligible
  reason_codes:
    - source_not_found
```

Vitrine creates no zero, missing-work, incomplete, or placeholder attempt.

## 14. Historical ScoreForm publication and current successor

Publication `pub_old` explicitly precedes `pub_new`.

A previously created Candidate points to `pub_old`.

### Current refresh

```yaml
new_evaluation:
  supersedes_candidate_evaluation_id: ce_old
  availability:
    series: superseded
  outcome: conditionally_eligible
  reason_codes:
    - source_superseded
    - historical_reference_preserved
```

The old Candidate is not retargeted to `pub_new`.

A separate Candidate may be created from a source in `pub_new`.

## 15. Withdrawn publication retained historically

A Candidate was selected before its publication was withdrawn.

### Result

- Candidate history remains.
- The current Evaluation records `withdrawn`.
- Working use is reviewed under the Profile.
- An issued snapshot continues to cite the exact historical Candidate.
- The Publication Record and manifest are not deleted by Vitrine.

## 16. Quillan reader unavailable without private fallback

Core does not yet expose an accepted Quillan publication/reader contract.

### Result

```yaml
candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - manifest_contract_unsupported
    - reader_missing
```

Vitrine does not inspect:

```text
submissions/<student_id>/submission.json
submissions/<student_id>/review.json
```

## 17. Quillan rendered feedback and original work are separate

A future Quillan reader exposes:

```yaml
source:
  source_record_kind: submission
  source_record_id: sub_0032

representations:
  - representation_kind: original
    media_type: application/pdf
  - representation_kind: rendered_feedback
    media_type: application/pdf
```

### Result

Two separate representation references and Candidates may exist.

Permission to consider rendered feedback does not authorize the original work.

## 18. Quillan private note is excluded without leakage

The native review record contains private notes, but the public reader omits them.

### Result

- No private-note representation exists.
- No Candidate count includes it.
- No diagnostic says “one hidden private note.”
- No metadata field indicates its presence.
- The rendered feedback Candidate remains valid if otherwise permitted.

## 19. Concord individual Artifact Author Candidate

A future Concord reader exposes:

```yaml
artifact_instance_id: artinst_101
artifact_author:
  actor_reference:
    class_id: english10_p2
    student_id: "0017"
```

### Relationship assertion

```yaml
relationship_kind: artifact_author
relationship_authority: producer_native
supporting_record_refs:
  - artifact_author:author_77
```

The original artifact representation may become eligible under the Profile.

## 20. Concord Group Member without authorship

Student `"0017"` is a Group Member, but no Artifact Author or contribution record connects the student to `artinst_102`.

### Result

```yaml
candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - relationship_missing
```

Membership alone does not support an individual Artifact Candidate.

## 21. Concord group artifact with documented contribution

The artifact is Group-owned. Concord exposes a documented contribution record for student `"0017"`.

### Relationship assertion

```yaml
relationship_kind: documented_contributor
relationship_authority: producer_native
```

### Candidate condition

```yaml
condition_state: conditional
reason_codes:
  - multi_subject_review_required
  - collaborator_treatment_required
```

The Candidate remains a Group artifact; it is not relabeled individually owned.

## 22. Concord Group Score remains nonindividual

A Score targets:

```yaml
target_kind: group
target_id: grp_88
```

Student `"0017"` is a Group Member.

### Result

No `individual_score_target` assertion is created.

The Group Score does not become individual proficiency.

## 23. Concord standard-backed Score preserves native scale

A future public manifest exposes:

```yaml
score_record_id: score_211
score_kind: standard_backed
standard_id: 8.1.12.AP.1
scoring_scale_id: scale_collab_v2
scale_revision: 2
value: proficient
```

### Result

The source reference preserves:

- exact Criterion;
- exact scale lineage and revision;
- native value;
- Score target;
- evidence links;
- and moderation state.

Vitrine does not convert the value to points, percentage, or a universal four-level scale.

## 24. Portia publication suppressed from ordinary discovery

A catalog query happens to match a Portia intervention publication.

The selected Profile contains no specific permitted Portia projection.

### Result

The user-facing discovery response contains:

```text
0 visible Portia Candidates
0 hidden-result placeholders
0 Portia facets
0 Portia filenames
0 Portia diagnostic counts
```

An internal privacy-safe suppressed Evaluation may exist only when policy permits retaining it without existence leakage.

## 25. Future minimum-necessary Portia projection

A future regulated Profile explicitly requires one authorized support-status statement.

Conditions include:

- exact purpose;
- authorized teacher;
- exact Portfolio Subject;
- minimum-necessary public Portia projection;
- restricted audience;
- no original case narrative;
- and explicit review.

### Result

```yaml
representation_kind: producer_summary
privacy:
  restricted_source: true
  minimum_necessary_projection_required: true
  metadata_visibility: restricted
candidate_evaluation:
  outcome: conditionally_eligible
  reason_codes:
    - privacy_review_required
    - audience_review_required
```

The existence of this example does not activate a current Portia integration.

## 26. Original and accessible alternate representations

One producer source exposes:

```yaml
representations:
  - id: repr_original_pdf
    kind: original
    media_type: application/pdf
  - id: repr_accessible_html
    kind: accessible_alternate
    media_type: text/html
```

### Result

Each representation has a distinct Candidate ID.

The accessible alternate records its relationship to the original.

## 27. Identical bytes, distinct issuance identity

Two ScoreForm students receive sheets whose PDF bytes happen to be identical.

Their producer identities differ:

```text
issuance_A
issuance_B
```

### Result

The artifacts remain distinct.

Digest equality is not a deduplication command.

## 28. Two sources share a title

Two Concord artifacts are both titled “Community Resource Map.”

Their source IDs differ.

### Result

Both remain distinct Candidates.

Title is a display snapshot only.

## 29. Candidate source artifact later unavailable

The publication and manifest remain valid, but an exposed artifact file is missing.

### New Evaluation

```yaml
availability:
  manifest_integrity: verified
  producer_parse: parsed
  source_resolution: resolved
  artifact: missing

outcome: unresolved
reason_codes:
  - artifact_missing
```

The earlier Candidate history remains.

## 30. Publication later superseded

Candidate `cand_old` cites an exact old publication.

### Result

- `cand_old` remains historically valid.
- Its current Evaluation observes `superseded`.
- A source in the successor publication receives a new Candidate ID.
- Selection replacement requires Issue #8 records.

## 31. Portfolio Subject correction affects Candidate

The Portfolio Subject association used to resolve student `"0017"` is later invalidated.

### Result

```yaml
new_evaluation:
  outcome: unresolved
  reason_codes:
    - subject_relationship_conflict
    - subject_identity_correction_required
```

The Candidate is not silently moved to another Portfolio Subject.

## 32. Access allowed, audience disclosure unresolved

The actor is authorized to inspect and consider an artifact for an internal working Portfolio.

Public disclosure has not been reviewed.

### Result

```yaml
availability:
  authorization: allowed
  profile_eligibility: permitted
  disclosure_review: unresolved

candidate_evaluation:
  outcome: conditionally_eligible
```

The Candidate may be considered internally. It is not publicly releasable.

## 33. Profile permits summary but prohibits original

The exact Profile revision allows a producer summary and prohibits the source scan.

### Results

```yaml
summary_evaluation:
  outcome: eligible

original_scan_evaluation:
  outcome: ineligible
  reason_codes:
    - profile_prohibited
```

One permission does not flow to the other representation.

## 34. Candidate requires rights or collaborator review

A showcase Candidate contains artwork created with two students and an external image.

### Result

```yaml
privacy:
  contains_other_students: true
  rights_review_required: true

candidate_evaluation:
  outcome: conditionally_eligible
  reason_codes:
    - multi_subject_review_required
    - rights_review_required
```

The Candidate is not approved for issue.

## 35. Candidate re-evaluated under new Profile revision

The Portfolio explicitly migrates from Profile revision `2` to `3`.

The exact source remains unchanged, but Candidate scope includes the Profile binding.

### Result

A new Candidate is created under the new binding:

```text
cand_profile_rev2
cand_profile_rev3
```

The old Candidate remains attached to the historical Profile context.

## 36. Adapter projection version changes

The exact publication and producer source remain the same.

Vitrine adapter projection contract changes from `1` to `2`.

### Result

A new Candidate Evaluation records the new adapter and projection version.

The Candidate may remain the same only if the exact projected source endpoint and semantics remain unchanged and the current pointer is explicitly updated.

A semantic source-reference change requires a new Candidate.

## 37. Future Meridian report snapshot source

A future Meridian public reader exposes an immutable report snapshot:

```yaml
producer_module_id: meridian
source_record_kind: report_snapshot
source_record_id: report_2026_q1_0017
```

### Result

The report is evaluated as its own source family.

Vitrine does not substitute the report’s underlying ScoreForm, Quillan, or Concord sources for the report Candidate.

## 38. Candidate without Selection

A successful Candidate exists:

```yaml
candidate_id: cand_57f0b1c9e2504d5991822e1f8fdd2115
```

No Selection record references it.

### Result

The Portfolio remains unchanged.

Candidate eligibility does not cause:

- section placement;
- ordering;
- caption;
- reflection;
- or snapshot inclusion.

## 39. Selected historical Candidate in issued snapshot

A Selection and issued snapshot reference a Candidate whose publication later becomes historical.

### Result

The snapshot preserves:

- Candidate ID;
- exact Candidate Evaluation;
- Core Publication Source Reference;
- manifest digest;
- producer source and representation;
- subject relationship;
- Profile revision;
- and copied-byte provenance defined later by Issue #9.

A current UI may show that the upstream publication is superseded, but the snapshot bytes and provenance are not rewritten.

## 40. Catalog result order differs

The same catalog rows arrive in different SQLite orders on two rebuilds.

### Result

Vitrine applies an explicit deterministic ordering key.

The Candidate set and IDs do not depend on SQLite row order.

The ordering does not establish which publication is current.

## 41. Conflicting adapters claim the same support key

Two installed Vitrine adapters claim:

```yaml
producer_module_id: scoreform
publication_kind: academic_result_set
manifest_contract_version: scoreform_academic_result_manifest_v1
producer_contract_version: assignment_unversioned
```

### Result

```yaml
availability:
  adapter: conflict

candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - adapter_conflict
```

Package discovery order does not break the tie.

## 42. Registration revision mismatch

An academic Publication Record references registration revision `3`, but revision `3` is missing or identifies different work.

### Result

```yaml
availability:
  registration: mismatched

candidate_evaluation:
  outcome: ineligible
  reason_codes:
    - registration_mismatch
```

Current registration revision `4` is not substituted.

## 43. Intervention publication correctly has no registration

A future authorized intervention publication has:

```yaml
publication_kind: intervention_record_set
academic_work_registration_revision: null
```

### Result

The Core Publication Source Reference records:

```yaml
registration_availability: absent_by_contract
```

Vitrine does not fabricate a registration or academic intent.

## 44. Historical publication remains structurally valid

A publication is an explicit predecessor and its manifest still verifies.

### Result

```yaml
series_state: historical_predecessor
manifest_integrity: verified
```

Historical status is not a validation error.

Profile policy decides whether it may be considered for current working use.

## 45. Source record lacks a Core ModuleRecordRef

A producer manifest contains a durable attempt item, but native results rows do not have valid Core `ModuleRecordRef` identities.

### Result

```yaml
source_reference_kind: manifest_local_item
manifest_local_item_id: student_0017_attempt_2
```

Vitrine does not fabricate a Core record reference.

## 46. Array position is not identity

A producer manifest orders attempts in an array.

Attempt number `2` moves from array index `1` to index `2` in a later serialization while retaining its producer identity.

### Result

References continue to use attempt identity, not array position.

## 47. Same source evaluated for two Portfolios

The same authorized artifact is considered for:

- an improvement Portfolio;
- and a showcase Portfolio.

### Result

Two Candidates exist because Portfolio and Profile context differ.

The improvement Candidate may be eligible as current evidence while the showcase Candidate may require rights review.

## 48. Same source evaluated for two Portfolio Subjects

A Concord group artifact has documented contributions from two students.

### Result

Each Portfolio Subject receives a separate Candidate with:

- the same producer source;
- a distinct subject relationship assertion;
- distinct Portfolio context;
- and potentially different annotations later.

The artifact is not duplicated upstream.

## 49. Source filename changes

The producer changes a display filename while preserving exact artifact identity and revision semantics.

### Result

A display snapshot may change in a new Evaluation.

Filename change alone does not create a new source identity.

## 50. Source artifact revision changes

The producer exposes a corrected artifact revision with explicit lineage.

### Result

A new Producer Source or Artifact Reference and a new Candidate are created.

The earlier Candidate links to the source successor but is not rewritten.

## 51. Authorization denied before parse

The canonical publication is compatible and the manifest exists.

Authorization denies access for the requested Portfolio purpose.

### Result

```yaml
availability:
  authorization: denied
  manifest_integrity: not_evaluated
  producer_parse: not_evaluated

candidate_evaluation:
  outcome: ineligible
  reason_codes:
    - purpose_scope_denied
```

The manifest is not opened.

## 52. Authorization unknown

The deployment cannot resolve whether the actor may inspect the source.

### Result

```yaml
candidate_evaluation:
  outcome: unresolved
  reason_codes:
    - access_unknown
```

Unknown does not become allowed.

## 53. Multi-student artifact metadata restricted

A group artifact is known to include multiple students, but unauthorized viewers may not see collaborator identities.

### Result

The privacy metadata preserves:

```yaml
contains_other_students: true
metadata_visibility: restricted
```

User-facing diagnostics do not list collaborator names or IDs.

## 54. Source digest versus copied-byte digest

The Producer Source Artifact Reference records:

```yaml
source_byte_digest: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
```

A later snapshot copies and redacts the artifact.

Issue #9 records a different copied-byte digest.

### Preserved distinction

```text
manifest digest
  != source artifact digest
  != copied/redacted snapshot digest
```

## 55. Profile eligibility unresolved

The Profile has a conditional rule depending on a human rights review.

The review does not yet exist.

### Result

```yaml
availability:
  profile_eligibility: unresolved

candidate_evaluation:
  outcome: conditionally_eligible
  reason_codes:
    - profile_rule_unresolved
    - rights_review_required
```

The condition is not silently treated as satisfied or not applicable.

## 56. Profile explicitly prohibits a source family

An internal-only teacher report is otherwise valid and authorized, but the showcase Profile prohibits teacher-internal reports.

### Result

```yaml
candidate_evaluation:
  outcome: ineligible
  reason_codes:
    - profile_prohibited
```

Producer validity remains intact.

## 57. Candidate correction

A Candidate was mistakenly projected as `rendered_feedback`, but the producer representation was actually `producer_summary`.

### Result

- Preserve the erroneous Candidate.
- Invalidate its current use through a new Evaluation.
- Create a corrected Candidate.
- Record actor, time, and reason.
- Later Selections are reviewed rather than silently retargeted.

## 58. Candidate Current Pointer

Candidate `cand_A` has three Evaluations:

```text
ce_A1 -> ce_A2 -> ce_A3
```

The explicit pointer says:

```yaml
candidate_id: cand_A
pointer_revision: 3
current_candidate_evaluation_id: ce_A2
```

### Result

`ce_A2` governs current use even though `ce_A3` has a later timestamp.

A pointer update requires an explicit reason.

## 59. Corrupt derived candidate index

The candidate search index is deleted or malformed.

### Result

Canonical Candidates, Evaluations, and pointers remain valid.

The index may be rebuilt.

No Candidate history is reconstructed from thumbnails or cached search rows.

## 60. Privacy-safe parse failure

The producer reader rejects one invariant.

### Acceptable diagnostic

```text
producer_validation_failed:
  producer=scoreform
  contract=scoreform_academic_result_manifest_v1
  code=attempt.responses.coverage
```

### Prohibited diagnostic

- full manifest JSON;
- student response list;
- student name;
- retained scan path;
- or exception dump containing private data.

## 61. Summary of exercised invariants

These examples demonstrate that:

- discovery is not candidacy;
- canonical Core state precedes trust;
- authorization precedes parsing;
- exact manifest verification precedes producer reading;
- producer readers preserve native semantics;
- Candidates are contextual and representation-specific;
- negative Evaluations do not create placeholder Candidates;
- attempts and standards are not prematurely interpreted;
- subject relationships remain typed;
- privacy and availability remain multidimensional;
- Portia is suppressed by default;
- historical source identity is preserved;
- current working use is explicit;
- and Selection and snapshot behavior remain later concerns.
