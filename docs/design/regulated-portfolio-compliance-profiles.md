# Regulated Portfolio and Compliance Profile Contracts

- **Issue:** #11, “Define regulated portfolio/compliance profiles”
- **Design date:** 2026-08-05
- **Status:** Foundation design paired with proposed ADR 0009; not a final serialized schema, operational compliance profile, or runtime implementation
- **Applies to:** `pds-vitrine` v0.1.0 foundation work

## 1. Purpose

This document defines how Vitrine specializes its generic Portfolio Profile architecture for regulated Portfolio and compliance workflows.

It defines:

- exact authority-source sets;
- operational activation gates;
- Regulated Portfolio Cases;
- independently evaluated case components;
- pathway selection and eligibility findings;
- versioned checklists and supporting-record requirements;
- immutable checklist, record, and missing-document findings;
- attestations and signer-authority references;
- deadlines, extensions, and late-state findings;
- staged institutional approvals;
- submission-readiness findings;
- school- or institution-level submission batches;
- exact case-to-batch membership;
- generated submission projections;
- rolling and corrected submissions;
- external receipts and outcomes;
- retention and custody references;
- lifecycle, correction, migration, and supersession;
- producer boundaries;
- and one researched New Jersey Graduation Portfolio Appeal reference family.

The paired decision is [ADR 0009: Regulated Portfolio and Compliance Profiles](../decisions/0009-regulated-portfolio-and-compliance-profiles.md). It is **Accepted** following the issue #13 portfolio foundation audit.

The representative scenarios are in [regulated-portfolio-compliance-examples.md](../examples/regulated-portfolio-compliance-examples.md).

## 2. Governing boundary

A regulated Profile describes policy.

A regulated case records execution of that policy for one Portfolio Subject.

A checklist finding records an evaluation.

An approval records an actor decision.

A submission records an external handoff.

An external outcome remains owned by the external authority.

```text
Profile definition
  != regulated case
  != checklist
  != supporting record
  != attestation
  != approval
  != submission readiness
  != Snapshot Edition
  != submission
  != external outcome
```

```text
document exists
  != document is current
  != document is valid
  != document satisfies a requirement
  != checklist is complete
  != institution approved submission
  != package was submitted
  != external authority accepted it
```

Vitrine may preserve attributable evidence and findings. It must not infer legal compliance, graduation eligibility, institutional approval, successful submission, or external acceptance from a local checklist.

## 3. Scope and non-goals

This issue is conceptual and documentation-only.

It does not define:

- final JSON Schema;
- Python models;
- persistence;
- Profile activation commands;
- a runtime evaluator;
- an operational New Jersey Profile;
- official forms or field definitions;
- an external portal integration;
- electronic signature validation;
- legal eligibility;
- official task design or scoring;
- Grades or proficiency;
- authentication or authorization;
- redaction engines;
- secure delivery;
- retention execution;
- or sibling-repository changes.

## 4. Cross-repository review baseline

The following repository state was reviewed for this design.

| Repository | Reviewed state | Implemented or authoritative behavior | Direction relevant to this issue | Boundary preserved |
| --- | --- | --- | --- | --- |
| `pds-vitrine` | [`bf32d04`](https://github.com/Paper-Data-Suite/pds-vitrine/commit/bf32d04ad9617868927054b4689dd269547f8b78) | Documentation-only Profiles, Candidates, curation, immutable Snapshots, privacy, redaction, authorization, and disclosure contracts | Regulated specialization is the remaining v0.1.0 foundation slice | No parallel Profile, authorization, or Snapshot model |
| `pds-core` | [`6c50721`](https://github.com/Paper-Data-Suite/pds-core/commit/6c507213618b68a6dd3ea096e1a898201ff029e6) | Core v0.6 immutable periods, registrations, publications, exact manifest binding, supersession, withdrawal, and rebuildable catalog | Future producer and consumer integration uses exact canonical records | Core does not become a compliance registry |
| `pds-scoreform` | [`c2fa06f`](https://github.com/Paper-Data-Suite/pds-scoreform/commit/c2fa06f1a4c33df01f3e0d9c8dd27702d4a06419) | Academic Work registration and immutable exact-byte manifest generation | Publication profile, Core publication, and public reader remain milestone work | Regulated policy never selects attempts or exposes secure material |
| `pds-quillan` | [`05fecf2`](https://github.com/Paper-Data-Suite/pds-quillan/commit/05fecf23d29e56b45cba58ed97906f5353290033) | Submissions, selected evidence, review, feedback, and private-source boundaries | Core v0.6 publication and consumer-neutral projections are planned | Private review state is not compliance approval |
| `pds-concord` | [`31b0efd`](https://github.com/Paper-Data-Suite/pds-concord/commit/31b0efd2864cd7a0945ff29f5af99b2a00db52ae) | Foundational records plus deterministic guarded persistence and work snapshots | Activity workflow, publication, and consumer-neutral readers remain planned | Group Membership and Group Scores never become individual evidence automatically |
| `pds-portia` | [`0841bd9`](https://github.com/Paper-Data-Suite/pds-portia/commit/0841bd946c6c3a098ebaad4bfb90669816ecc93b) | Append-preserving lifecycle, correction, migration, integrity findings, and exceptional removal | Participant-safe privacy projections remain future work | Sensitive records remain suppressed unless an exact safe projection exists |
| `pds-meridian` | [`0c1f57e`](https://github.com/Paper-Data-Suite/pds-meridian/commit/0c1f57e41da225079df1cb14ece3fe8c0522b744) | Installable package and CI foundation only | Ingestion, evidence, grading, reports, persistence, and delivery remain later work | Grades and reports do not establish regulated Portfolio completion |

### 4.1 Reusable patterns

The design deliberately reuses:

- stable logical identity plus immutable revisions;
- explicit predecessor, successor, supersession, and withdrawal;
- exact source and revision references;
- guarded current pointers rather than greatest-revision inference;
- canonical records plus rebuildable derived views;
- append-preserving correction;
- exact copied-byte and generated-byte provenance;
- action- and purpose-specific authorization;
- and external-outcome authority boundaries.

### 4.2 Incompatible assumptions rejected

The design rejects:

- treating a catalog row as regulated evidence;
- treating a producer result as Profile satisfaction;
- treating a Grade as external eligibility;
- treating Group Membership as authorship or permission;
- using Portia source existence as a checklist fact;
- and importing private producer storage into Vitrine.

## 5. New Jersey source revalidation baseline

The New Jersey research was rechecked on 2026-08-05 against current public NJDOE pages.

The Class of 2026 guidance remains the applicable researched reference:

- the graduation requirements hub identifies the Class of 2026 and a December 2025 Portfolio Appeal update;
- ELA and mathematics remain separate components;
- the standard ELA path requires two reading and two connected writing tasks;
- the standard mathematics path requires four CRTs;
- the streamlined option remains tied to an ASVAB AFQT score of at least 35 and reduces task quantity by 50 percent;
- the public process still separates locally retained student evidence from a school-specific Statement of Assurance and data spreadsheet submitted through Homeroom;
- multiple submissions and corrected `RESUBMISSION` files remain supported;
- the public submission window begins January 6, 2026, identifies May 1, 2026 for adequate June processing time, and permits uploads through August 26, 2026 for the Class of 2026 cohort;
- the 2026–2027 public schedule lists a later January 4 through May 3, 2027 Portfolio Appeals window;
- and NJGPA-Adaptive begins with the Class of 2027.

The complete operational Class of 2027 Portfolio Appeal rule set was not established from the reviewed public sources.

Therefore:

```text
Class of 2026 Profile rules
  != Class of 2027 Profile rules
```

The Class of 2026 reference remains research-only and must not be relabeled or silently migrated for a future cohort.

## 6. Terms

### 6.1 Regulated Profile Specification

The **Regulated Profile Specification** is the regulated specialization contained by one exact immutable Portfolio Profile Revision.

### 6.2 Authority Source Set

An **Authority Source Set** is the immutable inventory of public, restricted, local, and institutional authority inputs used to author and activate a Profile revision.

### 6.3 Regulated Portfolio Case

A **Regulated Portfolio Case** is the durable Vitrine record connecting one Portfolio and Subject to execution of one exact regulated Profile Binding.

### 6.4 Case Component

A **Case Component** is an independently evaluable portion of a case, such as English language arts or mathematics.

### 6.5 Pathway Selection

A **Pathway Selection** records the exact permitted pathway chosen for one case component and the authority and eligibility evidence supporting the choice.

### 6.6 Eligibility Finding

An **Eligibility Finding** records an evaluation of one exact applicability or pathway rule against one exact case state.

### 6.7 Regulated Checklist

A **Regulated Checklist** is a versioned Profile definition grouping ordered checklist items.

### 6.8 Checklist Item Finding

A **Checklist Item Finding** is an immutable evaluation of one exact checklist item against one exact case, component, batch, or submission state.

### 6.9 Supporting Record

A **Supporting Record** is an exact source-owned or Vitrine-generated record used as evidence for a regulated requirement.

### 6.10 Attestation

An **Attestation** is an actor-authored assertion of one exact versioned statement.

### 6.11 Regulated Approval

A **Regulated Approval** is an actor decision at one Profile-defined stage, bound to one exact target revision.

### 6.12 Submission Readiness

**Submission Readiness** is a derived evaluation of whether exact local prerequisites for a proposed handoff are complete.

### 6.13 Submission Batch

A **Submission Batch** is a school-, institution-, program-, or authority-scoped grouping of one or more cases or components for one external handoff.

### 6.14 External Outcome

An **External Outcome** is an authority-owned receipt, correction request, approval, denial, or other decision imported by exact reference.

## 7. Conceptual graph

```text
Portfolio Profile Family
  -> Portfolio Profile series [1..*]
      -> Portfolio Profile Revision [1..*]
          -> Regulated Profile Specification [0..1]
              -> Authority Source Set [1]
              -> Component Definitions [1..*]
              -> Pathway Definitions [1..*]
              -> Checklist Definitions [1..*]
              -> Supporting Record Requirements [0..*]
              -> Attestation Requirements [0..*]
              -> Deadline Rules [0..*]
              -> Approval Stage Definitions [0..*]
              -> Submission Batch Rules [0..*]

Portfolio
  -> Portfolio Profile Binding
      -> exact Portfolio Profile Revision
      -> Regulated Portfolio Case
          -> Case Components [1..*]
              -> Pathway Selections [0..*]
              -> Eligibility Findings [0..*]
              -> Checklist Item Findings [0..*]
              -> Supporting Record Instances [0..*]
              -> Approval Decisions [0..*]
              -> Submission Readiness Findings [0..*]

Submission Batch
  -> Case-to-Batch Memberships [1..*]
  -> generated data projections [0..*]
  -> exact Snapshot Edition / Export Artifacts
  -> Submission [0..*]
      -> Receipt [0..*]
      -> External Outcome [0..*]
```

No edge in the graph grants access, verifies a signature, creates an approval, or fabricates an external outcome.

## 8. Governing principles

### 8.1 Regulated specialization, not a parallel subsystem

Regulated policy uses the generic Portfolio Profile identity, revision, lifecycle, composition, overlay, binding, and migration contracts.

### 8.2 Research is not activation

A researched Profile example may explain structure while remaining prohibited for operational use.

### 8.3 Exact sources

Every operational rule must be traceable to an exact authority source or attributable local overlay.

### 8.4 Immutable activated meaning

Activated regulated Profiles are immutable. Material changes create successor revisions.

### 8.5 Component independence

One component's eligibility, readiness, approval, submission, or outcome does not imply another component's state.

### 8.6 Evidence dimensions remain separate

Presence, validity, satisfaction, approval, submission, and outcome are separate dimensions.

### 8.7 Unknown fails closed

Unknown never becomes satisfied, waived, approved, or accepted.

### 8.8 Human and external authority remain explicit

Vitrine may assist review but never manufactures actor authority or external decisions.

### 8.9 Historical preservation

Corrections and resubmissions create successor records. Prior cases, packages, submissions, receipts, and outcomes remain historical.

### 8.10 Minimum necessary

Regulated purpose does not justify unrestricted access to sensitive records.

## 9. Regulated Profile Specification conceptual contract

| Field | Meaning |
| --- | --- |
| `regulated_profile_specification_id` | Stable identity for the regulated specialization of one Profile revision. |
| `portfolio_profile_id` | Stable generic Profile series identity. |
| `profile_revision` | Exact immutable Profile revision containing this specification. |
| `regulated_program_family_id` | Durable grouping for related regulated program series. |
| `regulated_program_id` | Stable logical program or pathway identity. |
| `program_version` | Authority-owned program version where one exists. |
| `jurisdiction` | Jurisdictional scope without implying legal interpretation. |
| `administering_authority_ref` | Exact authority or custodian reference. |
| `school_year_scope` | Applicable school year or bounded set. |
| `cohort_scope` | Applicable graduation or program cohort. |
| `component_definition_ids` | Exact independently evaluated component definitions. |
| `pathway_definition_ids` | Permitted pathway definitions. |
| `authority_source_set_id` | Exact immutable authority-source inventory. |
| `checklist_definition_ids` | Exact versioned checklist definitions. |
| `supporting_record_requirement_ids` | Exact evidence requirements. |
| `attestation_requirement_ids` | Exact versioned assertions and signer rules. |
| `deadline_rule_ids` | Exact deadline and extension policies. |
| `approval_stage_definition_ids` | Exact staged review policy. |
| `submission_batch_rule_ids` | Exact batch and external-handoff policy. |
| `audience_rule_ids` | Existing Profile audience rules used for regulated review and submission. |
| `retention_rule_ids` | Existing Profile retention references. |
| `component_provenance` | Exact component Profiles and local overlays flattened into the effective revision. |

### 9.1 One-to-one revision binding

For v0.1.0 design:

```text
one Portfolio Profile Revision
  -> zero or one Regulated Profile Specification
```

The regulated specification cannot be reused by a different Profile revision.

### 9.2 Activation blockers

Activation is blocked when:

- a required authority source is unresolved;
- public and restricted sources conflict;
- a required form or field-definition version is unknown;
- cohort applicability is uncertain;
- a local overlay has unresolved conflicts;
- a checklist dependency cycle exists;
- signer or approval rules are structurally invalid;
- deadline rules cannot be evaluated deterministically;
- or required privacy and submission audience rules are absent.

### 9.3 Forbidden behavior

The regulated specification must not contain:

- student data;
- credentials;
- private signing keys;
- copied restricted templates intended for public distribution;
- executable condition code;
- hidden latest-version lookup;
- or a Boolean legal-compliance certification.

## 10. Authority Source Set conceptual contract

| Field | Meaning |
| --- | --- |
| `authority_source_set_id` | Stable identity for one immutable source-set revision. |
| `source_set_revision` | Immutable source-set revision. |
| `profile_revision_ref` | Exact regulated Profile revision supported by the source set. |
| `source_entries` | Ordered exact Authority Source Entries. |
| `verified_by` | Authorized actor or service that completed the review. |
| `verified_at` | Review completion time. |
| `verification_summary` | Privacy-safe structured result, not a legal opinion. |
| `activation_effect` | Whether unresolved findings block activation. |
| `predecessor_source_set_ref` | Prior source set when updated. |

### 10.1 Authority Source Entry

| Field | Meaning |
| --- | --- |
| `authority_source_entry_id` | Stable entry identity inside the source set. |
| `source_class` | `public_source`, `restricted_portal_source`, `local_policy_source`, or `institutional_decision`. |
| `title_snapshot` | Source title recorded at review time. |
| `controlling_authority_ref` | Authority responsible for the source. |
| `locator_ref` | Public URL or restricted/local locator reference. |
| `source_version` | Published version, form revision, or locally assigned revision. |
| `published_or_effective_at` | Source publication or effective time where known. |
| `retrieved_or_verified_at` | Exact review time. |
| `content_digest` | Digest where lawful, available, and meaningful. |
| `applicability` | Program, cohort, component, and date scope. |
| `verification_status` | Exact status from the controlled vocabulary. |
| `supersedes_source_ref` | Earlier source replaced by this source. |
| `distribution_restriction` | Whether content may be reproduced or only referenced. |
| `notes` | Bounded research or operational note without restricted content. |

### 10.2 Verification states

```text
verified_current
verified_historical
restricted_verified
local_verified
unavailable
stale
conflicting
superseded
unknown
```

`verified_historical` may support replay of an old Profile revision but cannot establish current operational authority.

### 10.3 Source-change classification

A revalidation finding classifies each change as:

```text
required_profile_contract_change
reference_profile_revision
research_documentation_update
future_cohort_concern
restricted_source_dependency
local_policy_dependency
no_immediate_implication
```

### 10.4 Restricted-source rule

Restricted-source metadata may be recorded without copying its substantive content into the repository.

The system may preserve:

- source identity;
- version;
- digest;
- authorized verifier;
- verification time;
- and activation effect.

It must not preserve portal credentials or publicly redistribute restricted templates.

## 11. Regulated Portfolio Case conceptual contract

| Field | Meaning |
| --- | --- |
| `regulated_case_id` | Stable opaque case identity. |
| `portfolio_id` | Exact Vitrine Portfolio. |
| `portfolio_subject_id` | Exact Portfolio Subject. |
| `portfolio_profile_binding_id` | Exact binding to one Profile revision. |
| `regulated_profile_specification_id` | Exact regulated specification. |
| `institution_ref` | Institution or LEA/APSSD reference. |
| `responsible_office_ref` | Institutional office responsible for custody and workflow. |
| `school_or_program_scope_ref` | School, program, or accountable entity. |
| `school_year` | Case school-year context. |
| `cohort` | Exact cohort context. |
| `opened_by` | Actor who opened the case. |
| `opened_at` | Case opening time. |
| `opening_authority_ref` | Authority for case initiation. |
| `component_ids` | Exact independently evaluated components. |
| `custody_ref` | Authoritative local custody location or system reference. |
| `lifecycle_event_ids` | Append-preserving lifecycle. |
| `predecessor_case_ref` | Prior case corrected or migrated into this case. |
| `successor_case_ref` | Later case where one exists. |

### 11.1 Case identity rules

Case identity must not encode:

- student name;
- state student identifier;
- disability status;
- pathway;
- outcome;
- or approval state.

### 11.2 Case lifecycle

Initial lifecycle events are:

```text
opened
activated
withdrawn
invalidated
closed
superseded
```

Profile-defined workflow stages may be represented separately. They must not replace lifecycle history.

### 11.3 Current case

Where a current-case pointer is used, it must be explicit and conflict-aware.

The greatest case revision or newest timestamp is not authority.

## 12. Case Component conceptual contract

| Field | Meaning |
| --- | --- |
| `case_component_id` | Stable component identity within the case. |
| `regulated_case_id` | Owning case. |
| `component_definition_id` | Exact Profile component definition. |
| `component_kind` | Controlled program-specific kind, such as `english_language_arts` or `mathematics`. |
| `applicability_finding_ref` | Exact applicability result. |
| `active_pathway_selection_ref` | Explicit current pathway selection where resolved. |
| `checklist_scope_refs` | Applicable checklist definitions. |
| `readiness_finding_refs` | Historical readiness findings. |
| `submission_membership_refs` | Exact batch memberships. |
| `external_outcome_refs` | Exact component outcomes. |
| `lifecycle_event_ids` | Append-preserving component lifecycle. |

### 12.1 Component independence

The following remain separate for every component:

- applicability;
- eligibility;
- selected pathway;
- evidence;
- checklist findings;
- approvals;
- readiness;
- submissions;
- receipts;
- and outcomes.

### 12.2 New Jersey reference components

The Class of 2026 reference family uses at least:

```text
english_language_arts
mathematics
```

A student may satisfy those requirements through different pathways. Vitrine must not create one undifferentiated case-complete Boolean.

## 13. Pathway Definition and Selection

### 13.1 Pathway Definition

| Field | Meaning |
| --- | --- |
| `pathway_definition_id` | Stable Profile-owned pathway identity. |
| `pathway_series_ref` | Independent logical pathway series where used. |
| `label` | Human-readable pathway label. |
| `component_scope` | Components to which the pathway may apply. |
| `applicability_condition` | Bounded three-valued Profile condition. |
| `eligibility_rule_ids` | Exact eligibility rules. |
| `checklist_definition_ids` | Checklist set for this pathway. |
| `record_requirement_ids` | Pathway-specific evidence requirements. |
| `attestation_requirement_ids` | Pathway-specific attestations. |
| `deadline_rule_ids` | Pathway-specific deadlines. |
| `simultaneous_variant_group` | Group identifying mutually exclusive or coexisting alternatives. |

### 13.2 Pathway Selection

| Field | Meaning |
| --- | --- |
| `pathway_selection_id` | Stable immutable selection record. |
| `regulated_case_id` | Owning case. |
| `case_component_id` | Exact component. |
| `pathway_definition_id` | Selected exact pathway definition. |
| `eligibility_finding_refs` | Evidence-backed findings supporting selection. |
| `selected_by` | Actor making or recording the selection. |
| `selection_authority_ref` | Authority permitting the actor to select. |
| `selected_at` | Selection time. |
| `rationale` | Bounded rationale. |
| `unresolved_condition_refs` | Conditions that remain explicit. |
| `predecessor_selection_ref` | Prior pathway selection when changed. |
| `selection_status` | `active`, `superseded`, `withdrawn`, or `invalidated`. |

### 13.3 Simultaneous alternatives

Standard and streamlined pathways are alternatives, not sequential policy revisions merely because their requirements differ.

Recommended reference-family structure:

```text
Portfolio Profile Family
  -> standard pathway Profile series
  -> streamlined pathway Profile series

each Profile series
  -> immutable cohort / school-year revisions
```

A composed-variant model may also be valid if it preserves:

- independent pathway identity;
- independently versioned rules;
- explicit selection;
- and no false latest-pathway inference.

### 13.4 No automatic easiest-path choice

Vitrine must not select a pathway because it:

- has fewer tasks;
- appears easier;
- has fewer missing findings;
- or was used last year.

## 14. Eligibility and Applicability Finding conceptual contract

| Field | Meaning |
| --- | --- |
| `eligibility_finding_id` | Stable immutable finding. |
| `regulated_case_id` | Exact case. |
| `case_component_id` | Exact component or null for case-wide applicability. |
| `pathway_definition_id` | Pathway evaluated where relevant. |
| `profile_requirement_id` | Exact eligibility/applicability rule. |
| `evaluated_fact_refs` | Exact facts or bounded external findings. |
| `supporting_record_refs` | Exact records supporting the evaluation. |
| `evaluated_by` | Actor or deterministic evaluator. |
| `evaluated_at` | Evaluation time. |
| `result` | Controlled result. |
| `unresolved_fact_refs` | Facts that could not be established. |
| `rationale` | Bounded explanation. |
| `predecessor_finding_ref` | Prior finding when reevaluated. |
| `effect` | Whether later workflow is permitted, blocked, or conditional. |

### 14.1 Results

```text
eligible
not_eligible
conditional
indeterminate
expired
```

### 14.2 Boundary

Eligibility does not establish:

- checklist completion;
- evidence validity;
- institutional approval;
- submission;
- or external acceptance.

## 15. Regulated Checklist Definition

| Field | Meaning |
| --- | --- |
| `regulated_checklist_id` | Stable checklist series identity. |
| `checklist_revision` | Exact immutable checklist revision. |
| `profile_revision_ref` | Exact Profile revision. |
| `scope_kind` | `case`, `component`, `supporting_record`, `institution`, `submission_batch`, `submission`, or `outcome`. |
| `scope_selector` | Exact component, pathway, batch rule, or other scope. |
| `item_ids` | Complete ordered checklist-item inventory. |
| `applicability_condition` | Bounded three-valued condition. |
| `blocking_policy` | How unsatisfied and unknown findings affect readiness. |
| `predecessor_checklist_ref` | Prior checklist revision. |

### 15.1 Checklist Item Definition

| Field | Meaning |
| --- | --- |
| `checklist_item_id` | Stable semantic item identity. |
| `sequence` | Explicit display and evaluation order. |
| `requirement_id` | Exact Profile requirement. |
| `obligation` | `required`, `optional`, `conditional`, or `prohibited`. |
| `applicability_condition` | Bounded condition. |
| `dependency_item_ids` | Acyclic prerequisite items. |
| `expected_record_requirement_ids` | Supporting records considered. |
| `evaluator_role_requirements` | Authorized evaluator roles. |
| `allowed_result_states` | Permitted finding states. |
| `readiness_effect` | Blocking, warning, informational, or prohibited. |
| `replacement_item_id` | Successor identity when semantics change. |

### 15.2 Stable checklist identity

An item ID remains stable only when semantic meaning remains continuous.

Changing wording alone may preserve identity.

Changing:

- obligation;
- evidence expectation;
- component;
- threshold;
- waiver authority;
- or readiness effect

normally requires a new item ID or explicit replacement relationship.

### 15.3 No mutable canonical checkboxes

User-interface checkboxes are derived controls.

The canonical result is an immutable Checklist Item Finding.

## 16. Checklist Item Finding conceptual contract

| Field | Meaning |
| --- | --- |
| `checklist_item_finding_id` | Stable immutable finding identity. |
| `regulated_checklist_ref` | Exact checklist and revision. |
| `checklist_item_id` | Exact item. |
| `target_ref` | Exact case, component, record, batch, submission, or outcome. |
| `evaluated_state_ref` | Exact case/composition/batch revision evaluated. |
| `evaluated_record_refs` | Exact Supporting Record Instances. |
| `requirement_result` | Satisfaction result. |
| `record_presence` | Presence dimension. |
| `record_validation` | Validation dimension. |
| `evaluated_by` | Actor or deterministic evaluator. |
| `evaluated_at` | Evaluation time. |
| `rationale` | Bounded reason. |
| `unresolved_condition_refs` | Exact unresolved conditions. |
| `waiver_decision_ref` | Exact authorized waiver where applicable. |
| `readiness_effect` | Resulting effect. |
| `predecessor_finding_ref` | Prior finding. |

### 16.1 Requirement result vocabulary

```text
satisfied
not_satisfied
not_applicable
waived
unknown
```

### 16.2 Record presence vocabulary

```text
present
missing
unavailable
withheld
unknown
```

### 16.3 Record validation vocabulary

```text
verified
unverified
invalid
stale
mismatched
superseded
not_applicable
```

### 16.4 Three dimensions are not collapsed

Examples:

- `present + stale + not_satisfied`;
- `withheld + unverified + unknown`;
- `present + verified + not_satisfied`;
- `missing + not_applicable + waived` only with an exact authorized waiver;
- and `present + verified + satisfied`.

### 16.5 Derived checklist completion

A completion summary is derived from exact findings.

It is not:

- an approval;
- a compliance certification;
- a submission;
- or an external outcome.

## 17. Supporting Record Requirement conceptual contract

| Field | Meaning |
| --- | --- |
| `supporting_record_requirement_id` | Stable Profile requirement identity. |
| `profile_requirement_id` | Parent generic Profile requirement. |
| `scope_kind` | Case, component, batch, submission, or outcome scope. |
| `permitted_record_kinds` | Controlled accepted record classes. |
| `required_cardinality` | Minimum, maximum, and exact counts where applicable. |
| `accepted_projection_kinds` | Producer-approved projection kinds permitted. |
| `required_properties` | Structured fields or properties to validate. |
| `recency_rule` | Allowed age or effective-date policy. |
| `signature_expectation` | Required signature/attestation relationship. |
| `grading_or_scoring_expectation` | Expected externally defined evaluation properties. |
| `privacy_class` | Minimum privacy classification. |
| `local_retention_rule_ref` | Required local custody/retention policy. |
| `submission_treatment` | Local-only, summarized, copied, generated, or externally transmitted. |
| `waiver_policy_ref` | Exact waiver authority, if any. |
| `prohibited_source_classes` | Explicitly prohibited sources. |

### 17.1 Producer neutrality

A requirement may accept several source types without declaring them semantically identical.

For example, a requirement may permit:

- a ScoreForm result projection;
- a Quillan reviewed-work projection;
- a Concord individual Artifact projection;
- a Meridian report projection;
- or an external document.

The Profile must still define what property is required and how satisfaction is evaluated.

## 18. Supporting Record Instance conceptual contract

| Field | Meaning |
| --- | --- |
| `supporting_record_instance_id` | Stable Vitrine evidence-reference identity. |
| `regulated_case_id` | Exact case. |
| `case_component_id` | Exact component where applicable. |
| `supporting_record_requirement_id` | Requirement the record may support. |
| `source_owner` | Producer, Vitrine, institution, or external authority. |
| `source_record_ref` | Exact authoritative source identity and revision. |
| `candidate_ref` | Exact Candidate where the record entered Vitrine discovery. |
| `selection_ref` | Exact Selection where curated. |
| `snapshot_entry_ref` | Exact copied/generated Entry where sealed. |
| `external_record_ref` | External authoritative reference where applicable. |
| `record_kind` | Controlled record kind. |
| `title_snapshot` | Bounded title at association time. |
| `custody_ref` | Local or external custody reference. |
| `recorded_or_acquired_at` | Association or acquisition time. |
| `content_digest` | Exact digest when meaningful and available. |
| `validation_finding_ref` | Current exact validation finding. |
| `predecessor_record_ref` | Earlier instance corrected or replaced. |
| `successor_record_ref` | Later instance. |
| `availability` | Current source availability, separate from historical use. |

### 18.1 Record identity

A filename is not record identity.

A file renamed without byte changes remains the same source only where the source authority says so.

A replaced file with the same name is a new record revision.

### 18.2 Source lifecycle

Source withdrawal or supersession does not rewrite:

- prior findings;
- prior sealed Snapshot Entries;
- prior submissions;
- or prior outcomes.

It may block future use or require reevaluation.

## 19. Missing or Defective Record Finding

| Field | Meaning |
| --- | --- |
| `record_finding_id` | Stable immutable finding. |
| `supporting_record_requirement_id` | Exact expected requirement. |
| `target_ref` | Exact case, component, batch, or submission. |
| `finding_kind` | Controlled missing/defect vocabulary. |
| `searched_or_evaluated_scope` | Bounded description of what was checked. |
| `record_refs` | Any records evaluated. |
| `evaluated_by` | Actor or service. |
| `evaluated_at` | Time. |
| `reason` | Privacy-safe reason. |
| `readiness_effect` | Blocking, conditional, warning, or informational. |
| `visibility_class` | Who may see the detailed reason. |
| `predecessor_finding_ref` | Earlier finding. |
| `resolution_ref` | Later record or finding resolving the issue. |

### 19.1 Finding kinds

```text
record_missing
record_unavailable
record_withheld
record_unverified
record_invalid
record_stale
record_wrong_revision
record_wrong_component
record_wrong_subject
record_wrong_cohort
record_signature_incomplete
record_content_mismatch
record_superseded
```

### 19.2 No placeholder documents

An empty file, blank form, or generated stub must not be created as evidence merely to satisfy file-count logic.

### 19.3 No-existence leakage

A user-facing missing finding must not reveal suppressed Portia source existence or other restricted facts.

Detailed internal findings remain subject to issue #10 authorization.

## 20. Attestation Requirement conceptual contract

| Field | Meaning |
| --- | --- |
| `attestation_requirement_id` | Stable statement requirement identity. |
| `statement_id` | Stable logical statement identity. |
| `statement_revision` | Exact immutable statement revision. |
| `statement_text_or_digest` | Exact text where distributable, otherwise a digest/reference. |
| `target_scope` | Case, component, batch, submission, or exact artifact. |
| `required_signer_roles` | Exact authorized roles. |
| `required_signer_count` | Required number of distinct signers. |
| `sequence_rule` | Signing order if meaningful. |
| `separation_of_duties_rule` | Required role or identity separation. |
| `permitted_signature_methods` | Reference, wet-signature document, approved electronic service, or other method. |
| `authority_evidence_requirements` | Required evidence that signer held the role. |
| `effective_period` | Validity period. |
| `invalidation_triggers` | Target changes, role changes, expiration, or document replacement. |

## 21. Attestation Record conceptual contract

| Field | Meaning |
| --- | --- |
| `attestation_record_id` | Stable immutable actor assertion. |
| `attestation_requirement_id` | Exact requirement. |
| `statement_revision` | Exact statement asserted. |
| `target_ref` | Exact target revision. |
| `signer_ref` | Actor identity reference. |
| `asserted_role` | Role asserted at signing. |
| `authority_evidence_ref` | Exact evidence of signer authority. |
| `asserted_at` | Signing or assertion time. |
| `signature_method_ref` | Method or external signature-system reference. |
| `signed_document_ref` | Exact signed document where applicable. |
| `signed_document_digest` | Exact digest where applicable. |
| `verification_decision_ref` | Separate exact verification. |
| `predecessor_attestation_ref` | Earlier replaced attestation. |
| `lifecycle` | Active, superseded, withdrawn, invalidated, or expired. |

### 21.1 Attestation Verification Decision

| Field | Meaning |
| --- | --- |
| `attestation_verification_id` | Stable immutable verification decision. |
| `attestation_record_id` | Exact attestation. |
| `reviewed_document_digest` | Exact bytes reviewed where applicable. |
| `reviewed_authority_evidence_ref` | Exact authority evidence. |
| `verified_by` | Authorized verifier. |
| `verified_at` | Verification time. |
| `decision` | `verified`, `rejected`, `changes_required`, `indeterminate`, or `expired`. |
| `reason` | Bounded reason. |
| `predecessor_verification_ref` | Earlier decision. |

### 21.2 Signature boundaries

A signature image alone does not prove:

- identity;
- role;
- authority;
- intent;
- document integrity;
- or legal validity.

Vitrine records references and verification decisions. It does not claim electronic-signature validity.

## 22. Deadline Rule conceptual contract

| Field | Meaning |
| --- | --- |
| `deadline_rule_id` | Stable Profile-owned rule identity. |
| `deadline_kind` | Controlled deadline class. |
| `authority_source_ref` | Exact source authorizing the rule. |
| `scope` | Profile, case, component, batch, or submission. |
| `calculation_kind` | `absolute`, `relative`, or bounded calendar expression. |
| `calculation_parameters` | Exact deterministic inputs. |
| `timezone` | IANA timezone or exact authority-defined zone. |
| `classification` | `recommended`, `internal_required`, or `external_final`. |
| `business_calendar_ref` | Exact calendar where business-day logic is required. |
| `extension_authority_rule` | Who may extend and what evidence is required. |
| `late_effect` | Workflow effect without fabricating an external outcome. |
| `predecessor_rule_ref` | Earlier rule. |

### 22.1 Deadline kinds

```text
case_open
evidence_complete
local_review
recommended_submission
final_submission
resubmission
external_response
retention_trigger
```

## 23. Deadline Instance and Status Finding

| Field | Meaning |
| --- | --- |
| `deadline_instance_id` | Exact case- or batch-specific deadline. |
| `deadline_rule_id` | Exact rule. |
| `target_ref` | Case, component, batch, or submission. |
| `calculation_input_refs` | Exact facts and calendars used. |
| `calculated_deadline` | Exact timestamp. |
| `calculated_at` | Calculation time. |
| `extension_record_refs` | Exact authorized extensions. |
| `status_finding` | Current status. |
| `predecessor_instance_ref` | Earlier instance replaced by rule/input change. |

### 23.1 Status vocabulary

```text
not_yet_due
due_soon
due
past_due
completed_on_time
completed_late
extended
not_applicable
indeterminate
```

### 23.2 Deadline Extension

| Field | Meaning |
| --- | --- |
| `deadline_extension_id` | Stable immutable extension or exception. |
| `deadline_instance_id` | Affected exact deadline. |
| `authority_ref` | Authority granting the change. |
| `authority_evidence_ref` | Exact evidence. |
| `reason` | Bounded reason. |
| `new_deadline` | Exact replacement timestamp. |
| `effective_at` | Effective time. |
| `scope` | Exact cases/components/batches affected. |
| `conditions` | Any explicit conditions. |
| `supersedes_extension_ref` | Earlier extension. |

### 23.3 No fabricated consequence

A passed local or external deadline may produce a `past_due` finding.

It does not independently prove:

- ineligibility;
- external denial;
- waiver;
- or legal consequence.

## 24. Approval Stage Definition

| Field | Meaning |
| --- | --- |
| `approval_stage_definition_id` | Stable Profile stage identity. |
| `stage_sequence` | Explicit stage order. |
| `stage_kind` | Profile-defined review purpose. |
| `target_scope` | Case, component, checklist state, Composition, Edition, batch, or submission. |
| `required_actor_roles` | Authorized decision roles. |
| `quorum_rule` | Required count and combination. |
| `sequence_dependencies` | Required prior stages. |
| `separation_of_duties_rule` | Role or identity separation. |
| `required_checklist_states` | Exact prerequisite findings. |
| `required_attestation_ids` | Exact prerequisite attestations. |
| `allowed_outcomes` | Permitted decision states. |
| `reapproval_triggers` | Material target changes requiring new review. |

### 24.1 Typical stage kinds

```text
evidence_review
content_area_review
privacy_review
accessibility_review
records_review
school_approval
institutional_submission_approval
```

## 25. Regulated Approval Decision

| Field | Meaning |
| --- | --- |
| `regulated_approval_decision_id` | Stable immutable decision. |
| `approval_stage_definition_id` | Exact stage. |
| `target_ref` | Exact immutable target revision. |
| `decision` | Controlled outcome. |
| `decided_by` | Actor. |
| `authority_evidence_ref` | Exact decision authority. |
| `decided_at` | Decision time. |
| `reason` | Bounded rationale. |
| `condition_refs` | Exact conditions. |
| `predecessor_decision_ref` | Earlier decision. |
| `supersedes_decision_ref` | Decision replaced for future use. |

### 25.1 Outcomes

```text
approved
rejected
changes_requested
acknowledged
waived
indeterminate
```

### 25.2 Exact-target rule

An approval applies only to the exact target reviewed.

A changed:

- checklist finding;
- supporting record;
- attestation;
- Composition Revision;
- Snapshot Edition;
- Export Artifact;
- batch membership;
- or generated data file

may require new approval under the Profile's reapproval rules.

## 26. Submission Readiness Finding

| Field | Meaning |
| --- | --- |
| `submission_readiness_finding_id` | Stable immutable readiness evaluation. |
| `target_ref` | Exact case, component, or batch revision. |
| `profile_revision_ref` | Exact Profile rules. |
| `evaluated_at` | Evaluation time. |
| `evaluated_by` | Evaluator or deterministic service. |
| `eligibility_finding_refs` | Exact eligibility inputs. |
| `checklist_finding_refs` | Exact checklist inputs. |
| `record_finding_refs` | Exact missing/defect inputs. |
| `attestation_verification_refs` | Exact verified attestations. |
| `deadline_instance_refs` | Exact deadline status. |
| `approval_decision_refs` | Exact stage decisions. |
| `authorization_decision_refs` | Exact privacy/authorization decisions. |
| `snapshot_or_export_refs` | Exact package state. |
| `result` | Controlled readiness result. |
| `blocking_finding_refs` | Exact blockers. |
| `predecessor_finding_ref` | Prior readiness evaluation. |

### 26.1 Results

```text
ready
not_ready
conditionally_ready
indeterminate
```

### 26.2 Boundary

Readiness is not:

- an institutional approval;
- a Submission;
- a Receipt;
- or an External Outcome.

## 27. Submission Batch conceptual contract

| Field | Meaning |
| --- | --- |
| `submission_batch_id` | Stable logical batch identity. |
| `batch_revision` | Exact immutable batch revision. |
| `profile_revision_ref` | Exact regulated Profile. |
| `institution_ref` | Submitting institution. |
| `school_or_program_scope_ref` | Single school/program scope where required. |
| `submission_period_ref` | Exact deadline/window context. |
| `destination_ref` | External authority or system. |
| `batch_rule_ref` | Exact Profile batch rules. |
| `membership_refs` | Exact case/component memberships. |
| `batch_supporting_record_refs` | Batch-level documents. |
| `batch_attestation_refs` | Batch-level attestations. |
| `batch_approval_refs` | Exact approvals. |
| `snapshot_edition_ref` | Exact sealed logical package where used. |
| `export_artifact_refs` | Exact files intended for handoff. |
| `lifecycle_event_refs` | Append-preserving lifecycle. |
| `predecessor_batch_ref` | Prior corrected or replaced batch. |

### 27.1 Student case and batch are distinct

```text
Regulated Portfolio Case
  != Submission Batch
```

One batch may contain several cases.

One case may participate in several batches over time.

### 27.2 Batch revision

Changing membership, a batch-level document, generated data, attestation, approval, Snapshot Edition, or Export Artifact creates a new immutable batch revision.

## 28. Case-to-Batch Membership

| Field | Meaning |
| --- | --- |
| `case_to_batch_membership_id` | Stable immutable membership. |
| `submission_batch_ref` | Exact batch revision. |
| `regulated_case_id` | Exact case. |
| `case_component_ids` | Exact components included. |
| `submitted_value_projection_ref` | Exact generated row/value projection. |
| `readiness_finding_ref` | Exact readiness result. |
| `included_by` | Actor. |
| `included_at` | Time. |
| `inclusion_authority_ref` | Authority. |
| `predecessor_membership_ref` | Earlier membership corrected or replaced. |
| `membership_status` | Included, superseded, withdrawn, or invalidated. |

### 28.1 Duplicate protection

The same case/component must not appear twice in one exact active batch revision unless the Profile explicitly permits separate distinguishable rows.

## 29. Generated Submission Projection

| Field | Meaning |
| --- | --- |
| `generated_submission_projection_id` | Stable generated projection identity. |
| `submission_batch_ref` | Exact batch revision. |
| `case_to_batch_membership_id` | Exact membership. |
| `field_rule_set_ref` | Exact Profile/restricted field-definition version. |
| `field_value_provenance` | Per-field source and transformation references. |
| `validation_finding_refs` | Exact validation results. |
| `generated_row_digest` | Digest of deterministic row representation. |
| `batch_position` | Exact position within generated file. |
| `generated_file_entry_ref` | Exact Snapshot or Export Entry. |
| `generator_contract` | Generator identity and version. |
| `generated_at` | Generation time. |

### 29.1 Projection is not the case

A spreadsheet row or upload record is an external-format projection.

It is not the canonical Regulated Portfolio Case.

### 29.2 Restricted field definitions

When field definitions are restricted:

- the Profile references the exact verified version or digest;
- generation requires authorized access;
- repository examples use synthetic field names;
- and activation remains blocked if required definitions are unavailable.

## 30. Submission, Receipt, and Resubmission

The generic immutable Submission contract from the snapshot design remains authoritative.

A regulated Submission binds:

- exact Submission Batch revision;
- exact Snapshot Edition;
- exact Export Artifacts;
- exact destination;
- exact submitter and authority;
- submission time;
- and external tracking or receipt references.

### 30.1 Rolling submission

A later submission may add newly completed cases or components.

It creates a new batch revision or new batch according to the Profile.

Earlier submissions remain historical.

### 30.2 Corrected resubmission

Changing submitted bytes creates:

- a new Export Artifact;
- a new Submission;
- an explicit correction or predecessor relationship;
- and preserved prior receipt history.

### 30.3 Receipt boundary

A successful local upload attempt is not a Receipt.

A Receipt must be grounded in the external system or authority.

## 31. External Outcome Reference

| Field | Meaning |
| --- | --- |
| `external_outcome_reference_id` | Stable Vitrine reference to one authority-owned outcome. |
| `external_authority_ref` | Authority issuing the outcome. |
| `target_kind` | Case, component, batch, or submission. |
| `target_ref` | Exact target. |
| `raw_outcome_kind` | Authority-native outcome. |
| `normalized_profile_mapping` | Bounded Profile interpretation. |
| `outcome_at` | Authority outcome time. |
| `received_at` | Institution receipt time. |
| `outcome_document_ref` | Exact authoritative document/system result. |
| `outcome_document_digest` | Digest where available. |
| `affected_component_ids` | Exact components affected. |
| `condition_or_correction_refs` | Authority-requested actions. |
| `recorded_by` | Actor importing or recording the outcome. |
| `predecessor_outcome_ref` | Earlier outcome corrected or replaced. |

### 31.1 Raw outcome preservation

The authority-native outcome remains preserved even when Vitrine maps it to controlled states.

### 31.2 Normalized mapping

A normalized mapping may support workflow values such as:

```text
approved
denied
returned_for_correction
partially_approved
pending
withdrawn
unknown
```

The mapping must not broaden the external meaning.

### 31.3 Partial outcomes

An outcome may approve one component while another remains pending, denied, or returned for correction.

## 32. Retention and custody

A regulated Profile may reference:

- record classes;
- retention schedules;
- trigger dates;
- minimum periods;
- permanent or indefinite status;
- legal or audit holds;
- responsible custodians;
- archival transfer;
- disposition approval;
- and staff-transition requirements.

Vitrine must preserve:

- the exact policy reference;
- who assigned the classification;
- the classification state;
- and unresolved status.

It must not autonomously classify or destroy records.

### 32.1 Staff transition

A case must remain retrievable independently of one teacher's account or workstation.

At minimum, preserve:

- responsible office;
- institutional custodian;
- storage/custody reference;
- current assigned coordinator;
- transition event;
- and verification that required records remain retrievable.

## 33. Lifecycle, correction, and migration

### 33.1 Profile correction

An activated Profile is never edited in place.

A material source or rule correction creates a successor Profile revision and explicit lifecycle relationship.

### 33.2 Case correction

A mistaken subject, Profile Binding, cohort, institution, or component assignment creates an invalidation and corrected successor case.

### 33.3 Finding correction

A later Checklist Item Finding supersedes the earlier operational finding while preserving it.

### 33.4 Record replacement

A corrected Supporting Record Instance links to the replaced instance.

### 33.5 Batch correction

A corrected batch creates a new revision or successor batch.

### 33.6 Submission correction

A corrected external handoff creates a new Submission and new exact bytes.

### 33.7 Outcome correction

A corrected authority letter creates a successor External Outcome Reference without erasing the earlier record.

### 33.8 Profile migration

Migration must:

1. identify old and new Profile revisions;
2. compare components, pathways, requirements, checklists, deadlines, attestations, approvals, and batch rules;
3. preserve old cases and findings;
4. reevaluate applicability and eligibility;
5. classify records as reusable, stale, invalid, or unresolved;
6. identify reattestation and reapproval needs;
7. create a successor Profile Binding and, where required, successor case;
8. preserve old submissions and outcomes;
9. and never declare existing evidence compliant automatically.

### 33.9 Cohort migration

A student completing after an authority-defined cohort boundary may require a new cohort Profile.

That is not a metadata edit.

It requires explicit authority review and migration or a new case.

## 34. New Jersey Graduation Portfolio Appeal reference family

### 34.1 Status

The New Jersey family in this issue is:

- researched;
- versioned;
- synthetic in examples;
- non-operational;
- incomplete without restricted Homeroom sources and local policy;
- and not legal advice.

### 34.2 Recommended identity

```text
portfolio_profile_family_id: nj_graduation_portfolio_appeal
purpose_kind: regulated
jurisdiction: US-NJ
reference_school_year: 2025-2026
reference_cohort: class_of_2026
status: research_only
```

### 34.3 Component scopes

```text
english_language_arts
mathematics
```

Each component has separate:

- eligibility;
- pathway;
- evidence;
- scoring requirements;
- checklist;
- readiness;
- batch membership;
- and outcome.

### 34.4 Pathway structure

The reference family must represent:

```text
standard_portfolio_appeal
streamlined_asvab_portfolio_appeal
```

as simultaneous alternatives.

The streamlined option requires exact qualifying-score evidence and explicit selection.

It is not inferred from fewer available tasks.

### 34.5 Reference standard evidence structure

The Class of 2026 research currently identifies:

- two ELA reading tasks and two connected writing tasks for the standard ELA pathway;
- four mathematics CRTs for the standard mathematics pathway;
- one reading plus one connected writing task for streamlined ELA;
- one reasoning plus one modeling task for streamlined mathematics;
- local retention of underlying student evidence;
- and school-level external submission of a Statement of Assurance and data spreadsheet.

Those values are exact reference-Profile data, not Vitrine defaults.

### 34.6 Local file and external batch separation

```text
student regulated case
  != locally retained evidence file
  != school submission batch
  != student row in batch
  != Statement of Assurance
  != data spreadsheet
  != receipt
  != outcome letter
```

### 34.7 State base and local overlay

The state base contains:

- state program identity;
- cohort rules;
- component and pathway definitions;
- public requirements;
- state deadlines;
- external submission policy;
- and authority-source references.

The local overlay may add:

- earlier internal deadlines;
- assigned coordinators;
- local task-development procedures;
- local review stages;
- custody and records policy;
- and local accessibility or translation workflow.

The local overlay must not silently weaken controlling state requirements.

### 34.8 Restricted-source activation gate

An operational implementation must review exact:

- Statement of Assurance text;
- data spreadsheet;
- field definitions;
- Homeroom permissions and validation behavior;
- receipt behavior;
- and outcome retrieval.

Public documentation alone is insufficient.

### 34.9 Future cohorts

The 2026–2027 public schedule and NJGPA-Adaptive information are future-cohort concerns.

They do not establish a complete Class of 2027 operational Profile.

## 35. Privacy, authorization, and accessibility integration

The privacy design remains authoritative.

Regulated purpose does not grant access.

Every sensitive action requires the applicable exact Authorization Decision.

### 35.1 Minimum-necessary accommodation evidence

A regulated case may record:

- accommodation required;
- accommodation provided;
- exact bounded authority reference;
- modality;
- and verification.

It should not copy a complete IEP, Section 504 plan, health record, or intervention history unless exact authority and necessity are established.

### 35.2 Translation and transcription

Where required, preserve:

- original representation;
- translated or transcribed representation;
- language;
- translator/interpreter role;
- method;
- relationship;
- and exact digests.

The derivative does not replace the original.

### 35.3 Disclosure package

A regulated submission requires:

- exact Audience Context;
- exact Recipient Scope;
- exact authorization;
- exact Disclosure Review;
- required redaction verification;
- exact Snapshot Edition;
- and exact Export Artifacts.

## 36. Producer-specific boundaries

### 36.1 Core

Core supplies neutral identity, periods, registrations, publications, exact verification, and discovery.

Core does not own:

- regulated Profiles;
- case eligibility;
- checklists;
- waivers;
- approvals;
- readiness;
- submissions;
- or external outcomes.

No Core change is required.

### 36.2 ScoreForm

A regulated Profile may accept an exact privacy-safe ScoreForm projection.

It must not:

- choose an official or best attempt automatically;
- expose answer keys or secure item content;
- infer standards proficiency not owned by ScoreForm;
- or treat an Academic Result Manifest as a complete regulated case.

### 36.3 Quillan

A regulated Profile may accept an exact Quillan selected-work or student-facing feedback projection when the future producer contract permits it.

It must not:

- reopen evidence selection;
- expose private notes;
- reinterpret review state as institutional approval;
- or claim external-rubric satisfaction without an explicit finding.

### 36.4 Concord

A collaborative Artifact may be used only when:

- the external program permits it;
- exact authorship and Subject relationships are appropriate;
- individual contribution is sufficiently established;
- privacy review succeeds;
- and the Profile's evidence rule is satisfied.

Group Membership or Group Score does not create individual evidence.

### 36.5 Portia

Ordinary Portia records remain suppressed.

Regulated purpose does not make behavior, intervention, disability, family, safety, counseling, or Communication records ordinary evidence.

Only an exact minimum-necessary portfolio-safe projection may be considered where required and authorized.

### 36.6 Meridian

A future public Meridian report projection may support a requirement.

A Grade or report does not establish:

- eligibility;
- checklist completion;
- local approval;
- submission;
- or external acceptance.

Vitrine must not inspect Meridian's private evidence inventory or calculation state.

## 37. Canonical and derived state

### 37.1 Canonical state

Canonical regulated state includes:

- Regulated Profile Specifications;
- Authority Source Sets and entries;
- Regulated Portfolio Cases;
- Case Components;
- Pathway Selections;
- Eligibility Findings;
- Checklist Definitions and Item Findings;
- Supporting Record Requirements and Instances;
- Missing or Defective Record Findings;
- Attestation Requirements, Records, and Verification Decisions;
- Deadline Rules, Instances, and Extensions;
- Approval Stage Definitions and Decisions;
- Submission Readiness Findings;
- Submission Batches and memberships;
- Generated Submission Projections;
- Submissions;
- Receipts;
- External Outcome References;
- lifecycle events;
- correction relationships;
- and migration records.

### 37.2 Derived state

Derived and rebuildable state includes:

- case dashboards;
- checklist completion summaries;
- missing-document queues;
- deadline calendars;
- pending-attestation queues;
- approval queues;
- ready-for-submission lists;
- batch rosters;
- resubmission histories;
- and external-outcome summaries.

Derived state is never the only evidence that an action or decision occurred.

## 38. Failure-state vocabulary

```text
regulated_profile_source_missing
regulated_profile_source_stale
regulated_profile_source_conflict
regulated_profile_not_activation_ready
regulated_profile_restricted_source_unverified
regulated_profile_local_overlay_missing
regulated_profile_applicability_unknown
regulated_case_profile_mismatch
regulated_case_component_invalid
regulated_case_pathway_unselected
regulated_case_pathway_ineligible
regulated_case_pathway_indeterminate
checklist_not_found
checklist_item_not_applicable
checklist_item_unsatisfied
checklist_item_unknown
supporting_record_missing
supporting_record_unavailable
supporting_record_withheld
supporting_record_unverified
supporting_record_invalid
supporting_record_stale
supporting_record_mismatched
supporting_record_superseded
attestation_missing
attestation_signer_unauthorized
attestation_signature_unverified
attestation_incomplete
deadline_rule_unknown
deadline_calculation_failed
deadline_past_due
deadline_extension_unverified
approval_stage_incomplete
approval_actor_unauthorized
approval_target_stale
submission_readiness_blocked
submission_readiness_indeterminate
submission_batch_profile_mismatch
submission_batch_school_mismatch
submission_membership_duplicate
submission_row_invalid
submission_artifact_mismatch
submission_receipt_missing
external_outcome_pending
external_outcome_unknown
external_outcome_component_mismatch
resubmission_predecessor_missing
retention_reference_unresolved
```

These states remain distinct from:

- Candidate failure;
- source-access denial;
- Snapshot build failure;
- delivery failure;
- external rejection;
- and legal noncompliance.

## 39. Edge-case behavior

### 39.1 Component split

ELA uses the regulated pathway while mathematics is satisfied elsewhere. Only the ELA component proceeds through regulated checklists and submission.

### 39.2 Different component pathways

ELA uses the standard regulated pathway while mathematics uses a streamlined pathway. Each component preserves its own eligibility evidence and checklist.

### 39.3 Guidance changes after opening

The case remains bound to its exact Profile revision until an authorized migration occurs.

### 39.4 Overlapping cohorts

Cases for two cohorts may remain active simultaneously under different Profile revisions.

### 39.5 Restricted source unavailable

Profile activation or case readiness remains blocked where the missing restricted source controls required fields or attestations.

### 39.6 Public and restricted sources conflict

The source set records `conflicting`; authorized review is required. Vitrine does not choose the more convenient source.

### 39.7 Stale transcript

Record presence is `present`, validation is `stale`, and the requirement remains `not_satisfied`.

### 39.8 Wrong subject

The record is `mismatched`; it must not be attached to the intended case.

### 39.9 Missing cover sheet

The task and response may exist, but the exact checklist item remains unsatisfied.

### 39.10 Unauthorized waiver

The attempted waiver is rejected; the original requirement remains unresolved.

### 39.11 Incomplete signer set

An attestation requiring three distinct authorized roles remains incomplete with two signatures.

### 39.12 Batch-level assurance missing

Student cases may be individually ready while the school batch remains not ready.

### 39.13 Rolling component submission

One component is submitted in an earlier batch and another later. Both memberships and submissions remain exact.

### 39.14 Corrected spreadsheet

A corrected file creates new bytes, Export Artifact, batch revision where applicable, and Submission.

### 39.15 No receipt

Submission remains recorded; receipt state is missing or pending. Vitrine does not fabricate confirmation.

### 39.16 Partial external outcome

ELA is approved and mathematics returned for correction. The case remains component-specific.

### 39.17 Outcome correction

A successor authority document supersedes the prior normalized current outcome while preserving both.

### 39.18 Source withdrawn after issuance

Historical sealed bytes and submission provenance remain. Future access and use follow privacy, retention, and authority rules.

### 39.19 Excess accommodation detail

The record is rejected or transformed to a minimum-necessary safe projection before regulated use.

### 39.20 Portia source appears relevant

Suppression remains. Relevance does not grant access or eligibility.

### 39.21 Dashboard loss

Canonical records rebuild the dashboard without changing case state.

### 39.22 Wrong cohort Profile

The case is invalidated or migrated explicitly. The Profile Binding is never edited silently.

## 40. Validation invariants

1. A regulated Profile is a specialization of the generic Portfolio Profile.
2. Profile definition and case execution are distinct.
3. Research-only examples are not operational Profiles.
4. Every operational case binds one exact Profile revision.
5. Authority Source Sets are immutable and attributable.
6. Required unresolved sources may block activation.
7. Public, restricted, local, and institutional sources remain distinct.
8. Cohort, school year, assessment version, program version, and Profile revision remain distinct.
9. Simultaneous pathways are not sequential revisions by default.
10. Case components are independently evaluable.
11. Pathway selection is explicit.
12. Eligibility and completion are distinct.
13. Eligibility and approval are distinct.
14. Checklist definitions and findings are distinct.
15. Checklist completion is derived.
16. Supporting-record requirements and instances are distinct.
17. Record presence and validation are distinct.
18. Record validation and requirement satisfaction are distinct.
19. Missing evidence is a finding, not an empty file.
20. Unknown never becomes satisfied or waived.
21. Waiver requires exact authority.
22. Attestation and verification are distinct.
23. Attestation and approval are distinct.
24. Signature presence and authority verification are distinct.
25. Deadline rules and instances are distinct.
26. Extensions require exact authoritative evidence.
27. Deadline passage does not fabricate an external consequence.
28. Approval applies only to an exact target revision.
29. Readiness and approval are distinct.
30. Student cases and submission batches are distinct.
31. One batch may contain several cases.
32. One case may appear in several rolling or corrected submissions.
33. Generated submission rows are not canonical cases.
34. Changed submission bytes create a new Export Artifact and Submission.
35. Submission and receipt are distinct.
36. Receipt and external outcome are distinct.
37. Local approval and external outcome are distinct.
38. Raw external outcomes remain preserved.
39. Normalized outcomes do not broaden authority meaning.
40. Partial component outcomes are supported.
41. Profile migration is explicit.
42. Historical packages remain bound to their original Profile revisions.
43. Restricted portal content is not committed publicly.
44. Accommodation evidence remains minimum necessary.
45. Producer-native authority remains unchanged.
46. ScoreForm attempt policy remains outside Vitrine.
47. Quillan private review state remains excluded.
48. Concord Group Membership does not create individual evidence.
49. Portia suppression remains intact.
50. Meridian grading state does not establish compliance.
51. Internal and external authority remain distinct.
52. Canonical and derived state remain distinct.
53. Derived views are rebuildable.
54. No legal compliance conclusion is inferred.
55. No sibling repository is modified.

## 41. New Jersey reference-profile activation checklist

Before an institution creates an operational New Jersey Profile, authorized reviewers must confirm:

- [ ] exact graduating cohort;
- [ ] exact school year;
- [ ] current statute and regulation;
- [ ] current public requirements hub;
- [ ] current ELA guidance;
- [ ] current mathematics guidance;
- [ ] current streamlined guidance;
- [ ] current special-populations guidance;
- [ ] current FAQ and submission process;
- [ ] current forms and cover sheets;
- [ ] current restricted Statement of Assurance;
- [ ] current data spreadsheet and field definitions;
- [ ] current Homeroom roles, validation, receipt, and outcome behavior;
- [ ] exact local CRT design and moderation policy;
- [ ] exact local scoring and approval policy;
- [ ] exact local deadline overlay;
- [ ] exact school and accountable-code mapping;
- [ ] exact accommodation and translation workflow;
- [ ] exact records classification and custody;
- [ ] exact authorization and recipient policy;
- [ ] assigned Profile approver;
- [ ] activation date;
- [ ] expiration or review date;
- [ ] and migration policy for later cohorts.

## 42. Unresolved implementation questions

1. Should Regulated Profile Specification be serialized inline in a Profile revision or as a one-to-one referenced record?
2. Should standard and streamlined pathways be separate Profile series or immutable composed variants?
3. Which checklist finding states belong in the first runtime contract?
4. Which authority-source digests can be preserved lawfully for restricted materials?
5. How should local overlays declare that they only strengthen, not weaken, controlling policy?
6. What deterministic calendar model should deadline rules use?
7. How should exact external spreadsheet field rules be loaded without redistributing restricted definitions?
8. Which signature services, if any, will be supported?
9. Which Vitrine records require current pointers versus lifecycle resolution?
10. How should batch revisions and Snapshot Editions relate when one batch produces several external files?
11. How should imported external outcomes preserve raw authority terminology across programs?
12. What retention and archival interface will eventually belong to Sunset?
13. Which operational checks can be deterministic and which require a human reviewer?
14. What minimum data is needed for staff transition without duplicating institutional systems?
15. Which source revalidation checks can be automated safely?

These questions do not block the conceptual architecture.

## 43. Downstream boundaries

### Runtime contract work

A later issue may define exact schemas, persistence, activation, evaluation, and CLI behavior.

### Operational New Jersey Profile

A separate reviewed implementation must use current public, restricted, and local authority sources.

This issue does not activate one.

### External submission integration

A later authorized integration may generate official files or submit through an external portal.

This issue defines provenance and workflow boundaries only.

### Sunset

Future Sunset or institutional records systems may own archival transfer, legal holds, retention execution, and disposition.

## 44. Security and privacy requirements

- Use synthetic examples only.
- Do not commit real student records, identifiers, signatures, forms, outcomes, or district codes.
- Do not commit restricted portal content or credentials.
- Use opaque non-PII IDs.
- Keep Profiles free of student data.
- Keep accommodation and special-population findings minimum necessary.
- Preserve no-existence leakage protections.
- Do not log complete educational documents.
- Do not expose absolute paths.
- Keep diagnostics bounded and privacy-safe.
- Do not claim electronic-signature validity.
- Do not claim legal compliance or state approval.
- Treat checksums as integrity evidence, not authorization.

## 45. References

- [Versioned Portfolio Profile contract](portfolio-profile-contract.md)
- [Selection and curation records](selection-curation-records.md)
- [Snapshot, export, checksum, and immutability contracts](snapshot-export-immutability-contracts.md)
- [Privacy, redaction, and audience controls](privacy-redaction-audience-controls.md)
- [New Jersey Graduation Portfolio Appeal research](../research/new-jersey-graduation-portfolio-appeal.md)
- [Portfolio research source register](../research/source-register.md)
- [Representative regulated Portfolio examples](../examples/regulated-portfolio-compliance-examples.md)
- [ADR 0009](../decisions/0009-regulated-portfolio-and-compliance-profiles.md)
