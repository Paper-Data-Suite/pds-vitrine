# Candidate Inbox v1

- **Issue:** #64
- **Contract:** `vitrine_candidate_inbox_v1`
- **Status:** Implemented read-only runtime contract

## Purpose

The Candidate inbox is Vitrine's transient teacher review projection over canonical Candidate Evaluation, Portfolio Candidate, Profile, Subject, current-Evaluation pointer, Core Publication, and curation state.

The governing distinctions are:

```text
Candidate Evaluation != Portfolio Candidate
Portfolio Candidate != Selection
Selection != disclosure permission
historical != current
stale != automatically invalid
attention != educational judgment
display order != ranking
Profile eligibility != disclosure permission
```

Opening, filtering, or inspecting the inbox is read-only. It does not discover sources, authorize producer reads, parse manifests, invoke producer readers, select evidence, place evidence, migrate a Profile, or approve disclosure.

## Canonical current Evaluation

`CandidateCurrentEvaluationPointerRevision` is the explicit append-preserving authority for the current Evaluation of a positive Candidate series. Revision 1 is created atomically with a newly created positive Evaluation and Portfolio Candidate. A successor pointer references the prior pointer revision and prior current Evaluation. Pointer branches, cycles, missing predecessors, cross-Candidate references, and mismatched Candidate context are invalid.

Currentness is never derived from `evaluated_at`, largest identifier, storage order, filesystem order, or filename ordering.

A pre-#64 Candidate without an explicit pointer may use its creation `candidate_evaluation_id` only when no explicit Evaluation successor makes that legacy state ambiguous. Ambiguous legacy state resolves as unresolved.

Changing the exact source endpoint or governing Portfolio, Subject, Profile Binding, or Profile Revision creates a different Candidate meaning rather than retargeting the existing Candidate.

## Transient read model

The runtime surface is `vitrine.candidate_inbox`:

```text
CandidateInboxQuery
CandidateInboxItem
CandidateInboxResult
CandidateInboxDetail
CandidateInboxError
```

No inbox row, count, filter, stale state, or attention state is persisted as a new canonical Vitrine record.

The primary list is workspace-wide. `portfolio_id` supplies the same service with an exact Portfolio filter. Positive rows represent current positive Candidates. Retained `ineligible` and `unresolved` Evaluation heads are also visible even when no Portfolio Candidate exists, and carry no fabricated Candidate ID.

`suppressed` Evaluations are omitted before result counting and filtering. Ordinary inbox behavior therefore emits no suppressed row, count, hidden-result placeholder, producer label, attention total, or detail result.

## Query boundaries and ordering

The query supports bounded filtering by Portfolio, Portfolio Subject, Profile purpose, Evaluation outcome, Candidate condition, attention-needed, stale, Selection state, producer module, `evaluated_since`, and result limit. `evaluated_since` is an explicit caller boundary; the inbox has no canonical unread/read state. The initial result limit is capped at 500.

Presentation order is deterministic: attention first, stale/unresolved currentness next, Evaluation time descending, safe display label, then stable entry identity. This order is not a quality policy. Scores, ratings, standard counts, proficiency, mastery, best-work, and producer latest-attempt concepts do not participate in ordering.

## Staleness

Staleness compares historical Candidate/Evaluation context with bounded current metadata and never rewrites historical state. Stable conditions include:

```text
candidate_inbox.profile_binding_changed
candidate_inbox.profile_binding_conflict
candidate_inbox.publication_superseded
candidate_inbox.publication_withdrawn
candidate_inbox.publication_unavailable
candidate_inbox.subject_relationship_changed
candidate_inbox.subject_relationship_conflict
candidate_inbox.current_evaluation_unresolved
candidate_inbox.evaluator_contract_changed
```

Profile checks use the explicit current Profile Binding head. Subject checks retain the exact original `subject_link_id` and exact `ClassQualifiedStudentRef`; display names and bare student IDs are not rematching authority. Core Publication checks use canonical Publication, series, and withdrawal metadata.

`current` means only that no stale condition was found through those bounded checks. It does not mean producer bytes were freshly reverified. The inbox does not request source-read authorization, open a manifest, invoke a ScoreForm/Quillan/Concord reader, or resolve Quillan/Concord Artifact bytes.

## Attention and Selection

Attention is a derived workflow signal. It includes unresolved Evaluations, stale or unresolved current context, every positive Candidate condition other than `ready_for_consideration`, and selected Candidates that became stale.

The non-ready condition taxonomy remains:

```text
review_required
rights_review_required
collaborator_review_required
accessible_representation_required
teacher_confirmation_required
```

Attention does not satisfy the underlying review requirement and is not a judgment about student quality, achievement, behavior, Grade, proficiency, or mastery. Ordinary ineligibility is not treated as student failure.

Selection is observational only: `unselected`, `selected`, or `historical_only`. A Selection retains the exact `candidate_evaluation_id` frozen when it was created. Advancing a Candidate's current-Evaluation pointer does not retarget historical Selection provenance. The inbox creates no Selection, Proposal, Placement, replacement, withdrawal, or curation Decision.

## Provenance detail

Detail preserves bounded persisted provenance: Portfolio, Portfolio Subject, Candidate ID when positive, current Candidate Evaluation ID, Profile Binding and exact Profile Revision, Profile purpose, eligible sections, Selection history, Evaluation history, current-pointer history, Core Publication ID, producer module/source/native revision, Artifact identity and representation when available, typed Subject relationships, Evaluation reasons and availability observations, and evaluator contract.

Raw manifests, response bodies, feedback bodies, answer keys, private teacher notes, private producer paths, moderation rationale, authorization-provider prose, and absolute workspace paths are not inbox output.

Producer semantics remain distinct:

```text
ScoreForm attempt != automatically official/highest/latest
Quillan original work != feedback != private review content
Concord Group Membership != Artifact Author
Concord Artifact Subject != Artifact Author
documented contribution != authorship
Group Score target != individual Score target
```

## Interfaces

Direct CLI:

```text
vitrine candidate inbox
vitrine candidate inbox show ENTRY_ID
```

The CLI requires no actor credentials for read-only display. The teacher shell exposes `5. Candidate Inbox`. The Portfolio Discover / Review Candidates workflow keeps discovery explicit and uses the same inbox service with an exact Portfolio filter for persisted review. Issue #66 now layers `vitrine.candidate_review` over this exact projection for guided Selection/Placement/Annotation/Reflection/Review orchestration; opening guided review remains read-only with respect to discovery and producer reads.

## Validation

Run:

```powershell
python scripts/validate_candidate_inbox.py
```

The complete repository validator also runs the Candidate inbox validator, package-content checks, and isolated Core+Vitrine Candidate inbox wheel smoke.
