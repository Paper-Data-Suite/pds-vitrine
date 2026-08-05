# ADR 0003: Versioned Portfolio Profiles

- **Status:** Proposed
- **Date:** 2026-08-04
- **Decision owners:** Paper Data Suite maintainers
- **Applies to:** `pds-vitrine` v0.1.0 foundation
- **Related issue:** #5, “Define portfolio profiles and versioned requirements”

## Context

Vitrine must support several portfolio families whose rules differ materially.

An improvement Portfolio may require a baseline, later evidence, comparison, and reflection. A showcase Portfolio may require curation, audience-specific rights review, accessibility alternatives, and institutional approval. A parent- or guardian-conference Portfolio may require representative evidence, plain-language context, translation, and a dated packet. A regulated Portfolio may require jurisdiction- and cohort-specific evidence, attestations, deadlines, retention, and externally controlled outcomes.

These differences cannot be represented safely through one universal Portfolio schema or a small purpose flag. The governing rules must remain explicit, purpose-specific, attributable, and versioned.

The existing Vitrine architecture establishes that:

- Vitrine owns portfolio-specific policy and curation records;
- Core owns neutral registration, publication, compatibility, and discovery infrastructure;
- producer modules own source meaning;
- Meridian owns grading and formal academic reporting;
- institutions own authorization, approval, consent, retention classification, and disposition;
- and external authorities own regulated acceptance and final outcomes.

Core supplies useful revision precedents: stable logical series identity, immutable revisions, explicit predecessors, supersession and withdrawal, exact replay, and no inference of current authority from the largest revision or newest timestamp. Core Standards Profiles and publication producer compatibility Profiles are separate Core concepts and are not suitable as Portfolio Profiles.

Meridian likewise requires explicit versioned policy before producer evidence contributes to a calculated result. A Vitrine Profile follows the same separation principle while governing portfolio policy rather than grading.

Vitrine also needs a precise relationship between a Portfolio and the rules under which it is curated. Binding only to an unversioned Profile name would make historical requirement findings and issued snapshots irreproducible.

## Decision

### Model Profile Family, Profile series, and Profile revision separately

Vitrine will model three distinct concepts:

1. **Portfolio Profile Family** — a durable, non-rule-bearing grouping for related Profile series.
2. **Portfolio Profile series** — one independently versioned logical policy with a stable `portfolio_profile_id`.
3. **Portfolio Profile Revision** — one immutable complete rule set identified by `portfolio_profile_id + profile_revision`.

The Family groups related policies such as standard and streamlined pathways. It does not supply inherited rules and does not determine which Profile is current.

A Profile series represents one coherent purpose, program, pathway or variant, and controlling authority. Simultaneously valid alternatives are separate series or explicit variants, not sequential revisions unless one truly supersedes the other.

### Use stable non-revisioned series identity

`portfolio_profile_id` is stable across revisions of the same logical policy. It does not contain a revision number and is never reused for a different semantic Profile.

The complete revision identity is:

```text
portfolio_profile_id + profile_revision
```

The following remain distinct:

```text
Profile contract version
Portfolio Profile Family ID
portfolio_profile_id
profile_revision
program version
source-authority version
school year
cohort
effective dates
Portfolio identity
Portfolio Profile Binding identity
snapshot edition
application package version
```

No one of these values allocates or implies another.

### Make activated revisions immutable

An activated Profile revision is immutable.

Any change that affects operational meaning creates a new revision, including changes to:

- applicability;
- purpose;
- audience rules;
- section structure;
- requirement identity or obligation;
- conditions;
- counts;
- source restrictions;
- selection policy;
- reflection policy;
- approvals;
- retention references;
- deadlines;
- output classification;
- or source-authority interpretation.

Mutable drafts may exist before activation, but they are not operative Profile revisions and cannot be bound to operational Portfolios.

### Use append-preserving lifecycle events

Profile lifecycle is represented by append-preserving events rather than a mutable status field alone.

The conceptual event vocabulary is:

```text
activated
deprecated
superseded
withdrawn
retired
```

An event identifies the exact revision, actor or authority, event and effective times, reason, and predecessor or successor where applicable.

Current operational use is resolved from canonical lifecycle events and explicit policy, never from:

- largest revision;
- newest timestamp;
- filename;
- directory order;
- or a mutable `latest` pointer.

### Bind each Portfolio to one exact Profile revision

For v0.1.0:

```text
one Portfolio -> exactly one active Portfolio Profile Binding
one Profile revision -> zero or many Portfolios
```

The Portfolio Profile Binding is a durable record with its own identity. It connects one Portfolio to one exact Profile revision and records attribution, time, rationale or authority, lifecycle, and predecessor binding where migration occurs.

Binding endpoints are immutable after operational use.

A Profile change does not modify the existing binding automatically.

### Require explicit migration

A working Portfolio may move to a new Profile revision only through an explicit successor binding.

Migration must:

- identify the old and new revisions;
- compare stable requirement IDs;
- classify requirements as unchanged, added, removed, or materially changed;
- preserve prior selections, reflections, approvals, and findings;
- identify unresolved migration effects;
- require reapproval where the new Profile says it is necessary;
- and record actor, time, and rationale.

Existing content is not automatically declared valid under the new Profile.

An issued snapshot remains permanently associated with the exact Profile revision and audience rule used at issuance.

### Define purpose as controlled vocabulary plus explicit policy

The initial purpose kinds are:

```text
improvement
showcase
parent_guardian_conference
regulated
```

Purpose kind is classification only. It does not expand into hidden universal requirements.

Each Profile revision carries its own purpose statement, intended outcome, applicability, rules, and authority metadata.

### Use stable requirement identity

Every operational requirement has a stable `requirement_id` within the Profile series.

A requirement ID remains stable across revisions only when semantic continuity is preserved. Materially different meaning receives a new ID. Replacements and supersession remain explicit.

The supported obligation vocabulary is:

```text
required
optional
conditional
prohibited
```

A prohibited item is not equivalent to an absent optional item.

### Use bounded three-valued declarative conditions

Conditional requirements use a bounded declarative condition model rather than arbitrary executable code.

Conditions may combine named predicates through approved operators such as:

```text
all
any
not
```

Predicates may reference explicit Profile context, selected variant, audience rule, content area, cohort, named external finding, human-verification state, or another requirement finding when acyclic.

Evaluation produces:

```text
true
false
unknown
```

Unknown never silently becomes false, not applicable, satisfied, or waived.

Condition dependency cycles are invalid.

### Separate requirement definitions from findings

A Profile requirement describes policy.

A requirement finding describes the result of evaluating that requirement against one Portfolio state.

A completeness summary is derived from findings. It is not an approval, authorization, legal conclusion, submission, or external outcome.

### Represent audience rules without granting access

A Profile may define named audience rules such as student, teacher-internal, parent/guardian, institutional reviewer, external reviewer, regulated submission, and public.

An audience rule declares intended purpose, output restrictions, reviews, accessibility, translation, redaction, rights, and approval requirements.

Selecting an audience rule does not authenticate recipients, verify guardian relationships, establish consent, authorize disclosure, or grant source access.

### Represent approval stages without fabricating approvals

A Profile may define review and approval stages, sequencing, actor roles, quorum, separation of duties, acknowledgments, consent references, signatures, attestations, privacy review, accessibility review, records review, or institutional approval.

The Profile defines what is required. Actual approvals are separate actor-authored records governed by later contracts and authoritative systems.

### Represent retention through references and unresolved classification

A Profile may identify record classes, authoritative schedule references, schedule versions, trigger rules, minimum periods, permanent status, holds, transfer expectations, and disposition-approval requirements.

A Profile cannot classify every Vitrine object unilaterally, delete upstream records, bypass legal holds, or authorize autonomous destruction.

Disposition remains an institutional or future archival-system action.

### Flatten composition and local overlays

Activated Profile revisions do not inherit dynamically from mutable parents.

Composition follows this pattern:

1. reference exact immutable component revisions;
2. validate applicability and authority;
3. detect conflicts;
4. flatten the resolved rules into one complete effective Profile revision;
5. preserve component identities and digests;
6. attribute composition;
7. and activate the composed revision explicitly.

Local overlays are explicit, versioned, attributable, authority-bounded inputs to composition.

Conflicts never use silent last-write-wins behavior.

### Use no blocking Core change

Vitrine can define and own Portfolio Profiles within its workspace-scoped namespace using existing Core identifier conventions where useful.

No new Core Profile type, publication kind, or global policy registry is required for this foundation issue.

Core Standards Profiles, Core producer compatibility Profiles, and Meridian grading policies remain separate authoritative concepts.

### Keep regulated Profiles as a later specialization

This ADR establishes generic extension points for jurisdiction, program, cohort, authority sources, eligibility conditions, documents, approvals, deadlines, local retention, external submission, and outcome references.

It does not activate or encode the New Jersey Graduation Portfolio Appeal as an operational Profile. That work remains assigned to issue #11 and must revalidate current public, restricted, and local authorities.

## Consequences

### Positive consequences

- Portfolio purpose and requirements are explicit rather than inferred.
- Historical findings and issued snapshots remain reproducible.
- Simultaneous pathways are not confused with revisions.
- Profiles can span instructional, showcase, conference, and regulated families.
- Requirements retain stable identity across compatible revisions.
- Unknown conditions remain visible.
- Profile changes require deliberate migration.
- Audience declarations cannot become accidental authorization grants.
- Approval and compliance claims remain with the correct actors.
- Retention remains policy-referenced without autonomous deletion.
- Local overlays cannot mutate historical parent policy.
- Later New Jersey Profiles can use generic extension points without becoming universal behavior.

### Costs and limitations

- Profile authoring and activation require explicit governance.
- A working Portfolio may remain on an older revision until migrated.
- Several active variants may coexist.
- Migration requires impact analysis and possible reapproval.
- Stable requirement IDs require editorial discipline.
- Three-valued conditions require more careful evaluation than booleans.
- Flattened composition duplicates effective rules by design.
- External or restricted sources may leave a Profile incomplete.
- The foundation does not yet implement a Profile editor, evaluator, or storage contract.

### Security and privacy consequences

- Profile metadata cannot substitute for authorization.
- Profiles must not contain credentials, signatures, restricted portal secrets, or real student data.
- Source-class eligibility must not reveal sensitive Portia presence.
- Public and family audience rules require later recipient, consent, redaction, and rights controls.
- Conditions must not execute arbitrary code.
- Profile error messages must not claim legal noncompliance or external rejection.

## Rejected alternatives

### One universal Portfolio schema with hard-coded requirements

Rejected because researched portfolio families have materially different purposes, actors, sections, evidence, approvals, audiences, and retention treatment.

### Treat purpose kind as the complete Profile

Rejected because two Profiles with the same purpose may require different sections, authorities, audiences, source restrictions, approvals, and output rules.

### Edit an activated Profile revision in place

Rejected because historical Portfolio evaluation and issued snapshots would become irreproducible.

### Select current revision by greatest number or newest time

Rejected because revision gaps, withdrawn heads, parallel variants, and correction workflows make ordering insufficient authority.

### Bind a Portfolio to only an unversioned Profile ID

Rejected because later rule changes would silently alter historical meaning.

### Silently upgrade every Portfolio to the latest Profile

Rejected because migration may introduce new requirements, invalidate old selections, require new approvals, or change applicability.

### Treat a simultaneous pathway as a later revision

Rejected because standard and streamlined or content-area pathways may remain valid at the same time.

### Reuse Core Standards Profiles

Rejected because Core Standards Profiles group academic standards and do not own portfolio purpose, audience, sections, approvals, or retention.

### Reuse Core publication producer compatibility Profiles

Rejected because compatibility Profiles describe producer contracts and capabilities, not portfolio eligibility or workflow policy.

### Reuse Meridian grading policies

Rejected because Meridian policies govern grading and proficiency rather than portfolio curation and issuance.

### Dynamic inheritance from mutable parent Profiles

Rejected because parent changes would silently mutate activated child behavior.

### Silent last-write-wins overlays

Rejected because conflicts may weaken controlling requirements or create ambiguous policy.

### Treat audience declaration as authorization

Rejected because recipient identity, consent, legitimate educational interest, disclosure basis, and source access remain separate.

### Treat requirement completeness as approval or compliance

Rejected because machine-checkable presence does not establish human approval, legal conclusion, submission, or external acceptance.

### Encode current New Jersey rules as universal behavior

Rejected because regulated rules are jurisdiction-, program-, cohort-, source-, and time-specific and include restricted operational material.

### Allow Profile retention rules to delete upstream records

Rejected because Vitrine does not own Core or producer records and is not the records-disposition authority.

### Use arbitrary executable condition code

Rejected because it creates security, reproducibility, portability, audit, and versioning risks.

### Treat missing condition data as false or not applicable

Rejected because unavailable or restricted facts can be material and require explicit unresolved handling.

## Validation requirements

Later serialized contracts and implementation must verify:

- stable and unique Profile family, series, revision, lifecycle-event, and binding identities;
- exact revision references;
- immutable activated content;
- explicit predecessor relationships;
- no contradictory logical revision reuse;
- no inference of current authority from ordering;
- one active Profile binding per Portfolio;
- stable and unique requirement IDs;
- valid obligation vocabulary;
- acyclic bounded conditions;
- explicit unknown propagation;
- valid section and rule references;
- no duplicate or contradictory audience-rule IDs;
- no unresolved composition conflicts;
- no dynamic parent dependencies;
- explicit migration impact;
- preserved historical bindings;
- and separation among completeness, approval, issuance, submission, and outcome.

## Required follow-up

- Issue #6 defines candidate and source-reference contracts.
- Issue #7 defines producer artifact exposure boundaries.
- Issue #8 defines selection, ordering, annotation, reflection, and approval records.
- Issue #9 defines snapshot, checksum, export, and immutability contracts.
- Issue #10 defines privacy, redaction, recipient, and audience enforcement.
- Issue #11 defines regulated compliance Profiles, including the researched New Jersey family.
- Later implementation work must define exact schemas, storage, authoring, activation, evaluation, migration, and audit services.

## References

- [Portfolio purposes and workflows](../research/portfolio-purpose-workflows.md)
- [Compliance and policy constraints](../research/compliance-constraints.md)
- [New Jersey Graduation Portfolio Appeal research](../research/new-jersey-graduation-portfolio-appeal.md)
- [Module boundaries and authority](../architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](../design/portfolio-subject-identity.md)
- [Versioned Portfolio Profile design](../design/portfolio-profile-contract.md)
- [Representative Portfolio Profile examples](../examples/portfolio-profile-examples.md)
