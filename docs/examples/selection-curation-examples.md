# Representative Selection and Curation Examples

## Status and use

These synthetic examples exercise the conceptual records in:

- [Selection, Ordering, Annotation, and Reflection Records](../design/selection-curation-records.md); and
- [ADR 0006: Selection, Ordering, Annotation, and Reflection](../decisions/0006-selection-ordering-annotation-and-reflection.md).

The examples are not final JSON Schema fixtures.

All people, classes, records, IDs, timestamps, and policies are fictional.

The examples preserve these boundaries:

```text
Candidate != Selection
Selection != Placement
Rationale != Annotation != Reflection
Approval != disclosure authorization
Composition Revision != snapshot
```

## Shared synthetic context

Unless an example states otherwise:

```yaml
portfolio_id: portfolio_elm_2026_showcase
portfolio_subject_id: subject_elm_0027
profile_binding_id: binding_showcase_r3
portfolio_profile_id: district_showcase
profile_revision: 3
student_actor: actor_student_0027
teacher_actor: actor_teacher_ela10
```

## 1. Student proposes and teacher accepts a showcase Candidate

```yaml
proposal:
  selection_proposal_id: proposal_0001
  candidate_id: candidate_quillan_story_r2
  candidate_evaluation_id: candidate_eval_quillan_story_4
  proposal_source: student
  proposer: actor_student_0027
  asserted_role: student
  proposed_section_ids: [creative_writing]
  rationale_id: rationale_0001

decision:
  selection_decision_id: decision_0001
  selection_proposal_id: proposal_0001
  decision: accepted
  decision_actor: actor_teacher_ela10
  asserted_role: teacher
  selection_rule_id: showcase_student_proposal_teacher_acceptance

selection:
  selection_id: selection_0001
  candidate_id: candidate_quillan_story_r2
  candidate_evaluation_id: candidate_eval_quillan_story_4
  selection_proposal_id: proposal_0001
  selection_decision_id: decision_0001
```

Result:

- the Proposal remains canonical;
- teacher acceptance remains a distinct Decision;
- the Selection binds the exact Candidate Evaluation;
- and student participation does not create public-release consent.

## 2. Student Proposal is rejected with rationale

```yaml
proposal:
  selection_proposal_id: proposal_0002
  candidate_id: candidate_scoreform_attempt_1
  proposal_source: student

decision:
  selection_decision_id: decision_0002
  decision: rejected
  reason_id: rationale_0002
```

Rationale: the Profile permits only one assessment-result summary, and a different attempt has already been selected.

Result:

- no positive Selection exists;
- the rejected Proposal remains historical;
- and the rationale is workflow provenance, not an audience-facing caption.

## 3. Changes requested creates a successor Proposal

```yaml
proposal_v1:
  selection_proposal_id: proposal_0003
  proposed_section_ids: [showcase]

decision:
  decision: changes_requested
  expected_successor_proposal: true

proposal_v2:
  selection_proposal_id: proposal_0004
  predecessor_proposal_id: proposal_0003
  proposed_section_ids: [growth_and_revision]
```

Result:

`proposal_0003` is not edited. The revised curation intent receives a new Proposal ID.

## 4. Teacher proposes where student participation is required

The Profile requires a student-authored Proposal for every showcase artifact.

```yaml
proposal:
  proposal_source: teacher
  proposer: actor_teacher_ela10
```

Result:

- the Proposal may be retained;
- activation is blocked with `selection_required_student_participation_missing`;
- and the system does not reinterpret the teacher as the student proposer.

## 5. System suggestion remains nonauthoritative

```yaml
proposal:
  proposal_source: system_suggestion
  proposer: vitrine_candidate_recommender
  candidate_id: candidate_quillan_poem_r1
```

Result:

The suggestion appears in a review queue but cannot create an active Selection without an authorized Decision.

## 6. Authorized direct teacher Selection

The parent-conference Profile permits direct teacher curation.

```yaml
selection:
  selection_id: selection_0006
  candidate_id: candidate_quillan_feedback_pdf_r1
  direct_selection_authority:
    profile_rule_id: conference_teacher_direct_selection
  selected_by: actor_teacher_ela10
  asserted_role: teacher
  selection_rationale_id: rationale_0006
```

Result:

Direct selection remains fully attributed and does not require an invented student Proposal.

## 7. Direct Selection attempted where Profile prohibits it

A showcase Profile requires student Proposal plus teacher acceptance.

A direct Selection fails with:

```text
selection_direct_workflow_not_permitted
```

No positive Selection is stored.

## 8. Duplicate active Selection is rejected

`candidate_quillan_story_r2` already has active `selection_0001` in the same Portfolio, Subject, and Profile Binding.

A second attempted Selection fails with:

```text
selection_duplicate_active
```

The UI should offer an additional Section Placement instead.

## 9. One Selection appears in two permitted sections

```yaml
selection_id: selection_0001
placements:
  - placement_id: placement_0001
    section_id: creative_writing
  - placement_id: placement_0002
    section_id: growth_and_revision
```

Result:

- one source-selection decision is preserved;
- each section appearance has separate Placement identity;
- and the Profile's repeated-use rule is validated.

## 10. Repeated placement is prohibited by Profile

The Profile says a selected item may appear in only one section.

Creating `placement_0002` fails with:

```text
section_repeated_use_not_permitted
```

The Selection remains active in its first section.

## 11. Requirement intent is not satisfaction

```yaml
placement_id: placement_0011
requirement_intent_ids:
  - evidence_of_revision
```

Result:

The Placement states curator intent. A separate Profile finding still evaluates whether the selected artifact actually satisfies `evidence_of_revision`.

## 12. Profile section order differs from item order

The Profile defines:

```yaml
sections:
  - growth_and_revision
  - creative_writing
  - assessment_context
```

Within `creative_writing`, the Arrangement defines:

```yaml
ordered_placement_ids:
  - placement_story
  - placement_poem
  - placement_script
```

Result:

Section order and item order remain separate authorities.

## 13. Immutable initial Section Arrangement

```yaml
section_arrangement_id: arrangement_creative_writing
arrangement_revision: 1
section_id: creative_writing
ordered_placement_ids:
  - placement_story
  - placement_poem
predecessor_revision: null
```

Result:

Revision 1 is immutable and complete.

## 14. Reorder creates a successor Arrangement

```yaml
section_arrangement_id: arrangement_creative_writing
arrangement_revision: 2
predecessor_revision: 1
ordered_placement_ids:
  - placement_poem
  - placement_story
reason_id: rationale_reorder_open_with_poem
```

Result:

No Placement position is edited in place.

## 15. Concurrent reorder conflict

Teacher and student both start from Arrangement revision 2.

```yaml
teacher_revision: 3
student_revision: 4
expected_current_revision: 2
```

The teacher's pointer update succeeds first.

The student's pointer update fails with:

```text
arrangement_current_pointer_conflict
```

Both immutable proposed revisions may remain available for deliberate reconciliation.

## 16. Arrangement contains the same Placement twice

```yaml
ordered_placement_ids:
  - placement_story
  - placement_story
```

Result:

Validation fails with `arrangement_duplicate_placement`.

## 17. Arrangement references a Placement from another section

A `creative_writing` arrangement references `placement_assessment_summary` assigned to `assessment_context`.

Result:

Validation fails with `arrangement_foreign_placement`.

## 18. Explicit empty section

```yaml
section_arrangement_id: arrangement_optional_appendix
arrangement_revision: 1
ordered_placement_ids: []
```

Result:

The empty list records deliberate empty arrangement state. It is not confused with a missing arrangement record.

## 19. Curator display title remains separate from producer title

Producer title snapshot:

```text
Narrative Assignment 3
```

Curator Presentation:

```yaml
selection_presentation_id: presentation_0019
presentation_revision: 1
display_title: The Last Light in Apartment 4B
presentation_class: family
```

Result:

The Candidate retains `Narrative Assignment 3`; the family-facing title is a separate curator record.

## 20. Source title changes after Presentation creation

A successor Candidate Evaluation reports the producer title as `Narrative Assignment 3 — Revised`.

Result:

- Presentation revision 1 remains unchanged;
- the Selection remains bound to its original Candidate Evaluation;
- and a curator may create Presentation revision 2 after review.

## 21. Public caption is drafted without public authorization

```yaml
presentation_class: public
short_caption: A revision-centered short story selected by the student.
```

Result:

The Presentation may exist as a draft. It does not authorize public disclosure or identify a permitted recipient.

## 22. Selection rationale is private workflow provenance

```yaml
reason_kind: representative_growth_evidence
text: This draft and revision pair best illustrates changes in narrative pacing.
```

Result:

The rationale supports teacher decision history. It is not automatically rendered in a family or public snapshot.

## 23. Annotation adds curator context

```yaml
annotation_id: annotation_0023
annotation_revision: 1
purpose: curator_context
target_type: selection
target_ids: [selection_0001]
content: Written during the opening unit and revised after peer and teacher feedback.
```

Result:

The text is Vitrine-authored context, not Quillan producer feedback or a source fact.

## 24. Annotation does not create proficiency

```yaml
purpose: standards_context
content: This piece demonstrates mastery of narrative structure.
```

Result:

The phrase remains curator interpretation. It does not create a Meridian proficiency result or Profile requirement finding.

## 25. Annotation revision preserves history

```yaml
annotation_revision_1:
  content: Revised after peer review.
annotation_revision_2:
  predecessor_revision: 1
  content: Revised after peer and teacher review.
```

Result:

Revision 1 remains available for historical Composition Revisions.

## 26. Student item Reflection

```yaml
reflection_id: reflection_0026
reflection_revision: 1
reflection_rule_id: showcase_item_reflection
prompt_id: why_this_piece
prompt_version: 2
author: actor_student_0027
asserted_role: student
scope: selection
target_ids: [selection_0001]
content_mode: inline_text
```

Result:

The Reflection is student interpretation attached to an exact Selection and prompt version.

## 27. Comparison Reflection for improvement Portfolio

```yaml
reflection_id: reflection_0027
reflection_revision: 1
reflection_rule_id: improvement_comparison
scope: comparison_set
target_ids:
  - selection_baseline
  - selection_intermediate
  - selection_current
target_order_semantics:
  roles:
    selection_baseline: baseline
    selection_intermediate: intermediate
    selection_current: current
```

Result:

All compared Selections and their roles are explicit.

## 28. Comparison Reflection omits one required target

The rule requires baseline and current evidence.

Only baseline is supplied.

Result:

Validation fails with `reflection_comparison_incomplete`.

## 29. Section Reflection

```yaml
scope: section
target_ids: [creative_writing]
prompt_id: section_theme
prompt_version: 1
```

Result:

The Reflection targets the exact Profile section under the exact Profile Binding.

## 30. Checkpoint Reflection

```yaml
scope: checkpoint
target_ids: [checkpoint_fall_conference]
```

Result:

Checkpoint identity remains separate from Portfolio and section identity.

## 31. Whole-Portfolio Reflection

```yaml
scope: portfolio
target_ids: [composition_revision_7]
```

Result:

The Reflection addresses one exact working composition, not an unspecified mutable Portfolio.

## 32. External-artifact Reflection

A student records a spoken reflection through a future producer-approved audio projection.

```yaml
content_mode: external_artifact_reference
external_reference:
  candidate_id: candidate_audio_reflection_r1
```

Result:

Vitrine references the exact Candidate. It does not copy bytes or infer authorship beyond the Candidate's relationships.

## 33. Reflection revised after teacher approval

```yaml
reflection_v1:
  reflection_revision: 1
approval:
  target_revision: 1
  decision: approved
reflection_v2:
  reflection_revision: 2
  predecessor_revision: 1
```

Result:

The approval remains attached to revision 1. Revision 2 requires review where Profile policy requires it.

## 34. Reflection prompt version changes

The Profile migrates from prompt version 2 to version 3.

Result:

- existing Reflection remains bound to version 2;
- no prompt text is silently replaced;
- and a required response to version 3 receives a new Reflection series or revision according to the final contract.

## 35. Reflection is not proof of growth

A student writes, “I improved my analysis.”

Result:

The statement remains Reflection content. Vitrine does not create a proficiency or verified-growth finding from the sentence alone.

## 36. Reflection is not confession or remorse

A regulated or sensitive workflow must not reinterpret free text as:

- confession;
- admission of responsibility;
- remorse;
- or compliance.

Such interpretations require separate authoritative processes and are outside Vitrine curation.

## 37. Teacher approves exact Selection

```yaml
curation_review_decision_id: review_0037
approval_rule_id: teacher_selection_review
target_type: selection
target_id: selection_0001
decision: approved
actor: actor_teacher_ela10
asserted_role: teacher
```

Result:

The review approves that exact Selection. It does not approve its public disclosure.

## 38. Changes requested on Reflection

```yaml
target_type: reflection_revision
target_id: reflection_0026
target_revision: 1
decision: changes_requested
required_follow_up: Address how the revision changed the intended audience.
```

Result:

A successor Reflection revision is expected; revision 1 remains unchanged.

## 39. Waiver without Profile authority is rejected

```yaml
decision: waived
approval_rule_id: required_student_acknowledgment
```

The Profile does not permit waiver.

Result:

Validation fails with `approval_waiver_not_permitted`.

## 40. Staged regulated review skeleton

```yaml
reviews:
  - approval_rule_id: teacher_completeness_review
    decision: approved
  - approval_rule_id: records_review
    decision: approved
  - approval_rule_id: institutional_authorization
    decision: changes_requested
```

Result:

The Portfolio is not institutionally approved. Earlier stage approvals remain exact and historical.

## 41. Approval applies to an earlier Composition Revision only

```yaml
approval:
  target_type: working_portfolio_composition_revision
  target_id: composition_showcase
  target_revision: 6
current_composition_revision: 7
```

Result:

Revision 7 is not approved automatically.

## 42. Composition Revision freezes exact curation state

```yaml
working_composition_id: composition_showcase
composition_revision: 7
active_selection_ids:
  - selection_story
  - selection_poem
  - selection_feedback
active_placement_ids:
  - placement_story_showcase
  - placement_poem_showcase
  - placement_story_growth
  - placement_feedback_context
section_arrangement_revisions:
  creative_writing: 4
  growth_and_revision: 3
  assessment_context: 2
reflection_revisions:
  - reflection_story: 2
  - reflection_comparison: 1
unresolved_obligations:
  - public_rights_review
```

Result:

The composition is coherent and reproducible but not ready for public issue while the rights review remains unresolved.

## 43. Composition hides an unresolved obligation

A Candidate requires collaborator review, but the composition omits that obligation.

Result:

Validation fails with `composition_unresolved_obligation_hidden`.

## 44. Composition references an inactive Selection

A withdrawn Selection appears in `active_selection_ids`.

Result:

Validation fails with `composition_inconsistent` or a more specific lifecycle diagnostic.

## 45. Composition current-pointer conflict

Two composition revisions are created from revision 7.

Only the first pointer update succeeds.

The second fails with:

```text
composition_current_pointer_conflict
```

No revision is deleted.

## 46. Explicit composition rollback

The curator deliberately returns the current pointer from revision 9 to revision 7 because revision 8 introduced an incorrect section mapping.

Result:

- revisions 8 and 9 remain historical;
- the pointer transition records actor and reason;
- and rollback is not represented as deletion.

## 47. ScoreForm has three attempt Candidates

```yaml
candidates:
  - candidate_scoreform_attempt_1
  - candidate_scoreform_attempt_2
  - candidate_scoreform_attempt_3
```

Result:

Vitrine does not choose attempt 3 because it is latest or attempt 2 because it has the highest points. The curator must make an explicit Profile-permitted Selection.

## 48. Portfolio attempt choice differs from Meridian grading policy

The showcase Portfolio selects ScoreForm attempt 1 because it supports a Reflection about early misconceptions.

Meridian grades attempt 3 under a recency policy.

Result:

Both decisions are valid within their separate authorities.

## 49. Quillan original work and feedback are separate Selections

```yaml
selections:
  - selection_id: selection_quillan_original
    candidate_id: candidate_quillan_original_r2
  - selection_id: selection_quillan_feedback
    candidate_id: candidate_quillan_feedback_pdf_r1
```

Result:

Feedback does not replace original work, and original work does not expose Quillan private review state.

## 50. Quillan selected evidence changes

Quillan publishes a successor original-work projection after the teacher changes producer-selected evidence.

Result:

- the old Candidate and Selection remain historical;
- Vitrine does not modify Quillan evidence state;
- and a new Candidate requires an explicit replacement Selection.

## 51. Concord confirmed individual Artifact

```yaml
candidate_relationships:
  artifact_author:
    person: subject_elm_0027
    authorship_mode: individual_author
    attribution_status: confirmed
```

Result:

The Candidate may be selected as individual work where Profile and privacy rules permit.

## 52. Concord Group Member without Artifact authorship

```yaml
relationships:
  group_membership: confirmed
  artifact_author: absent
```

Result:

Group Membership alone cannot support an individual-authorship Selection.

## 53. Concord disputed attribution

```yaml
artifact_author:
  authorship_mode: co_author
  attribution_status: disputed
```

Result:

The curation record preserves disputed status. A curator caption cannot convert it into confirmed authorship.

## 54. Concord recorder for Group

```yaml
artifact_author:
  authorship_mode: recorder_for_group
representation_status: multiple_named_positions
```

Result:

The Selection may represent Group documentation, but the recorder is not described as sole author of every position.

## 55. Concord Group Score selected as context

```yaml
score_target:
  target_type: group
  target_id: group_lab_4
```

Result:

The Score summary may be selected for Group context where permitted. It cannot be relabeled as the Portfolio Subject's individual Score or proficiency.

## 56. Portia-safe student reflection Selection

```yaml
candidate_id: candidate_portia_safe_reflection_r1
projection_kind: portia:portfolio_safe_projection
safe_kind: student_selected_reflection
```

Result:

The Selection references only the safe projection. No Event, determination, intervention, family, disability, or safety record is exposed.

## 57. Portia-safe projection is revoked

A later authorized Portia projection state marks the safe projection revoked.

Result:

- the historical Selection remains;
- current composition becomes unresolved or prohibited according to Profile policy;
- and Vitrine does not erase prior curation or reveal the underlying Portia source.

## 58. Selection withdrawn without replacement

```yaml
lifecycle_event:
  event_kind: withdrawn
  selection_id: selection_poem
  reason_id: student_changed_showcase_choice
```

Result:

- the Selection remains historical;
- active Placements are explicitly withdrawn or replaced;
- and new arrangements and composition are created.

## 59. Selection replaced and Placement recreated

```yaml
old_selection: selection_story_draft
new_selection: selection_story_revision
replacement_event:
  event_kind: replaced
  successor_selection_ids: [selection_story_revision]
```

Result:

New Placements reference the successor Selection. Old Placements and arrangements remain historical.

## 60. Selection invalidated for wrong Portfolio Subject

An imported curation record referenced `subject_elm_0028` instead of `subject_elm_0027`.

Result:

- invalidate the erroneous Selection;
- create or resolve the correct Candidate under the correct Subject;
- create a new Selection;
- and preserve downstream impact analysis.

## 61. Section Placement moved during Profile migration

Old Profile:

```text
section: best_work
```

New Profile:

```text
section: creative_showcase
```

Result:

- old Placement remains under the predecessor binding;
- new Placement references `creative_showcase` under the successor binding;
- and no section ID is edited in place.

## 62. Profile migration adds a student approval stage

The predecessor composition had teacher approval only.

The successor Profile requires student acknowledgment.

Result:

Teacher approval remains historically valid for the predecessor target. The successor composition remains incomplete until the student stage is satisfied.

## 63. Profile migration prohibits a previously selected projection

A successor Profile no longer permits `scoreform:question_evidence_summary`.

Result:

The old Selection remains historical. It is classified `prohibited_in_successor` and is omitted from successor active composition unless policy provides a lawful replacement.

## 64. Candidate Current Pointer advances after Selection

The selected Candidate receives a new current Evaluation because its source is now unavailable.

Result:

The Selection remains bound to the original Evaluation. Current-use diagnostics and composition validation use the new observation without retargeting the Selection.

## 65. Publication is withdrawn after Selection

Result:

- historical Selection remains valid provenance;
- new working use requires Profile and lifecycle review;
- and a prior issued snapshot would remain tied to its historical source under issue #9.

## 66. Same source with original-work and feedback representations

```yaml
candidates:
  - candidate_original
  - candidate_feedback
```

Result:

Each exact representation may receive its own Selection. Vitrine does not deduplicate them because they share a producer source.

## 67. One Selection receives two audience-intended Presentations

```yaml
presentations:
  - presentation_revision: 1
    presentation_class: family
  - presentation_revision: 2
    presentation_class: public
```

Result:

Each Presentation revision is explicit. Neither grants audience authorization; issue #10 decides which may be disclosed.

## 68. Approval sequence is out of order

The Profile requires teacher review before institutional review.

An institutional reviewer attempts approval first.

Result:

Validation fails with `approval_sequence_invalid`.

## 69. Quorum approval is incomplete

A regulated stage requires two authorized reviewers.

Only one approval exists.

Result:

The exact approval records remain valid, but the stage remains incomplete with `approval_quorum_unmet`.

## 70. Derived section index is deleted and rebuilt

Canonical records still contain:

- active Selection lifecycle;
- active Placements;
- current Arrangement pointers;
- and current Composition pointer.

Result:

The section index is rebuilt without changing curation history.

## 71. Working Composition becomes exact snapshot input

A later snapshot request identifies:

```yaml
working_composition_id: composition_showcase
composition_revision: 7
```

Result:

Issue #9 may retrieve exact selected representations and copy bytes from this immutable curation input. It must not silently use current composition revision 8.

## 72. Historical Composition remains reviewable after successor

Composition revision 7 is superseded by revision 8.

Result:

Revision 7 remains resolvable for:

- historical approval;
- prior snapshot provenance;
- curation diff;
- and audit.

## Coverage summary

These examples demonstrate:

- Proposal and Decision separation;
- direct and proposal-based Selection;
- rejected and changes-requested history;
- repeated Placement without duplicate Selection;
- deterministic immutable ordering;
- concurrency conflicts;
- producer-versus-curator title separation;
- distinct rationale, Annotation, and Reflection;
- prompt and target versioning;
- exact-revision approval;
- whole-Portfolio composition;
- ScoreForm attempt boundaries;
- Quillan evidence boundaries;
- Concord relationship and Group boundaries;
- Portia-safe projection limits;
- Profile migration;
- source lifecycle changes;
- replacement and invalidation;
- derived-index rebuildability;
- and exact handoff to later snapshot construction.
