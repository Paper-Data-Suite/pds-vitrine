# ADR 0008: Privacy, Redaction, and Audience Controls

- **Status:** Accepted
- **Date:** 2026-08-05
- **Accepted:** 2026-08-06 — approved by issue #13 portfolio foundation audit
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #10, “Define privacy, redaction, and audience controls”
- **Related design:** [`../design/privacy-redaction-audience-controls.md`](../design/privacy-redaction-audience-controls.md)
- **Related examples:** [`../examples/privacy-redaction-audience-examples.md`](../examples/privacy-redaction-audience-examples.md)

## Context

Vitrine now has conceptual contracts for:

- Portfolio and Portfolio Subject identity;
- immutable versioned Portfolio Profiles;
- Candidate discovery and exact source references;
- producer-approved artifact exposure;
- Selection, Placement, ordering, Annotation, Reflection, and exact-revision curation approval;
- immutable byte-free Working Portfolio Composition Revisions;
- exact-byte source acquisition and rendering;
- immutable Snapshot Series and Editions;
- format-specific Export Artifacts;
- and separate Issuance and Submission records.

Those contracts intentionally preserve the difference between discoverability, eligibility, curation, copying, issuance, and external handoff.

They do not yet define:

- who may learn that a source exists;
- who may inspect student-level source content;
- how actor role and institutional authority are verified;
- how a parent, guardian, student, teacher, reviewer, or regulated authority is scoped;
- how consent or appointment evidence is referenced;
- how multi-subject artifacts are reviewed;
- how redaction is planned, materialized, and verified;
- how de-identification differs from direct-name removal;
- which exact Snapshot Edition and Export Artifact set may be disclosed;
- or how actual viewing, delivery, submission, expiration, and revocation are preserved.

The surrounding suite reinforces these boundaries:

- Core catalog discovery and Publication verification do not authorize student-level access;
- ScoreForm deliberately excludes answer keys, detector internals, scan diagnostics, and other secure or private fields from its public result manifest;
- Quillan distinguishes selected evidence and student-facing feedback from private notes and native review state;
- Concord distinguishes Artifact authorship, subject, Group, privacy, Review, Moderation, and Score targets;
- Portia is deny-by-default for ordinary Portfolio use and requires future participant-specific safe projections;
- Meridian now has an installable package foundation but no authorization, report, or delivery implementation;
- and Vitrine's Snapshot contract already requires audience-content changes to create new immutable Editions.

A single role check or mutable `can_view` Boolean cannot safely represent these requirements.

It would lose:

- exact action and purpose;
- exact target and revision;
- recipient scope;
- authority evidence;
- time limits;
- redaction and de-identification state;
- disclosure history;
- and no-existence-leakage behavior.

## Decision

Vitrine will use separate, immutable, append-preserving records for:

1. Audience Context;
2. Recipient Scope;
3. Authorization Request;
4. bounded Authority Evidence Reference;
5. Authorization Decision;
6. Metadata Visibility Decision;
7. Protected Access Event;
8. Disclosure Review and Findings;
9. Redaction Plan and media-appropriate Redaction Operations;
10. Redaction Result;
11. Redaction Verification Decision;
12. De-identification Review;
13. Disclosure Authorization;
14. Disclosure Event;
15. Authorization Revocation;
16. and rebuildable privacy workflow views.

The governing authorization sequence is:

```text
bounded discovery
  -> Metadata Visibility Decision
  -> source-access Authorization Decision
  -> producer-approved projection
  -> separate curation authority
  -> exact Composition Revision
  -> snapshot-build Authorization Decision
  -> Disclosure Review
  -> Redaction / De-identification where required
  -> immutable Snapshot Edition
  -> Disclosure Authorization for exact Export Artifact(s)
  -> actual access, delivery, or submission event
```

No stage is implied by the previous stage.

## Decision details

### Authorization gates remain separate

Vitrine will distinguish at least these protected action classes:

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

The exact final vocabulary may split actions further.

It must not collapse them into one generic `view`, `access`, or `share` permission.

An allowed decision for one action has no implied effect on another action.

### Authorization is action-, purpose-, target-, time-, and recipient-specific

Each Authorization Request binds exact:

- actor identity reference;
- asserted role;
- requested action;
- immutable target IDs and revisions;
- Portfolio and Subject where applicable;
- Profile Binding;
- purpose;
- Audience Context;
- Recipient Scope where disclosure is involved;
- authority evidence;
- and requested validity period.

A broad role or relationship is never the whole authorization result.

### Audience Context and Recipient Scope are distinct

Audience Context is Profile-derived policy describing appropriate content and review for a purpose and audience class.

Initial classes include:

```text
student_facing
parent_guardian_facing
teacher_internal
external_reviewer
regulated_submission
public_community
```

Recipient Scope identifies the exact recipient or bounded recipient class, relationship, organization, purpose, validity, and redisclosure conditions.

An Audience Context does not authorize a recipient.

A Recipient Scope does not determine what content is appropriate.

### Institutional authority remains external

Vitrine records bounded Authority Evidence References for facts such as:

- authenticated identity;
- employment or assignment;
- roster relationship;
- parent/guardian relationship;
- rights-holder status;
- consent;
- institutional approval;
- reviewer appointment;
- regulated submission authority;
- and policy exceptions.

Vitrine does not become the canonical source for those facts.

It does not store credentials or duplicate complete authority records.

### Authorization outcomes are explicit

The initial outcomes are:

```text
allowed
denied
conditional
indeterminate
expired
```

`indeterminate` fails closed.

A conditional Decision is not executable until every condition has exact completion evidence.

A later resolution creates a successor evaluation or separately attributable completion evidence; it does not mutate the earlier Decision.

### Discovery metadata has its own privacy decision

Metadata Visibility Decision controls whether a user may see:

```text
no_existence_disclosure
bounded_generic_result
safe_summary
authorized_detailed_metadata
```

For suppressed or sensitive sources, ordinary responses may intentionally make these cases indistinguishable:

- no source exists;
- a source exists but is suppressed;
- a source exists but metadata access is denied;
- or authority cannot be established.

Authorized restricted diagnostics may preserve exact reasons separately.

### Minimum necessary applies at every stage

An allowed Decision states an exact permitted scope.

It may allow:

- selected safe metadata fields;
- one exact producer projection;
- one Composition Revision;
- one internal manifest for a review task;
- one exact Snapshot Edition;
- or one exact Export Artifact for one recipient.

It does not grant broad workspace or source-system access.

### Protected access is distinct from authorization

A Protected Access Event records actual policy-relevant use of restricted metadata, source content, internal manifests, or historical Editions.

The event references the governing Decision and exact target.

It does not copy educational content into an access log.

### Disclosure Review evaluates concrete content

Disclosure Review binds one exact proposed content inventory to:

- Audience Context;
- Recipient Scope;
- Authorization Decision;
- exact Composition, Build Plan, Entry inventory, Edition, or Export Artifact set;
- and exact review findings.

The review outcome is one of:

```text
approved_as_is
redaction_required
changes_required
denied
indeterminate
```

A changed content inventory requires a new review.

### Redaction is an immutable materialization process

Redaction uses separate records for:

- immutable Plan;
- ordered media-appropriate operations;
- exact Result;
- and exact-output Verification Decision.

A Redaction Plan binds exact input identity and digest, Audience Context, Recipient Scope, policy, operations, transformer contract, transformer version, and accessibility requirements.

A Redaction Result binds exact input digest, operation outcomes, output media type, byte size, and output SHA-256.

Verification applies only to the reviewed output digest.

### Redaction never edits source or sealed snapshot bytes

Vitrine must not redact:

- producer-native records in place;
- producer public projections in place;
- Candidate references in place;
- or existing sealed Snapshot Entries or Editions in place.

Changed audience-visible bytes create a new Entry and, under ADR 0007, a new Snapshot Edition.

### Redaction must address hidden and embedded content

Visible covering alone is insufficient.

A valid transformation contract must address relevant:

- underlying text layers;
- comments and annotations;
- embedded metadata;
- document properties;
- image regions;
- audio segments;
- hidden attachments;
- filenames and paths;
- and accessibility structure.

Partial or failed redaction is not distributable.

### De-identification is a separate contextual review

Removing names does not establish de-identification.

De-identification Review evaluates an exact output in one exact intended release context, considering direct and indirect identifiers and reasonably available outside information.

The initial outcomes are:

```text
deidentified_for_context
not_deidentified
additional_transformation_required
indeterminate
```

The result is not a permanent anonymous classification on the source.

### Multi-subject artifacts require explicit collaborator treatment

The model preserves exact producer relationships such as:

- Author;
- Subject;
- Group Member;
- co-author;
- recorder;
- represented speaker;
- depicted person;
- peer reviewer;
- third-party source;
- and family or staff participant.

No relationship automatically creates disclosure permission.

A multi-subject review must determine whether the representation is:

```text
safe_as_is
safe_with_redaction
safe_with_authorized_summary
reference_only
not_safely_isolatable
indeterminate
```

Unsafe or indeterminate isolation blocks disclosure.

### Audience defaults remain distinct

#### Student-facing

Normally includes exact subject-scoped selected work, approved reflections, and student-facing feedback.

It excludes teacher-private notes, producer internals, unrelated students, secure assessment material, internal manifests, and suppressed Portia existence.

#### Parent/guardian-facing

Requires current exact relationship or rights-holder evidence and remains purpose-limited.

A parent-conference package is not automatically a complete formal records-access response.

#### Teacher-internal

Remains class-, student-, role-, and purpose-limited.

Teacher status does not create unrestricted workspace access.

#### External reviewer

Normally receives one exact, time-bound, non-browsable package.

It does not receive Candidate discovery or source-system access.

#### Regulated submission

Binds exact Profile, destination authority, Snapshot Edition, Export Artifacts, approvals, redaction, and submission purpose.

Concrete regulated requirements remain assigned to issue #11.

#### Public/community

Uses deny-by-default release policy.

It requires exact authority/consent or context-specific verified de-identification and any required rights review.

### Disclosure Authorization binds exact immutable content

Disclosure Authorization binds:

```text
exact Snapshot Edition
+ exact Export Artifact IDs
+ exact Audience Context
+ exact Recipient Scope
+ exact Authorization Decision
+ exact Disclosure Review
+ exact Redaction Verification(s), where required
+ exact De-identification Review, where required
```

Consent or authority for one Edition does not silently authorize a successor Edition.

A newly generated Export Artifact is not automatically authorized.

### Internal Snapshot Manifests remain restricted

The internal Snapshot Manifest contains provenance and omission details not automatically appropriate for any audience package.

It requires a separate protected action and Authorization Decision.

Audience-safe provenance is generated as a distinct reviewed and digested Entry.

### Disclosure events remain separate from issue #9 records

ADR 0007 remains authoritative for Snapshot Issuance and Submission identity.

This decision adds privacy-aware events for actual view, download, delivery, failure, receipt, external review, or future access revocation.

The model preserves:

```text
issuance != delivery
submission != receipt
receipt != review
review != acceptance
```

### Logging is minimum-necessary

Access and disclosure events retain exact references, actor, recipient scope, purpose, channel, time, and outcome as policy requires.

They do not retain:

- source content;
- exported bytes;
- authentication secrets;
- screenshots;
- full identity-provider assertions;
- or unnecessary contact data.

Vitrine records enough information for institutional policy to determine whether a disclosure record is required.

It does not claim that every view is a legally recordable disclosure or that Vitrine alone satisfies every institutional logging obligation.

### Expiration, supersession, and revocation preserve history

Authorization Decisions, Authority Evidence References, Recipient Scopes, and Disclosure Authorizations are immutable.

Changed facts create successors or revocations.

Revocation may restrict future:

- view;
- download;
- issue;
- delivery;
- submission;
- or reuse.

It does not rewrite earlier lawful Disclosure Events or claim that external copies were recalled.

### Mistaken disclosure is preserved as an event

A mistaken disclosure is not deleted from history.

Later institutional response may be referenced through exact incident, containment, or corrective-action records without duplicating the disclosed educational content.

### Producer boundaries remain authoritative

#### Core

Catalog and Publication discovery do not grant source access.

No Core authorization registry is added.

#### ScoreForm

Secure assessment content, answer keys, detector internals, scan diagnostics, raw retained scans, and private paths remain prohibited.

A result disclosure does not establish Grade, proficiency, or official-attempt status.

#### Quillan

Original work, student-facing feedback, private notes, native reviews, and evidence-management records remain distinct.

Vitrine does not parse private Quillan files.

#### Concord

Author, Subject, Group, Group Membership, contribution, representation, privacy, Review, Moderation, and Score targets remain distinct.

Group Membership does not grant disclosure permission.

#### Portia

Ordinary records remain suppressed with no existence leakage.

Only Portia-owned portfolio-safe projections may be evaluated.

Vitrine does not redact raw Portia records into safety.

#### Meridian

Future report authorization remains Meridian-owned.

Vitrine may authorize only exact public report projections copied into its own Snapshot Edition.

### Canonical and derived privacy state remain distinct

Canonical state includes the immutable records named in this decision.

Derived state includes queues, dashboards, safe counts, previews, and disclosure summaries.

A derived row cannot grant access, establish relationship, prove consent, approve redaction, or authorize disclosure.

Missing derived state does not mean no authorization or disclosure history exists.

### No Core change is required

Core already supplies canonical publication identity, exact manifest verification, supersession, withdrawal, and bounded discovery infrastructure.

Vitrine privacy decisions are purpose-, actor-, audience-, recipient-, and Portfolio-specific.

Adding them to Core would:

- centralize domain policy improperly;
- burden unrelated consumers;
- risk conflating publication visibility with disclosure authority;
- and make Core authoritative for institutional facts it does not own.

Vitrine should reference Core records rather than modify them.

## Consequences

### Positive consequences

- Publication discovery can remain useful without becoming a data leak.
- Every allowed or denied action is attributable to exact purpose, target, evidence, and policy.
- Parent, student, teacher, reviewer, regulated, and public audiences can use different content and authority rules.
- Redaction becomes reproducible and reviewable rather than a destructive edit.
- Multi-subject and collaborative artifacts can preserve exact relationships and privacy conditions.
- Snapshot immutability remains intact.
- Consent, relationship, and reviewer changes do not rewrite historical disclosure.
- Producer-private and sensitive Portia boundaries remain enforceable.
- Future institutional identity and delivery integrations have stable reference points.

### Costs and complexity

- More records are required than a simple permissions table.
- Implementations need careful target and revision binding.
- Media redaction requires format-specific contracts and verification.
- De-identification may require human review and institutional expertise.
- Offline/local-first deployments need explicit policy for stale authority evidence and clocks.
- No-leakage behavior makes diagnostics more complex.
- Institutions must supply authoritative identity, relationship, consent, and policy sources.

### Deliberate limitations

This decision does not prove:

- legal guardianship;
- lawful consent;
- FERPA applicability or exception;
- de-identification under every external context;
- secure channel configuration;
- successful delivery;
- external deletion;
- or compliance certification.

Those claims remain with authoritative institutions, policies, and external systems.

## Alternatives considered

### 1. Treat catalog visibility as artifact-access authorization

Rejected.

Catalogs are derived discovery aids and may reveal only safe bounded metadata.

### 2. Use one mutable `can_view` Boolean

Rejected.

It cannot preserve action, purpose, target, recipient, time, conditions, evidence, or history.

### 3. Authorize solely by role name

Rejected.

A role assertion does not prove current assignment, legitimate purpose, subject scope, or recipient authority.

### 4. Give every teacher access to every student record

Rejected.

Teacher access remains class-, assignment-, function-, and purpose-limited.

### 5. Treat a parent/guardian label as self-proving authority

Rejected.

Relationship, rights-holder status, validity, and purpose require authoritative evidence.

### 6. Let Portfolio Subject identity grant access to every related record

Rejected.

Records may include other students, teacher-private information, secure assessment content, or sensitive sources.

### 7. Treat Selection as disclosure consent

Rejected.

Selection is a curation decision, not recipient authorization.

### 8. Treat curation approval as disclosure authorization

Rejected.

Curation review and audience disclosure evaluate different risks and evidence.

### 9. Treat audience class as exact recipient authorization

Rejected.

Audience Context defines content policy; Recipient Scope identifies the recipient context.

### 10. Use one authorization for every action

Rejected.

Discovery, source access, build, issue, delivery, submission, and historical access are distinct.

### 11. Default `indeterminate` to allow

Rejected.

Unresolved authority, relationship, consent, or policy fails closed.

### 12. Return detailed denial reasons to every actor

Rejected.

Detailed reasons may leak suppressed source existence or sensitive categories.

### 13. Assign privacy solely by file type

Rejected.

Privacy depends on content, relationships, purpose, audience, and institutional context.

### 14. Treat name removal as de-identification

Rejected.

Indirect identifiers and outside information can still identify a person.

### 15. Redact producer files in place

Rejected.

Producer records remain authoritative and immutable under producer rules.

### 16. Redact sealed Snapshot Edition files in place

Rejected.

Audience-visible changes require a new Entry and new Edition.

### 17. Record no input or output digest for redaction

Rejected.

Without exact digests, verification and historical reproduction are impossible.

### 18. Use a mutable `redacted = true` flag

Rejected.

Verification must bind exact output bytes, method, reviewer, and findings.

### 19. Infer collaborator permission from Group Membership

Rejected.

Membership, authorship, depiction, contribution, and disclosure authority are separate.

### 20. Infer public permission from directory-information assumptions

Rejected.

Institutional designation, notice, opt-out, purpose, and content context remain external policy facts.

### 21. Apply consent automatically to successor Editions

Rejected.

Changed content and Edition identity require exact scope evaluation.

### 22. Include the internal Snapshot Manifest by default

Rejected.

It may contain restricted provenance, IDs, omission details, and source relationships.

### 23. Let Vitrine redact raw Portia records

Rejected.

Portia owns participant-specific and portfolio-safe projections from its sensitive graph.

### 24. Include Quillan private review records in family packages

Rejected.

Only producer-approved student-facing projections may be considered.

### 25. Disclose ScoreForm answer keys or detector details with result summaries

Rejected.

Those fields remain prohibited secure or operational content.

### 26. Put full educational content in disclosure logs

Rejected.

Logs remain minimum-necessary and reference exact artifacts instead.

### 27. Delete prior disclosure events when consent is withdrawn

Rejected.

Withdrawal affects future use and does not rewrite history.

### 28. Claim revocation recalled external copies

Rejected.

Local future-use restrictions cannot prove external deletion or recall.

### 29. Build a new Core authorization registry

Rejected.

Vitrine authorization is Portfolio- and audience-specific and relies on authority systems outside Core.

## Implementation implications

Later runtime work should introduce contracts and services in this order:

1. exact identifiers and reference primitives;
2. Audience Context and Recipient Scope models;
3. Authority Evidence Reference and Authorization Request models;
4. Authorization Decision and Metadata Visibility Decision models;
5. no-leakage-safe policy evaluation;
6. Protected Access Event storage;
7. Disclosure Review and Finding models;
8. media-specific Redaction Plan and Operation contracts;
9. Redaction Result and Verification contracts;
10. De-identification Review;
11. Disclosure Authorization;
12. Disclosure Event and Revocation;
13. derived queues and audit views;
14. identity/authority integration adapters;
15. snapshot-builder integration;
16. delivery-system integration;
17. and regulated Profile specialization.

Strict low-level writers and higher-level idempotent services should remain separate.

Exact replay must require equality of action, target, actor, recipient, purpose, policy, evidence, and requested scope.

## Validation expectations

Future validation must test at least:

- exact reference consistency;
- actor and target scope agreement;
- Audience Context/Profile agreement;
- Recipient Scope validity and relationship evidence;
- Decision time and expiration;
- conditional requirements;
- no-existence-leakage mappings;
- content-inventory equality for Disclosure Review;
- Redaction Plan canonical digest;
- one outcome per Redaction Operation;
- input/output digest equality;
- Verification output-digest binding;
- De-identification context binding;
- exact Edition and Export Artifact authorization;
- delivery-channel constraints;
- Revocation future-use effects;
- supersession acyclicity;
- and canonical versus derived state separation.

All fixtures must be synthetic.

No test should depend on real student, guardian, employee, consent, or disclosure data.

## Documentation and follow-up

This decision is elaborated by:

- [`../design/privacy-redaction-audience-controls.md`](../design/privacy-redaction-audience-controls.md); and
- [`../examples/privacy-redaction-audience-examples.md`](../examples/privacy-redaction-audience-examples.md).

Issue #11 should consume these generic records when defining regulated Portfolio Profiles.

Future Portia privacy work should provide producer-owned participant-specific projections rather than requiring Vitrine to inspect Portia-native graphs.

Future producer and Meridian work should expose only reviewed public projections and keep internal authorization separate.

## Decision status

This ADR is **Accepted** following the issue #13 portfolio foundation audit.

It becomes governing architecture only after explicit maintainer acceptance.
