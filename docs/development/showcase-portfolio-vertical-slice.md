# Executable showcase Portfolio vertical slice

This development-only acceptance slice composes the generic Subject, Profile,
Candidate, curation, Snapshot, custody, and Export services. It is not a
production `build_showcase_portfolio` API and does not import Quillan, Concord,
ScoreForm, Portia, or Meridian.

## Exact identity and Profile

The synthetic Portfolio is `portfolio-showcase-syn-001`, whose exact Subject is
`portfolio-subject-syn-001`. Subject creation resolves the Core roster tuple
`2025-2026 / class-ela12-syn / student-syn-001`; a same-looking display name in
the roster is deliberately not identity evidence. The service retains the
class-qualified link, display snapshot, and attributable identity decisions.

The activated `profile-showcase-rev-001` and
`profile-binding-showcase-001` define two required sections:

- `featured_work` accepts one `student_work` Candidate with the exact
  `submission_subject` relationship.
- `collaboration` accepts one `student_work` Candidate with the exact
  `documented_contributor` relationship.

The required approval `showcase_collaborator_treatment_review` concerns exact
curation and minimum-necessary presentation. It is not consent, recipient
authorization, or legal disclosure authorization.

## Producer-shaped discovery

The runtime manifests under `showcase/runtime/` are repository-local,
deterministic development fixtures. Core catalog discovery reloads each
canonical Publication and historical Registration, verifies the manifest,
selects the explicit development reader/adapter, obtains source-read
authorization, and projects immutable producer-shaped facts. This is not live
Quillan or Concord integration.

The polished source is a Quillan-shaped selected evidence record backed by
`polished-literary-analysis.txt` (377 bytes,
`5a86178f64b55c4774c919bf0c7c863e8c7d74268ec86ce6194fa22af519c575`).
It becomes `candidate-show-polished`, eligible only for `featured_work`.

The collaborative source is `concord-artifact-syn-001`, backed by truthful
`text/plain` bytes in `group-artifact.txt` (322 bytes,
`0b9ffbb18e44d698ffb51e8973bb3647df45995d815ba5dcea949a9dafe1cbc8`).
Its projection preserves:

- Group membership: the Portfolio Subject is one member.
- Artifact Author: collective `concord-group-syn-007`.
- Artifact Subjects: the declared student and Group subjects remain distinct.
- Documented contribution: `concord-contribution-syn-001`, the methods paragraph
  and chart explanation, belongs to the Portfolio Subject.
- Represented Group: the same Concord Group remains separately represented.
- Score targets: scored and deferred records remain `concord_group` targeted.

Membership and Artifact Subject relationships do not generate individual
authorship. The documented contribution supports collaboration eligibility but
does not claim authorship or ownership of the whole Artifact. Group Scores are
not individual Scores, Grades, or proficiency evidence. Both Score projections
produce explicit unresolved Evaluations and no Candidates; deferred remains a
non-score without a zero value.

## Explicit curation and privacy treatment

Discovery creates no Selection. Student Proposals and teacher Decisions create
exact active Selections for the polished and collaborative Candidates. The
collaborative Decision explicitly acknowledges
`collaborator_review_required`; acknowledgement does not complete the separate
review.

The Selections are placed in `featured_work` and `collaboration`. Current
Arrangement revisions make ordering derive from Profile section order plus
explicit Placement order.

The teacher-authored attribution Annotation targets the collaborative Selection:

```text
Audience-safe attribution: Created by Synthetic Group 7. The Portfolio Subject contributed the methods paragraph and chart explanation. Collaborator display names are intentionally omitted.
```

Its exact rendered bytes are 190 bytes with SHA-256
`1f51f05825c7907d4398c7807de97c1fd968cffe139f27c6d1b15e09f195d58e`.
It is Vitrine presentation treatment derived from producer provenance, not a new
producer authorship fact.

The student-authored rationale targets the polished Selection followed by the
collaborative Selection. It describes close reading and contribution to a shared
investigation without claiming Grade, mastery, proficiency, or an individual
Concord Score.

The approved collaborator-treatment Review targets the exact collaborative
Selection and attribution Annotation revision. A successor Annotation revision
makes that Review stale; Composition then reports the required approval as
unresolved until a new exact Review exists.

## Composition, Audience, Snapshot, and Export

One immutable Composition revision freezes both Selections, Placements,
Arrangements, both Annotation revisions, the applicable Review, related Profile
requirements, and the remaining acknowledged Candidate condition. Composition
contains no producer bytes and grants no disclosure authority.

`audience-show-external` uses `external_reviewer / showcase` and minimum-necessary
policy. It permits `student_work`, `audience_safe_attribution`,
`curation_rationale`, and `portfolio_index`; it prohibits private teacher notes,
raw collaborator data, secure assessment content, and restricted internal data.

The immutable Build Plan contains exactly five visible entries in order:

1. copied polished individual work;
2. copied collaborative Artifact, bound to the exact Review;
3. deterministically generated audience-safe attribution, also Review-bound;
4. deterministically generated student rationale;
5. deterministically generated audience-safe index.

There are zero successful-path Omissions and no Score Entry. Copied bytes are
hashed at acquisition and staging. Generated entries freeze renderer identity,
version, contract, configuration/template digests, Annotation/Composition
inputs, output digest, and size. The deterministic internal Manifest and logical
inventory are re-derived before one Edition seals.

The `directory_package` Export contains exactly those five visible files. It
does not distribute the internal Manifest. Every path, size, digest, and the
directory inventory digest verifies; replay reconciles to the same immutable
artifact. After the disposable producer source root is removed,
`verify_snapshot_edition` and `verify_snapshot_export` still succeed using only
sealed Vitrine custody.

## Privacy and execution

The validator scans all audience-visible bytes for collaborator fixture IDs,
private Quillan markers, restricted/secure content, and authorization claims.
It also asserts that no individual Score or assessment Entry exists.

Run the complete slice from the repository root:

```powershell
python scripts\validate_showcase_portfolio.py
```

The validator uses a disposable workspace, emits privacy-minimal diagnostics,
does not mutate the representative corpus, and exits nonzero on any mismatch.
