# Privacy, Redaction, and Audience Controls

## Status and boundary

This document defines a conceptual Vitrine privacy and disclosure-control model for issue #10, **Define privacy, redaction, and audience controls**.

It is a foundation design, not a final serialized contract, legal opinion, compliance certification, identity platform, or runtime authorization implementation.

The design defines Vitrine-owned records and invariants for:

- separating publication discovery from student-level source access;
- evaluating exact actions against purpose, target, time, audience, and recipient scope;
- preserving bounded references to authoritative identity, relationship, consent, and institutional records;
- distinguishing audience-content policy from exact recipient authorization;
- preventing existence leakage for suppressed or sensitive sources;
- reviewing proposed disclosures for minimum-necessary content;
- planning, performing, and verifying redaction without mutating producer or sealed bytes;
- evaluating de-identification separately from mechanical identifier removal;
- handling collaborators, co-authors, Group artifacts, and other multi-subject sources;
- authorizing one exact Snapshot Edition and Export Artifact set for one exact recipient scope;
- preserving access, delivery, and disclosure events without duplicating educational content;
- and preserving expiration, revocation, correction, and historical disclosure state.

The design does not:

- authenticate users;
- determine legal guardianship or FERPA rights-holder status;
- validate legal consent or electronic signatures;
- replace institutional identity, roster, records, or disclosure systems;
- implement source readers, redaction engines, renderers, delivery channels, or secure portals;
- decide institution-specific legal questions;
- define a regulated Portfolio Profile;
- change producer-native privacy policy;
- or create a new Core authorization registry.

Those responsibilities remain with the systems and later issues identified below.

## Governing separation

The privacy model preserves this sequence:

```text
Core discovery candidate
  -> metadata-visibility evaluation
  -> canonical Publication reload and compatibility verification
  -> source-access authorization
  -> producer-owned projection
  -> Candidate eligibility
  -> curation authority
  -> exact Working Portfolio Composition Revision
  -> snapshot-build authorization
  -> Disclosure Review
  -> Redaction / De-identification review where required
  -> immutable Snapshot Edition
  -> Disclosure Authorization for exact Export Artifact(s)
  -> optional access / delivery / submission event
  -> optional receipt / external outcome
```

No arrow is implicit.

The following concepts remain distinct:

```text
publication discovery
  != safe metadata visibility
  != source-content access
  != Candidate visibility
  != curation authority
  != permission to copy
  != permission to build an audience Edition
  != permission to inspect the internal Snapshot Manifest
  != permission to issue
  != permission to deliver
  != permission to submit
  != external receipt
  != external acceptance
```

Likewise:

```text
audience class
  != exact recipient
  != authenticated identity
  != verified relationship
  != verified authority
  != consent
  != disclosure approval
  != completed delivery
```

## Reviewed repository baseline

The design was reconciled against these repository states.

| Repository | Reviewed baseline | Relevant authority and readiness |
| --- | --- | --- |
| `pds-vitrine` | `a2e45d525ab8d6962cc71f43e0c20d87e77f617d` | Profiles, Candidates, producer projections, curation, byte-free Composition Revisions, Snapshot Editions, Export Artifacts, Issuance, Submission, and Proposed ADRs 0001–0007 are documented; no runtime authorization or redaction implementation exists. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Core owns canonical registrations, Publications, withdrawals, compatibility metadata, exact manifest verification, and the disposable catalog; it does not authorize Portfolio source access or disclosure. |
| `pds-scoreform` | `c2fa06f1a4c33df01f3e0d9c8dd27702d4a06419` | Immutable all-attempt result-manifest generation exists with secure exclusions; answer keys, detector internals, review diagnostics, and raw scans remain outside ordinary Portfolio exposure. |
| `pds-quillan` | `05fecf23d29e56b45cba58ed97906f5353290033` | Quillan owns selected evidence, private notes, teacher review, student-facing feedback, retained-source provenance, and assignment-local reports; a Core 0.6 public Portfolio reader remains unavailable. |
| `pds-concord` | `31b0efd2864cd7a0945ff29f5af99b2a00db52ae` | Concord implements typed Artifact, Author, Subject, Group, Score, Review, privacy, correction, and guarded-persistence foundations; public Vitrine projections remain future work. |
| `pds-portia` | `0841bd946c6c3a098ebaad4bfb90669816ecc93b` | Portia has accepted exact-reference, lifecycle, correction, migration, exceptional-removal, and integrity-finding contracts; ordinary Portia sources remain suppressed and participant-specific privacy projections are future work. |
| `pds-meridian` | `0c1f57e41da225079df1cb14ece3fe8c0522b744` | Meridian now has an installable package and CI foundation but no producer adapters, evidence inventory, authorization engine, reports, snapshots, or delivery implementation. |

### Current reality versus planned capability

The reviewed state supports the architecture but does not make all integrations executable.

In particular:

- Core can establish canonical publication identity and exact manifest bytes but not Portfolio authorization;
- ScoreForm can publish immutable result manifests but does not yet expose all Portfolio representations described by Vitrine;
- Quillan has private and student-facing boundaries but no accepted Core 0.6 Vitrine reader;
- Concord has native privacy and relationship records but no public Portfolio projection;
- Portia has strong deny-by-default foundations but no portfolio-safe projection implementation;
- Meridian has a package foundation but no report authorization or delivery contracts;
- and Vitrine remains documentation-only.

A permitted conceptual operation must therefore remain unavailable where the required producer reader, authority source, renderer, or delivery mechanism does not exist.

No private-file fallback is allowed.

### Reusable cross-repository patterns

The design reuses these suite-wide patterns:

- opaque, non-PII durable IDs;
- exact typed references instead of inference from names or paths;
- immutable operational records;
- explicit predecessor, successor, supersession, and revocation links;
- three-valued or explicit indeterminate outcomes;
- expected-revision and exact-digest binding;
- append-preserving lifecycle history;
- canonical state separated from derived indexes;
- minimum-necessary projections;
- and denial that fails closed rather than guessing.

### Incompatible assumptions rejected

The design rejects these assumptions from adjacent domains:

- a Core catalog row is safe to show to every teacher;
- a canonical Publication Record grants permission to open its manifest;
- a Portfolio Subject can access every record that mentions the same student;
- a teacher role grants access to every class, year, producer, or sensitive record;
- a parent or guardian label proves current authority;
- a selected source may be disclosed because it was approved for curation;
- a Profile audience label identifies an authorized recipient;
- a redacted filename proves the file contents are de-identified;
- a Group relationship supplies every collaborator's disclosure permission;
- a ScoreForm result disclosure permits secure answer-key or detector access;
- a Quillan feedback export permits access to private review state;
- a Portia-safe projection permits access to its underlying Portia graph;
- or a successful Export Artifact generation proves lawful delivery.

## Authority model

### Vitrine owns

Vitrine owns the conceptual privacy and disclosure records defined here:

- Audience Context;
- Recipient Scope;
- Authorization Request;
- bounded Authority Evidence Reference;
- Authorization Decision;
- Metadata Visibility Decision;
- Protected Access Event;
- Disclosure Review;
- Disclosure Review Finding;
- Redaction Plan;
- Redaction Operation;
- Redaction Result;
- Redaction Verification Decision;
- De-identification Review;
- Disclosure Authorization;
- Disclosure Event;
- Authorization Revocation;
- and Vitrine-derived privacy workflow views.

Vitrine owns only the meaning of its own decisions and events.

### Portfolio Profile owns policy definitions

The exact bound Portfolio Profile revision may define:

- audience classes;
- audience-content rules;
- permitted and prohibited content families;
- required privacy reviews;
- required consent or institutional authority classes;
- collaborator handling;
- redaction requirements;
- de-identification requirements;
- allowed delivery channels;
- retention-policy references;
- and regulated submission obligations.

A Profile describes policy.

It does not authenticate actors, resolve exact recipients, create consent, or authorize disclosure by itself.

### Core owns publication identity, not Portfolio authorization

Core remains authoritative for:

- Publication Record identity;
- registration revision identity;
- publication-series state;
- withdrawals and supersession;
- manifest paths and SHA-256 binding;
- compatibility metadata;
- and catalog discovery.

A Core record may establish which publication would be accessed.

It does not grant access to student-level content or permission to disclose it.

### Producers retain source and native privacy authority

Producers remain authoritative for:

- native record identity;
- native subject, authorship, Group, and participant relationships;
- native privacy classifications;
- private versus public fields;
- producer-approved projections;
- projection allowlists;
- secure assessment exclusions;
- source correction and withdrawal;
- and whether a safe representation can be constructed.

Vitrine may narrow an approved projection further.

It may not broaden the projection or reinterpret private fields as shareable.

### Institutional systems retain identity and authority

Institutional or otherwise authoritative systems remain authoritative for:

- authenticated actor identity;
- employment and assignment authority;
- student enrollment and class relationship;
- parent or guardian relationship;
- rights-holder status;
- consent documents;
- reviewer appointment;
- regulated authority;
- legal or policy exceptions;
- and authoritative disclosure logs where one exists.

Vitrine records bounded references and verification snapshots.

It does not create competing canonical records for those facts.

### Issue #11 owns regulated Profile details

Issue #11 will define concrete regulated Profile requirements, including exact checklists, attestations, deadlines, approval stages, destination requirements, and missing-document findings.

This design supplies generic privacy and disclosure primitives for those Profiles.

### External systems own delivery and external outcomes

Email, portals, secure transfer systems, government submission systems, and external reviewers remain authoritative for their own:

- recipient accounts;
- transmission state;
- delivery receipts;
- access logs;
- submission identifiers;
- and decisions.

Vitrine may retain exact references or imported evidence.

It must not fabricate external delivery or acceptance.

## Terminology

### Audience Context

A versioned Vitrine policy context describing the intended audience class, purpose, content constraints, and required reviews.

It does not identify the exact recipient or grant access.

### Recipient Scope

An exact bounded description of the recipient, recipient class, relationship, organization, purpose, validity period, and redisclosure restrictions relevant to one disclosure decision.

### Authorization Request

An immutable request to perform one exact protected action against one exact target for one exact purpose and audience/recipient context.

### Authority Evidence Reference

A bounded reference to an authoritative identity, relationship, consent, appointment, or institutional record.

The reference does not replace the source record or prove more than the verified snapshot states.

### Authorization Decision

An immutable result evaluating one exact Authorization Request under exact policy and evidence.

### Metadata Visibility Decision

A privacy decision specifying how much, if any, metadata may be revealed before source access.

### Protected Access Event

An append-preserving record of a protected internal access action where policy requires logging.

It records the action and outcome, not the educational content viewed.

### Disclosure Review

An immutable review of a proposed content set for one audience and recipient scope before snapshot building, issuance, or delivery.

### Redaction Plan

An immutable ordered plan describing exact transformations or omissions required to create an audience-safe representation.

### Redaction Result

The provenance-bound output of one exact Redaction Plan against one exact input.

### Redaction Verification Decision

An immutable decision about one exact Redaction Result and output digest.

### De-identification Review

A context-specific evaluation of whether an exact output is reasonably non-identifiable in the intended release environment.

### Disclosure Authorization

An immutable authorization binding one exact Snapshot Edition, Export Artifact set, Audience Context, Recipient Scope, underlying Authorization Decision, and required review results.

### Disclosure Event

An append-preserving record of actual viewing, download, delivery, submission, failure, receipt, or related use of an authorized exact artifact.

### Authorization Revocation

An immutable future-use restriction on one exact Authorization Decision or Disclosure Authorization.

It does not rewrite historical events or claim that external copies were recalled.

## Conceptual graph

```text
Portfolio Profile revision
  -> Audience Rule
  -> Audience Context

Actor / asserted role
  -> bounded identity and authority evidence

Recipient / recipient class
  -> Recipient Scope
  -> relationship and authority evidence

Authorization Request
  -> exact protected action
  -> exact target
  -> exact purpose
  -> Audience Context
  -> optional Recipient Scope

Authorization Decision
  -> exact Authorization Request
  -> policy rules
  -> bounded permitted scope
  -> conditions / expiration

Candidate / Selection / Composition / Snapshot plan
  -> Disclosure Review
  -> Disclosure Review Findings
  -> optional Redaction Plan
  -> Redaction Result
  -> Redaction Verification
  -> optional De-identification Review

Snapshot Edition
  -> exact Export Artifact(s)
  -> Disclosure Authorization
  -> optional Protected Access / Disclosure Events
  -> optional Revocation
```

## Record overview

| Record | Canonical? | Mutable? | Primary role |
| --- | --- | --- | --- |
| Audience Context | Yes | No | Bind one Profile audience rule to one purpose-specific content context. |
| Recipient Scope | Yes | No | Identify the exact bounded recipient or recipient class and relationship context. |
| Authorization Request | Yes | No | Preserve one protected action request. |
| Authority Evidence Reference | Yes | No | Preserve a bounded verified reference to an authoritative external or local record. |
| Authorization Decision | Yes | No | Allow, deny, condition, or leave indeterminate one exact request. |
| Metadata Visibility Decision | Yes | No | Limit pre-access metadata without leaking sensitive existence. |
| Protected Access Event | Yes | No | Record policy-relevant protected internal access without copying content. |
| Disclosure Review | Yes | No | Evaluate a proposed content set for one audience and recipient scope. |
| Disclosure Review Finding | Yes | No | Preserve one exact privacy or disclosure issue found during review. |
| Redaction Plan | Yes | No | Define ordered, attributable transformations or omissions. |
| Redaction Operation | Embedded or canonical by final contract | No | Describe one exact media-appropriate transformation. |
| Redaction Result | Yes | No | Bind exact input, operations, transformer, output, and digest. |
| Redaction Verification Decision | Yes | No | Approve or reject one exact redacted output. |
| De-identification Review | Yes | No | Evaluate contextual re-identification risk. |
| Disclosure Authorization | Yes | No | Authorize one exact Edition and Export Artifact set for one exact recipient scope. |
| Disclosure Event | Yes | No | Record actual protected use, delivery, submission, failure, or receipt. |
| Authorization Revocation | Yes | No | Restrict future use while preserving history. |
| Privacy dashboards and queues | No | Rebuildable | Support workflow and reporting. |

## Identity conventions

Every canonical privacy record receives an opaque, non-PII, never-reused ID.

IDs must not encode:

- student name;
- parent or guardian name;
- email address;
- class ID;
- school name;
- producer module;
- sensitive record class;
- denial reason;
- consent status;
- audience label;
- or lifecycle state.

Human-readable labels are display snapshots, never identity.

References to external identity or authority systems should use opaque source-system identifiers where available.

Vitrine must not persist authentication credentials, tokens, passwords, private keys, or full identity-provider assertions in these records.

## Authorization gates

### Gate model

The design uses separate gates because the evidence and risks differ at each stage.

| Gate | Question | Typical target |
| --- | --- | --- |
| Discovery metadata | May this actor learn that a possible source exists? | catalog or bounded candidate row |
| Candidate metadata | May this actor inspect safe title, date, producer, or relationship summaries? | Candidate summary |
| Source content | May this actor open the exact producer projection? | source representation |
| Sensitive-source review | May this actor inspect a conditionally restricted projection? | Portia-safe or multi-subject source |
| Curation | May this actor propose, activate, annotate, or approve curation? | Candidate, Selection, Composition |
| Snapshot build | May this actor cause exact representations to be copied or rendered? | Composition Revision / Build Plan |
| Internal manifest | May this actor inspect internal provenance, omissions, and source IDs? | Snapshot Manifest |
| Issuance | May this actor declare an exact Edition issued? | Snapshot Edition / Export Artifact |
| Delivery | May this exact recipient receive or access this exact artifact by this channel? | Export Artifact |
| Submission | May this exact artifact be sent to this exact regulated destination? | Export Artifact / submission target |
| Historical access | May this actor access a retained predecessor or withdrawn Edition? | historical Edition |
| External outcome | May this actor record or inspect an external receipt or decision? | receipt / outcome reference |

Passing one gate does not imply any later gate.

### Initial protected action vocabulary

```text
discover_metadata
inspect_candidate_metadata
read_source_representation
review_sensitive_source
propose_selection
activate_selection
annotate_selection
approve_composition
build_snapshot
inspect_internal_manifest
inspect_snapshot_edition
approve_issuance
issue_export
deliver_export
submit_export
access_historical_edition
record_external_receipt
record_external_outcome
export_disclosure_log
revoke_future_access
```

The final contract may split actions further.

It must not collapse materially different actions into one `view` or `share` permission.

### Evaluation order

A conceptual authorization evaluator should proceed in this order:

1. validate request structure and exact target identity;
2. resolve the exact Profile Binding and policy revision;
3. validate actor identity evidence without accepting an asserted role as proof;
4. resolve recipient scope where disclosure is requested;
5. verify purpose and action are recognized;
6. verify authority and relationship evidence are current and target-scoped;
7. evaluate producer and source restrictions;
8. evaluate sensitive-source and multi-subject conditions;
9. evaluate consent, institutional authority, or applicable exception evidence;
10. evaluate time window and expiration;
11. determine minimum-necessary permitted fields or artifacts;
12. record conditions, denial, or indeterminate facts;
13. and create an immutable Decision.

A required fact that cannot be resolved produces `indeterminate`, not `allowed`.

### Decision outcomes

```text
allowed
denied
conditional
indeterminate
expired
```

`Expired` may be recorded as a current evaluation of an earlier Decision or as an explicit outcome for a request relying on expired evidence.

A `conditional` Decision identifies every condition that must be satisfied before use.

Examples include:

- collaborator review;
- recipient verification;
- redaction;
- de-identification review;
- institutional approval;
- secure-channel restriction;
- or time-window activation.

### Denial and no-existence leakage

External or ordinary user-facing results must be privacy-safe.

The response may need to collapse several internal conditions into the same safe result, including:

- no source exists;
- source exists but is suppressed;
- source exists but metadata visibility is denied;
- source exists but actor authority is unresolved;
- source exists but the relationship is outside scope;
- or source exists but policy prohibits disclosure.

Restricted internal diagnostics may preserve the exact reason for authorized administrators or reviewers.

The existence of restricted diagnostic detail must not make it available to the denied actor.

## Audience Context

### Purpose

Audience Context binds an exact Profile audience rule to a purpose-specific content policy.

It answers:

> What kind of content and review would be appropriate for this class of audience and purpose, assuming an exact recipient is later authorized?

It does not answer:

> Is this person the recipient, and may they receive this package now?

### Initial audience classes

```text
student_facing
parent_guardian_facing
teacher_internal
external_reviewer
regulated_submission
public_community
```

Institutions may define narrower audience classes through versioned Profile rules.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `audience_context_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Context contract version. |
| `portfolio_id` | Required | Exact Portfolio. |
| `portfolio_subject_id` | Required | Exact Portfolio Subject. |
| `profile_binding_id` | Required | Exact operational Profile Binding. |
| `portfolio_profile_id` | Required | Profile series snapshot. |
| `profile_revision` | Required | Exact Profile revision. |
| `audience_rule_id` | Required | Exact Profile audience rule. |
| `audience_class` | Required | Controlled audience class. |
| `purpose` | Required | Bounded purpose code and optional safe description. |
| `subject_scope` | Required | Exact subject or permitted group scope. |
| `permitted_content_classes` | Required | Closed allowlist of content families. |
| `prohibited_content_classes` | Required | Explicit deny list reinforcing producer and policy restrictions. |
| `required_review_classes` | Optional | Redaction, collaborator, rights, de-identification, institutional, or other reviews. |
| `intended_presentation_class` | Required | Internal, family, reviewer, regulated, public, or equivalent presentation policy. |
| `allowed_delivery_channel_classes` | Optional | Policy-level channel classes, not configured endpoints. |
| `retention_policy_reference` | Optional | Policy reference for generated privacy records and issued artifacts. |
| `created_at` | Required | Aware timestamp. |
| `created_by` | Required | Actor or authorized process. |

### Forbidden interpretations

Audience Context does not prove:

- recipient identity;
- relationship;
- consent;
- source access;
- disclosure authorization;
- secure delivery;
- or external acceptance.

### Revision behavior

Audience Context is immutable.

A changed Profile rule, purpose, permitted-content set, prohibited-content set, or required-review set creates a new Context.

Historical authorizations retain their original Context.

## Recipient Scope

### Purpose

Recipient Scope identifies who or what recipient class is being considered and under which relationship, organization, purpose, and validity constraints.

### Recipient types

```text
portfolio_subject
parent_or_guardian
teacher_or_curator
institutional_reviewer
external_reviewer
regulated_authority
named_publication_recipient
public_unrestricted
```

`public_unrestricted` is a high-risk recipient scope, not a default.

It requires exact Profile support and either exact applicable authority or context-specific verified de-identification.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `recipient_scope_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Scope contract version. |
| `recipient_type` | Required | Controlled recipient type. |
| `recipient_references` | Conditional | Exact recipient or recipient-class references; omitted only for approved public-unrestricted scope. |
| `recipient_organization_reference` | Optional | Exact institution, agency, or external organization reference. |
| `portfolio_subject_id` | Required | Exact subject whose Portfolio is being disclosed. |
| `relationship_type` | Required | Student, parent/guardian, assigned teacher, appointed reviewer, agency authority, or equivalent. |
| `relationship_evidence_reference_ids` | Conditional | Exact Authority Evidence References. |
| `purpose` | Required | Exact disclosure purpose. |
| `valid_from` | Required | Earliest valid time. |
| `valid_until` | Optional | Expiration time. |
| `redisclosure_restrictions` | Optional | Policy or authority restrictions. |
| `recipient_resolution_status` | Required | `resolved`, `unresolved`, `disputed`, `expired`, or `not_applicable`. |
| `created_at` | Required | Aware timestamp. |
| `created_by` | Required | Actor or authorized process. |

### Cardinality

One Disclosure Authorization binds one exact Recipient Scope.

Where recipients differ materially, create separate scopes and authorizations.

A recipient-class authorization must not be silently expanded into unbounded named recipients.

### Relationship changes

A changed guardian, teacher, reviewer, or agency relationship does not rewrite the earlier Scope.

A successor Scope and new Authorization Decision are required for future use.

## Authority Evidence Reference

### Purpose

Authority Evidence Reference preserves the minimum information needed to evaluate authority while leaving the authoritative record in its owning system.

### Evidence types

```text
authenticated_identity
employment_assignment
roster_relationship
parent_guardian_relationship
rights_holder_status
consent
institutional_approval
reviewer_appointment
regulated_submission_authority
policy_exception
court_or_agency_authority
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `authority_evidence_reference_id` | Required | Opaque Vitrine reference identity. |
| `contract_version` | Required | Reference contract version. |
| `evidence_type` | Required | Controlled evidence type. |
| `authority_system` | Required | Owning system, office, or custodian. |
| `authority_record_reference` | Required | Opaque exact source record reference. |
| `authority_record_revision` | Optional | Exact version, revision, or digest where exposed. |
| `subject_scope` | Required | Subject or case scope. |
| `actor_scope` | Optional | Actor covered by the evidence. |
| `recipient_scope` | Optional | Recipient or recipient class covered. |
| `purpose_scope` | Optional | Allowed purpose or purposes. |
| `record_scope` | Optional | Exact records, Edition, or artifact classes covered. |
| `effective_at` | Required | Evidence effective time. |
| `expires_at` | Optional | Evidence expiration time. |
| `verified_at` | Required | Time Vitrine verified the reference. |
| `verified_by` | Required | Authorized verifier or trusted service. |
| `verification_method` | Required | Bounded method reference. |
| `status_snapshot` | Required | `valid`, `invalid`, `revoked`, `expired`, `disputed`, or `indeterminate`. |

### Data minimization

The reference must not duplicate:

- complete consent forms;
- full guardian files;
- full identity-provider assertions;
- employment files;
- passwords or tokens;
- court records;
- or unrelated personal information.

The final implementation may retain a digest or secure external link where institutional policy requires it.

### Evidence freshness

Evidence validity is evaluated at the action time required by policy.

A valid relationship at Selection time may be insufficient at delivery time.

## Authorization Request

### Purpose

An Authorization Request preserves one exact protected action request before a Decision exists.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `authorization_request_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Request contract version. |
| `actor_reference` | Required | Exact actor identity reference. |
| `asserted_role` | Required | Role claimed for this action. |
| `requested_action` | Required | Exact protected action. |
| `target_type` | Required | Publication, Candidate, Selection, Composition, Plan, Edition, Export Artifact, manifest, or other bounded target. |
| `target_references` | Required | Exact immutable target IDs and revisions. |
| `portfolio_id` | Conditional | Required for Portfolio-scoped actions. |
| `portfolio_subject_id` | Conditional | Required for student-related actions. |
| `profile_binding_id` | Conditional | Required where Profile policy applies. |
| `audience_context_id` | Conditional | Required for audience-specific build, issue, delivery, or submission actions. |
| `recipient_scope_id` | Conditional | Required for exact recipient disclosure actions. |
| `purpose` | Required | Bounded purpose. |
| `requested_valid_from` | Required | Requested start time. |
| `requested_valid_until` | Optional | Requested expiration. |
| `authority_evidence_reference_ids` | Optional | Evidence supplied for evaluation. |
| `requested_by` | Required | Actor or authorized process initiating evaluation. |
| `requested_at` | Required | Aware timestamp. |
| `predecessor_request_id` | Optional | Earlier request revised or renewed. |

### Validation

A Request is structurally valid only when:

- target references are exact and internally consistent;
- Portfolio, Subject, Profile, and Snapshot contexts agree;
- required audience and recipient fields are present for the action;
- the action is recognized;
- time bounds are coherent;
- and predecessor relationships are acyclic.

Structural validity does not imply authorization.

## Authorization Decision

### Purpose

Authorization Decision records the result of evaluating one exact Request.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `authorization_decision_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Decision contract version. |
| `authorization_request_id` | Required | Exact Request. |
| `decision` | Required | `allowed`, `denied`, `conditional`, `indeterminate`, or `expired`. |
| `decision_actor` | Required | Authorized human or policy service. |
| `asserted_authority` | Required | Authority used to decide. |
| `policy_reference_ids` | Required | Exact Profile, institutional, or external policy references. |
| `rule_ids` | Required | Exact rules evaluated. |
| `evidence_reference_ids` | Required | Evidence actually relied upon. |
| `permitted_action_scope` | Conditional | Exact action scope when allowed or conditional. |
| `permitted_target_scope` | Conditional | Exact target IDs, revisions, fields, or artifact set. |
| `permitted_recipient_scope_id` | Conditional | Exact Scope for disclosure actions. |
| `conditions` | Optional | Explicit unsatisfied or ongoing conditions. |
| `denial_reason_code` | Conditional | Restricted reason code for denied decisions. |
| `indeterminate_fact_codes` | Conditional | Required unresolved facts. |
| `decided_at` | Required | Aware timestamp. |
| `effective_at` | Required | Effective time. |
| `expires_at` | Optional | Expiration time. |
| `supersedes_decision_id` | Optional | Earlier Decision superseded for future use. |

### Exact scope

An allowed Decision must state what is allowed.

It must not mean “the actor may do anything related to this Portfolio.”

Examples of exact scope include:

- safe metadata fields for one discovery query;
- one producer projection for one Candidate;
- one exact Composition Revision for snapshot planning;
- one exact internal manifest for one review task;
- or one exact Export Artifact for one exact recipient.

### Conditional decisions

A conditional Decision is not an executable allow until all conditions have exact completion evidence.

The final runtime may create a successor evaluation or a separate condition-resolution record.

It must not mutate `conditional` into `allowed` in place.

### Indeterminate decisions

`indeterminate` applies where required facts cannot be safely established, including:

- identity-provider unavailable;
- guardian relationship disputed;
- consent scope unclear;
- collaborator identity unresolved;
- policy version unavailable;
- source sensitivity unknown;
- or a no-leakage rule prevents ordinary resolution.

Indeterminate fails closed.

### Decision expiration

Expiration does not delete or rewrite the Decision.

A new action after expiration requires new evaluation.

## Metadata Visibility Decision

### Purpose

Metadata Visibility Decision constrains what can be revealed before artifact access.

### Visibility levels

```text
no_existence_disclosure
bounded_generic_result
safe_summary
authorized_detailed_metadata
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `metadata_visibility_decision_id` | Required | Opaque durable identity. |
| `authorization_decision_id` | Required | Governing Decision. |
| `target_scope` | Required | Query, publication, Candidate, or source family. |
| `visibility_level` | Required | Controlled visibility level. |
| `allowed_field_ids` | Conditional | Closed field allowlist. |
| `suppressed_field_ids` | Optional | Explicitly suppressed fields. |
| `safe_empty_behavior` | Required | Response behavior when result cannot be revealed. |
| `created_at` | Required | Aware timestamp. |

### Safe empty behavior

For sensitive sources, the ordinary result should not distinguish:

- zero matching sources;
- matching but suppressed sources;
- matching but unauthorized sources;
- or matching sources whose existence is itself restricted.

### Examples of safe metadata

Depending on policy, safe metadata may include:

- generic “portfolio item available for review” status;
- an approved curator display title;
- an approved date range;
- an approved section label;
- or a review-required indicator.

It must not automatically include:

- producer name;
- source filename;
- internal title;
- manifest path;
- attempt number;
- sensitive category;
- Portia existence;
- collaborator names;
- or denial reason.

## Protected Access Event

### Purpose

Protected Access Event records policy-relevant use of restricted metadata, source content, internal manifests, historical Editions, or other protected objects.

It is separate from an Authorization Decision because approval and actual use are different facts.

### Event kinds

```text
metadata_viewed
source_opened
sensitive_source_reviewed
internal_manifest_viewed
historical_edition_viewed
export_downloaded_internal
access_failed
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `protected_access_event_id` | Required | Opaque durable identity. |
| `authorization_decision_id` | Required | Exact governing Decision. |
| `event_kind` | Required | Controlled event kind. |
| `actor_reference` | Required | Exact actor. |
| `target_references` | Required | Exact object accessed or attempted. |
| `purpose` | Required | Exact purpose. |
| `occurred_at` | Required | Aware timestamp. |
| `outcome` | Required | `completed`, `denied`, `failed`, or `indeterminate`. |
| `channel_or_interface` | Optional | Bounded local interface or service class. |
| `policy_logging_disposition` | Required | Whether and why the event is retained or forwarded. |
| `failure_code` | Optional | Privacy-safe failure code. |

### Minimum-necessary logging

The event must not contain:

- viewed educational content;
- full source path;
- full search query where it contains sensitive data;
- screenshots;
- authentication token;
- or complete authority evidence.

## Disclosure Review

### Purpose

Disclosure Review evaluates a concrete proposed content set before build, issuance, delivery, or submission.

It is more specific than Audience Context and more content-aware than general Authorization Decision.

### Review targets

A Disclosure Review may target:

- a Working Portfolio Composition Revision;
- a Snapshot Build Plan;
- a proposed Snapshot Entry inventory;
- a sealed Snapshot Edition;
- an Export Artifact set;
- or a successor Edition proposed after redaction.

### Review outcomes

```text
approved_as_is
redaction_required
changes_required
denied
indeterminate
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `disclosure_review_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Review contract version. |
| `target_type` | Required | Composition, Plan, Entry inventory, Edition, or Export Artifact set. |
| `target_references` | Required | Exact IDs, revisions, and digests. |
| `audience_context_id` | Required | Exact Audience Context. |
| `recipient_scope_id` | Required | Exact Recipient Scope. |
| `authorization_decision_id` | Required | Governing Decision. |
| `reviewer` | Required | Exact reviewer or trusted service. |
| `reviewer_role` | Required | Role used for review. |
| `content_inventory_reference` | Required | Exact reviewed content inventory. |
| `finding_ids` | Required | Ordered unique Disclosure Review Findings. |
| `outcome` | Required | Controlled outcome. |
| `required_redaction_plan_id` | Conditional | Required where redaction is needed. |
| `required_follow_up` | Optional | Additional review or authority requirements. |
| `reviewed_at` | Required | Aware timestamp. |

### Disclosure Review Finding

Each finding should preserve:

- exact target Entry or field;
- information class;
- subject or third-party relationship;
- direct or indirect identifier risk;
- sensitive-source restriction;
- assessment-security concern;
- rights or consent concern;
- recommended action;
- severity or blocking effect;
- and reviewer rationale.

Findings must not duplicate prohibited content unnecessarily.

For suppressed Portia information, a finding may identify an opaque protected target and suppression rule without revealing the source category in an audience-facing view.

### Information classes

The design should support policy-controlled classifications such as:

```text
direct_identifier
indirect_identifier
student_work
assessment_result
assessment_security
teacher_private_note
producer_operational_metadata
collaborator_information
third_party_account
family_information
disability_or_accommodation_detail
health_or_safety_information
behavior_or_intervention_information
contact_information
institutional_identifier
location_or_schedule_detail
image_or_biometric_like_media
voice_or_audio_identifier
copyright_or_rights_restriction
internal_provenance
```

Classification remains contextual.

A file type alone does not determine privacy.

## Redaction Plan

### Purpose

Redaction Plan defines an exact, ordered, immutable transformation from one exact input representation to one intended audience-safe output.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `redaction_plan_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Plan contract version. |
| `disclosure_review_id` | Required | Exact review requiring the plan. |
| `input_type` | Required | Source representation, planned Entry, Snapshot Entry, or Export Artifact component. |
| `input_reference` | Required | Exact input ID, revision, and digest. |
| `audience_context_id` | Required | Exact Audience Context. |
| `recipient_scope_id` | Required | Exact Recipient Scope. |
| `operation_ids` | Required | Ordered unique operations. |
| `transformer_contract` | Required | Exact transformer or renderer contract. |
| `transformer_version` | Required | Exact implementation version. |
| `required_human_verification` | Required | Boolean policy requirement; not proof that verification occurred. |
| `accessibility_requirements` | Optional | Requirements to preserve or improve accessible output. |
| `plan_digest_algorithm` | Required | Initial value `sha256`. |
| `plan_digest` | Required | Digest of canonical plan bytes. |
| `created_by` | Required | Actor or authorized process. |
| `created_at` | Required | Aware timestamp. |

### Redaction operations

Initial conceptual operations include:

```text
omit_entry
omit_page
mask_field
replace_text
crop_region
blur_region
remove_image_region
remove_audio_segment
replace_audio_segment
pseudonymize_identifier
generalize_date
generalize_location
strip_embedded_metadata
suppress_provenance_detail
remove_comment_or_annotation
substitute_authorized_summary
```

The final wire contract should use media-specific operation variants rather than one unsafe universal operation with many optional fields.

### Operation requirements

Each Redaction Operation must identify:

- operation ID;
- media or structured-content type;
- exact target locator appropriate to that media;
- protected information class;
- affected subject or third party through an opaque reference;
- transformation kind;
- replacement value or summary reference where applicable;
- operation order;
- expected input context or digest;
- and rationale or policy rule.

### Prohibited redaction behavior

The plan must not:

- edit producer-native files;
- edit an existing sealed Snapshot Edition;
- rely on manual visual covering that leaves underlying text extractable;
- retain removed audio or image content in hidden layers;
- omit embedded metadata review;
- use freehand coordinates without an exact media contract;
- or claim de-identification merely because direct names were removed.

## Redaction Result

### Purpose

Redaction Result records what exact output was produced from one exact input under one exact Plan.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `redaction_result_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Result contract version. |
| `redaction_plan_id` | Required | Exact Plan. |
| `input_digest_algorithm` | Required | Input digest algorithm. |
| `input_digest` | Required | Exact input bytes or canonical structured input digest. |
| `transformer_id` | Required | Exact transformer. |
| `transformer_version` | Required | Exact version. |
| `operation_outcomes` | Required | One terminal outcome for every planned operation. |
| `output_media_type` | Required | Exact output media type. |
| `output_byte_size` | Required | Output byte count. |
| `output_digest_algorithm` | Required | Initial value `sha256`. |
| `output_digest` | Required | Exact output digest. |
| `warnings` | Optional | Bounded warnings. |
| `completed_at` | Required | Aware timestamp. |
| `status` | Required | `completed`, `failed`, or `partial`. |

### Terminal outcome rule

A Result is usable only when:

- every required operation completed;
- the output is readable;
- the output digest is verified;
- no hidden content remains under the transformation contract;
- and required Redaction Verification succeeds.

`partial` is not a distributable result.

### Snapshot relationship

When redaction changes audience-visible bytes, issue #9 requires a new Snapshot Entry and new Snapshot Edition.

The Redaction Result becomes Materialization provenance for that new Entry.

## Redaction Verification Decision

### Purpose

Verification evaluates the exact redacted output, not the intent expressed by the Plan.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `redaction_verification_decision_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Decision contract version. |
| `redaction_result_id` | Required | Exact Result. |
| `reviewed_output_digest` | Required | Exact output digest. |
| `verifier` | Required | Exact human or authorized service. |
| `verifier_role` | Required | Role used for verification. |
| `verification_method` | Required | Visual, extraction, metadata, media playback, accessibility, or combined method. |
| `decision` | Required | `verified`, `rejected`, `changes_required`, or `indeterminate`. |
| `finding_ids` | Optional | Remaining leakage or accessibility findings. |
| `verified_at` | Required | Aware timestamp. |
| `supersedes_verification_id` | Optional | Earlier verification superseded for a successor Result. |

### Digest binding

Verification applies only to the exact reviewed output digest.

Any byte change requires new verification.

### Accessibility

Verification should confirm that redaction did not create inaccessible or misleading output where accessibility is required.

Examples include:

- missing alternative text;
- broken reading order;
- unlabeled replacement text;
- inaccessible color-only masking;
- missing captions after audio removal;
- or a PDF that visually hides text while leaving it extractable.

## De-identification Review

### Purpose

De-identification Review evaluates whether an exact output is reasonably non-identifiable in one exact intended context.

It is separate from ordinary redaction because contextual re-identification may remain possible after all direct identifiers are removed.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `deidentification_review_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Review contract version. |
| `output_reference` | Required | Exact output ID and digest. |
| `audience_context_id` | Required | Exact release context. |
| `recipient_scope_id` | Required | Exact recipient context, including public-unrestricted where applicable. |
| `direct_identifier_classes_considered` | Required | Direct identifiers reviewed. |
| `indirect_identifier_classes_considered` | Required | Indirect identifiers reviewed. |
| `external_information_context` | Required | Bounded description or policy reference for reasonably available outside information. |
| `methodology_reference` | Required | Review method or policy. |
| `reviewer` | Required | Exact reviewer. |
| `reviewer_role` | Required | Authority used. |
| `decision` | Required | `deidentified_for_context`, `not_deidentified`, `additional_transformation_required`, or `indeterminate`. |
| `limitations` | Optional | Known scope limitations. |
| `reviewed_at` | Required | Aware timestamp. |

### Context specificity

A result may be de-identified for:

- a large internal research pool;
- but not a small class;
- a district reviewer;
- but not public social media;
- or a family meeting;
- but not an unrestricted public site.

The Decision must not become a permanent `anonymous` attribute on the source.

### Indirect identifiers

Review should consider, where relevant:

- small class or program;
- distinctive project topic;
- teacher and period combination;
- dates and event timing;
- school logo or uniform;
- voice, face, handwriting, and image background;
- collaborator names;
- embedded author metadata;
- file naming;
- rubric comments;
- unusual accommodations;
- and provenance detail.

## Multi-subject and collaborator handling

### Relationship preservation

Vitrine must preserve producer-authoritative distinctions among:

- Portfolio Subject;
- Artifact Author;
- Artifact Subject;
- Group Member;
- co-author;
- recorder;
- represented speaker or position;
- photographed or recorded person;
- peer reviewer;
- third-party account source;
- family member;
- and staff member.

### Permission is not inferred from relationship

```text
Group Membership != authorship
Group Membership != collaborator disclosure permission
authorship != public-release permission
being depicted != consent
being the recorder != ownership of every represented statement
```

### Collaborator review

A multi-subject artifact should identify:

- every known identifiable person;
- authoritative relationship type;
- whether individual contribution can be isolated;
- whether names, voices, images, or statements may be shown;
- exact authority or consent evidence;
- required redaction per recipient scope;
- and whether a safe representation can be produced.

### Isolation outcomes

```text
safe_as_is
safe_with_redaction
safe_with_authorized_summary
reference_only
not_safely_isolatable
indeterminate
```

Where safe isolation is impossible, disclosure is denied or limited to an approved summary.

### Group Score and proficiency

Redaction or disclosure of a Group Artifact must not turn a Group-targeted Score into an individual Score or proof of proficiency.

## Disclosure Authorization

### Purpose

Disclosure Authorization is the final Vitrine authorization for future use of one exact immutable audience package.

It binds content, recipient, authority, and review evidence.

### Conceptual binding

```text
exact Snapshot Edition
+ exact Export Artifact set
+ exact Audience Context
+ exact Recipient Scope
+ exact Authorization Decision
+ exact Disclosure Review
+ exact Redaction Verification(s), where required
+ exact De-identification Review, where required
```

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `disclosure_authorization_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Authorization contract version. |
| `snapshot_series_id` | Required | Exact Snapshot Series. |
| `snapshot_edition` | Required | Exact immutable Edition. |
| `export_artifact_ids` | Required | Exact authorized Export Artifact set. |
| `audience_context_id` | Required | Exact Audience Context. |
| `recipient_scope_id` | Required | Exact Recipient Scope. |
| `authorization_decision_id` | Required | Governing Decision. |
| `disclosure_review_id` | Required | Exact approved Review. |
| `redaction_verification_ids` | Conditional | Every required exact verification. |
| `deidentification_review_id` | Conditional | Required where de-identification is the release basis. |
| `authorized_by` | Required | Exact approving actor or service. |
| `asserted_authority` | Required | Authority used. |
| `authorized_purpose` | Required | Exact purpose. |
| `permitted_channel_classes` | Required | Closed channel allowlist. |
| `valid_from` | Required | Earliest permitted use. |
| `valid_until` | Optional | Expiration. |
| `redisclosure_conditions` | Optional | Bounded restrictions. |
| `supersedes_authorization_id` | Optional | Earlier future-use authorization superseded. |
| `created_at` | Required | Aware timestamp. |

### Edition binding

Authorization for Edition 1 does not cover Edition 2 unless an authoritative policy and exact successor authorization explicitly establish that coverage.

A content-identical later Edition still receives its own authorization where identity or issuance history differs.

### Export Artifact binding

Authorization identifies the exact Export Artifact IDs.

A newly generated ZIP or PDF is not covered merely because it claims to represent the same Edition.

It must be validated and explicitly authorized or fall under an exact artifact-set rule defined by the final contract.

## Disclosure Event

### Purpose

Disclosure Event records actual use of an exact authorized artifact.

### Event kinds

```text
viewed
downloaded
issued
delivered
submitted
delivery_failed
receipt_recorded
external_review_recorded
external_decision_recorded
access_revoked
```

Issue #9 remains authoritative for Snapshot Issuance and Submission identities.

Disclosure Event references those records where they exist rather than replacing them.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `disclosure_event_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Event contract version. |
| `disclosure_authorization_id` | Required | Exact governing authorization. |
| `event_kind` | Required | Controlled event kind. |
| `snapshot_series_id` | Required | Exact Series. |
| `snapshot_edition` | Required | Exact Edition. |
| `export_artifact_ids` | Required | Exact artifact set used. |
| `actor_reference` | Required | Actor initiating or recording the event. |
| `recipient_scope_id` | Required | Exact recipient scope. |
| `channel_class` | Required | Portal, in-person, secure transfer, mail, external system, or equivalent bounded class. |
| `occurred_at` | Required | Aware event time. |
| `outcome` | Required | `completed`, `failed`, `partial`, `indeterminate`, or `not_applicable`. |
| `issuance_id` | Optional | Exact issue #9 Issuance. |
| `submission_id` | Optional | Exact issue #9 Submission. |
| `external_reference` | Optional | Opaque delivery, receipt, or tracking reference. |
| `policy_logging_disposition` | Required | Retention or forwarding basis. |
| `failure_code` | Optional | Privacy-safe failure code. |

### Event separation

```text
issued != delivered
submitted != received
received != reviewed
reviewed != accepted
```

The design preserves each stage separately.

### Disclosure logging boundary

Vitrine should retain enough information for institutional policy to determine whether a disclosure log is required.

It must not claim that every internal view is a legally recordable disclosure or that Vitrine alone satisfies all disclosure-record obligations.

## Authorization Revocation

### Purpose

Revocation restricts future use of an exact Decision or Disclosure Authorization.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `authorization_revocation_id` | Required | Opaque durable identity. |
| `contract_version` | Required | Revocation contract version. |
| `target_type` | Required | Authorization Decision or Disclosure Authorization. |
| `target_id` | Required | Exact affected record. |
| `revoked_by` | Required | Actor or authorized service. |
| `asserted_authority` | Required | Authority used. |
| `reason_code` | Required | Controlled reason. |
| `effective_at` | Required | Future-use restriction time. |
| `affected_action_classes` | Required | View, download, issue, deliver, submit, reuse, or other bounded actions. |
| `historical_treatment` | Required | Policy for retained history and logs. |
| `successor_authorization_id` | Optional | Replacement authorization where applicable. |
| `recorded_at` | Required | Aware timestamp. |

### No recall claim

Revocation does not establish that:

- an external recipient deleted a copy;
- a sent email attachment was recalled;
- a public download disappeared from caches;
- or a regulated authority returned the package.

External containment or deletion evidence remains separately attributable.

## Audience-specific policy

### Audience matrix

| Audience | Normal access shape | Default exclusions | Common required evidence |
| --- | --- | --- | --- |
| Student-facing | Exact subject-scoped selected artifacts, approved reflections, and student-facing feedback | teacher-private notes, internal manifests, unrelated students, secure assessment data, suppressed Portia sources | authenticated subject identity, Profile rule, exact content review |
| Parent/guardian-facing | Purpose-limited conference or family Edition | complete record graph, teacher drafts, unrelated students, internal provenance, secure assessment material | current relationship or rights-holder evidence, purpose, exact recipient scope |
| Teacher-internal | Class-, student-, role-, and purpose-scoped working information | unrelated classes/years, other functions' restricted records, private producer internals without need | authenticated identity, assignment/role evidence, legitimate purpose |
| External reviewer | Exact package only, normally time-bound and non-browsable | Candidate search, native files, internal paths, unrelated history, hidden omission reasons | appointment, purpose, exact package, expiration, secure channel |
| Regulated submission | Exact requirement- and destination-bound package | unrelated work, unrequired sensitive information, internal notes, unapproved provenance | Profile, destination authority, required approvals, attestations, redaction verification |
| Public/community | Narrowest approved Edition or verified context-specific de-identified output | direct/indirect identifiers, sensitive records, collaborator data without authority, internal provenance | explicit authority/consent or verified de-identification, rights review |

### Student-facing rules

Student-facing access should normally be limited to exact information related to the Portfolio Subject and approved for that purpose.

It must not automatically expose:

- teacher-private drafts or notes;
- Quillan private review fields;
- ScoreForm answer keys, detector internals, or scan diagnostics;
- unrelated student names or work;
- unresolved collaborator details;
- internal source paths or IDs;
- the internal Snapshot Manifest;
- or suppressed Portia source existence.

A student-facing Portfolio is not automatically the complete response to a formal education-record request.

### Parent/guardian-facing rules

Parent/guardian access requires current, exact relationship and authority evidence under institutional policy.

A conference Edition is purpose-limited.

It must not automatically include:

- every student record;
- teacher preparation notes;
- other students' identifiable information;
- unrelated intervention or support history;
- secure assessment content;
- private producer provenance;
- or the internal Snapshot Manifest.

The model must support:

- relationship expiration;
- corrected relationship records;
- disputed authority;
- rights transfer to an eligible student under applicable policy;
- and separate formal records-access processes outside Vitrine.

### Teacher-internal rules

Teacher-internal access remains least-privilege.

Teacher status alone must not authorize:

- unrelated classes;
- unrelated school years;
- another teacher's Portfolio without assignment or legitimate interest;
- unrestricted Portia graphs;
- broad workspace export;
- or private producer files unrelated to the authorized task.

Private working notes and formal Portfolio annotations remain distinct.

A note shared through Vitrine must not automatically be treated as a sole-possession note.

### External-reviewer rules

External-reviewer access should normally be:

- exact-package only;
- non-browsable;
- purpose-bound;
- time-bound;
- least-privilege;
- and limited to one exact recipient or appointed reviewer class.

The reviewer should not receive:

- Candidate discovery;
- source-system navigation;
- internal manifests;
- absolute or private paths;
- hidden omission reasons;
- unrelated historical Editions;
- or unrelated student context.

### Regulated-submission rules

Regulated disclosure requires exact:

- Profile and requirement revision;
- destination authority;
- recipient scope;
- Snapshot Edition;
- Export Artifact set;
- approvals and attestations;
- privacy and redaction review;
- permitted delivery channel;
- and submission provenance.

Issue #11 defines authority-specific requirements.

This design defines the generic privacy and disclosure records they consume.

### Public/community rules

Public release uses deny-by-default policy.

It requires either:

- exact authority and consent covering the exact Edition, purpose, and public recipient scope;
- or context-specific verified de-identification and any required rights review.

Public permission must not be inferred from:

- a showcase Profile;
- student Selection;
- a public-looking caption;
- common directory-information assumptions;
- or removal of the student's name.

## Snapshot integration

### Audience-content policy versus authorization

Issue #9 defines audience-content policy as part of Snapshot Series and Edition planning.

This design adds exact authorization for:

- the actor building the Edition;
- the recipient receiving it;
- required transformations;
- and the actual delivery or submission.

### Build authorization

A Snapshot Build Request should reference an allowed or fully satisfied conditional Authorization Decision for `build_snapshot`.

That Decision binds:

- exact Composition Revision;
- Audience Context;
- intended Recipient Scope or recipient class where known;
- source and producer restrictions;
- and required Disclosure Review.

### Disclosure Review before sealing

Where the content set is known before sealing, Disclosure Review should occur against the exact Build Plan or planned Entry inventory.

A changed Plan invalidates the earlier review.

### Redaction and new Editions

Redaction changes audience-visible content.

Therefore:

- redacted bytes become a new Snapshot Entry;
- the Redaction Result is Materialization provenance;
- the Entry receives a new digest;
- and the audience-safe package is a distinct Snapshot Edition where content differs.

Vitrine never edits a sealed Edition in place.

### Internal Snapshot Manifest

The internal Snapshot Manifest is restricted provenance.

Access requires its own protected action and Authorization Decision.

It must not automatically be included in:

- student-facing packages;
- parent/guardian packages;
- external-reviewer packages;
- regulated submissions;
- or public packages.

An audience-safe provenance appendix is a separate generated Entry with its own Disclosure Review.

### Historical Editions

Historical Editions remain exact even after:

- authority expires;
- consent is withdrawn;
- a recipient relationship changes;
- the source is withdrawn;
- a redaction defect is found;
- or a successor Edition is issued.

Future access may be restricted through Decision supersession, Revocation, lifecycle events, or exceptional removal under issue #9.

The Edition is not rewritten.

## Producer-specific boundaries

### Core

- Catalog results are discovery aids, not authorization.
- Canonical Publication reload establishes identity, not permission.
- Compatibility metadata does not grant manifest access.
- Exact manifest verification may occur only within an authorized operation boundary appropriate to the implementation.
- Vitrine must not add Portfolio authorization fields to Core Publication Records.
- No Core authorization registry is required for this design.

### ScoreForm

- Academic Result Manifests remain restricted source projections rather than audience artifacts by default.
- Attempt summaries may be disclosed only through exact producer-approved projections and Vitrine authorization.
- Answer keys, secure item material, raw QR values, detector internals, scan-review notes, raw retained scans, and private paths remain prohibited.
- Student or parent access to a result does not imply access to assessment-security material.
- Attempt selection for Portfolio disclosure does not identify the official or Grade-bearing attempt.
- A later attempt does not silently expand an earlier authorization.

### Quillan

- Original student work and student-facing feedback remain separate disclosure objects.
- Private notes, complete native review records, candidate evidence, duplicate evidence, excluded evidence, routing state, scan-intake details, and retained paths remain unavailable.
- Teacher-internal views must not be copied into student- or family-facing Editions merely because they concern the same submission.
- Vitrine must await a public Core-compatible projection rather than parsing private Quillan files.

### Concord

- Artifact, Author, Subject, Group, Group Membership, contribution, representation status, privacy classification, Review, Moderation, and Score target remain distinct.
- Group Membership does not establish authorship or disclosure permission.
- Co-authored, discussion, laboratory, and recorded-media artifacts require exact collaborator treatment.
- Teacher-restricted observations, Review records, and Moderation records remain restricted.
- A redacted Artifact must preserve provenance to the exact unredacted producer projection without exposing that source to the recipient.
- Group-targeted Scores must not be presented as individual Scores through redaction or annotation.

### Portia

- Ordinary Portia records remain suppressed with no existence leakage.
- Vitrine must not reveal underlying Event, Account, Observation, Determination, Response, Communication, Support, family, disability, safety, or intervention information.
- Only an exact Portia-owned portfolio-safe projection may enter Vitrine.
- Vitrine must not attempt to redact raw Portia records into safety.
- Redaction plans, diagnostics, omission notices, result counts, and audit views must not leak suppressed source categories.
- Portia participant-specific privacy projections remain Portia-owned future work.

### Meridian

- Future Meridian reports may have their own audience and disclosure policies.
- Vitrine may copy only exact public report projections.
- Vitrine authorization does not grant access to Meridian's internal evidence inventory, attempt policy, overrides, calculations, or unpublished reports.
- Similar audience labels do not create shared authorization records or IDs.
- Meridian's installable package foundation does not yet implement any report or authorization behavior.

## Consent and authority lifecycle

### Consent scope

Where consent is the authority basis, the evidence reference should cover exact:

- rights holder or authority;
- subject;
- records, Edition, or content class;
- purpose;
- recipient or recipient class;
- signed/effective date reference;
- expiration or withdrawal terms;
- and redisclosure restrictions.

### Successor Editions

Consent for one Edition does not silently cover a successor Edition with changed content.

A Profile may define a lawful broader consent class, but Vitrine must preserve the exact rule and evidence supporting that scope.

### Rights transfer

A changed rights-holder status does not mutate earlier evidence.

Future actions use a successor Authority Evidence Reference and new Decision.

### Expiration

Expired authority blocks future action.

It does not invalidate earlier lawful disclosure automatically.

### Withdrawal or revocation

Withdrawal may block future:

- build;
- view;
- download;
- issue;
- delivery;
- submission;
- or reuse.

Historical Disclosure Events remain.

## Correction and supersession

### Authority evidence correction

A materially incorrect authority reference is superseded or invalidated according to its owning-system and Vitrine reference rules.

Dependent future-use Decisions require reevaluation.

### Authorization Decision correction

A Decision with wrong actor, target, purpose, evidence, recipient, or policy cannot be retargeted in place.

Create a successor Decision and preserve the predecessor.

### Recipient Scope correction

A wrong recipient or relationship requires a new Recipient Scope and new Disclosure Authorization.

### Disclosure Review correction

A review performed against the wrong content inventory is invalidated and replaced.

### Redaction correction

A defective Redaction Result is rejected or invalidated.

Corrected bytes receive a new Result, digest, verification, Entry, and Edition where content changes.

### Mistaken disclosure

A mistaken disclosure is not erased from audit history.

The design should support references to:

- affected Disclosure Event;
- exact artifact;
- recipient scope;
- containment or corrective action;
- institutional incident workflow;
- and future authorization restrictions.

The privacy record must remain minimum-necessary and must not duplicate the disclosed content.

## Canonical and derived state

### Canonical privacy state

Canonical Vitrine privacy state includes:

- Audience Contexts;
- Recipient Scopes;
- Authorization Requests;
- Authority Evidence References;
- Authorization Decisions;
- Metadata Visibility Decisions;
- Protected Access Events;
- Disclosure Reviews and Findings;
- Redaction Plans and Results;
- Redaction Verification Decisions;
- De-identification Reviews;
- Disclosure Authorizations;
- Disclosure Events;
- Revocations;
- and correction/supersession relationships.

### Derived state

Derived and rebuildable state includes:

- pending-authorization queues;
- expiring-authority dashboards;
- pending collaborator review;
- redaction-verification queues;
- audience-package previews;
- disclosure history summaries;
- recipient access dashboards;
- no-leakage-safe counts;
- and disclosure-log exports.

A derived row cannot:

- grant access;
- establish identity or relationship;
- create consent;
- satisfy a redaction requirement;
- authorize disclosure;
- or prove that no restricted source exists.

### Rebuilding

A derived view must be rebuilt from exact canonical records and current policy context.

Missing derived state must not be interpreted as an empty authorization or disclosure history.

## Failure-state vocabulary

The design should define privacy-safe failures including:

```text
authorization_request_invalid
actor_identity_unresolved
actor_role_unverified
actor_scope_mismatch
purpose_not_permitted
target_scope_mismatch
recipient_scope_unresolved
recipient_scope_disputed
recipient_scope_expired
relationship_unverified
relationship_expired
authority_evidence_missing
authority_evidence_invalid
authority_evidence_expired
authority_evidence_revoked
consent_missing
consent_scope_mismatch
consent_expired
consent_withdrawn
policy_reference_unavailable
policy_rule_unsupported
authorization_denied
authorization_conditional
authorization_indeterminate
authorization_expired
metadata_visibility_denied
metadata_visibility_suppressed
source_access_denied
source_suppressed
candidate_visibility_denied
curation_action_denied
snapshot_build_denied
internal_manifest_access_denied
disclosure_review_required
disclosure_review_denied
disclosure_review_indeterminate
collaborator_review_required
collaborator_permission_missing
third_party_information_present
assessment_security_restricted
redaction_required
redaction_plan_invalid
redaction_input_mismatch
redaction_failed
redaction_partial
redaction_verification_failed
redaction_result_stale
accessibility_verification_failed
deidentification_not_established
deidentification_context_mismatch
indirect_identifier_risk
disclosure_authorization_missing
disclosure_authorization_stale
disclosure_authorization_expired
disclosure_authorization_revoked
export_artifact_mismatch
delivery_channel_not_permitted
delivery_failed
disclosure_log_required
historical_access_restricted
external_copy_not_recalled
```

### Safe external failure mapping

The final implementation should define a restricted mapping from internal failure to safe user-facing response.

For example, these internal states may all map to a generic unavailable result for an ordinary actor:

```text
no matching source
source_suppressed
metadata_visibility_denied
actor_scope_mismatch
relationship_unverified
source_access_denied
```

Authorized administrators may receive more specific diagnostics under their own Authorization Decision.

## Required edge cases

The design must remain valid for at least these cases:

1. A teacher sees a safe catalog result but lacks source-content authority.
2. A suppressed Portia source produces no visible result, count, or hidden-result placeholder.
3. A student can view one selected artifact but not teacher-private feedback.
4. A student requests a Group Artifact containing identifiable peers.
5. A parent conference Edition is permitted, but a full records-access request remains outside Vitrine.
6. Parent/guardian relationship evidence is expired.
7. Rights-holder status changes under institutional policy.
8. A teacher assigned to one class requests another teacher's Portfolio.
9. An external reviewer receives one exact package without Candidate browsing.
10. Reviewer authorization expires after an earlier download.
11. Regulated submission requires a named authority and exact destination.
12. A public showcase has student consent but lacks collaborator permission.
13. Names are removed, but a distinctive photo still identifies the student.
14. A filename and embedded document metadata reveal identity after visible redaction.
15. A ScoreForm attempt summary is allowed while answer-key access is denied.
16. Quillan feedback is allowed while private notes remain hidden.
17. A Concord Group Artifact requires collaborator-specific redaction.
18. A Concord discussion record cannot be safely isolated.
19. A Portia-safe growth statement is allowed without source-graph access.
20. The internal Snapshot Manifest is excluded from a family package.
21. Redaction changes bytes and creates a successor Edition.
22. A Redaction Result exists, but verification fails.
23. De-identification is sufficient for one internal context but not public release.
24. Consent covers Edition 1 but not Edition 2.
25. Consent is withdrawn after an earlier lawful disclosure.
26. Authorization permits issuance but not electronic delivery.
27. Delivery fails after authorization and Issuance.
28. A recipient receives a package, but no external acceptance exists.
29. Authorization expires while snapshot construction is in progress.
30. Actor relationship changes after the Snapshot is sealed.
31. A historical Edition remains retained while future access is revoked.
32. Local policy requires a disclosure-log export.
33. A denial response must not distinguish absent from suppressed.
34. A derived authorization dashboard is deleted and rebuilt.
35. A mistaken disclosure is preserved and referred to institutional response.
36. An actor has an asserted teacher role but no verified assignment evidence.
37. The identity provider is unavailable, producing an indeterminate result.
38. Collaborator review is required before a conditional Decision can be used.
39. A teacher-private note is referenced by a formal Annotation and loses any assumed private-note treatment.
40. A parent asks for every source discovered during a conference workflow.
41. A public release relies only on a directory-information assumption.
42. A small cohort makes an otherwise generalized artifact identifiable.
43. An audio recording remains identifiable by voice after names are removed.
44. A blurred video still identifies a student through uniform and setting.
45. PDF author metadata remains after visible text redaction.
46. A redaction Plan applies operations in an unsafe order.
47. A crop removes a signature but leaves the same name in a teacher comment.
48. Redaction makes a PDF unreadable to assistive technology.
49. An approved summary substitutes for an artifact that cannot be safely isolated.
50. Secure assessment content appears in a student-facing source but is prohibited by producer policy.
51. A source is withdrawn after lawful snapshot issuance.
52. Candidate Selection is allowed, but snapshot building is denied for this audience.
53. Snapshot building is allowed, but Issuance is denied.
54. Issuance is allowed, but the requested channel is prohibited.
55. An Export Artifact digest does not match the authorized artifact.
56. A recipient scope references the wrong organization.
57. Consent has expired before delivery.
58. Consent purpose does not match the requested public release.
59. A de-identification review becomes stale after the bytes change.
60. Group Membership is mistakenly treated as collaborator permission.
61. A Concord `recorder_for_group` is incorrectly treated as sole author.
62. A Portia omission notice would reveal that a suppressed source existed.
63. A future Meridian report is approved as a Candidate, but internal grading provenance remains restricted.
64. An access event records the source ID and outcome without copying source content.
65. A delivery event retains recipient scope and artifact digest but not the artifact bytes.
66. Revocation blocks future download without claiming external recall.
67. Family-facing and public-facing Editions contain different bytes and therefore have distinct Edition identities.
68. ZIP and PDF Export Artifacts contain the same approved Edition content and remain separately authorized artifacts.
69. A public-unrestricted scope is requested without consent or verified de-identification.
70. A policy evaluator returns `indeterminate`; the UI must not offer a download action.
71. A historical authorization remains auditable after its Authority Evidence Reference is superseded.

## Foundational invariants

1. Publication discovery is not artifact access.
2. Metadata visibility is separate from source-content access.
3. Source access is separate from Candidate eligibility.
4. Candidate eligibility is separate from curation authority.
5. Curation approval is separate from snapshot-build authority.
6. Snapshot-build authority is separate from Issuance authority.
7. Issuance authority is separate from delivery or submission authority.
8. Audience Context is separate from Recipient Scope.
9. Asserted role is separate from verified authority.
10. Authorization is action-specific.
11. Authorization is purpose-specific.
12. Authorization is target-specific.
13. Authorization is time-bounded where policy requires it.
14. Disclosure authorization is recipient-specific.
15. `indeterminate` never means allowed.
16. Conditional authorization cannot be used before conditions are satisfied.
17. Denial does not leak suppressed source existence.
18. A teacher role does not authorize every student or record.
19. A parent or guardian label does not prove current authority.
20. Portfolio Subject identity does not grant access to every related record.
21. Vitrine does not become the institutional identity or guardian authority.
22. Authority Evidence References remain bounded and externally authoritative.
23. Consent binds exact scope.
24. Consent does not silently cover successor Editions.
25. Expiration and revocation preserve history.
26. Student-facing content excludes private teacher and producer information by default.
27. Parent-facing content is not a complete formal records-access response by default.
28. Teacher-internal access remains purpose- and assignment-limited.
29. External reviewers receive exact packages, not discovery or browsing access.
30. Regulated submissions bind exact Profile, destination, Edition, and artifact set.
31. Public release requires exact authority or context-specific verified de-identification.
32. Redaction never mutates producer-native bytes.
33. Redaction never mutates a sealed Snapshot Edition.
34. Every Redaction Result binds exact input and output digests.
35. Failed or partial redaction is not distributable.
36. Redaction verification binds one exact output digest.
37. De-identification is separate from direct identifier removal.
38. De-identification is context-specific.
39. Multi-subject sources require explicit collaborator treatment.
40. Group Membership does not imply authorship or disclosure permission.
41. Unsafe isolation blocks disclosure or requires an approved summary.
42. Internal Snapshot Manifests are not automatically distributed.
43. Audience-visible content changes require a new Snapshot Edition.
44. Disclosure Authorization binds exact Edition and Export Artifact IDs.
45. A new Export Artifact is not automatically authorized.
46. Issuance, delivery, receipt, external review, and external decision remain distinct.
47. Disclosure logs remain minimum-necessary.
48. Revocation does not claim external copies were recalled.
49. Producer-private fields remain prohibited.
50. Portia suppression remains no-leakage.
51. ScoreForm secure assessment boundaries remain intact.
52. Quillan private and student-facing records remain distinct.
53. Concord authorship, subject, Group, contribution, privacy, and Score target remain distinct.
54. Meridian internal grading state remains Meridian-owned.
55. Canonical privacy records are append-preserving.
56. Derived privacy views are rebuildable.
57. Missing derived state does not prove no authorization or disclosure history.
58. Ordinary correction does not delete prior privacy decisions or events.
59. No private-file fallback is allowed.
60. No sibling repository is modified by this issue.

## Downstream boundaries

### Issue #11: regulated Portfolio and compliance Profiles

Issue #11 will define concrete:

- regulated audience rules;
- checklists;
- attestations;
- signatures or signature references;
- deadlines;
- approval stages;
- missing-document findings;
- destination authorities;
- and New Jersey Graduation Portfolio Appeal Profile revisions.

Those Profiles should reuse:

- Audience Context;
- Recipient Scope;
- Authority Evidence Reference;
- Authorization Decision;
- Disclosure Review;
- Redaction and De-identification reviews;
- Disclosure Authorization;
- and Disclosure Events.

### Portia privacy projections

Portia remains responsible for creating participant-specific and portfolio-safe projections from its own sensitive graph.

Vitrine must not accept responsibility for redacting raw Portia records into a safe projection.

### Producer public readers

ScoreForm, Quillan, Concord, Portia, and Meridian remain responsible for public consumer contracts that expose only approved representations.

Vitrine authorization cannot compensate for a missing public projection.

### Future Sunset integration

Sunset or institutional records systems may later own:

- retention execution;
- legal holds;
- archival transfer;
- approved disposition;
- and external custody.

Vitrine preserves exact privacy, authorization, and disclosure references without implementing those records-management authorities here.

### External identity and authorization systems

Future deployment may integrate with:

- school identity providers;
- student information systems;
- guardian portals;
- consent or document-management systems;
- secure delivery systems;
- and regulated submission portals.

This design defines stable boundaries but not one mandatory vendor or protocol.

## Unresolved questions for final contracts

The final contract and implementation work must resolve:

1. which authorization records are workspace-local versus institutionally synchronized;
2. which protected access events are logged by default versus policy-controlled;
3. how Vitrine identifies an authoritative identity-provider session without storing credentials;
4. whether recipient-class authorization is permitted for recurring institutional reviewers;
5. how consent document digests or references are protected;
6. how offline use verifies time-bounded authority;
7. how clock uncertainty affects expiration;
8. which media redaction operation contracts are supported initially;
9. which formats can be verified automatically and which require human review;
10. how accessible redacted PDFs, HTML, images, audio, and video are produced;
11. whether an internal privacy administrator role is needed in v0.1.0;
12. how no-leakage-safe diagnostics are exposed to ordinary teachers;
13. how institutional disclosure-log systems receive Vitrine events;
14. how external deletion or containment evidence is referenced after mistaken disclosure;
15. how public de-identification review is revalidated when outside information changes;
16. how Profile migration affects prior Audience Contexts and authorizations;
17. how a revoked producer projection affects future access to retained historical Editions;
18. and how regulated Profiles specialize generic authority evidence without embedding legal forms.

Unresolved questions must not be answered by broad allow, native-file fallback, or silent inference.

## Non-goals

This foundation design does not:

- implement authentication or identity federation;
- define institutional roles universally;
- determine legal guardianship;
- determine FERPA rights-holder status;
- validate signatures or consent legality;
- create a consent document store;
- add runtime authorization code;
- add final JSON Schema;
- add persistence;
- implement redaction of PDF, image, audio, video, or structured records;
- implement de-identification tooling;
- implement encryption or digital signatures;
- implement secure portals, email, or delivery;
- implement public sharing;
- implement regulated Profiles;
- create a complete formal records-access workflow;
- define Portia participant-specific privacy projections;
- define Meridian report authorization;
- implement Sunset retention or disposition;
- modify Core publication contracts;
- or modify sibling repositories.

## Security and privacy requirements for later implementation

Later runtime work must:

- use opaque non-PII IDs;
- reject identity and authority claims that cannot be verified;
- never store authentication secrets in privacy records;
- never log student work or full source content;
- avoid absolute paths and private filenames in ordinary diagnostics;
- minimize retained recipient and authority data;
- protect internal denial reasons;
- isolate internal manifests from audience packages;
- fail closed on indeterminate policy, relationship, or consent;
- verify redacted output bytes rather than trusting a plan;
- preserve accessibility during transformation;
- prevent suppressed-source counts and previews;
- maintain append-preserving history;
- and distinguish checksums from authorization, encryption, signatures, or legal proof.

## Documentation deliverables

This design is paired with:

- [ADR 0008: Privacy, Redaction, and Audience Controls](../decisions/0008-privacy-redaction-and-audience-controls.md); and
- [Representative Privacy, Redaction, and Audience Examples](../examples/privacy-redaction-audience-examples.md).

The ADR is **Accepted** following the issue #13 portfolio foundation audit.
