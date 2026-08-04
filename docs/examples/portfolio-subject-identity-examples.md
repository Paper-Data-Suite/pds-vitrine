# Portfolio Subject Identity: Representative Synthetic Examples

- **Issue:** #4, “Define portfolio identity, subject identity, and cross-class linking”
- **Date:** 2026-08-04
- **Status:** Conceptual examples; not final JSON Schema or production fixtures

## 1. Purpose

These examples exercise the identity decisions in:

- [Portfolio Subject identity design](../design/portfolio-subject-identity.md); and
- [ADR 0002](../decisions/0002-portfolio-subject-identity-and-roster-linking.md).

All names, identifiers, classes, timestamps, and records are synthetic.

The YAML-like blocks are illustrative. They show semantic fields and relationships rather than a final serialized contract.

## 2. Shared conventions

### 2.1 Synthetic actor

```yaml
actor_ref:
  actor_kind: local_teacher
  actor_id: teacher_demo_01
  display_snapshot: "Morgan Lee"
role_at_decision: portfolio_teacher
identity_authority_source: workspace_teacher_assignment
```

The actor ID is illustrative. Runtime authentication and authorization remain future work.

### 2.2 Exact roster reference

```yaml
roster_student_ref:
  school_year: "2026-2027"
  class_id: english10_p2
  student_id: "00107"
```

The complete historical reference includes school year. A bare `student_id` is never sufficient.

### 2.3 Nonauthoritative display snapshot

```yaml
person_display_snapshot:
  person_display_snapshot_id: pdsnap_demo_001
  captured_at: "2026-08-04T13:00:00-04:00"
  first_name: Avery
  last_name: Rivera
  preferred_name: null
  display_name: "Avery Rivera"
  source_kind: core_roster
```

The snapshot aids display only.

## 3. Example 1: one subject, one class association

### Source context

```yaml
core_class_metadata:
  class_id: english10_p2
  school_year: "2026-2027"

core_roster_row:
  class_id: english10_p2
  student_id: "00107"
  first_name: Avery
  last_name: Rivera
  period: "2"
```

### Vitrine records

```yaml
portfolio_subject:
  portfolio_subject_id: sub_demo_0001
  identity_status: active
  created_at: "2026-08-04T13:00:00-04:00"
  created_by: teacher_demo_01

subject_roster_association:
  subject_roster_association_id: sra_demo_0001
  portfolio_subject_id: sub_demo_0001
  roster_student_ref:
    school_year: "2026-2027"
    class_id: english10_p2
    student_id: "00107"
  display_snapshot_id: pdsnap_demo_0001
  status: confirmed
  confirmation_decision_id: idec_demo_0001

identity_decision:
  identity_decision_id: idec_demo_0001
  decision_type: confirm_association
  association_ids: [sra_demo_0001]
  decided_at: "2026-08-04T13:02:00-04:00"
  decided_by: teacher_demo_01
  role_at_decision: portfolio_teacher
  authority_source: workspace_teacher_assignment
  basis_type: direct_teacher_knowledge
  basis_summary: "Teacher confirmed the student from the active class roster."
```

### Expected behavior

- The subject is valid in the local Vitrine workspace.
- Candidate discovery may later consider this class only after separate authorization.
- The name is not the identity key.

## 4. Example 2: one student across two concurrent classes

Avery is enrolled in English and computer science during the same year.

### Second source context

```yaml
core_class_metadata:
  class_id: apcsp_p1
  school_year: "2026-2027"

core_roster_row:
  class_id: apcsp_p1
  student_id: "CSP-442"
  first_name: Avery
  last_name: Rivera
  period: "1"
```

### Additional confirmed association

```yaml
subject_roster_association:
  subject_roster_association_id: sra_demo_0002
  portfolio_subject_id: sub_demo_0001
  roster_student_ref:
    school_year: "2026-2027"
    class_id: apcsp_p1
    student_id: "CSP-442"
  display_snapshot_id: pdsnap_demo_0002
  status: confirmed
  confirmation_decision_id: idec_demo_0002

identity_decision:
  identity_decision_id: idec_demo_0002
  decision_type: confirm_association
  association_ids: [sra_demo_0002]
  decided_at: "2026-08-05T08:10:00-04:00"
  decided_by: teacher_demo_01
  role_at_decision: portfolio_teacher
  authority_source: workspace_teacher_assignment
  basis_type: direct_teacher_knowledge
  basis_summary: "Teacher confirmed that the AP CSP roster row represents the same student."
```

### Expected behavior

- One subject has two exact associations.
- Different student IDs do not prevent confirmation.
- English and AP CSP producer records remain in their owning classes.
- Confirmation does not automatically authorize discovery in both classes.

## 5. Example 3: one student across two school years with different IDs

### Prior-year source

```yaml
roster_student_ref:
  school_year: "2025-2026"
  class_id: english9_p7
  student_id: "09031"

display_snapshot:
  first_name: Avery
  last_name: Rivera
```

### Later-year source

```yaml
roster_student_ref:
  school_year: "2026-2027"
  class_id: english10_p2
  student_id: "00107"

display_snapshot:
  first_name: Avery
  last_name: Rivera
```

### Associations

```yaml
portfolio_subject_id: sub_demo_0001
confirmed_association_ids:
  - sra_demo_prior_year
  - sra_demo_0001
```

### Expected behavior

- Both associations remain independently confirmed.
- The different IDs are acceptable.
- The later year does not replace the prior-year reference.
- Longitudinal Portfolio views may later use both after authorization.

## 6. Example 4: same student ID in different classes, different people

### Roster A

```yaml
school_year: "2026-2027"
class_id: english10_p2
student_id: "00412"
first_name: Jordan
last_name: Kim
```

### Roster B

```yaml
school_year: "2026-2027"
class_id: english12_p6
student_id: "00412"
first_name: Taylor
last_name: Brooks
```

### Vitrine outcome

```yaml
portfolio_subjects:
  - portfolio_subject_id: sub_demo_jordan
    confirmed_ref: ["2026-2027", english10_p2, "00412"]
  - portfolio_subject_id: sub_demo_taylor
    confirmed_ref: ["2026-2027", english12_p6, "00412"]
```

### Expected behavior

- Repeated `student_id` does not merge the students.
- The exact references are different.
- A heuristic may not create a proposed match solely from the repeated ID.

## 7. Example 5: proposed name-based match remains unconfirmed

Two roster rows have the display name “Sam Patel.”

```yaml
association:
  subject_roster_association_id: sra_demo_proposal
  portfolio_subject_id: sub_demo_sam_1
  roster_student_ref:
    school_year: "2026-2027"
    class_id: english12_p4
    student_id: "8810"
  display_snapshot_id: pdsnap_demo_sam_2
  status: proposed

identity_decision:
  identity_decision_id: idec_demo_proposal
  decision_type: propose_association
  basis_type: automated_similarity_suggestion
  basis_summary: "Exact display-name match; confirmation required."
```

### Expected behavior

- The proposal does not unlock English 12 records.
- The proposal does not appear as confirmed identity in an issued snapshot.
- A teacher must confirm or reject it.
- Name matching never changes the state automatically.

## 8. Example 6: student name change

### Historical snapshot

```yaml
person_display_snapshot_id: pdsnap_demo_name_1
first_name: Riley
last_name: Chen
captured_at: "2025-09-05T09:00:00-04:00"
```

### Current snapshot

```yaml
person_display_snapshot_id: pdsnap_demo_name_2
first_name: Riley
last_name: Morgan
captured_at: "2026-09-04T09:00:00-04:00"
```

### Subject

```yaml
portfolio_subject_id: sub_demo_riley
identity_status: active
current_display_snapshot_id: pdsnap_demo_name_2
```

### Expected behavior

- Subject identity does not change.
- Historical Portfolio editions may continue to show the earlier authorized snapshot.
- The name difference neither invalidates nor confirms another association.

## 9. Example 7: roster removal with historical association preserved

### Historical confirmed association

```yaml
subject_roster_association_id: sra_demo_removed
status: confirmed
roster_student_ref:
  school_year: "2026-2027"
  class_id: english10_p5
  student_id: "01803"
```

### Current resolver result

```yaml
resolution:
  state: student_not_found
  checked_at: "2026-11-01T08:00:00-04:00"
  message: "The active roster no longer contains student_id 01803."
```

### Expected behavior

- The association remains historically confirmed.
- The subject and its Portfolios are not deleted.
- Live source access requiring the active row may be blocked.
- Vitrine must not substitute a similarly named row.

## 10. Example 8: correcting an incorrect association

A teacher originally associated subject `sub_demo_ana` with the wrong student ID.

### Incorrect association

```yaml
subject_roster_association_id: sra_demo_wrong
portfolio_subject_id: sub_demo_ana
roster_student_ref:
  school_year: "2026-2027"
  class_id: english10_p2
  student_id: "00218"
status: superseded
terminal_decision_id: idec_demo_supersede_wrong
```

### Correct successor association

```yaml
subject_roster_association_id: sra_demo_correct
portfolio_subject_id: sub_demo_ana
roster_student_ref:
  school_year: "2026-2027"
  class_id: english10_p2
  student_id: "00281"
status: confirmed
supersedes_association_ids: [sra_demo_wrong]
confirmation_decision_id: idec_demo_confirm_correct
```

### Decisions

```yaml
- identity_decision_id: idec_demo_supersede_wrong
  decision_type: supersede_association
  association_ids: [sra_demo_wrong, sra_demo_correct]
  basis_type: verified_sis_information
  basis_summary: "The original roster ID was transposed."

- identity_decision_id: idec_demo_confirm_correct
  decision_type: confirm_association
  association_ids: [sra_demo_correct]
  basis_type: verified_sis_information
  basis_summary: "Teacher verified the corrected exact roster row."
```

### Expected behavior

- The old endpoint is not edited.
- Both records remain auditable.
- Future resolution uses the corrected association.
- Existing selections are reviewed rather than silently retargeted.

## 11. Example 9: merging duplicate Portfolio Subjects

Two subjects were created independently for the same person.

### Predecessors

```yaml
subjects:
  - portfolio_subject_id: sub_demo_merge_a
    identity_status: merged
  - portfolio_subject_id: sub_demo_merge_b
    identity_status: merged
```

### Merge transition

```yaml
subject_identity_transition:
  subject_identity_transition_id: sit_demo_merge
  transition_type: merge
  predecessor_subject_ids:
    - sub_demo_merge_a
    - sub_demo_merge_b
  successor_subject_ids:
    - sub_demo_merge_c
  decided_at: "2026-10-15T15:30:00-04:00"
  decided_by: teacher_demo_01
  authority_source: workspace_teacher_assignment
  basis_summary: "Teacher verified that both subject records represent the same student."
  affected_portfolio_ids:
    - port_demo_growth_a
    - port_demo_showcase_b
```

### Successor

```yaml
portfolio_subject:
  portfolio_subject_id: sub_demo_merge_c
  identity_status: active

successor_associations:
  - subject_roster_association_id: sra_demo_merge_c_1
    portfolio_subject_id: sub_demo_merge_c
    roster_student_ref: ["2026-2027", english10_p2, "00107"]
    status: confirmed
    supersedes_association_ids: [sra_demo_merge_a_1]
  - subject_roster_association_id: sra_demo_merge_c_2
    portfolio_subject_id: sub_demo_merge_c
    roster_student_ref: ["2026-2027", apcsp_p1, "CSP-442"]
    status: confirmed
    supersedes_association_ids: [sra_demo_merge_b_1]
```

### Expected behavior

- A and B are preserved.
- C is a new subject, not a renamed predecessor.
- Existing Portfolios retain historical bindings.
- Continued active work uses explicit successor Portfolios bound to C.
- No issued snapshot is rewritten.

## 12. Example 10: splitting an incorrectly combined subject

One subject incorrectly contains associations for two different students.

### Erroneous predecessor

```yaml
portfolio_subject_id: sub_demo_combined
identity_status: split
association_ids:
  - sra_demo_person_x
  - sra_demo_person_y
```

### Split transition

```yaml
subject_identity_transition:
  subject_identity_transition_id: sit_demo_split
  transition_type: split
  predecessor_subject_ids:
    - sub_demo_combined
  successor_subject_ids:
    - sub_demo_person_x
    - sub_demo_person_y
  association_allocation:
    sra_demo_person_x:
      successor_subject_id: sub_demo_person_x
      successor_association_id: sra_demo_person_x_successor
    sra_demo_person_y:
      successor_subject_id: sub_demo_person_y
      successor_association_id: sra_demo_person_y_successor
  affected_portfolio_ids:
    - port_demo_combined_growth
```

### Expected behavior

- The predecessor remains in history.
- New subjects receive prospective identity use through new successor associations.
- Predecessor associations are explicitly superseded.
- Association endpoints are not rewritten.
- The affected Portfolio requires explicit review and successor creation.
- Artifact authorship is not inferred during allocation.

## 13. Example 11: Portfolio bound to the wrong subject

### Original Portfolio

```yaml
portfolio:
  portfolio_id: port_demo_wrong_subject
  identity_status: superseded
  subject_binding_id: psb_demo_wrong

portfolio_subject_binding:
  portfolio_subject_binding_id: psb_demo_wrong
  portfolio_id: port_demo_wrong_subject
  portfolio_subject_id: sub_demo_person_x
  status: invalidated
```

### Successor Portfolio

```yaml
portfolio:
  portfolio_id: port_demo_correct_subject
  identity_status: active
  subject_binding_id: psb_demo_correct
  supersedes_portfolio_id: port_demo_wrong_subject

portfolio_subject_binding:
  portfolio_subject_binding_id: psb_demo_correct
  portfolio_id: port_demo_correct_subject
  portfolio_subject_id: sub_demo_person_y
  status: active
```

### Expected behavior

- The original binding is never changed to person Y.
- The successor has a new Portfolio ID.
- Working selections require explicit migration or reconsideration.
- Issued editions of the predecessor remain historical records.

## 14. Example 12: issued snapshot association later invalidated

### Issued identity context

```yaml
issued_snapshot_identity:
  portfolio_id: port_demo_conference
  portfolio_subject_id: sub_demo_conference
  portfolio_subject_binding_id: psb_demo_conference
  roster_association_ids:
    - sra_demo_later_invalidated
  display_snapshot_ids:
    - pdsnap_demo_conference
  issued_at: "2026-10-20T16:00:00-04:00"
```

### Later decision

```yaml
identity_decision:
  decision_type: invalidate_association
  association_ids:
    - sra_demo_later_invalidated
  decided_at: "2026-10-22T09:15:00-04:00"
  basis_summary: "The association referred to a different student with the same name."
```

### Expected behavior

- Snapshot bytes remain unchanged.
- Current views show the identity integrity problem.
- Future access, withdrawal, or corrected reissue is explicit.
- The snapshot must not be silently relabeled with another student.

## 15. Example 13: Concord group artifact remains group-owned

### Confirmed Portfolio Subject

```yaml
portfolio_subject_id: sub_demo_group_member
confirmed_roster_ref:
  school_year: "2026-2027"
  class_id: apcsp_p1
  student_id: "CSP-510"
```

### Concord source facts

```yaml
concord_artifact:
  artifact_id: artifact_demo_robot
  represented_group_id: group_demo_07
  author_refs:
    - group_demo_07
  subject_refs:
    - group_demo_07
  individual_score_targets: []
```

### Expected Vitrine treatment

```yaml
portfolio_relationship:
  relationship_kind: group_member_context
  source_authority: concord
  individual_ownership_claim: false
  individual_proficiency_claim: false
```

### Expected behavior

- Roster identity does not make the student an Artifact Author.
- Group membership alone does not prove contribution.
- Portfolio inclusion requires later explicit source relationship and authorization.
- Vitrine does not create an individual Score target.

## 16. Example 14: Portia reference remains excluded

### Identity context

```yaml
portfolio_subject_id: sub_demo_sensitive
confirmed_roster_ref:
  school_year: "2026-2027"
  class_id: english10_p2
  student_id: "00731"
```

### Discoverable Core envelope

```yaml
publication:
  producer_module_id: portia
  publication_kind: intervention_record_set
  related_student_ref:
    class_id: english10_p2
    student_id: "00731"
```

### Expected behavior

- Matching identity does not authorize Portia access.
- Ordinary candidate results reveal no Portia title, count, preview, or filename.
- The record remains excluded unless a later purpose-specific, authorized opt-in path applies.
- Identity linking does not transform intervention material into academic evidence.

## 17. Example 15: duplicate active roster reference conflict

Two subjects improperly claim the same exact reference.

```yaml
exact_ref:
  school_year: "2026-2027"
  class_id: english10_p6
  student_id: "00901"

active_claims:
  - portfolio_subject_id: sub_demo_conflict_a
    association_id: sra_demo_conflict_a
  - portfolio_subject_id: sub_demo_conflict_b
    association_id: sra_demo_conflict_b
```

### Resolver result

```yaml
resolution:
  state: duplicate_active_association
  current_portfolio_subject_id: null
  required_action: explicit_reconciliation
```

### Expected behavior

- Do not choose the older or newer subject.
- Do not choose based on display name.
- Block ordinary current resolution.
- Require merge, split, invalidation, or supersession.

## 18. Example 16: same student ID reused in a later school year

```yaml
reference_1:
  school_year: "2025-2026"
  class_id: english9_p3
  student_id: "00444"

reference_2:
  school_year: "2026-2027"
  class_id: english9_p3
  student_id: "00444"
```

### Expected behavior

- These are different historical references because school year differs.
- Vitrine does not assume the class folder reuse is valid or that the person is the same.
- Current Core metadata must match the reference being confirmed.
- An authorized actor must confirm any longitudinal association.

## 19. Example 17: class metadata mismatch

### Proposed reference

```yaml
school_year: "2025-2026"
class_id: english10_p2
student_id: "00107"
```

### Current Core metadata

```yaml
class_id: english10_p2
school_year: "2026-2027"
```

### Expected result

```yaml
state: class_school_year_mismatch
confirmation_allowed: false
```

Vitrine does not silently rewrite the proposed year or treat current metadata as proof of historical context.

## 20. Example 18: cross-workspace identities remain separate

### Workspace A

```yaml
workspace: teacher_a_workspace
portfolio_subject_id: sub_local_0001
confirmed_ref: ["2026-2027", english10_p2, "00107"]
```

### Workspace B

```yaml
workspace: teacher_b_workspace
portfolio_subject_id: sub_local_0001
confirmed_ref: ["2026-2027", science10_p4, "SCI-77"]
```

### Expected behavior

- Equal opaque IDs in different workspaces do not prove identity.
- No cross-workspace merge occurs automatically.
- Institution-wide reconciliation requires a future authorized migration contract.

## 21. Cross-example validation matrix

| Requirement | Examples |
| --- | --- |
| One subject and one class | 1 |
| Concurrent cross-class association | 2 |
| Multi-year association with changed ID | 3 |
| Repeated ID for different people | 4 |
| Name proposal without confirmation | 5 |
| Name change | 6 |
| Historical association after roster removal | 7 |
| Association correction | 8 |
| Nondestructive merge | 9 |
| Nondestructive split | 10 |
| Wrong Portfolio subject correction | 11 |
| Issued snapshot preservation | 12 |
| Concord group boundary | 13 |
| Portia deny-by-default boundary | 14 |
| Duplicate active-reference conflict | 15 |
| Later-year ID reuse | 16 |
| School-year validation | 17 |
| Workspace scope | 18 |

## 22. Assertions for later automated fixtures

A later serialized test suite should translate these examples into assertions such as:

- bare `student_id` references are rejected;
- leading-zero IDs round-trip unchanged;
- proposed associations cannot resolve as confirmed;
- exact duplicate active references are rejected or reported as conflicts;
- association endpoints cannot be edited;
- merge and split graphs reject cycles;
- one Portfolio cannot have two active subject bindings;
- name changes do not change subject identity;
- current source failure does not delete historical association;
- and identity confirmation never changes Concord or Portia semantics.
