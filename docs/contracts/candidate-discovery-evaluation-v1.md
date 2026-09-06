# Candidate Discovery and Evaluation v1

- **Issue:** #33
- **Milestone:** v0.2.0 — Runtime Foundations and Fixture-Backed Portfolio Slice
- **Status:** Implemented fixture-backed runtime contract
- **Evaluator contract:** `vitrine_candidate_evaluator_v1`

## Purpose

This contract implements Vitrine's first executable Core-backed Candidate
pipeline. Core's disposable academic catalog proposes publication IDs; canonical
Core and producer state must then be re-established before any source can become
a Vitrine Candidate.

```text
bounded Core catalog discovery
  -> canonical Publication Record reload
  -> exact historical registration reload
  -> canonical series/withdrawal observation
  -> Core producer compatibility
  -> exact Vitrine adapter selection
  -> explicit source-read authorization
  -> exact manifest verification and byte digest
  -> producer public reader
  -> Vitrine producer projection
  -> exact Portfolio Subject relationship
  -> exact bound Profile eligibility
  -> Candidate Evaluation
  -> Portfolio Candidate, only for a positive Evaluation
```

The trust boundaries are deliberate:

```text
catalog discovery != canonical publication authority
canonical publication != source authorization
source authorization != manifest integrity
manifest integrity != Profile eligibility
Profile eligibility != Candidate
Candidate != Selection
Candidate != disclosure authorization
```

A Candidate is also not a Grade, proficiency/mastery result, or designation of
an official/best/latest producer attempt.

## Runtime API

The application boundary is `vitrine.candidate_services`.

Primary types are:

```text
CandidateDiscoveryRequest
CandidateDiscoveryFinding
CandidateEvaluationResult
CandidateDiscoveryResult
CandidateWorkflowError
SourceReadAuthorizationRequest
SourceReadAuthorizationDecision
SourceReadAuthorizationGate
```

The high-level operation is:

```python
discover_and_evaluate_candidates(...)
```

Its producer compatibility registry, Vitrine adapter registry, authorization
gate, clock, and ID factory are explicit dependencies. Importing the service
performs no workspace, catalog, producer, or network discovery.

A request requires an explicit positive catalog limit. The initial contract caps
the limit at 1000 and accepts Core's typed `PublicationCatalogQuery`; ordinary
use should query `state="current"`.

## Discovery is nonauthoritative

`query_publication_catalog()` is used only to obtain bounded proposals. A
catalog row never constructs a source endpoint. Each proposal is reloaded by
exact `publication_id` through Core canonical services, and relevant catalog
fields are compared with the canonical record to detect drift.

A missing, incompatible, corrupt, or unreadable catalog becomes a structured
transient finding. Candidate discovery never rebuilds or repairs Core's catalog.

## Canonical publication and registration

Academic publications reload the exact historical Academic Work Registration
revision named by the Publication Record. The current registration is not used
as a substitute. The Vitrine `AcademicWorkRegistrationSnapshot` preserves the
runtime model's existing exact fields:

```text
registration_revision
producer_contract_version
title_snapshot
work_kind
academic_intent
lifecycle
source_records
```

Non-academic publications receive no fabricated registration.

Publication series state is derived from Core's validated canonical series and
explicit predecessor/withdrawal records. Greatest revision, newest timestamp,
filename, and identifier ordering never establish currency. The ordinary
Candidate path accepts only a current non-withdrawn series head.

## Producer compatibility and adapter selection

Core compatibility is evaluated through an explicitly supplied
`PublicationProducerRegistry` and `evaluate_publication_compatibility()`.
Missing Profile and incompatible Profile are distinct failures.

The #32 `ProducerAdapterSupportRequest` is built only from canonical Publication
and exact registration state. Selection is delegated unchanged to the #32
registry. Unsupported and conflicting adapter claims fail closed; no fallback
parser exists.

`vitrine.development_candidate_fixtures` supplies explicit Core compatibility
Profiles only for these Vitrine-owned development fixture identities:

```text
vitrine_scoreform_fixture
vitrine_quillan_fixture
vitrine_concord_fixture
```

They are not entry points and do not claim the live ScoreForm, Quillan, or
Concord contracts.

```text
development fixture Candidate flow
!= live ScoreForm integration
!= live Quillan integration
!= live Concord integration
```

## Authorization before manifest access

`SourceReadAuthorizationGate` is intentionally small and replaceable by later
authorization services. Its immutable decision is one of:

```text
allowed
denied
unresolved
```

The request is scoped to Portfolio, Portfolio Subject, Publication, operation,
and purpose. Absence of permission is never permission.

Denied or unresolved authorization stops the pipeline before Vitrine verifies
or reads student-level manifest bytes and before a producer reader is called.
Authorization remains a separate `source_authorization` availability dimension.
This contract does not create recipient or disclosure authorization records.

## Manifest integrity and exact reader bytes

After authorization, Core's manifest verification surface validates the exact
canonical path, work-root containment, regular-file requirements, and bound
SHA-256. Vitrine then reads the verified file as immutable bytes, hashes those
exact bytes again, and compares that digest with the canonical Publication
Record before reader invocation. This prevents a verified path from silently
feeding changed bytes to a producer reader.

No path guessing, work-tree crawling, `latest.json`, alternate revision, or
generic JSON fallback is permitted.

Diagnostics and persisted records do not retain raw manifest bytes or absolute
filesystem paths.

## Producer projection and source identity

The selected #32 reader validates the bytes and the selected adapter projects the
validated public model. Candidate services do not duplicate producer JSON
validation or inspect producer-native private files.

Every projected source is evaluated independently. `CandidateEvaluationResult`
retains the privacy-bounded `ProjectedProducerSource` transiently so callers can
observe producer-native projected fields without changing the foundational
Candidate wire model. The canonical Candidate endpoint retains exact Core,
producer-source, Artifact/representation, relationship, and privacy provenance.

This is important for ScoreForm: attempt identity, response states, points, and
standard alignments remain producer projection facts; Vitrine does not calculate
an official attempt, Grade, proficiency, or mastery.

## Portfolio Subject relationship resolution

For projected `core_student` relationships, Vitrine constructs an exact
`ClassQualifiedStudentRef` from:

```text
canonical class school year
canonical Publication work.class_id
projected producer student_id
```

That reference must resolve through an existing current Vitrine Subject link to
the exact Portfolio Subject. Display names and unqualified student IDs are never
identity evidence.

Only then is the transient #32 relationship converted into an embedded
`PortfolioSubjectRelationshipAssertion`. The exact relationship kind is retained.
No cross-kind inference is allowed, including:

```text
group_member != artifact_author
group_member != documented_contributor
artifact_subject != artifact_author
artifact_author != individual_score_target
group_score_target != individual_score_target
```

Non-`core_student` relationships remain producer facts but do not create an
individual Portfolio Subject assertion without a future explicit crosswalk or
policy authority.

## Candidate kind and Profile eligibility

The initial explicit Artifact-to-Candidate-kind mapping is:

```text
assessment_summary    -> assessment_summary
collaborative_artifact -> student_work
original_student_work -> student_work
rendered_feedback     -> feedback
```

Unknown kinds fail closed rather than being inferred from filename, title,
media type, or producer module.

The exact Profile Binding and Profile Revision are loaded from the same immutable
Vitrine state snapshot used for Subject resolution. A section is eligible only
when:

- it is not prohibited;
- the mapped Candidate kind is explicitly allowed;
- every `required_relationship_kind` is present in the exact Subject assertions.

Matched Profile rule IDs use existing section-scoped
`PortfolioProfileRequirement.requirement_id` values. Candidate eligibility does
not claim that Placement cardinality, approval, Selection, Reflection, output,
or disclosure requirements are satisfied.

## Evaluations and Candidates

`CandidateEvaluation` remains the durable record for positive and negative
source-level outcomes. Once a verified producer source endpoint exists:

- `eligible` means no currently known Candidate-level review condition remains;
- `conditionally_eligible` means a later review such as rights or collaborator
  review is required;
- `ineligible` means the verified source is not permitted by the exact Profile;
- `unresolved` means an exact Subject/source fact cannot be established safely.

Only `eligible` and `conditionally_eligible` create `PortfolioCandidate`.

The Evaluation and its positive Candidate are committed in the same guarded
Vitrine batch. All projected sources in one discovery request are evaluated from
one immutable Vitrine state revision and all new records are committed together,
so persistence does not change policy context mid-run.

An exact expected Vitrine state revision is mandatory. A state change before the
commit fails with `candidate.state_conflict`; the service does not silently
re-evaluate under a new Binding or Subject state.

Exact positive replay may reuse an existing Candidate when the Portfolio,
Subject, Binding/Revision, canonical Publication, producer source, Artifact,
relationship semantics, privacy metadata, eligible sections/rules, purpose, and
actor remain equivalent. Titles, filenames, timestamps, scores, and digest alone
are never deduplication keys.

## Availability matrix

Durable Evaluations use the existing multidimensional observations:

```text
canonical_publication
registration
series_state
producer_profile
adapter_support
producer_reader
manifest_integrity
producer_parse
source_resolution
artifact_availability
source_authorization
subject_relationship
profile_eligibility
disclosure_review
```

`disclosure_review` remains `not_evaluated` in #33. Candidate creation is not a
disclosure approval.

Failures before a valid source endpoint exists remain structured transient
`CandidateDiscoveryFinding` values rather than fabricated negative Candidates.

## Fixture acceptance

The development validation constructs a real temporary Core 0.6 workspace using
Core public services, writes class metadata and roster state, registers three
Vitrine-owned synthetic works, copies the existing #32 canonical manifest bytes,
publishes canonical Core records, and explicitly rebuilds Core's disposable
catalog during setup. Runtime discovery never performs that rebuild.

The slice proves:

- ScoreForm-shaped attempts remain separate and preserve selected/blank/ambiguous
  states without private answer-key/scan data or Grade/proficiency inference;
- Quillan-shaped selected/approved work and student-facing feedback are exposed
  while candidate/duplicate/excluded/replacement evidence and private teacher
  content are absent;
- Concord-shaped Group Membership, Artifact Subject, documented contribution,
  Artifact Author, represented Group, Group Score target, and non-score
  disposition remain distinct;
- collaborative privacy can make an otherwise eligible source conditional;
- no Candidate operation creates a Selection.

## Failure codes

The stable family is `candidate.*`, including request/context, catalog,
canonical Publication, registration, series, producer compatibility, adapter,
authorization, manifest, reader/projection, Subject, Profile, and state-conflict
failures. Core `contracts.*` and #32 adapter codes may appear only as bounded
transient diagnostics where safe.

Failure text must not expose student names, responses, answer keys, private
teacher notes, scan-review material, raw manifests, private native paths,
absolute workspace paths, or OS usernames.

## Persistence and side effects

Candidate discovery reads Core and producer fixture state but never mutates Core
canonical registry state. It writes only Vitrine Candidate Evaluation/Candidate
records after successful source-level evaluation. It creates no Selection,
Placement, Arrangement, Composition, source copy, Snapshot, export, or sibling
module record.

## Validation

Run:

```powershell
python scripts\validate_candidate_discovery.py
```

or the complete repository gate. The validator also verifies the #28
foundational runtime fixture hashes remain byte-identical.


## Issue #58 shared reader service

Issue #58 extracts the authorization/manifest/reader portion of this Candidate
pipeline into `vitrine.producer_reader_services`.

Candidate orchestration now calls:

```text
read_authorized_producer_manifest(...)
```

after canonical state, Core producer compatibility, and exact adapter selection.
That shared operation performs:

```text
source-read authorization
-> Core manifest verification
-> immutable manifest byte read
-> independent post-read SHA-256 verification
-> selected adapter reader invocation
```

Candidate then passes the returned validated public model to the selected
adapter's pure `project()` operation.

This refactor does not change Candidate current-selectable policy, Subject
resolution, Profile eligibility, persistence, final source-stability checks, or
the `candidate.*` failure surface.

Installed Core producer Profile discovery is explicit through
`build_installed_producer_registry()`; `default_workflow_dependencies()` remains
empty/fail-closed and performs no installed producer discovery.

## Issue #64 current-Evaluation extension

Issue #64 operationalizes ADR 0004's explicit Candidate current-Evaluation state without changing the `vitrine_candidate_evaluator_v1` discovery meaning.

Every newly created positive Candidate is now committed atomically with `CandidateCurrentEvaluationPointerRevision(pointer_revision=1)`. Exact positive replay creates no duplicate pointer revision. A later Evaluation in the same exact Candidate series requires explicit Evaluation predecessor lineage and an explicit successor pointer. Currentness is never selected from `evaluated_at`, identifier ordering, storage ordering, or filenames.

Pre-#64 Candidates may fall back to their creation `PortfolioCandidate.candidate_evaluation_id` only while no explicit pointer or successor Evaluation makes the governing Evaluation ambiguous.

The read-only `vitrine_candidate_inbox_v1` projection is documented in [candidate-inbox-v1.md](candidate-inbox-v1.md). Candidate discovery remains an explicit source-read/mutation operation; opening the inbox never runs discovery.
