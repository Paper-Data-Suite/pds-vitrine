# Representative Privacy, Redaction, and Audience Examples

## Status and use

These synthetic examples exercise the conceptual records in:

- [Privacy, Redaction, and Audience Controls](../design/privacy-redaction-audience-controls.md); and
- [ADR 0008: Privacy, Redaction, and Audience Controls](../decisions/0008-privacy-redaction-and-audience-controls.md).

The examples are not final JSON Schema fixtures, legal determinations, consent forms, or production authorization decisions.

All people, classes, organizations, records, IDs, timestamps, and policies are fictional.

The examples preserve these boundaries:

```text
discovery != access
Audience Context != Recipient Scope
role assertion != verified authority
Selection != consent
redaction != de-identification
Issuance != delivery != receipt != acceptance
revocation != external recall
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
parent_actor: actor_parent_017
external_reviewer_actor: actor_reviewer_009
audience_context_student: audience_student_r3
audience_context_family: audience_family_r3
audience_context_teacher: audience_teacher_internal_r3
audience_context_reviewer: audience_external_reviewer_r3
audience_context_public: audience_public_r3
```

The examples use shortened digests for readability. A final contract would require complete lowercase SHA-256 values.

## 1. Safe catalog result does not grant source access

```yaml
authorization_request:
  authorization_request_id: auth_req_0001
  actor_reference: actor_teacher_ela10
  asserted_role: teacher
  requested_action: discover_metadata
  target_type: core_catalog_query
  purpose: curate_showcase

authorization_decision:
  authorization_decision_id: auth_dec_0001
  decision: allowed
  permitted_target_scope:
    fields: [safe_display_title, producer_family]

source_access_request:
  authorization_request_id: auth_req_0002
  requested_action: read_source_representation
  target_references: [source_quillan_story_private]

source_access_decision:
  authorization_decision_id: auth_dec_0002
  decision: denied
  denial_reason_code: actor_scope_mismatch
```

Result:

- bounded discovery may return safe metadata;
- source content remains closed;
- and the UI must not convert the discovery result into a working download link.

## 2. Suppressed Portia source produces no existence signal

```yaml
query:
  actor_reference: actor_teacher_ela10
  requested_action: discover_metadata
  producer_filter: portia

internal_result:
  matching_sources: 1
  source_disposition: suppressed

external_result:
  visibility_level: no_existence_disclosure
  result_count: 0
  hidden_result_indicator: false
```

Result:

- ordinary output is indistinguishable from no matching source;
- no title, producer name, count, or denial reason is revealed;
- and restricted diagnostics remain separately authorized.

## 3. Student may view selected work but not teacher-private feedback

```yaml
student_request:
  requested_action: inspect_snapshot_edition
  target_references: [edition_student_4]
  audience_context_id: audience_student_r3
  recipient_scope_id: recipient_subject_0027

disclosure_review:
  included: [entry_original_story, entry_student_reflection]
  excluded: [entry_teacher_private_note]
  outcome: approved_as_is
```

Result:

- the student receives only approved subject-facing content;
- teacher-private content is not represented as an omission notice;
- and the internal manifest remains restricted.

## 4. Student requests a Group Artifact containing identifiable peers

```yaml
candidate:
  candidate_id: candidate_concord_group_lab
  authorship_mode: collective_group_author
  identifiable_people: [subject_0027, subject_0031, subject_0044]

review:
  disclosure_review_id: disclosure_review_0004
  audience_context_id: audience_student_r3
  recipient_scope_id: recipient_subject_0027
  outcome: redaction_required
  findings:
    - collaborator_permission_missing: subject_0031
    - collaborator_permission_missing: subject_0044
```

Result:

- Portfolio Subject status does not grant access to peer information;
- Group Membership is not disclosure permission;
- and the artifact is withheld until a safe representation is verified.

## 5. Parent conference Edition is not a complete records-access response

```yaml
recipient_scope:
  recipient_scope_id: recipient_parent_conference_017
  recipient_type: parent_or_guardian
  relationship_type: current_guardian
  purpose: scheduled_parent_conference

edition:
  snapshot_series_id: series_parent_conference
  snapshot_edition: 2
  included_entries: [entry_work_sample, entry_student_reflection, entry_family_summary]
  excluded_internal_classes: [teacher_private_note, internal_manifest, unrelated_source]
```

Result:

- the package is purpose-limited;
- it does not claim to satisfy a formal inspection/review request;
- and broader records access remains an institutional workflow outside Vitrine.

## 6. Parent relationship evidence is expired

```yaml
authority_evidence_reference:
  authority_evidence_reference_id: evidence_guardian_017_r2
  evidence_type: parent_guardian_relationship
  status_snapshot: expired
  expires_at: 2026-06-30T23:59:59-04:00

authorization_decision:
  decision: expired
  effective_at: 2026-08-05T18:00:00-04:00
```

Result:

- previous relationship evidence remains historical;
- future disclosure is blocked;
- and a fresh authoritative relationship reference is required.

## 7. Rights-holder status changes under institutional policy

```yaml
prior_evidence:
  authority_evidence_reference_id: evidence_parent_rights_r1
  evidence_type: rights_holder_status
  status_snapshot: valid

successor_evidence:
  authority_evidence_reference_id: evidence_student_rights_r2
  evidence_type: rights_holder_status
  status_snapshot: valid
  effective_at: 2026-07-01T00:00:00-04:00

new_recipient_scope:
  recipient_type: portfolio_subject
  relationship_type: current_rights_holder
```

Result:

- earlier disclosures retain their original authority evidence;
- future actions use the successor evidence;
- and Vitrine does not decide the legal transfer itself.

## 8. Teacher requests another teacher’s Portfolio

```yaml
request:
  actor_reference: actor_teacher_ela10
  asserted_role: teacher
  requested_action: inspect_snapshot_edition
  target_references: [edition_math_teacher_internal_3]
  purpose: general_interest

evidence:
  employment_assignment:
    classes: [class_ela10_a, class_ela10_b]

decision:
  decision: denied
  denial_reason_code: actor_scope_mismatch
```

Result:

- teacher status alone is insufficient;
- class and purpose scope are evaluated;
- and no artifact metadata beyond a privacy-safe denial is returned.

## 9. External reviewer receives one exact non-browsable package

```yaml
recipient_scope:
  recipient_scope_id: recipient_reviewer_case_44
  recipient_type: external_reviewer
  recipient_references: [actor_reviewer_009]
  purpose: scholarship_review
  valid_until: 2026-08-12T17:00:00-04:00

disclosure_authorization:
  snapshot_series_id: series_scholarship_44
  snapshot_edition: 1
  export_artifact_ids: [export_pdf_44, export_zip_44]
  permitted_channel_classes: [secure_portal]

reviewer_capabilities:
  candidate_search: false
  source_browsing: false
  historical_editions: false
```

Result:

- access is exact-package only;
- authorization is time- and purpose-bounded;
- and source-system browsing remains unavailable.

## 10. Reviewer authorization expires after an earlier download

```yaml
authorization:
  disclosure_authorization_id: disclosure_auth_0010
  valid_until: 2026-08-08T17:00:00-04:00

prior_event:
  disclosure_event_id: disclosure_event_0010_a
  event_kind: downloaded
  occurred_at: 2026-08-07T11:15:00-04:00
  outcome: completed

later_request:
  occurred_at: 2026-08-09T09:00:00-04:00
  outcome: denied
  failure_code: disclosure_authorization_expired
```

Result:

- prior lawful access remains recorded;
- future access is blocked;
- and expiration does not claim that the downloaded copy disappeared.

## 11. Regulated submission binds exact authority and destination

```yaml
audience_context:
  audience_class: regulated_submission
  purpose: alternate_graduation_pathway_submission

recipient_scope:
  recipient_type: regulated_authority
  recipient_organization_reference: authority_state_review_unit
  relationship_type: designated_submission_destination

submission_authorization:
  snapshot_series_id: series_regulated_case_18
  snapshot_edition: 5
  export_artifact_ids: [export_regulated_zip_5]
  permitted_channel_classes: [regulated_portal]
```

Result:

- exact destination and package are bound;
- generic external-reviewer authority is insufficient;
- and issue #11 supplies the concrete regulated checklist.

## 12. Public showcase has student consent but not collaborator permission

```yaml
student_consent:
  evidence_type: consent
  subject_scope: subject_0027
  purpose_scope: public_showcase
  status_snapshot: valid

artifact:
  candidate_id: candidate_concord_duet
  identifiable_people: [subject_0027, subject_0031]

review:
  outcome: redaction_required
  findings:
    - collaborator_permission_missing: subject_0031
```

Result:

- student consent covers only the consenting subject;
- co-authorship does not supply the collaborator’s permission;
- and public release remains blocked or requires a safe alternate representation.

## 13. A distinctive photo remains identifying after names are removed

```yaml
redaction_result:
  output_reference: entry_photo_no_names
  operations: [remove_caption_name, strip_filename_name]

deidentification_review:
  decision: not_deidentified
  indirect_identifier_classes_considered:
    - face
    - unique_costume
    - classroom_background
    - public_event_context
```

Result:

- direct-name removal is not enough;
- context and visual identifiers remain;
- and public disclosure is denied or requires further transformation.

## 14. Filename and embedded metadata leak identity

```yaml
visible_document:
  visible_student_name: false

file_properties:
  filename: "Avery_Rivera_Portfolio.pdf"
  pdf_author: "Avery Rivera"
  xmp_creator: "Avery Rivera"

review_findings:
  - direct_identifier: filename
  - direct_identifier: pdf_author
  - direct_identifier: xmp_creator

required_operations:
  - strip_embedded_metadata
  - replace_export_filename
```

Result:

- visible-page review alone is insufficient;
- metadata and filenames are part of the disclosure surface;
- and the final output digest is verified after cleanup.

## 15. ScoreForm summary allowed while answer key remains denied

```yaml
allowed_projection:
  projection_kind: scoreform:attempt_summary
  fields: [assignment_title, attempt_number, points_earned, points_possible]

prohibited_requests:
  - answer_key
  - detector_fill_values
  - scan_review_notes
  - retained_source_path

authorization_decision:
  decision: allowed
  permitted_target_scope:
    projection: scoreform:attempt_summary
    fields: [assignment_title, attempt_number, points_earned, points_possible]
```

Result:

- result access is field-allowlisted;
- assessment-security and operational data stay prohibited;
- and the summary is not labeled as a Grade or proficiency finding.

## 16. Quillan feedback allowed while private notes remain hidden

```yaml
allowed_candidate:
  projection_kind: quillan:student_feedback
  representation: student_feedback_pdf

excluded_native_fields:
  - private_notes
  - unselected_observations
  - candidate_evidence
  - duplicate_evidence
  - retained_source_path

review:
  outcome: approved_as_is
```

Result:

- only the student-facing producer projection is considered;
- private review state remains unavailable;
- and Vitrine does not inspect `review.json` directly.

## 17. Concord Group Artifact requires collaborator-specific redaction

```yaml
artifact:
  artifact_id: concord_artifact_group_17
  authorship_mode: co_author
  authors: [subject_0027, subject_0031]
  subjects: [subject_0027, subject_0031]

recipient_scope:
  recipient_type: parent_or_guardian
  portfolio_subject_id: subject_0027

redaction_plan:
  operations:
    - pseudonymize_identifier: subject_0031
    - remove_comment_or_annotation: peer_comment_31
    - suppress_provenance_detail: collaborator_contact_ref
```

Result:

- authorship relationships remain preserved internally;
- a recipient-specific representation is generated;
- and the redacted output does not imply sole authorship by subject_0027.

## 18. Concord discussion record cannot be safely isolated

```yaml
artifact:
  artifact_category: discussion_record
  representation_status: multiple_named_positions
  identifiable_people: [subject_0027, subject_0031, subject_0044]

isolation_review:
  outcome: not_safely_isolatable
  reason: positions lose meaning when other speakers are removed

disclosure_review:
  outcome: denied
```

Result:

- Vitrine does not fabricate an individual transcript;
- unsafe isolation blocks disclosure;
- and an authorized producer summary may be considered separately if Concord exposes one.

## 19. Portia-safe growth statement is disclosed without source-graph access

```yaml
candidate:
  projection_kind: portia:portfolio_safe_projection
  projection_revision: 2
  content_kind: teacher_approved_growth_statement

source_access:
  underlying_portia_event_graph: prohibited
  internal_portia_record_count: suppressed

disclosure_review:
  outcome: approved_as_is
```

Result:

- only the exact safe projection is visible;
- no Event, Account, intervention, or family record is exposed;
- and Vitrine cannot follow the projection back into the Portia graph.

## 20. Internal Snapshot Manifest is excluded from a family package

```yaml
snapshot_edition:
  snapshot_edition: 3
  internal_manifest_id: snapshot_manifest_family_3

family_export:
  export_artifact_id: export_family_pdf_3
  included_entries: [cover, work_sample, student_reflection, family_summary]
  excluded_entries: [internal_snapshot_manifest]

generated_provenance_entry:
  entry_id: family_safe_provenance_appendix
  source: reviewed_minimum_provenance_fields
```

Result:

- internal provenance remains canonical but restricted;
- audience-safe provenance is separately rendered and reviewed;
- and exclusion is not represented as missing data.

## 21. Redaction creates a successor Snapshot Edition

```yaml
source_edition:
  snapshot_series_id: series_showcase_public
  snapshot_edition: 1
  entry_digest: aaaa

redaction_result:
  input_digest: aaaa
  output_digest: bbbb
  status: completed

successor_edition:
  snapshot_series_id: series_showcase_public
  snapshot_edition: 2
  predecessor_edition: 1
  redacted_entry_digest: bbbb
```

Result:

- Edition 1 remains immutable;
- Edition 2 records the Redaction Result as Materialization provenance;
- and prior authorization does not silently carry forward.

## 22. Redaction succeeds mechanically but verification fails

```yaml
redaction_result:
  redaction_result_id: redaction_result_0022
  status: completed
  output_digest: cccc

verification:
  redaction_verification_decision_id: redaction_verify_0022
  reviewed_output_digest: cccc
  decision: rejected
  findings:
    - hidden_text_layer_contains_name
    - pdf_reading_order_broken
```

Result:

- the output is not distributable;
- completed transformation is not equivalent to verified safety;
- and a corrected Result requires new bytes and verification.

## 23. De-identification is adequate internally but not publicly

```yaml
output:
  output_digest: dddd

internal_review:
  audience_context_id: audience_district_research
  decision: deidentified_for_context

public_review:
  audience_context_id: audience_public_r3
  decision: not_deidentified
  limitations: small program and unique project topic
```

Result:

- de-identification is context-specific;
- one favorable decision does not become a universal anonymous flag;
- and public release remains blocked.

## 24. Consent covers Edition 1 but not Edition 2

```yaml
consent_reference:
  evidence_type: consent
  record_scope:
    snapshot_series_id: series_showcase_public
    snapshot_editions: [1]
  purpose_scope: public_showcase

requested_disclosure:
  snapshot_edition: 2

decision:
  decision: denied
  denial_reason_code: consent_scope_mismatch
```

Result:

- Edition identity is part of consent scope;
- changed content requires fresh authority;
- and byte similarity does not expand consent.

## 25. Consent is withdrawn after an earlier lawful disclosure

```yaml
prior_event:
  disclosure_event_id: disclosure_event_0025
  event_kind: delivered
  occurred_at: 2026-07-15T12:00:00-04:00
  outcome: completed

revocation:
  authorization_revocation_id: revocation_0025
  effective_at: 2026-08-01T00:00:00-04:00
  affected_action_classes: [view, download, deliver, reuse]

future_request:
  decision: denied
  denial_reason_code: consent_withdrawn
```

Result:

- prior history remains;
- future use is blocked;
- and Vitrine does not claim that the earlier recipient deleted the copy.

## 26. Issuance is permitted but electronic delivery is not

```yaml
issuance_decision:
  requested_action: issue_export
  decision: allowed

delivery_request:
  requested_action: deliver_export
  channel_class: ordinary_email

delivery_decision:
  decision: denied
  denial_reason_code: delivery_channel_not_permitted
  permitted_channel_classes: [in_person, secure_portal]
```

Result:

- Issuance and delivery are distinct;
- an exact Edition may be prepared without being emailed;
- and channel restrictions are enforced separately.

## 27. Delivery fails after authorization and Issuance

```yaml
disclosure_authorization:
  disclosure_authorization_id: disclosure_auth_0027
  valid_until: 2026-08-30T17:00:00-04:00

issuance:
  issuance_id: issuance_0027
  issued_at: 2026-08-05T10:00:00-04:00

delivery_event:
  event_kind: delivery_failed
  outcome: failed
  failure_code: external_channel_unavailable
```

Result:

- authorization and Issuance remain valid historical facts;
- delivery failure is recorded separately;
- and no receipt is fabricated.

## 28. Receipt exists without external acceptance

```yaml
submission:
  submission_id: submission_0028
  submitted_at: 2026-08-05T09:00:00-04:00

receipt_event:
  event_kind: receipt_recorded
  external_reference: receipt_SYNTH_8821
  occurred_at: 2026-08-05T09:05:00-04:00

external_decision:
  status: not_received
```

Result:

- receipt proves only the recorded receipt fact;
- it does not establish review or approval;
- and Vitrine preserves the missing external decision honestly.

## 29. Authorization expires while a build is in progress

```yaml
build_request:
  requested_action: build_snapshot
  requested_at: 2026-08-05T16:50:00-04:00

authorization_decision:
  decision: allowed
  expires_at: 2026-08-05T17:00:00-04:00

build_attempt:
  started_at: 2026-08-05T16:55:00-04:00
  sealing_attempted_at: 2026-08-05T17:03:00-04:00
  outcome: blocked
  failure_code: authorization_expired
```

Result:

- policy defines which stage requires current authority;
- expiration is not ignored because the build started earlier;
- and a new Decision or plan is required.

## 30. Recipient relationship changes after sealing

```yaml
sealed_edition:
  snapshot_edition: 4
  sealed_at: 2026-07-20T12:00:00-04:00

relationship_change:
  prior_recipient_scope_id: recipient_guardian_old
  successor_recipient_scope_id: recipient_guardian_new
  effective_at: 2026-08-01T00:00:00-04:00

future_delivery:
  prior_scope_decision: denied
  new_scope_requires_authorization: true
```

Result:

- Edition bytes remain unchanged;
- recipient changes require new scope and authorization;
- and prior delivery history remains attributable to the old scope.

## 31. Historical Edition retained but future access revoked

```yaml
edition:
  snapshot_edition: 2
  lifecycle: superseded
  retention_status: retained

revocation:
  affected_action_classes: [view, download, deliver]
  historical_treatment: retain_for_audit_without_ordinary_access

current_pointer:
  snapshot_edition: 4
```

Result:

- retention does not imply ordinary access;
- revocation and Edition lifecycle remain separate;
- and authorized audit access requires its own Decision.

## 32. Disclosure-log export is policy-required

```yaml
request:
  requested_action: export_disclosure_log
  target_references: [portfolio_elm_2026_showcase]
  purpose: annual_records_review

authorization_decision:
  decision: allowed
  permitted_target_scope:
    event_fields: [event_kind, occurred_at, recipient_scope_id, artifact_id, outcome]
    excluded_fields: [artifact_bytes, source_content, authentication_data]
```

Result:

- log export uses a strict allowlist;
- educational content is not duplicated;
- and policy determines whether the exported record satisfies institutional needs.

## 33. Denied result does not distinguish absent from suppressed

```yaml
request_a:
  target: nonexistent_source
  internal_reason: no_match

request_b:
  target: suppressed_portia_source
  internal_reason: source_suppressed

ordinary_response_a:
  status: unavailable
ordinary_response_b:
  status: unavailable
```

Result:

- ordinary responses are intentionally identical;
- restricted diagnostics remain access-controlled;
- and result timing or counts should not become a side channel.

## 34. Derived authorization dashboard is rebuilt

```yaml
canonical_records:
  authorization_decisions: [auth_dec_1, auth_dec_2]
  disclosure_authorizations: [disclosure_auth_1]
  revocations: [revocation_1]

derived_dashboard:
  state: missing

rebuild:
  source_snapshot: privacy_canonical_snapshot_34
  outcome: complete
```

Result:

- missing derived state does not mean no authorizations exist;
- canonical records remain authoritative;
- and the rebuilt dashboard cannot create or alter permission.

## 35. Mistaken disclosure is preserved and referred to institutional response

```yaml
disclosure_event:
  disclosure_event_id: disclosure_event_0035
  event_kind: delivered
  outcome: completed
  recipient_scope_id: recipient_wrong_organization

incident_reference:
  authority_system: institutional_incident_system
  authority_record_reference: incident_SYNTH_35

future_revocation:
  affected_action_classes: [deliver, reuse]
  reason_code: recipient_scope_error
```

Result:

- event history is not deleted;
- Vitrine stores only bounded incident references;
- and corrective action does not duplicate the disclosed content.

## 36. Asserted teacher role lacks verified assignment evidence

```yaml
request:
  actor_reference: actor_teacher_temp
  asserted_role: teacher
  requested_action: read_source_representation

evidence:
  authenticated_identity: valid
  employment_assignment: missing

decision:
  decision: indeterminate
  indeterminate_fact_codes: [actor_role_unverified]
```

Result:

- authentication alone does not establish assignment authority;
- indeterminate fails closed;
- and the actor receives no restricted metadata.

## 37. Identity provider outage produces an indeterminate result

```yaml
request:
  requested_action: inspect_snapshot_edition
  actor_reference: actor_student_0027

identity_verification:
  status: unavailable

decision:
  decision: indeterminate
  indeterminate_fact_codes: [actor_identity_unresolved]
```

Result:

- cached display name is not accepted as identity proof;
- access remains blocked;
- and the system reports a privacy-safe temporary unavailability state.

## 38. Conditional collaborator review must be completed

```yaml
authorization_decision:
  decision: conditional
  conditions:
    - collaborator_review_required: subject_0031
    - redaction_verification_required: redaction_result_38

condition_state:
  collaborator_review: complete
  redaction_verification: pending

use_attempt:
  outcome: denied
  failure_code: authorization_conditional
```

Result:

- partial condition completion is not enough;
- conditions are exact and attributable;
- and the Decision is not mutated into allowed.

## 39. Teacher-private note becomes a formal Annotation

```yaml
private_draft:
  note_id: teacher_draft_39
  access_scope: sole_actor_working_note

formal_annotation:
  annotation_id: annotation_39
  source_note_reference: teacher_draft_39
  shared_with_reviewers: true

privacy_result:
  sole_possession_assumption: not_preserved
```

Result:

- Vitrine does not make a legal classification;
- once shared or formalized, the note follows the Annotation and disclosure rules;
- and teacher-private drafts remain distinct from formal records.

## 40. Parent asks for every discovered source during a conference

```yaml
conference_authorization:
  purpose: scheduled_parent_conference
  permitted_target_scope: [edition_parent_conference_5]

request:
  requested_action: discover_metadata
  target_scope: all_student_sources
  purpose: complete_record_access

decision:
  decision: denied
  denial_reason_code: purpose_not_permitted
```

Result:

- conference authority does not expand into source discovery;
- Vitrine does not represent the conference Edition as a complete record response;
- and institutional records-access workflow remains separate.

## 41. Directory-information assumption is insufficient for public release

```yaml
request:
  requested_action: deliver_export
  recipient_scope_id: recipient_public_unrestricted
  purpose: public_showcase

evidence:
  directory_information_assumption: true
  institutional_notice_reference: missing
  opt_out_status: unknown

decision:
  decision: indeterminate
```

Result:

- common directory-information assumptions are not authority evidence;
- notice, purpose, and opt-out facts remain institutional;
- and public release fails closed.

## 42. Small cohort creates indirect identification risk

```yaml
output:
  direct_names_removed: true
  program_label: district_only_robotics_fellowship
  cohort_size: 3
  project_topic: solar_drone_rescue

deidentification_review:
  decision: not_deidentified
  indirect_identifier_classes_considered: [small_cohort, unique_project, program_label]
```

Result:

- generalized names do not remove contextual uniqueness;
- cohort and project details may identify the subject;
- and public disclosure requires further transformation or denial.

## 43. Voice remains identifying after transcript names are removed

```yaml
audio_output:
  transcript_names_removed: true
  original_voice_retained: true
  school_event_intro_retained: true

deidentification_review:
  decision: not_deidentified
  indirect_identifier_classes_considered: [voice, event_context]
```

Result:

- voice and context remain identifiers;
- a transcript-only alternative may be reviewed separately;
- and the audio is not treated as anonymous.

## 44. Blurred video still identifies students through context

```yaml
redaction_operations:
  - blur_region: faces

remaining_context:
  - unique_team_uniforms
  - classroom_number
  - named_award_banner

verification:
  decision: changes_required
```

Result:

- face blur is not sufficient;
- setting and uniforms are reviewed as indirect identifiers;
- and a safer crop, replacement, or omission is required.

## 45. PDF author metadata remains after visible redaction

```yaml
redaction_result:
  visible_names_removed: true
  output_digest: eeee

metadata_scan:
  author: "Synthetic Student"
  last_modified_by: "Synthetic Student"

verification:
  decision: rejected
  findings: [embedded_metadata_identifier]
```

Result:

- metadata scanning is part of verification;
- visible correctness is not enough;
- and a new Result is required after metadata stripping.

## 46. Redaction operation order is unsafe

```yaml
plan:
  operations:
    - generate_public_index
    - pseudonymize_identifier
    - strip_embedded_metadata

review:
  outcome: changes_required
  reason: generated index captures identifiers before pseudonymization
```

Result:

- operation order is contract-significant;
- derived files must be generated from already-safe inputs;
- and the Plan digest changes when order changes.

## 47. Crop removes a signature but leaves a name in comments

```yaml
operations:
  - crop_region: signature_block

remaining_content:
  teacher_comment: "Excellent revision, Synthetic Student"

verification:
  decision: rejected
  findings: [direct_identifier_in_comment]
```

Result:

- every disclosure surface is reviewed;
- one successful operation does not satisfy the Plan;
- and comment removal or replacement is required.

## 48. Redaction breaks accessibility

```yaml
redaction_result:
  output_media_type: application/pdf
  visual_masking_complete: true
  tagged_pdf_structure: broken
  reading_order: invalid

verification:
  decision: rejected
  findings: [accessibility_verification_failed]
```

Result:

- privacy transformation must not silently make output inaccessible;
- accessible alternatives or corrected rendering are required;
- and the unsafe output is not distributable.

## 49. Approved summary substitutes for an unsafe artifact

```yaml
source_artifact:
  isolation_outcome: not_safely_isolatable

producer_projection:
  projection_kind: concord:authorized_individual_summary
  source_artifact_reference: concord_artifact_group_49

review:
  outcome: approved_as_is
```

Result:

- summary substitution is an explicit producer-approved projection;
- Vitrine does not rewrite the original artifact;
- and provenance to the restricted source remains internal.

## 50. Secure assessment content appears in a student-facing source

```yaml
candidate_projection:
  projection_kind: scoreform:attempt_summary
  accidental_field: answer_key

disclosure_review:
  outcome: denied
  findings: [assessment_security_restricted]

adapter_result:
  status: projection_private_field_present
```

Result:

- Vitrine does not redact a contract violation into acceptance;
- producer projection must be corrected;
- and secure content remains prohibited.

## 51. Source withdrawal after lawful issuance

```yaml
edition:
  snapshot_edition: 6
  sealed_at: 2026-06-01T12:00:00-04:00

prior_disclosure:
  event_kind: delivered
  occurred_at: 2026-06-03T14:00:00-04:00

source_withdrawal:
  occurred_at: 2026-07-01T09:00:00-04:00

future_policy:
  historical_access: restricted
  edition_bytes: retained_per_policy
```

Result:

- withdrawal does not silently erase historical Edition bytes;
- future access is reevaluated;
- and prior disclosure remains exact history.

## 52. Selection allowed but snapshot building denied

```yaml
curation_decision:
  requested_action: activate_selection
  decision: allowed

build_request:
  requested_action: build_snapshot
  audience_context_id: audience_public_r3

build_decision:
  decision: denied
  denial_reason_code: collaborator_permission_missing
```

Result:

- curation and copying are separate gates;
- the working Portfolio may retain the Selection;
- and no public Edition is built.

## 53. Snapshot build allowed but Issuance denied

```yaml
build_decision:
  requested_action: build_snapshot
  decision: allowed

sealed_edition:
  snapshot_edition: 7

issuance_request:
  requested_action: issue_export

issuance_decision:
  decision: denied
  denial_reason_code: institutional_approval_missing
```

Result:

- building a reviewed internal Edition does not authorize issuance;
- Edition 7 remains sealed but unissued;
- and no delivery action is enabled.

## 54. Requested delivery channel is prohibited

```yaml
disclosure_authorization:
  permitted_channel_classes: [secure_portal, in_person]

requested_event:
  event_kind: delivered
  channel_class: consumer_file_share

outcome:
  status: denied
  failure_code: delivery_channel_not_permitted
```

Result:

- content authorization does not authorize every channel;
- delivery restrictions are exact;
- and the prohibited service receives no artifact.

## 55. Export Artifact does not match authorized digest

```yaml
disclosure_authorization:
  export_artifact_ids: [export_pdf_55]

authorized_artifact:
  export_artifact_id: export_pdf_55
  digest: ffff

presented_file:
  export_artifact_id: export_pdf_55
  digest: 1111

result:
  outcome: denied
  failure_code: export_artifact_mismatch
```

Result:

- identity alone is insufficient when bytes disagree;
- delivery fails closed;
- and the mismatched file is not silently regenerated or substituted.

## 56. Recipient Scope references the wrong organization

```yaml
recipient_scope:
  recipient_type: regulated_authority
  recipient_organization_reference: authority_unit_A

submission_target:
  organization_reference: authority_unit_B

decision:
  decision: denied
  denial_reason_code: recipient_scope_mismatch
```

Result:

- destination identity is exact;
- similar agency labels do not authorize substitution;
- and a corrected Scope requires new evaluation.

## 57. Consent expires before delivery

```yaml
consent_evidence:
  expires_at: 2026-08-05T17:00:00-04:00

issuance:
  issued_at: 2026-08-05T16:30:00-04:00

delivery_attempt:
  occurred_at: 2026-08-05T17:10:00-04:00
  outcome: denied
  failure_code: consent_expired
```

Result:

- validity is checked at the policy-required action time;
- Issuance does not freeze consent indefinitely;
- and prior Issuance history remains.

## 58. Consent purpose does not match requested public release

```yaml
consent_evidence:
  purpose_scope: family_conference
  recipient_scope: parent_guardian_facing

request:
  purpose: public_showcase
  recipient_scope: public_unrestricted

decision:
  decision: denied
  denial_reason_code: consent_scope_mismatch
```

Result:

- consent is purpose- and recipient-scoped;
- family sharing does not authorize public release;
- and no broad “consent on file” shortcut is accepted.

## 59. De-identification review is stale after byte change

```yaml
prior_review:
  output_digest: 2222
  decision: deidentified_for_context

current_output:
  output_digest: 3333
  change: new_caption_added

release_check:
  outcome: denied
  failure_code: deidentification_context_mismatch
```

Result:

- review binds exact bytes;
- a changed caption may add identifiers;
- and a new review is required.

## 60. Group Membership is not collaborator permission

```yaml
concord_relationships:
  group_members: [subject_0027, subject_0031]
  artifact_authors: [subject_0027]

permission_evidence:
  subject_0031: missing

public_review:
  outcome: redaction_required
```

Result:

- membership is not authorship or permission;
- relationships remain exact;
- and subject_0031 is handled according to actual identifiability and authority.

## 61. Recorder-for-Group is not sole author

```yaml
artifact_author:
  subject_id: subject_0027
  authorship_mode: recorder_for_group

presentation_request:
  display_title: "My Independent Position"

review:
  outcome: changes_required
  finding: presentation_misstates_authorship
```

Result:

- curator presentation cannot overwrite producer relationships;
- recorder status is preserved;
- and disclosure must not claim sole authorship.

## 62. Portia omission notice would leak source existence

```yaml
internal_omission:
  reason: source_suppressed
  protected_target: opaque_portia_projection_ref

audience_notice_request:
  text: "A behavior record was removed for privacy."

review:
  outcome: denied
  finding: suppressed_source_existence_leak
```

Result:

- internal omission remains canonical;
- audience output does not mention the source;
- and counts and indexes remain unchanged.

## 63. Future Meridian report projection keeps grading internals restricted

```yaml
candidate:
  projection_kind: meridian:student_report
  report_snapshot_id: meridian_report_snapshot_63

allowed_fields:
  - student_facing_grade_summary
  - published_standard_summary

restricted_fields:
  - internal_evidence_inventory
  - unpublished_override_rationale
  - adapter_diagnostics
  - grading_policy_working_state
```

Result:

- only an exact public report projection is eligible;
- Vitrine authorization does not open Meridian internals;
- and Meridian report identity remains producer-owned.

## 64. Protected access event logs no source content

```yaml
access_event:
  protected_access_event_id: access_event_64
  event_kind: source_opened
  authorization_decision_id: auth_dec_64
  target_references: [candidate_quillan_story_r2]
  occurred_at: 2026-08-05T10:15:00-04:00
  outcome: completed

not_stored:
  - document_text
  - screenshot
  - absolute_path
  - authentication_token
```

Result:

- logging is minimum-necessary;
- exact references support audit;
- and the log does not become a duplicate education-record payload.

## 65. Delivery event references artifact without copying bytes

```yaml
delivery_event:
  disclosure_event_id: disclosure_event_65
  event_kind: delivered
  export_artifact_ids: [export_family_pdf_65]
  recipient_scope_id: recipient_parent_65
  channel_class: secure_portal
  outcome: completed

not_stored:
  artifact_bytes: true
  recipient_password: true
  full_contact_record: true
```

Result:

- event provenance is sufficient without duplicating the package;
- credentials remain outside Vitrine privacy records;
- and the authoritative delivery system may retain its own receipt.

## 66. Revocation blocks future download without external-recall claim

```yaml
revocation:
  authorization_revocation_id: revocation_66
  target_type: disclosure_authorization
  affected_action_classes: [view, download, deliver]
  effective_at: 2026-08-05T12:00:00-04:00

prior_external_copy:
  status: unknown

vitrine_claim:
  future_access_blocked: true
  external_copy_recalled: false
```

Result:

- future Vitrine access is blocked;
- external state remains honestly unknown;
- and prior Disclosure Events remain.

## 67. Family and public Editions contain different bytes

```yaml
family_edition:
  snapshot_series_id: series_family_67
  snapshot_edition: 1
  entries: [named_story, named_reflection, family_caption]

public_edition:
  snapshot_series_id: series_public_67
  snapshot_edition: 1
  entries: [pseudonymized_story, generalized_reflection, public_caption]

relationship:
  common_composition_revision: composition_67
  same_edition_identity: false
```

Result:

- audience-visible differences create distinct logical Editions;
- each receives separate review and authorization;
- and one package is not a format variant of the other.

## 68. ZIP and PDF are separately authorized Export Artifacts

```yaml
snapshot_edition:
  snapshot_series_id: series_reviewer_68
  snapshot_edition: 2

exports:
  - export_artifact_id: export_zip_68
    format: zip_archive
    digest: 4444
  - export_artifact_id: export_pdf_68
    format: pdf_bundle
    digest: 5555

disclosure_authorization:
  export_artifact_ids: [export_zip_68, export_pdf_68]
```

Result:

- one logical Edition can have several formats;
- each artifact has exact identity and digest;
- and authorization lists both explicitly.

## 69. Public-unrestricted scope lacks authority and de-identification

```yaml
recipient_scope:
  recipient_type: public_unrestricted
  recipient_resolution_status: not_applicable

request:
  requested_action: deliver_export
  purpose: public_showcase

evidence:
  consent: missing
  deidentification_review: missing

decision:
  decision: denied
```

Result:

- public release is deny-by-default;
- a public recipient class does not reduce authority requirements;
- and no artifact URL is generated.

## 70. Indeterminate policy result does not expose a download action

```yaml
policy_evaluation:
  policy_reference: district_public_release_r4
  status: unavailable

authorization_decision:
  decision: indeterminate
  indeterminate_fact_codes: [policy_reference_unavailable]

ui_state:
  download_enabled: false
  safe_message: "This item is not currently available."
```

Result:

- indeterminate fails closed;
- ordinary messaging avoids sensitive detail;
- and a later successful evaluation creates a new Decision.

## 71. Historical authorization remains auditable after evidence supersession

```yaml
historical_authorization:
  disclosure_authorization_id: disclosure_auth_71
  authority_evidence_reference_ids: [evidence_guardian_71_r1]
  created_at: 2026-05-01T10:00:00-04:00

successor_evidence:
  authority_evidence_reference_id: evidence_guardian_71_r2
  supersedes: evidence_guardian_71_r1
  created_at: 2026-07-01T10:00:00-04:00

historical_event:
  disclosure_event_id: disclosure_event_71
  disclosure_authorization_id: disclosure_auth_71
```

Result:

- prior authorization remains bound to the evidence actually used;
- successor evidence governs future requests;
- and historical audit does not reinterpret the old event through current state.

## Coverage summary

The examples collectively exercise:

- every initial audience class;
- discovery, metadata, source, curation, build, manifest, issuance, delivery, submission, historical-access, and logging gates;
- allowed, denied, conditional, indeterminate, expired, and revoked outcomes;
- no-existence leakage;
- exact actor, purpose, target, time, and recipient scope;
- parent/guardian relationship changes and rights transfer;
- public-release and directory-information boundaries;
- direct and indirect identifiers;
- PDF, image, audio, video, filename, metadata, and accessibility redaction concerns;
- context-specific de-identification;
- multi-subject and Group artifacts;
- ScoreForm, Quillan, Concord, Portia, and future Meridian boundaries;
- exact Snapshot Edition and Export Artifact authorization;
- Issuance, delivery, receipt, and external decision separation;
- consent expiration and withdrawal;
- future-use revocation without external-recall claims;
- minimum-necessary access and disclosure logs;
- derived-view rebuilding;
- and historical evidence preservation.

No example authorizes production use or establishes a legal conclusion.
