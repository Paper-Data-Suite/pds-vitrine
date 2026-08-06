# ADR 0009: Regulated Portfolio and Compliance Profiles

- **Status:** Accepted
- **Date:** 2026-08-05
- **Accepted:** 2026-08-06 — approved by issue #13 portfolio foundation audit
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #11, “Define regulated portfolio/compliance profiles”
- **Related design:** [`../design/regulated-portfolio-compliance-profiles.md`](../design/regulated-portfolio-compliance-profiles.md)
- **Related examples:** [`../examples/regulated-portfolio-compliance-examples.md`](../examples/regulated-portfolio-compliance-examples.md)
- **Related research:** [`../research/new-jersey-graduation-portfolio-appeal.md`](../research/new-jersey-graduation-portfolio-appeal.md)

## Context

Vitrine already has conceptual contracts for:

- immutable Portfolio Profile families, series, revisions, Bindings, requirements, audience rules, approvals, retention references, and migration;
- Candidate discovery and exact source references;
- producer-approved exposure;
- Selection, Placement, ordering, Annotation, Reflection, and exact Composition Revisions;
- immutable Snapshot Series, Editions, Entries, manifests, checksums, Export Artifacts, Issuance, and Submission;
- action- and purpose-specific authorization;
- Audience Context and Recipient Scope;
- redaction and de-identification;
- and append-preserving disclosure history.

Those contracts provide the general machinery needed for regulated workflows, but they do not yet define:

- how a regulated Profile records exact authority sources;
- how research-only and operational Profiles differ;
- how one subject's regulated case is represented;
- how independently evaluated components and pathways work;
- how versioned checklists produce immutable findings;
- how supporting-record presence, validity, and satisfaction remain distinct;
- how missing and defective records are represented;
- how attestations, signatures, and verification remain distinct from approval;
- how deadlines, extensions, and late findings are represented;
- how institutional approvals bind exact target revisions;
- how local student case files remain distinct from school-level submission batches;
- how rolling and corrected submissions preserve history;
- or how external receipts and outcomes remain authority-owned.

The New Jersey Graduation Portfolio Appeal provides a useful researched example.

The Class of 2026 public guidance demonstrates:

- separate ELA and mathematics components;
- independently selectable graduation pathways by component;
- standard and streamlined Portfolio Appeal alternatives;
- local retention of substantive student evidence;
- school-specific external submission of a Statement of Assurance and data spreadsheet;
- rolling additions and corrected resubmissions;
- restricted Homeroom forms and field definitions;
- and external receipts and outcome letters.

The complete Class of 2027 Portfolio Appeal policy is not established by the reviewed Class of 2026 sources. The later public appeal window and NJGPA-Adaptive transition are future-cohort concerns, not permission to reuse prior rules.

A regulated workflow cannot be represented safely by:

```text
regulated = true
checklist_complete = true
approved = true
```

Those flags would erase exact authority, source versions, components, evidence, signer authority, deadlines, submissions, and external outcomes.

## Decision

Vitrine will model regulated Portfolio policy as an immutable specialization of the existing Portfolio Profile Revision.

It will not create a parallel Profile identity system.

The regulated specialization will use separate immutable or append-preserving records for:

1. Regulated Profile Specification;
2. Authority Source Set and Authority Source Entries;
3. Regulated Portfolio Case;
4. Case Components;
5. Pathway Definitions and Pathway Selections;
6. Eligibility and Applicability Findings;
7. Regulated Checklist Definitions and Checklist Item Findings;
8. Supporting Record Requirements and Supporting Record Instances;
9. Missing or Defective Record Findings;
10. Attestation Requirements, Attestation Records, and Attestation Verification Decisions;
11. Deadline Rules, Deadline Instances, and Deadline Extensions;
12. Approval Stage Definitions and Regulated Approval Decisions;
13. Submission Readiness Findings;
14. Submission Batches and Case-to-Batch Memberships;
15. Generated Submission Projections;
16. immutable Submissions, Receipts, and External Outcome References;
17. lifecycle, correction, and migration records;
18. and rebuildable workflow views.

The governing sequence is:

```text
exact Profile revision
  -> activated Regulated Profile Specification
  -> Regulated Portfolio Case
  -> independent Case Components
  -> explicit Pathway Selection
  -> Eligibility Findings
  -> Supporting Record Instances
  -> Checklist Item Findings
  -> Attestations and verification
  -> staged Approval Decisions
  -> Submission Readiness Finding
  -> Submission Batch
  -> exact Snapshot Edition / Export Artifacts
  -> Submission
  -> Receipt
  -> External Outcome
```

No stage is implied by the prior stage.

## Decision details

### Regulated policy extends the generic Profile contract

A regulated Profile is an ordinary Vitrine Portfolio Profile revision with:

```text
purpose_kind = regulated
```

and one exact Regulated Profile Specification.

It reuses:

- Profile Family and series identity;
- immutable revision rules;
- lifecycle events;
- exact Portfolio Profile Binding;
- bounded conditions;
- stable requirement identity;
- Audience Rules;
- Approval Stage patterns;
- Retention Rules;
- flattened composition;
- local overlays;
- and explicit migration.

### Research-only and operational Profiles are distinct

A researched example may document:

- a program family;
- apparent public requirements;
- authority sources;
- structural mappings;
- and unresolved restricted dependencies.

It is not operational.

Operational activation requires:

- exact cohort and effective dates;
- current public sources;
- required restricted-source review;
- local policy review;
- current forms and templates;
- explicit institutional approval;
- and an activation event.

### Authority sources are immutable and attributable

Each activated regulated Profile revision references one immutable Authority Source Set.

The set distinguishes:

```text
public_source
restricted_portal_source
local_policy_source
institutional_decision
```

Every source entry preserves exact identity, version or publication date, review time, applicability, verification status, and distribution restrictions.

Required unresolved, stale, conflicting, or unknown sources may block activation.

### Current policy is never inferred from recency alone

Vitrine will not choose an operational Profile because it has:

- the largest revision;
- the newest source date;
- the newest filename;
- or the latest web-page retrieval time.

Activation and lifecycle remain explicit.

### Program version, Profile revision, cohort, and school year remain distinct

The following identities are independent:

```text
portfolio_profile_id
profile_revision
regulated_program_id
program_version
school_year
cohort
assessment_program
assessment_version
pathway_variant
effective_dates
```

A change to one may require—but does not automatically allocate—a change to another.

### Cases bind exact Profile revisions

Every Regulated Portfolio Case binds:

- one Portfolio;
- one Portfolio Subject;
- one exact Portfolio Profile Binding;
- one regulated Profile revision;
- one institution/responsible-office context;
- one cohort and school-year context;
- and one append-preserving lifecycle.

Case identity does not encode student names, identifiers, pathway, or outcome.

### Components are independently evaluable

A regulated case may have several components.

Each component preserves its own:

- applicability;
- pathway;
- eligibility;
- evidence;
- checklist findings;
- approvals;
- readiness;
- submissions;
- receipts;
- and outcomes.

The New Jersey reference family requires separate ELA and mathematics components.

### Pathway selection is explicit

A pathway definition is Profile policy.

A Pathway Selection is a case record.

Standard and streamlined pathways are simultaneous alternatives, not sequential revisions solely because they require different evidence quantities.

Vitrine must not choose the pathway requiring fewer records automatically.

### Recommended New Jersey pathway structure

The recommended reference structure is:

```text
one Profile Family
  -> standard pathway Profile series
  -> streamlined pathway Profile series

each series
  -> immutable cohort / school-year revisions
```

A composed-variant design remains possible if it preserves independent identity, versioning, explicit selection, and no false current-pathway inference.

### Eligibility findings are evidence-backed and three-valued in practice

Eligibility outcomes are:

```text
eligible
not_eligible
conditional
indeterminate
expired
```

Eligibility remains distinct from checklist completion, institutional approval, and external outcome.

`indeterminate` fails closed.

### Checklists are versioned policy

A Regulated Checklist Definition is immutable and Profile-owned.

A Checklist Item Finding is a separate evaluation against one exact target state.

The design distinguishes:

```text
requirement result
record presence
record validation
```

A user-interface checkbox is never canonical evidence.

### Checklist completion is derived

Completeness is calculated from exact immutable findings.

Completeness is not:

- an approval;
- a legal conclusion;
- a Submission;
- a Receipt;
- or an External Outcome.

### Supporting-record presence, validity, and satisfaction remain distinct

A record can be:

- present but stale;
- present but mismatched;
- present and verified but insufficient;
- unavailable;
- withheld;
- superseded;
- or missing.

The design never treats existence as satisfaction.

### Missing evidence is a finding

A missing or defective record is represented through an exact finding.

Vitrine will not create blank placeholder documents merely to satisfy file-count logic.

### Unknown and unavailable remain explicit

Unknown is not converted to:

- absent;
- not applicable;
- waived;
- satisfied;
- approved;
- or accepted.

### Waivers require exact authority

A waived requirement must identify:

- the exact requirement;
- exact target;
- authority;
- decision actor;
- policy basis;
- effective time;
- and conditions.

The absence of evidence is never an implicit waiver.

### Attestations are versioned actor assertions

An Attestation Requirement defines the exact statement, signer roles, count, sequence, separation of duties, signature methods, authority evidence, validity, and invalidation triggers.

An Attestation Record binds:

- exact statement revision;
- exact target revision;
- exact signer;
- asserted role;
- authority evidence;
- signing time;
- and signed-document reference/digest where applicable.

### Signature presence is not verification

A signature image does not prove identity, role, authority, intent, or document integrity.

Verification is a separate immutable Decision bound to the exact attestation and reviewed bytes or authoritative reference.

### Attestation and approval remain distinct

An attestation records an assertion.

An approval records a decision.

Neither implies the other.

### Deadlines are immutable Profile rules

Deadline Rules preserve:

- authority source;
- absolute or relative calculation;
- timezone;
- applicable scope;
- recommended, internal-required, or external-final classification;
- extension authority;
- and late effect.

Case-specific Deadline Instances preserve exact calculation inputs and extensions.

### Deadline passage does not fabricate external consequences

A passed deadline may create a `past_due` finding.

It does not independently establish ineligibility, denial, or waiver.

### Extensions require authoritative evidence

A local actor cannot invent an external extension.

Every extension binds exact authority and evidence.

### Approvals are staged and exact-target

Profiles may define evidence, content-area, privacy, accessibility, records, school, and institutional submission approval stages.

Each Approval Decision binds one exact immutable target.

Material changes require reevaluation according to Profile reapproval rules.

### Submission readiness is a separate evaluation

Readiness evaluates exact:

- eligibility;
- checklist findings;
- supporting-record findings;
- attestations;
- deadlines;
- approvals;
- authorization;
- privacy/redaction;
- accessibility;
- and Snapshot/export state.

Readiness is not approval, submission, receipt, or acceptance.

### Student cases and submission batches remain distinct

A Regulated Portfolio Case represents one subject's workflow.

A Submission Batch represents one institution-, school-, program-, or authority-scoped handoff.

One batch may contain several cases.

One case may enter several rolling or corrected submissions.

### Generated external rows are projections

A spreadsheet row or structured external record is generated from exact case/component facts under one exact field-rule version.

It preserves per-field provenance and a digest.

It is not the canonical case record.

### Restricted field definitions are referenced

When external field definitions are restricted:

- an authorized reviewer verifies the exact version or digest;
- the Profile references that verification;
- public repository examples remain synthetic;
- and operational activation is blocked where the required definition is unavailable.

### Submissions are immutable

Changed submitted bytes create:

- a new Export Artifact;
- a new Submission;
- an explicit predecessor or correction relationship;
- and preserved earlier history.

Prior uploads and receipts are never overwritten.

### Submission, Receipt, and External Outcome remain distinct

```text
Submission
  != Receipt
  != External Outcome
```

A local upload success does not fabricate a receipt.

A receipt does not establish external approval.

### External raw outcomes remain authoritative

Vitrine preserves the authority-native outcome and may record a bounded normalized mapping.

The normalized mapping never broadens the external meaning.

### Partial component outcomes are supported

One external outcome may approve ELA while mathematics remains pending, denied, or returned for correction.

### Profile migration is explicit

Migration compares:

- components;
- pathways;
- eligibility;
- checklists;
- supporting-record requirements;
- deadlines;
- attestations;
- approvals;
- batch rules;
- and outcomes.

It preserves prior cases and findings and does not declare prior evidence valid under the successor Profile automatically.

### Historical packages remain exact

A historical Snapshot Edition, Export Artifact, Submission, Receipt, and Outcome remains bound to the original Profile revision.

A later Profile or case correction does not rewrite historical issued or submitted bytes.

### Minimum-necessary sensitive evidence

Regulated purpose does not justify importing complete sensitive source records.

Where accommodation or special-population evidence is required, Vitrine records the minimum necessary bounded finding and exact authority reference.

### Producer authority remains unchanged

Core remains neutral infrastructure.

ScoreForm, Quillan, Concord, Portia, and Meridian remain authoritative for their own records and meanings.

No producer output becomes regulated evidence without an exact Profile rule, exact authorized projection, and exact finding.

### No Core change is required

Vitrine can own regulated Profile and case identity within its existing namespace.

Core does not need a compliance registry, regulated Profile kind, approval service, or outcome registry.

## New Jersey reference-family decision

### Reference status

The Class of 2026 / 2025–2026 New Jersey Graduation Portfolio Appeal is documented as a research-only reference family.

It is not activated operationally.

### Component structure

The reference family preserves separate:

```text
english_language_arts
mathematics
```

components.

### Pathway structure

It preserves separate standard and streamlined alternatives.

The streamlined selection requires exact qualifying ASVAB AFQT evidence under the exact Profile rule.

### Local and external layers

The reference family distinguishes:

```text
student case
  != locally retained evidence
  != school submission batch
  != student row
  != Statement of Assurance
  != data spreadsheet
  != Submission
  != Receipt
  != Outcome
```

### Restricted-source dependency

An operational Profile cannot be activated solely from public guidance.

It requires review of exact restricted:

- Statement of Assurance;
- data spreadsheet;
- field definitions;
- Homeroom validation behavior;
- receipt behavior;
- and outcome retrieval.

### Local overlay

Local policy may add earlier deadlines, assigned actors, task-development procedures, review stages, custody, and retention.

A local overlay may not silently weaken state requirements.

### Future cohort boundary

Class of 2026 rules do not apply automatically to Class of 2027.

The 2026–2027 public appeal window and NJGPA-Adaptive transition require separate source review and a new or successor Profile revision.

## Consequences

### Positive consequences

- Regulated workflows reuse the existing Profile architecture.
- Authority sources are attributable and versioned.
- Research examples cannot masquerade as active policy.
- Cases remain reproducible under exact Profile revisions.
- Components and pathways remain independent.
- Missing and invalid evidence remain distinguishable.
- Attestations, approvals, submissions, and outcomes retain correct authority.
- Rolling and corrected submissions preserve history.
- External authority is not fabricated.
- Sensitive evidence remains minimum necessary.
- Producer responsibilities remain stable.
- Future regulated programs can reuse the same contracts.

### Costs and limitations

- Profile activation requires substantial source and institutional review.
- Restricted sources may block activation.
- Checklists require editorial discipline and stable IDs.
- Multiple component and pathway states increase workflow complexity.
- Attestation and approval records require exact target revisioning.
- External spreadsheet integration requires versioned field rules.
- Staff must understand local versus external authority.
- Migration may require reevaluation, reattestation, and reapproval.
- The foundation does not implement runtime behavior.

### Security and privacy consequences

- Profile definitions must remain free of student data.
- Restricted templates and portal details must not be committed publicly.
- Case and batch identifiers must be opaque.
- Sensitive evidence requires issue #10 authorization.
- Portia no-leakage behavior remains mandatory.
- Logs must not contain complete educational documents.
- Signature records do not claim cryptographic or legal validity.
- Checksums remain integrity evidence, not authorization.

## Rejected alternatives

### One permanent `new_jersey_portfolio` ruleset

Rejected because cohort, school year, assessment program, forms, dates, thresholds, guidance, and restricted submission contracts change independently.

### One universal regulated checklist

Rejected because different programs, components, pathways, institutions, and cohorts require materially different evidence and decisions.

### A `regulated=true` flag as the entire model

Rejected because it cannot represent authority sources, cases, pathways, records, findings, attestations, deadlines, batches, submissions, or outcomes.

### Editing an activated regulated Profile in place

Rejected because historical cases, findings, packages, and submissions would become irreproducible.

### Selecting current policy by newest date

Rejected because publication date or retrieval time does not establish activation authority.

### Copying one cohort's rules into another automatically

Rejected because future cohorts may use different assessment programs, forms, dates, thresholds, and authority sources.

### Treating standard and streamlined pathways as sequential revisions

Rejected because they may be simultaneously valid alternatives.

### One undifferentiated status for ELA and mathematics

Rejected because component pathways, evidence, approvals, and outcomes may differ.

### Mutable checkboxes as canonical compliance evidence

Rejected because they erase evaluator, exact target, evidence, time, and historical correction.

### Document filename as document identity

Rejected because names can be reused or changed independently of authoritative content identity.

### Document presence as document validity

Rejected because a present record may be stale, invalid, mismatched, or superseded.

### Document validity as requirement satisfaction

Rejected because a valid record may not satisfy the exact Profile rule.

### Empty placeholder files for missing evidence

Rejected because they create false content and corrupt provenance.

### Unknown evidence treated as absent or waived

Rejected because uncertainty must remain explicit and fail closed.

### Attestation represented as a Boolean

Rejected because exact statement, signer, authority, target, time, method, and verification are required.

### Signature image treated as verified authority

Rejected because an image alone proves none of the required identity or authority facts.

### Attestation treated as approval

Rejected because assertion and decision are different acts.

### Checklist completion treated as institutional approval

Rejected because completeness does not create actor authority or a decision.

### Local approval treated as external acceptance

Rejected because the external authority owns its outcome.

### Deadline passage treated as automatic denial

Rejected because late consequences require exact authority and may include extensions or later review.

### Local users creating external extensions without evidence

Rejected because external deadline authority remains external.

### One object for student case and school submission batch

Rejected because one batch may contain several cases and one case may appear in several submissions.

### Mutating a prior upload for resubmission

Rejected because submitted bytes and receipts must remain historically exact.

### Spreadsheet rows treated as canonical cases

Rejected because they are format-specific external projections.

### Submission success treated as receipt

Rejected because the external system owns receipt issuance.

### Receipt treated as external approval

Rejected because acknowledgment and substantive decision are different.

### Normalizing away the raw external outcome

Rejected because Vitrine's interpretation cannot replace authority-native meaning.

### Embedding restricted portal templates in the repository

Rejected because access and redistribution may be restricted and the content may contain operational details.

### Storing complete IEP or sensitive records for a bounded accommodation finding

Rejected because minimum-necessary evidence is required.

### Automatically accepting any producer output as regulated evidence

Rejected because producer meaning and regulated satisfaction are distinct.

### Using Portia records merely because the workflow is regulated

Rejected because regulated purpose does not override suppression or authorization.

### A new Core compliance registry

Rejected because regulated policy and execution are Vitrine-owned and do not require neutral global registration.

## Follow-up requirements

Later implementation must:

1. define exact schemas and contract versions;
2. define Profile activation and source-verification workflows;
3. define canonical storage and guarded current pointers;
4. define deterministic checklist and deadline evaluation;
5. define exact authority and signer integrations;
6. define restricted field-definition loading;
7. define batch generation and validation;
8. define external receipt/outcome import;
9. add installed synthetic acceptance;
10. and separately review any operational New Jersey Profile.

## References

- [Regulated Portfolio and compliance design](../design/regulated-portfolio-compliance-profiles.md)
- [Representative regulated Portfolio examples](../examples/regulated-portfolio-compliance-examples.md)
- [Versioned Portfolio Profile design](../design/portfolio-profile-contract.md)
- [Snapshot, export, checksum, and immutability design](../design/snapshot-export-immutability-contracts.md)
- [Privacy, redaction, and audience-control design](../design/privacy-redaction-audience-controls.md)
- [New Jersey Graduation Portfolio Appeal research](../research/new-jersey-graduation-portfolio-appeal.md)
- [Source register](../research/source-register.md)
