# Representative Snapshot, Export, Checksum, and Immutability Examples

## Status and use

These synthetic examples exercise the conceptual records in:

- [Snapshot, Export, Checksum, and Immutability Contracts](../design/snapshot-export-immutability-contracts.md); and
- [ADR 0007: Snapshot, Export, Checksum, and Immutability](../decisions/0007-snapshot-export-checksum-and-immutability.md).

The examples are not final JSON Schema fixtures and do not represent implemented Vitrine runtime behavior.

All people, classes, records, files, IDs, timestamps, destinations, and policies are fictional.

The examples preserve these boundaries:

```text
Composition Revision != Snapshot Edition
Snapshot Edition != Export Artifact
Export Artifact != Issuance
Issuance != Submission
Submission != external Receipt
Receipt != external Decision
```

They also preserve:

```text
producer manifest digest
  != source artifact digest
  != Snapshot Entry digest
  != Snapshot Manifest digest
  != Export Artifact digest
```

## Shared synthetic context

Unless an example states otherwise:

```yaml
portfolio_id: portfolio_elm_2026_showcase
portfolio_subject_id: subject_elm_0027
profile_binding_id: binding_showcase_r3
portfolio_profile_id: district_showcase
profile_revision: 3
composition_revision_id: composition_0017
snapshot_series_id: snapshot_series_showcase_family
snapshot_edition: 4
builder_id: vitrine_snapshot_builder
builder_version: 0.1.0.dev0
```

## 1. Successful Edition from one exact Composition Revision

```yaml
request:
  snapshot_build_request_id: request_0001
  composition_revision_id: composition_0017
  requested_export_formats: [directory_package, zip_archive]
plan:
  snapshot_build_plan_id: plan_0001
  composition_revision_id: composition_0017
attempt:
  snapshot_build_attempt_id: attempt_0001
  terminal_outcome: sealed
edition:
  snapshot_series_id: snapshot_series_showcase_family
  snapshot_edition: 4
```

Result:

- the Edition binds `composition_0017` permanently;
- later working-Portfolio changes do not alter Edition 4;
- directory and ZIP exports may be generated from the same logical Edition;

## 2. Composition Current Pointer advances during the build

```yaml
planned_composition: composition_0017
current_pointer_during_build: composition_0018
builder_action: continue_with_planned_composition
```

Result:

- the Attempt continues against `composition_0017`;
- the builder does not merge content from `composition_0018`;
- a build from `composition_0018` requires a new Request or Plan;

## 3. Candidate Current Pointer advances after Selection

```yaml
selection_id: selection_story
selected_candidate_id: candidate_story_r2
selected_candidate_evaluation_id: candidate_eval_story_4
current_candidate_evaluation_during_build: candidate_eval_story_5
```

Result:

- the planned source remains `candidate_eval_story_4`;
- the successor Evaluation does not retarget the Selection or snapshot;
- current Candidate state may affect policy but not source identity;

## 4. Core Publication is superseded before copying

```yaml
planned_publication_id: pub_scoreform_assignment7_r3
successor_publication_id: pub_scoreform_assignment7_r4
series_state: superseded
policy_result: historical_use_permitted
```

Result:

- Vitrine either uses the exact historical publication under policy or records failure/omission;
- it does not copy revision 4 while claiming revision 3 provenance;
- supersession remains visible in internal provenance;

## 5. Source bytes change while being read

```yaml
source_path: producer_authorized/work.pdf
initial_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
reopened_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
outcome: source_changed_during_copy
```

Result:

- the Attempt fails closed;
- no Snapshot Entry is sealed;
- filesystem metadata equality cannot override the byte mismatch;

## 6. Producer digest claim does not match acquired bytes

```yaml
producer_digest: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
acquired_digest: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
outcome: source_digest_mismatch
```

Result:

- the source-owner claim and Vitrine-acquired bytes are inconsistent;
- copying stops before sealing;
- Vitrine does not repair or rewrite the producer source;

## 7. Acquired source bytes and staged output differ

```yaml
acquired_source_digest: dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
staged_output_digest: eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
outcome: entry_digest_mismatch
```

Result:

- independent output hashing catches the mismatch;
- the source digest is not reused as the Entry digest;
- the staging output is not promoted;

## 8. ScoreForm structured attempt summary is rendered

```yaml
entry_plan:
  producer_projection: scoreform:attempt_summary
  attempt_number: 2
  acquisition_mode: structured_projection
materialization:
  materialization_kind: vitrine_render
  renderer_contract: scoreform_attempt_summary_html_v1
  configuration_digest: ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
entry:
  relative_path: assessments/argument-analysis-attempt-2.html
  media_type: text/html
```

Result:

- the Entry preserves exact ScoreForm attempt identity;
- renderer and configuration provenance explain the HTML bytes;
- the result is not relabeled as a Grade or proficiency;

## 9. A later ScoreForm attempt exists

```yaml
selected_attempt: 2
current_manifest_attempts: [1, 2, 3]
snapshot_action: materialize_attempt_2_only
```

Result:

- attempt 3 does not silently replace attempt 2;
- Portfolio Selection remains independent of Meridian grading policy;
- a snapshot containing attempt 3 requires separate curation;

## 10. Raw ScoreForm retained scan is requested

```yaml
requested_source: scans/source/2026-04-10/batch.pdf
projection_kind: raw_retained_scan
exposure_disposition: prohibited
outcome: raw_native_record_prohibited
```

Result:

- the builder rejects the request;
- it does not open the retained path;
- a future sanitized producer rendering would be a separate projection and Entry;

## 11. Quillan selected original work is copied

```yaml
producer_projection: quillan:student_work
selected_evidence_ids: [evidence_page_1, evidence_page_2]
materialization_kind: exact_byte_copy
entry_path: writing/personal-narrative.pdf
```

Result:

- only producer-confirmed selected evidence is represented;
- candidate, duplicate, and excluded evidence remain absent;
- Quillan source identity remains authoritative;

## 12. Quillan feedback is a separate Entry

```yaml
entries:
  - semantic_role: original_work
    relative_path: writing/personal-narrative.pdf
  - semantic_role: feedback
    relative_path: feedback/personal-narrative-feedback.pdf
```

Result:

- original work and feedback have separate Entry IDs and digests;
- feedback does not replace the original work;
- private review state remains outside the snapshot;

## 13. Quillan feedback becomes stale before build

```yaml
planned_feedback_revision: feedback_r3
producer_feedback_state: stale_after_submission_change
policy: stale_feedback_not_permitted
outcome: build_plan_stale
```

Result:

- Vitrine does not regenerate feedback privately;
- the Plan must be replaced or the item omitted where policy permits;
- the old feedback may remain valid in an earlier issued Edition;

## 14. Quillan private-file fallback is attempted

```yaml
public_projection_status: unavailable
fallback_path: review.json
requested_action: parse_private_file
outcome: projection_unavailable
```

Result:

- private-file fallback is rejected;
- no review or private-note existence leaks into an audience package;
- operational copying waits for an accepted public contract;

## 15. Concord Group Artifact is copied with relationship provenance

```yaml
producer_projection: concord:artifact
artifact_id: artifact_lab_bridge_4
group_id: group_delta
authorship_mode: collective_group_author
attribution_status: confirmed
representation_status: multiple_named_positions
```

Result:

- the Entry preserves Group and representation semantics;
- Portfolio Subject membership is not rewritten as sole authorship;
- collaborator review remains an issue #10 requirement;

## 16. Concord canonical Work Snapshot is offered as a Portfolio file

```yaml
source_kind: concord_work_snapshot
contains_complete_record_graph: true
requested_entry_kind: copied_source_representation
outcome: raw_native_record_prohibited
```

Result:

- the producer storage snapshot is not a portfolio projection;
- Vitrine does not copy the complete Concord graph;
- an exact public Artifact projection is required;

## 17. Concord Group Score remains Group-targeted

```yaml
producer_projection: concord:score_summary
score_target_kind: group
score_target_id: group_delta
selected_for_portfolio_subject: subject_elm_0027
```

Result:

- the snapshot may present Group-context evaluation;
- it does not relabel the Score as individual proficiency;
- native scale and disposition remain exact;

## 18. Portia-safe projection is copied

```yaml
producer_projection: portia:student_selected_reflection
projection_revision: 2
materialization_kind: producer_render
entry_path: reflections/self-advocacy.pdf
```

Result:

- only the safe projection is materialized;
- the underlying Event and intervention graph remain inaccessible;
- the internal Entry retains minimum-necessary exact provenance;

## 19. Portia source graph is suppressed

```yaml
core_publication_found: true
ordinary_portia_records_present: true
portfolio_safe_projection_present: false
audience_output: no_result_no_count_no_placeholder
```

Result:

- no Snapshot Entry or audience Omission reveals the hidden source;
- internal diagnostics use privacy-safe suppression codes;
- the Core publication does not authorize exposure;

## 20. Portia-safe projection is revoked after issuance

```yaml
issued_edition: 4
source_projection_revision: 2
producer_event: revoked
new_snapshot_lifecycle_event: revoked_for_future_use
```

Result:

- Edition 4 and its Issuance remain historical;
- new distribution may be prohibited;
- the old Edition is not rewritten and external copies are not claimed recalled;

## 21. Required source is unavailable and omission is prohibited

```yaml
entry_plan_id: entry_plan_required_work
source_state: unavailable
profile_omission_rule: prohibited
outcome: required_entry_omitted
```

Result:

- sealing fails;
- no Edition is created;
- the failed Attempt preserves a bounded reason;

## 22. Optional source is unavailable and omission is permitted

```yaml
entry_plan_id: entry_plan_optional_feedback
source_state: unavailable
omission:
  omission_kind: source_unavailable
  sealing_permitted: true
  audience_notice_policy: generic_notice
```

Result:

- the Edition may seal;
- the Omission is explicit in the internal manifest;
- the generic audience notice does not expose private source details;

## 23. Prior Snapshot Entry carry-forward is permitted

```yaml
new_edition: 5
source_state: historically_unavailable
carried_forward_from_entry_id: entry_edition3_story_pdf
materialization_kind: prior_snapshot_copy
profile_rule: historical_carry_forward_permitted
```

Result:

- the exact prior Entry is validated and copied;
- the new Edition preserves original producer provenance;
- the Materialization Record does not claim fresh producer verification;

## 24. Silent cached-byte fallback is attempted

```yaml
planned_source: candidate_quillan_story_r3
source_state: unavailable
local_cache_contains: entry_edition3_story_pdf
plan_names_prior_entry: false
outcome: source_unavailable
```

Result:

- the cache is not used;
- prior-snapshot reuse requires explicit planning and policy;
- the Attempt fails or records a permitted Omission;

## 25. Generated table of contents is included

```yaml
generated_entry:
  semantic_role: table_of_contents
  materialization_kind: vitrine_render
  renderer_contract: vitrine_toc_html_v1
  input_references: [manifest_inventory_projection]
  relative_path: index.html
  digest: 1111111111111111111111111111111111111111111111111111111111111111
```

Result:

- the table of contents is an ordinary byte-bearing Entry;
- its renderer and input inventory are preserved;
- it does not replace the canonical internal manifest;

## 26. Internal manifest is excluded from the audience package

```yaml
internal_manifest_path: canonical/snapshot-manifest.json
public_zip_includes_internal_manifest: false
public_provenance_appendix_entry: provenance/source-credits.pdf
```

Result:

- restricted IDs remain internal;
- the public appendix is generated from an allowlist;
- the appendix has its own digest and renderer provenance;

## 27. Audience-safe provenance appendix is generated

```yaml
audience_policy: family_view_r2
allowed_fields: [display_title, producer_name, academic_year]
prohibited_fields: [publication_id, student_id, private_source_path]
entry_path: appendices/source-credits.pdf
```

Result:

- only declared fields appear;
- the appendix is distinct from the internal manifest;
- issue #10 still decides whether the family recipient is authorized;

## 28. ZIP and PDF exports represent one Edition

```yaml
edition: 4
export_artifacts:
  - id: export_zip_4
    format: zip_archive
    digest: 2222222222222222222222222222222222222222222222222222222222222222
  - id: export_pdf_4
    format: pdf_bundle
    digest: 3333333333333333333333333333333333333333333333333333333333333333
```

Result:

- the two artifact digests differ;
- both bind the same logical Entry inventory;
- Edition identity is independent of either container digest;

## 29. Family and public packages differ in visible content

```yaml
family_content_policy: family_view_r2
public_content_policy: public_showcase_r1
family_includes: [collaborator_names, detailed_reflection]
public_includes: [redacted_collaborators, short_caption]
result: separate_snapshot_editions
```

Result:

- the packages cannot be two formats of one Edition;
- each Edition records its own content policy and Entry digests;
- authorization for each audience remains separate;

## 30. Optional ZIP generation fails after sealing

```yaml
edition_state: sealed
required_export_formats: [directory_package]
optional_export_formats: [zip_archive]
zip_result: export_failed
attempt_outcome: partial_success_after_seal
```

Result:

- the Edition and required directory package remain valid;
- the optional ZIP failure is structured;
- no sealed content is removed;

## 31. Required PDF generation fails

```yaml
edition_content_staged: true
profile_requires_export: pdf_bundle
pdf_result: render_failed
sealing_policy: required_exports_inside_seal_gate
```

Result:

- the Build Attempt fails before Edition sealing;
- staging is not an Edition;
- a successor Plan or renderer fix is required;

## 32. Seal succeeds but lock cleanup fails

```yaml
edition: 4
seal_result: durable
lock_cleanup_result: failed
attempt_outcome: partial_success_after_seal
warning_code: post_seal_cleanup_failed
```

Result:

- Edition 4 remains allocated and immutable;
- cleanup failure is visible to the operator;
- the operation never deletes the durable Edition;

## 33. Current-pointer update fails after sealing

```yaml
sealed_edition: 5
expected_predecessor_edition: 4
actual_current_edition: 6
pointer_result: pointer_conflict
```

Result:

- Edition 5 remains a valid historical Edition;
- it does not become current;
- the conflict requires an explicit follow-up decision;

## 34. Two builders attempt the same Edition

```yaml
builder_a_target: edition_7
builder_b_target: edition_7
exclusive_creation_winner: builder_a
builder_b_result: edition_already_exists
```

Result:

- only one builder publishes the Edition;
- builder B may exact-replay only after proving full equality;
- last-writer overwrite is impossible;

## 35. Two Editions contain identical bytes

```yaml
edition_8_manifest_digest: 4444444444444444444444444444444444444444444444444444444444444444
edition_9_manifest_digest: 4444444444444444444444444444444444444444444444444444444444444444
reason_for_edition_9: separately_approved_reissuance
```

Result:

- the Editions remain distinct business records;
- byte equality may support a duplicate warning;
- the digest does not collapse identity or lifecycle;

## 36. Exact Edition replay returns existing history

```yaml
requested_request: request_0010
requested_plan: plan_0010
existing_edition: 9
manifest_bytes_equal: true
seal_equal: true
replay_result: existing_edition_9
```

Result:

- sealed files and timestamps remain untouched;
- the original seal time is preserved;
- different inputs would cause a conflict rather than replay;

## 37. Authorization changes after Plan creation

```yaml
plan_authorization_reference: auth_decision_12
current_authorization_state: revoked
attempt_start_result: build_plan_stale
```

Result:

- the builder does not rely on stale authorization;
- the Plan remains historical;
- issue #10 determines whether a successor authorization permits a new Plan;

## 38. Renderer version changes

```yaml
planned_renderer: vitrine_feedback_renderer_1.2
installed_renderer: vitrine_feedback_renderer_1.3
policy: exact_version_required
outcome: renderer_contract_unsupported
```

Result:

- the builder does not silently use version 1.3;
- a successor Plan can explicitly bind the new renderer;
- an existing Edition is never regenerated under the new renderer;

## 39. Template bytes change

```yaml
planned_template_digest: 5555555555555555555555555555555555555555555555555555555555555555
actual_template_digest: 6666666666666666666666666666666666666666666666666666666666666666
outcome: build_plan_fingerprint_mismatch
```

Result:

- generation stops before sealing;
- template changes are materialized as explicit Plan changes;
- the old template remains part of historical provenance;

## 40. Path traversal is rejected

```yaml
planned_relative_path: ../../private/review.json
outcome: entry_path_invalid
```

Result:

- the path cannot escape the Edition root;
- no source or staging file is opened through that target;
- the Plan must be corrected;

## 41. Case-insensitive path collision is rejected

```yaml
paths:
  - Work/Essay.pdf
  - work/essay.pdf
path_policy: portable_case_insensitive
outcome: entry_path_collision
```

Result:

- portable packages cannot contain ambiguous aliases;
- the builder does not rename silently;
- a successor Plan must select unique paths;

## 42. Unicode-normalization path collision is rejected

```yaml
paths:
  - artifacts/café.pdf
  - artifacts/café.pdf
normalization_policy: NFC
outcome: entry_path_collision
```

Result:

- visually equivalent aliases are detected;
- one canonical normalized path policy governs the Edition;
- source titles remain display metadata rather than paths;

## 43. Symlink source is rejected

```yaml
source_path: producer/work/student-work.pdf
source_file_type: symlink
outcome: source_reference_invalid
```

Result:

- the builder refuses traversal through the link;
- the source must be exposed as a regular producer-authorized file or structured projection;
- no copied Entry is created;

## 44. Nonregular source is rejected

```yaml
source_path: producer/work/live-stream
source_file_type: named_pipe
outcome: source_reference_invalid
```

Result:

- only contract-permitted stable sources are materialized;
- the builder does not block on or snapshot a live stream accidentally;
- a producer-rendered immutable representation is required;

## 45. Source changes after planning but before opening

```yaml
plan_source_revision: artifact_r4
resolved_source_revision_at_attempt: artifact_r5
outcome: build_plan_stale
```

Result:

- the builder does not accept the newer source;
- a successor Candidate or Plan is required;
- the old Plan remains exact historical intent;

## 46. Structured projection contract is unavailable

```yaml
projection_kind: quillan:student_feedback
projection_contract: 1
reader_status: unavailable
outcome: projection_unavailable
```

Result:

- the builder does not parse private Quillan JSON;
- the Selection remains historical;
- the build fails or records a permitted Omission;

## 47. Renderer is unavailable

```yaml
projection_kind: scoreform:attempt_summary
renderer_contract: scoreform_attempt_summary_pdf_v1
renderer_status: not_installed
outcome: renderer_unavailable
```

Result:

- source validity is not misclassified as corruption;
- the Attempt records a renderer-layer failure;
- another exact permitted format may proceed only if the Plan allows it;

## 48. Omission notice does not leak a suppressed source

```yaml
internal_omission_kind: suppressed
audience_notice_policy: no_notice
audience_index_item_count: 5
internal_expected_item_count: 6
```

Result:

- the audience package does not reveal a hidden sixth source;
- internal audit may preserve a restricted Omission reference;
- counts and diagnostics follow minimum-necessary policy;

## 49. Reference-only Entry

```yaml
entry_kind: reference_only
semantic_role: external_media_reference
source_reference: library_catalog_item_44
relative_path: null
digest: null
```

Result:

- the Edition records the logical reference without claiming copied bytes;
- the Profile explicitly permits reference-only content;
- an external link is not treated as durable local custody;

## 50. Failed staging never becomes an Edition

```yaml
attempt_id: attempt_0049
staged_files_created: 3
blocking_failure: entry_digest_mismatch
sealed_edition: null
```

Result:

- staging may be removed safely;
- the failed Attempt remains process history;
- no current pointer or Edition lifecycle event is created;

## 51. Edition durability is uncertain

```yaml
exclusive_target_created: true
final_sync_result: unknown
reload_result: io_error
outcome: edition_durability_uncertain
```

Result:

- the Edition number is not reused;
- the target requires explicit recovery or quarantine;
- Vitrine does not claim either ordinary success or ordinary pre-seal failure;

## 52. Issued but not delivered

```yaml
issuance_id: issuance_0051
issued_at: 2026-06-01T15:00:00Z
delivery_record: null
```

Result:

- Issuance proves only the local issuance event;
- recipient delivery remains unknown;
- the Edition and issued Artifact IDs remain exact;

## 53. Submitted without external receipt

```yaml
submission_id: submission_0052
local_transmission_result: handoff_completed_locally
external_tracking_reference: null
external_receipt: null
```

Result:

- Vitrine records the local handoff;
- it does not claim the authority received the package;
- a later receipt is a separate record;

## 54. External receipt exists without acceptance

```yaml
submission_id: submission_0053
receipt:
  received_at: 2026-06-02T14:30:00Z
  tracking_reference: receipt-4481
external_decision: null
```

Result:

- receipt and acceptance remain distinct;
- the external review may still be pending;
- the receipt artifact may have its own imported-byte digest;

## 55. Successor Edition supersedes an issued Edition

```yaml
predecessor_edition: 4
successor_edition: 5
lifecycle_event:
  event_kind: superseded
  successor_editions: [5]
```

Result:

- Edition 4 and its Issuance remain historical;
- the current pointer may move to Edition 5 explicitly;
- old submissions are not rewritten;

## 56. Edition invalidated after wrong Subject association

```yaml
edition: 6
defect: composition_referenced_wrong_portfolio_subject
lifecycle_event: invalidated
successor_edition: 7
```

Result:

- Edition 6 remains immutable evidence of the error;
- new issuance is prohibited under policy;
- Edition 7 uses a corrected Composition and separate seal;

## 57. Edition withdrawn without replacement

```yaml
edition: 8
lifecycle_event: withdrawn
successor_editions: []
```

Result:

- the Edition remains historical;
- future ordinary issuance stops;
- withdrawal does not imply byte deletion;

## 58. Edition revoked for future use

```yaml
edition: 9
reason: collaborator_consent_withdrawn
lifecycle_event: revoked_for_future_use
```

Result:

- historical issuance is not erased;
- future distribution is prohibited under policy;
- external copies are not claimed recalled;

## 59. Authorized exceptional local removal

```yaml
edition: 10
lifecycle_event: exceptionally_removed
certificate:
  manifest_digest: 7777777777777777777777777777777777777777777777777777777777777777
  affected_storage_scope: teacher_laptop_primary_copy
  reason_class: retention_prohibited
```

Result:

- substantive local bytes are removed under explicit authority;
- minimum identity and integrity evidence remains;
- ordinary workflow cannot perform this action;

## 60. External copy cannot be recalled

```yaml
local_edition_state: exceptionally_removed
prior_external_submission: submission_0052
external_copy_status: unknown
```

Result:

- the removal record explicitly limits its custody claim;
- Vitrine does not claim remote deletion;
- notification or external withdrawal is a separate institutional process;

## 61. Derived snapshot index is rebuilt

```yaml
canonical_editions: [4, 5, 6]
derived_index_state: deleted
rebuild_result: success
```

Result:

- canonical Editions remain readable without the index;
- rebuild does not modify manifests or current pointers;
- derived search metadata remains nonauthoritative;

## 62. Future Meridian report projection is copied

```yaml
producer_projection: meridian:report_snapshot_pdf
meridian_report_snapshot_id: report_snapshot_q2_17
materialization_kind: exact_byte_copy
entry_path: reports/q2-progress-report.pdf
```

Result:

- Meridian retains report-snapshot identity and grading authority;
- Vitrine records independent copied-byte provenance;
- private Meridian evidence inventory is not imported;

## 63. Regulated submission package uses generic snapshot records

```yaml
profile_family: regulated_pathway
edition: 12
required_exports: [pdf_bundle, zip_archive]
required_generated_entries: [submission_checklist, source_credit_appendix]
submission_target_class: state_portfolio_portal
```

Result:

- the regulated Profile specializes requirements without inventing new snapshot identity;
- issue #11 defines exact checklist and destination rules;
- Submission remains separate from external acceptance;

## 64. Profile migration requires explicit snapshot lineage

```yaml
old_profile_binding: binding_showcase_r3
new_profile_binding: binding_showcase_r4
old_edition: 4
new_composition: composition_0021
new_edition: 5
```

Result:

- the old Edition remains bound to revision 3;
- the successor Edition records migration lineage and revision 4 policy;
- Profile migration does not regenerate Edition 4;

## 65. Export contract successor for the same Edition

```yaml
edition: 4
old_export:
  id: export_zip_v1
  contract: zip_package_v1
new_export:
  id: export_zip_v2
  contract: zip_package_v2
  predecessor_export_artifact_id: export_zip_v1
```

Result:

- the logical Edition may remain the same when substantive content is unchanged;
- both ZIP byte sequences retain independent digests;
- issuance identifies the exact artifact used;

## 66. Directory package uses an inventory digest

```yaml
export_format: directory_package
files:
  - index.html
  - work/story.pdf
  - feedback/story-feedback.pdf
directory_inventory_digest: 8888888888888888888888888888888888888888888888888888888888888888
```

Result:

- no arbitrary filesystem metadata becomes canonical;
- the inventory digest binds normalized paths, sizes, and file digests;
- the Edition manifest remains the logical authority;

## 67. Logical inventory matches across ZIP and PDF exports

```yaml
edition_logical_inventory_digest: 9999999999999999999999999999999999999999999999999999999999999999
zip_artifact_digest: a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1
pdf_artifact_digest: b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2
```

Result:

- container digests differ while the declared logical inventory matches;
- format validation still verifies representation completeness;
- logical equality does not make the artifacts byte-identical;

## 68. External receipt artifact is imported

```yaml
submission_id: submission_0066
receipt_artifact:
  media_type: application/pdf
  digest: c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3
  imported_at: 2026-06-03T12:00:00Z
external_decision: pending
```

Result:

- the imported receipt bytes have independent provenance;
- the digest does not prove authenticity without an external verification contract;
- receipt still does not imply acceptance;

## 69. Snapshot manifest digest and ZIP digest are confused

```yaml
manifest_digest: d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4
zip_digest: e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5
invalid_claim: manifest_digest_equals_export_digest
```

Result:

- validation rejects the semantic mislabeling even though both values are valid SHA-256 text;
- each digest field must identify its byte layer;
- the Seal and Export Artifact remain separate records;

## 70. Audience package omits a format-incompatible Entry

```yaml
edition_entries: [essay_pdf, audio_reflection, toc_html]
export_format: pdf_bundle
excluded_entry_ids: [audio_reflection]
profile_policy: pdf_must_include_audio_transcript
transcript_entry_present: true
```

Result:

- the PDF artifact may be valid only because the required transcript represents the audio content;
- the original audio remains in another Export Artifact;
- silent format loss is prohibited;

## 71. Audience package cannot faithfully represent required media

```yaml
required_entry: interactive_code_project
requested_export_format: pdf_bundle
permitted_alternative: none
outcome: export_inventory_mismatch
```

Result:

- the PDF export fails;
- the Edition may still support an HTML package;
- the builder does not replace the project with an unapproved screenshot;

## Cross-example conclusions

These scenarios establish that:

- exact curation state is frozen before source acquisition;
- source and output byte claims remain independently verifiable;
- unavailable and suppressed content is never represented by silent absence;
- a logical Edition can have several format-specific exports;
- audience-visible changes create successor Editions;
- failed staging is not canonical snapshot history;
- durable sealing survives later cleanup and optional-export failures;
- lifecycle changes preserve issued history;
- external submission facts remain outside local export claims;
- and no producer-private storage becomes accessible merely because a Portfolio selected a source.
