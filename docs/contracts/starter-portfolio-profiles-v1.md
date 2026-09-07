# Starter Portfolio Profiles v1

## Status and scope

This document freezes the Vitrine issue #63 contract for optional packaged
starter Portfolio Profiles. It extends the existing Portfolio Profile workflow
contract without changing its authority or lifecycle semantics.

The contract versions are:

```text
vitrine_starter_profile_catalog_v1
vitrine_starter_profile_pack_v1
```

The catalog contains exactly two initial packs, in deterministic order:

```text
improvement_portfolio_v1
showcase_portfolio_v1
```

Starter packs are convenience content. They are not new canonical Vitrine
record types and they are not hidden behavior attached to a Profile purpose.

## Authority boundary

`purpose_kind` remains classification only. Selecting `improvement` or
`showcase` never creates sections, Requirements, audience rules, lifecycle
events, evidence selections, or Bindings.

A packaged starter is Vitrine-owned general guidance. It is not school,
district, state, regulatory, grading, proficiency, retention, disclosure, or
legal policy. A starter audience rule is Profile policy metadata; it is not
source-read authority and does not authorize disclosure.

Starter Requirements describe explicit Portfolio policy. They are not findings
that evidence satisfies the policy, and they do not constitute grading or
proficiency conclusions.

## Durable result

Installation reuses the ordinary Profile architecture:

```text
PortfolioProfileFamily
-> PortfolioProfileRevision
-> PortfolioProfileRequirement[]
-> PortfolioProfileLifecycleEvent(event_kind = activated)
```

No canonical records named `StarterProfileRecord`, `InstalledStarterRecord`,
`StarterBinding`, or `StarterProfileUsage` exist. Installation does not create a
Portfolio, Profile Binding, Candidate, Selection, Snapshot, or producer record.

Installed starter records are visible through the ordinary Profile APIs and
remain subject to the ordinary immutable-revision and lifecycle rules.

## Frozen identities

The initial Improvement starter uses:

```text
pack: improvement_portfolio_v1
family: vitrine_starter_improvement_family
profile series: vitrine_starter_improvement
revision: 1
predecessor: none
```

The initial Showcase starter uses:

```text
pack: showcase_portfolio_v1
family: vitrine_starter_showcase_family
profile series: vitrine_starter_showcase
revision: 1
predecessor: none
```

Future packaged starter revisions must use ordinary predecessor, lifecycle,
composition, overlay, and migration semantics. A higher starter revision is not
automatically newer, current, preferred, activated, or migrated into existing
Portfolios.

## Deterministic authored provenance

Packaged Family and Revision records use deterministic Vitrine catalog
authorship:

```text
actor_kind: system
actor_id: vitrine_starter_profile_catalog
owning_system: vitrine
role_snapshot: starter_profile_author
source authority: vitrine_starter_profile_catalog_v1
```

The authored timestamp is fixed in the package. Installation must not rewrite
this provenance with the installing teacher's identity or current time.

Operational acceptance is separate. When activation is required, the lifecycle
event records the installing actor, activation time, reason, and explicit local
authority/reference.

## Catalog and pack reads

Catalog list, pack retrieval, and pack validation are read-only package-resource
operations. They must not resolve or mutate a workspace, create canonical
storage, import sibling producer packages, or contact producer data sources.

Pack validation must use the ordinary Profile aggregate rules and additionally
freeze catalog/pack identity, deterministic provenance, exact initial revision,
Requirement identity, producer-neutral Candidate vocabulary, known limitations,
and catalog consistency.

## Installation planning

Planning is a read-only comparison between one exact packaged aggregate and the
current canonical Profile state. Every Family, Revision, and Requirement is
classified as one of:

```text
create
reuse_exact
conflict
```

The exact starter lifecycle plan is one of:

```text
activate_new
activate_existing_exact
already_active
lifecycle_conflict
```

A stable Profile series collision, immutable-content difference, unexpected
Requirement, or incompatible lifecycle state is reported rather than repaired.
Planning never writes canonical state.

## Installation transaction

Installation is an explicit teacher action after review and confirmation. The
installer must:

1. compare the observed state revision with the caller's expected revision;
2. reject immutable or lifecycle conflicts without writing;
3. construct only missing exact canonical starter records;
4. create one activation event only when the exact Revision is absent or has
   never been activated;
5. validate one proposed ordinary Profile aggregate; and
6. perform one expected-revision-guarded canonical batch commit.

Sequential Family/Revision/activation commits are not an acceptable starter
installation transaction because they could expose partial installation.

An exact already-active install is an idempotent no-op. An exact inactive
Revision may be explicitly activated. A Revision that has been deprecated,
superseded, withdrawn, or retired must never be silently reactivated.

## Producer-neutral Candidate policy

Starter sections use Vitrine Candidate vocabulary, currently bounded to:

```text
assessment_summary
feedback
student_work
```

The starter contract does not name ScoreForm, Quillan, or Concord as section
policy and has no runtime dependency on those packages. Producer availability
does not install or alter a starter.

No starter automatically selects earliest, latest, highest, lowest, best,
preferred, most improved, portfolio-worthy, or otherwise ranked evidence.
Placement remains explicit Vitrine curation.

## Improvement starter

The Improvement starter contains ordered sections:

```text
baseline
later_evidence
supporting_feedback
reflection
```

and stable Requirements:

```text
baseline_cardinality
later_evidence_cardinality
comparison_reflection
teacher_review
```

It supports explicit comparison of curated evidence. It does not determine that
improvement occurred and does not derive growth, mastery, proficiency, or a
preferred attempt from score, date, rating, or revision metadata.

## Showcase starter

The Showcase starter contains ordered sections:

```text
featured_work
supporting_evidence
reflection
```

and stable Requirements:

```text
featured_work_cardinality
showcase_reflection
privacy_review
rights_review
accessibility_treatment
collaborative_work_treatment
final_curator_approval
```

Its bounded external-review audience rule requires explicit privacy, rights,
and accessibility review and prohibits private/restricted content classes. The
Profile does not determine "best work" and does not grant permission to disclose
student work.

## Customization

Packaged starter revisions are immutable. Local customization must use ordinary
Profile mechanisms rather than editing the installed Revision in place:

- author a successor Profile Revision;
- author a local Overlay and compose an effective Profile;
- create a separate Profile series when policy identity should diverge; or
- leave the starter unchanged and bind another exact Profile.

No customization path changes the meaning of `purpose_kind` or creates hidden
starter policy.

## Issue #65 guided setup handoff

`Create Portfolio for Student` may list an already installed and bindable starter
Revision exactly like any other Profile Revision. It does not install, activate,
reactivate, upgrade, or otherwise mutate starter Profiles. If no suitable
bindable Profile exists, setup stops read-only. See
[Create Portfolio for Student v1](create-portfolio-for-student-v1.md).
