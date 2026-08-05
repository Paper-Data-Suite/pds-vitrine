# Representative Portfolio Profile Examples

- **Issue:** #5, “Define portfolio profiles and versioned requirements”
- **Example date:** 2026-08-04
- **Status:** Synthetic conceptual examples; not final JSON, executable fixtures, legal guidance, or operational policy

## 1. Purpose and notation

These examples exercise the [Versioned Portfolio Profile contract](../design/portfolio-profile-contract.md) and proposed [ADR 0003](../decisions/0003-versioned-portfolio-profiles.md).

All organizations, programs, people, identifiers, dates, and records are synthetic.

The examples use abbreviated YAML-like notation. Omitted fields remain required by the full conceptual contract where applicable.

Common abbreviations:

```text
family  = Portfolio Profile Family
series  = Portfolio Profile series
revision = immutable Portfolio Profile Revision
binding = Portfolio Profile Binding
finding = Requirement finding
```

No example grants access, creates an approval, calculates a Grade, or certifies compliance.

## 2. Improvement Profile with baseline, intermediate, and current evidence

```yaml
profile_family_id: pfam_growth
portfolio_profile_id: pprof_growth_english
profile_revision: 1
purpose:
  kind: improvement
  statement: Explain change in analytical writing across one course.
sections:
  - section_id: baseline
    obligation: required
    minimum_selections: 1
    maximum_selections: 1
  - section_id: intermediate
    obligation: optional
    maximum_selections: 2
  - section_id: current
    obligation: required
    minimum_selections: 1
    maximum_selections: 1
selection_rules:
  - selection_rule_id: select_growth_sequence
    required_portfolio_roles: [baseline, current]
    rationale_required: true
reflection_rules:
  - reflection_rule_id: compare_baseline_current
    scope_kind: item_comparison
    author_roles: [student]
    obligation: required
```

Expected behavior:

- the Profile requires one baseline and one current item;
- the student must explain the comparison;
- later candidate and selection contracts decide which exact artifacts satisfy the roles;
- no rule chooses the highest or latest producer result automatically;
- no Grade or proficiency result is created.

## 3. Showcase Profile with limited and public audiences

```yaml
portfolio_profile_id: pprof_showcase_creative_work
profile_revision: 1
purpose:
  kind: showcase
audience_rules:
  - audience_rule_id: school_exhibition
    audience_class: institutional_reviewer
    privacy_review_required: true
    rights_review_required: true
  - audience_rule_id: public_web
    audience_class: public
    privacy_review_required: true
    rights_review_required: true
    prohibited_document_classes:
      - teacher_private_note
      - secure_assessment_content
      - sensitive_intervention_record
approval_stages:
  - approval_stage_id: adviser_review
    stage_kind: review
  - approval_stage_id: public_issue_approval
    stage_kind: institutional_approval
    scope: audience_rule:public_web
```

Expected behavior:

- one working Portfolio may later produce separate school-exhibition and public snapshots;
- school approval does not authorize the public edition;
- selecting `public_web` does not verify recipients or consent;
- issue #10 must enforce actual disclosure controls.

## 4. Parent-conference Profile with family and internal variants

```yaml
portfolio_profile_id: pprof_conference_progress
profile_revision: 1
purpose:
  kind: parent_guardian_conference
sections:
  - section_id: strengths
    obligation: required
  - section_id: needs
    obligation: required
  - section_id: next_steps
    obligation: required
audience_rules:
  - audience_rule_id: teacher_preparation
    audience_class: teacher_internal
  - audience_rule_id: family_packet
    audience_class: parent_guardian
    prohibited_document_classes: [teacher_private_note]
    translation_requirements:
      mode: as_needed
approval_stages:
  - approval_stage_id: family_packet_review
    stage_kind: privacy_review
```

Expected behavior:

- the internal preparation view may contain material not allowed in the family packet;
- family relationship and access rights remain external authorization questions;
- the issued packet is dated and immutable under later snapshot contracts;
- post-conference notes do not rewrite the packet.

## 5. Generic regulated Profile skeleton

This example is deliberately not New Jersey-specific.

```yaml
profile_family_id: pfam_northland_certificate_review
portfolio_profile_id: pprof_northland_certificate_standard
profile_revision: 1
purpose:
  kind: regulated
applicability:
  jurisdiction: Synthetic State of Northland
  program_id: certificate_review
  cohorts: [cohort_2027]
  content_areas: [literacy]
  variant_id: standard
requirements:
  - requirement_id: eligibility_evidence
    kind: eligibility
    obligation: conditional
  - requirement_id: local_task_package
    kind: document
    obligation: required
    custody_treatment: local_retained
  - requirement_id: assurance_form
    kind: document
    obligation: required
    custody_treatment: submission_included
  - requirement_id: external_receipt
    kind: document
    obligation: optional
    custody_treatment: external_outcome
approval_stages:
  - approval_stage_id: institutional_assurance
    stage_kind: attestation_reference
retention_rules:
  - retention_rule_id: local_case_file
    classification_status: unresolved
```

Expected behavior:

- the Profile demonstrates generic jurisdiction, program, cohort, eligibility, local evidence, submission, approval, and retention extension points;
- no current jurisdictional rule is implied;
- the Profile cannot become operational until authority sources and restricted details are verified.

## 6. Conditional requirement evaluates to unknown

```yaml
requirement_id: alternate_language_copy
obligation: conditional
condition:
  predicate:
    name: authorized_translation_required
    operator: equals
    expected_value: true
```

Runtime context:

```yaml
authorized_translation_required: unknown
```

Expected finding:

```yaml
state: unresolved
condition_result: unknown
reason: Authoritative language-access determination is unavailable.
```

The requirement is not treated as false or not applicable.

## 7. Required, optional, prohibited, and conditional sections

```yaml
sections:
  - section_id: purpose_statement
    obligation: required
  - section_id: awards
    obligation: optional
  - section_id: teacher_private_notes
    obligation: prohibited
  - section_id: accessibility_appendix
    obligation: conditional
    condition:
      predicate:
        name: alternate_format_required
        operator: equals
        expected_value: true
```

Expected behavior:

- absence of `awards` is not missing;
- presence of `teacher_private_notes` creates `prohibited_present` for the scoped audience;
- unknown accessibility status creates an unresolved condition.

## 8. Document retained locally but excluded from submission

```yaml
requirement_id: scored_source_tasks
requirement_kind: document
obligation: required
document_class: institution_record
custody_treatment: local_retained
representation_modes: [reference]
audience_rule_ids: [institutional_review]
```

A separate requirement states:

```yaml
requirement_id: submission_summary_sheet
custody_treatment: submission_included
```

Expected behavior:

- source tasks must exist locally;
- they are not copied into the external submission merely because they are required;
- the submitted summary and local evidence remain distinct document classes.

## 9. Reflection required for each selected item

```yaml
reflection_rule_id: item_reflection
obligation: required
author_roles: [student]
scope_kind: selected_item
minimum_count: 1
```

Conceptual cardinality:

```text
one required reflection per selected item
```

Expected behavior:

- the Profile defines the rule;
- issue #8 defines each reflection record and item relationship;
- a missing reflection produces a finding, not an automatically generated student statement.

## 10. Sequential teacher and institutional approval

```yaml
approval_stages:
  - approval_stage_id: teacher_review
    stage_kind: review
    sequence: 1
    required_actor_roles: [teacher]
  - approval_stage_id: institution_issue_approval
    stage_kind: institutional_approval
    sequence: 2
    required_actor_roles: [program_administrator]
```

Expected behavior:

- stage 2 cannot be satisfied before stage 1 under this Profile;
- the Profile does not fabricate either approval;
- actor authentication and authority remain outside the Profile record.

## 11. Audience change requires reapproval

Initial state:

```yaml
active_audience_rule: school_exhibition
approvals_present: [adviser_review]
```

Requested change:

```yaml
target_audience_rule: public_web
```

Profile rule:

```yaml
reapproval_triggers:
  - audience_rule_changed
required_approval_stage_ids:
  - public_issue_approval
  - rights_review
  - privacy_review
```

Expected behavior:

- the prior adviser review remains historical;
- it does not satisfy the public approval stages;
- public issuance remains blocked or unresolved until new records exist.

## 12. Profile revision adds a new section

Revision 1:

```yaml
portfolio_profile_id: pprof_growth_english
profile_revision: 1
sections: [baseline, current]
```

Revision 2:

```yaml
portfolio_profile_id: pprof_growth_english
profile_revision: 2
predecessor_revision: 1
sections: [baseline, feedback_context, current]
```

The new requirement is:

```yaml
requirement_id: feedback_context_required
obligation: required
scope: section:feedback_context
```

Expected behavior:

- revision 1 remains immutable;
- revision 2 does not change Portfolios still bound to revision 1;
- the new section requires explicit migration.

## 13. Working Portfolio explicitly migrates

Before migration:

```yaml
portfolio_id: port_synthetic_growth_01
binding_id: pbind_growth_r1
profile_revision: 1
status: active
```

Migration analysis:

```yaml
unchanged: [baseline_required, current_required]
added: [feedback_context_required]
removed: []
materially_changed: []
reapproval_required: [teacher_review]
```

After migration:

```yaml
binding_id: pbind_growth_r2
profile_revision: 2
predecessor_binding_id: pbind_growth_r1
status: active
```

Expected behavior:

- the old binding becomes superseded, not deleted;
- existing selections are preserved but not automatically declared sufficient;
- a new finding identifies the missing feedback-context requirement.

## 14. Issued snapshot remains on predecessor revision

Historical snapshot:

```yaml
snapshot_id: snap_growth_2026_05
portfolio_profile_binding_id: pbind_growth_r1
portfolio_profile_id: pprof_growth_english
profile_revision: 1
```

Current working Portfolio:

```yaml
portfolio_profile_binding_id: pbind_growth_r2
profile_revision: 2
```

Expected behavior:

- the snapshot remains tied to revision 1;
- the new section in revision 2 is not retroactively missing from the historical snapshot;
- a new issued edition would reference revision 2.

## 15. Two simultaneous variants are not revisions

```yaml
profile_family_id: pfam_certificate_review
series:
  - portfolio_profile_id: pprof_certificate_standard
    variant_id: standard
    profile_revision: 1
  - portfolio_profile_id: pprof_certificate_streamlined
    variant_id: streamlined
    profile_revision: 1
```

Expected behavior:

- both series may be active for the same dates;
- streamlined is not revision 2 of standard;
- applicability or explicit human choice selects the appropriate series.

## 16. Flattened institutional base plus local overlay

Component 1:

```yaml
portfolio_profile_id: pprof_showcase_institutional_base
profile_revision: 3
requirements:
  - requirement_id: privacy_review
  - requirement_id: rights_review
```

Component 2:

```yaml
overlay_id: overlay_riverview_showcase
revision: 2
adds:
  - requirement_id: local_branding_review
```

Effective revision:

```yaml
portfolio_profile_id: pprof_riverview_showcase
profile_revision: 1
component_revisions:
  - pprof_showcase_institutional_base@3
  - overlay_riverview_showcase@2
requirements:
  - privacy_review
  - rights_review
  - local_branding_review
```

Expected behavior:

- the effective revision is self-contained;
- later changes to either component do not alter it;
- component identities and future digests remain recorded.

## 17. Overlay conflict fails validation

Base rule:

```yaml
requirement_id: privacy_review
obligation: required
```

Local overlay:

```yaml
requirement_id: privacy_review
obligation: optional
```

No authoritative override permission exists.

Expected result:

```yaml
state: profile_composition_conflict
reason: Local overlay weakens a controlling required review.
```

No last-write-wins resolution occurs.

## 18. Restricted controlling source leaves Profile incomplete

```yaml
authority_sources:
  - authority_source_id: restricted_submission_dictionary
    access_status: restricted_unreviewed
    supports_requirement_ids:
      - submission_field_contract
known_limitations:
  - Exact submission fields and validation rules have not been reviewed.
```

Expected behavior:

- the Profile may remain a research template;
- affected requirements are `restricted_requirement_unverified`;
- operational binding and compliance claims are blocked;
- Vitrine does not guess fields.

## 19. Withdrawn Profile remains historically resolvable

Lifecycle events:

```yaml
- event_kind: activated
  profile_revision: 1
- event_kind: withdrawn
  profile_revision: 1
  reason: Controlling authority revoked the guidance.
```

Historical Portfolio:

```yaml
binding_id: pbind_old_program
profile_revision: 1
```

Expected behavior:

- new bindings to revision 1 are rejected;
- the historical binding, findings, and snapshots remain resolvable;
- withdrawal does not erase content.

## 20. Retention classification unresolved

```yaml
retention_rule_id: conference_packet
record_class: issued_parent_conference_snapshot
classification_status: unresolved
policy_owner: Synthetic Riverview Records Office
hold_behavior: preserve_when_hold_exists
disposition_approval_required: true
```

Expected behavior:

- the Profile records the unresolved classification;
- Vitrine does not invent a period or delete the packet;
- the records officer remains authoritative.

## 21. Explicit Portia exclusion

```yaml
requirement_id: ordinary_candidate_source_classes
requirement_kind: selection
prohibited_source_classes:
  - intervention_record_set
  - sensitive_behavior_support_projection
```

Expected behavior:

- ordinary candidate discovery does not reveal Portia titles, counts, previews, or existence;
- a later specialized Profile requires an exact reviewed projection and issue #10 authorization;
- no broad `allow_portia: true` escape hatch exists.

## 22. Concord group artifact requires explicit relationship

```yaml
selection_rule_id: group_artifact_showcase
required_source_relationships:
  - confirmed_author
  - documented_contributor
  - explicit_subject
  - student_authored_participation_statement
```

Expected behavior:

- Group Membership alone is insufficient;
- inclusion does not establish individual proficiency;
- collaborator privacy and rights review may still be required;
- Concord remains authoritative for actual relationships.

## 23. ScoreForm attempts require deliberate selection

Invalid Profile language:

```yaml
attempt_policy: latest
```

Reason for rejection:

- greatest attempt number may not mean official;
- latest timestamp may not mean Grade-bearing;
- producer publication preserves all attempts without selecting one.

Acceptable conceptual replacement:

```yaml
selection_rule_id: assessment_attempt_choice
actor_roles: [teacher, student]
student_selection_mode: shared
rationale_required: true
allowed_source_relationships: [exact_scoreform_attempt]
```

Expected behavior:

- a later selection record identifies the exact attempt and actor rationale;
- Meridian grading policy remains separate.

## 24. Profile completeness remains unapproved

Findings:

```yaml
required_machine_checkable:
  state: satisfied
prohibited_content:
  state: satisfied
institutional_issue_approval:
  state: missing
```

Derived summary:

```yaml
machine_checkable_complete: true
approval_complete: false
ready_to_issue: false
```

Expected behavior:

- the Portfolio is not described as approved;
- no snapshot is issued solely from the machine result;
- the responsible actor must supply the missing approval.

## 25. Research-only Profile cannot be operational

```yaml
portfolio_profile_id: pprof_research_future_cohort
profile_revision: 1
applicability_status: incomplete
known_limitations:
  - Complete controlling guidance is unavailable.
lifecycle_events: []
```

Expected behavior:

- structural validity does not create activation;
- no operational Portfolio Profile Binding may reference the revision;
- the document remains research input only.

## 26. Profile purpose kind does not create hidden rules

Two Profiles both use:

```yaml
purpose_kind: showcase
```

Profile A requires:

- student selection;
- public rights review;
- three sections.

Profile B requires:

- teacher curation;
- internal audience only;
- one section.

Expected behavior:

- both are valid showcase Profiles;
- no universal showcase defaults override their explicit rules.

## 27. Requirement ID continuity and replacement

Revision 1:

```yaml
requirement_id: student_final_reflection
statement: Student writes one final Portfolio reflection.
```

Revision 2, nonsemantic clarification:

```yaml
requirement_id: student_final_reflection
statement: Student writes one final reflection addressing the Portfolio as a whole.
```

The ID may remain stable if reviewers confirm equivalent meaning.

Revision 3, material change:

```yaml
requirement_id: student_item_reflections
statement: Student writes one reflection for every selected item.
replaces_requirement_id: student_final_reflection
```

Expected behavior:

- material change receives a new ID;
- migration can distinguish replacement from unchanged policy.

## 28. Condition dependency cycle is invalid

```yaml
requirement_a:
  condition: requirement_finding(requirement_b, satisfied)
requirement_b:
  condition: requirement_finding(requirement_a, satisfied)
```

Expected result:

```yaml
state: requirement_condition_cycle
```

The Profile cannot be activated.

## 29. Profile not effective for requested cohort

Profile applicability:

```yaml
cohorts: [cohort_2026]
effective_through: 2026-08-31
```

Requested Portfolio context:

```yaml
cohort: cohort_2027
binding_date: 2026-09-10
```

Expected result:

```yaml
state: profile_context_mismatch
```

Vitrine does not copy the prior cohort rules forward.

## 30. Deprecated revision remains bound until migration

Lifecycle:

```yaml
revision_1: deprecated
revision_2: activated
```

Existing Portfolio:

```yaml
profile_revision: 1
```

Expected behavior:

- the Portfolio remains on revision 1 unless policy explicitly prohibits continued use;
- the interface may recommend migration;
- no silent binding update occurs.

## 31. Profile source version changes without semantic rule change

Revision 1 cites a public guidance document updated only to correct a broken URL. Institutional review determines the operative requirements are unchanged.

Two permissible design outcomes are documented for later implementation review:

1. create revision 2 because source provenance changed; or
2. append a separately authorized source-maintenance event if the final contract permits nonsemantic source-location maintenance without changing activated content.

The implementation must choose one deterministic rule and preserve historical provenance. It must not mutate revision 1 silently.

## 32. Local retention rule cannot delete producer evidence

Profile rule:

```yaml
retention_rule_id: working_preview_cache
record_class: vitrine_derived_preview
minimum_duration: 30_days
```

Invalid action:

```text
delete Quillan submission because the Vitrine preview expired
```

Expected behavior:

- only the Vitrine-owned derived preview is in scope;
- producer and Core records remain untouched;
- disposition still requires appropriate authority where applicable.

## 33. Audience rule does not verify guardian status

```yaml
audience_rule_id: family_packet
audience_class: parent_guardian
```

Recipient supplied:

```yaml
name: Morgan Example
claimed_relationship: guardian
```

Expected behavior:

- the audience rule alone is insufficient;
- issue #10 or an institutional identity system must verify the relationship and disclosure authority;
- no packet is released from the claim alone.

## 34. Approval of working Portfolio does not approve exact issue package

Existing approval:

```yaml
scope: portfolio_working_state
approved_at: 2026-05-01T14:00:00Z
```

Later change:

```yaml
selected_item_added: true
snapshot_requested_at: 2026-05-03T10:00:00Z
```

Profile reapproval trigger:

```yaml
reapproval_triggers: [selected_item_added, snapshot_content_changed]
```

Expected behavior:

- prior review remains valid history;
- exact snapshot approval remains unsatisfied.

## 35. External outcome does not change Profile completeness retroactively

A regulated Portfolio was complete under its Profile and submitted. The external authority later rejects the submission for an external-system field mismatch.

Expected behavior:

- preserve the Profile findings at submission time;
- record the external rejection separately;
- do not rewrite the Profile requirement into a source-evidence failure without authority;
- correction uses a new submission event and, if policy changed, possibly a new Profile revision.

## 36. Cross-example invariants

These examples collectively demonstrate:

1. Profile purpose does not create hidden policy.
2. Family, series, revision, binding, and snapshot identities remain distinct.
3. Activated revisions are immutable.
4. Simultaneous variants are not revisions.
5. Unknown conditions remain unresolved.
6. Requirement identities support migration.
7. Composition is flattened and conflict-checked.
8. Audience declaration is not authorization.
9. Approval requirements do not create approvals.
10. Retention references do not execute deletion.
11. Local evidence and external submission remain separate.
12. Portia remains excluded by default.
13. Concord group relationships remain explicit.
14. ScoreForm attempt use remains deliberate consumer policy.
15. Completeness is not approval.
16. Research-only content is not operational.
17. Historical bindings and snapshots preserve exact Profile revisions.
