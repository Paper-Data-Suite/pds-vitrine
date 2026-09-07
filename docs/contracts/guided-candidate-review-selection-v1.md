# Guided Candidate Review and Selection v1

- **Issue:** #66
- **Contract:** `vitrine_guided_candidate_review_v1`
- **Status:** Implemented guided orchestration contract

## Purpose

This contract defines Vitrine's presentation-independent teacher-guided Candidate
review and Selection workflow over the canonical Candidate Inbox and existing
curation records/services.

It does not introduce a durable review-session model, Candidate ranking, or a
second Selection truth model. Canonical history remains:

```text
CandidateEvaluation
PortfolioCandidate
SelectionProposal
SelectionDecision
PortfolioSelection
SelectionLifecycleEvent
PortfolioPlacement
PlacementLifecycleEvent
SectionArrangementRevision
SectionArrangementPointerRevision
CurationRationale
CurationAnnotation
PortfolioReflection
CurationReviewDecision
```

The governing separations remain:

```text
Candidate Evaluation != Portfolio Candidate
Portfolio Candidate != Selection Proposal
Selection Proposal != Selection Decision
Selection Decision != Portfolio Selection
Portfolio Selection != Placement
Placement != Profile requirement satisfaction
Candidate declined for curation != Candidate ineligible
Candidate selected != disclosure authorized
Annotation != producer fact
Reflection != proof of improvement
Curation Review != disclosure authorization
```

## Runtime surface

The reusable orchestration layer is `vitrine.candidate_review`.

Its primary transient projections and plans include:

```text
CandidateReviewDetail
CandidateReviewProposalSummary
CandidateReviewSelectionSummary
CandidateReviewPlacementSummary
CandidateReviewAnnotationSummary
CandidateReviewReflectionSummary
CandidateReviewReviewSummary
CandidateReviewActionPlan
CandidateReviewPlacementActionPlan
CandidateReviewWithdrawalActionPlan
CandidateReviewReplacementActionPlan
CandidateReviewAnnotationActionPlan
CandidateReviewReflectionActionPlan
CandidateReviewCurationReviewActionPlan
CandidateReviewError
```

No `CandidateReview`, `CandidateReviewSession`, `CandidateInboxDecision`, or
other canonical review-session record is persisted.

## Candidate Inbox authority

Review listing delegates to the Candidate Inbox using an exact Portfolio query.
Opening review does not run Candidate discovery and does not invoke producer
readers. Discovery remains a separate explicit source-read action.

Positive Candidate rows may be curated. Retained `ineligible` and `unresolved`
Evaluation-only rows remain reviewable with `candidate_id=None` and are not
selectable. Suppressed Evaluations remain absent from rows, counts, attention,
action availability, and detail.

## Review detail and safe provenance

`CandidateReviewDetail` carries the exact observed Vitrine state revision and
bounded persisted context needed for a teacher decision:

```text
Portfolio / Portfolio Subject
Profile Binding / exact Profile Revision / purpose
current Evaluation outcome and reason codes
Candidate condition
current/stale/unresolved state and stale reasons
attention state from Candidate Inbox
eligible section labels/IDs and cardinality context
Profile requirements
Proposal/Decision history
Selection lifecycle and Placement history
Annotation / Reflection / curation Review summaries
Core Publication identity/state
producer module/source/native revision
Artifact identity/representation where retained
typed Subject relationships
availability observations
```

Review projections do not expose raw manifests, student work bodies, answer
keys, feedback bodies, private teacher notes, private producer paths,
authorization-provider prose, or absolute workspace paths.

## Current Evaluation versus curation provenance

The Candidate Inbox current-Evaluation pointer and immutable Candidate curation
provenance remain distinct.

```text
Current review Evaluation
!= necessarily
PortfolioCandidate.candidate_evaluation_id
```

The current Evaluation is the review/currentness head. The immutable Candidate
continues to govern Proposal/Selection provenance through its exact
`candidate_evaluation_id`. Advancing the Candidate current-Evaluation pointer
does not retarget the Candidate, an existing Selection, or historical curation.

Guided detail and action plans therefore carry both:

```text
current_review_evaluation_id
curation_provenance_evaluation_id
```

No #66 action silently changes the frozen #34 Proposal/Selection validation
rule.

## Select, decline, and defer

`Not now`/defer is read-only and creates no unread/read or review-session state.

A fresh positive Selection reuses `select_candidate_directly(...)`, preserving
one atomic canonical chain:

```text
SelectionProposal(proposal_origin=direct_selection)
+
SelectionDecision(decision=accepted)
+
PortfolioSelection
+
SelectionLifecycleEvent(event_kind=activated)
```

A fresh decline reuses `reject_candidate_directly(...)` and atomically creates:

```text
optional CurationRationale
+
SelectionProposal(proposal_origin=teacher)
+
SelectionDecision(decision=rejected)
```

It creates no Selection or Placement and does not rewrite Candidate eligibility
or Evaluation outcome.

If an undecided Proposal already exists, guided planning requires that exact
Proposal identity; it does not infer a latest Proposal or create a duplicate.
The existing low-level Decision vocabulary remains authoritative.

## Explicit section intent

Fresh select/decline and guided replacement require explicit nonempty proposed
section IDs. Candidate-eligible sections are shown with labels, obligation,
active Placement count, maximum cardinality, Arrangement pointer revision, and
relevant Profile requirement IDs.

Guided orchestration never chooses the first, all, highest-capacity, best, or
otherwise inferred section. Proposal section intent remains distinct from
active Placement.

## Placement

Acceptance does not automatically place a Selection. Placement is a separate
planned mutation over one exact active Selection and one explicit eligible
section.

The plan freezes the observed Vitrine state revision and observed Arrangement
pointer revision. Execution calls `place_selection(...)` with those exact
values. A changed state or pointer fails closed; no silent refresh/retry or
last-write-wins merge occurs.

## Withdrawal and replacement

Withdrawal plans freeze the exact active Selection, every affected active
Placement, affected section IDs, exact Arrangement pointer observations, and a
reason. Execution reuses append-preserving `withdraw_selection(...)`; historical
Proposal, Decision, Selection, Placement, Annotation, and Reflection records are
not deleted.

Replacement requires:

```text
exact active Selection
exact successor Candidate
explicit nonempty successor Proposal section intent
one explicit disposition for every active old Placement
exact Arrangement pointer observations for every affected section
reason
```

Each old Placement disposition is either `drop` or one exact successor-eligible
section. Guided replacement never preserves the same section implicitly and
never uses the low-level compatibility fallback that can derive Proposal intent.
Execution reuses `replace_selection(...)` with explicit `proposed_section_ids`.

## Annotation, Reflection, and curation Review

Annotation and Reflection remain their canonical revisioned records. Guided
creation/revision plans carry exact target identities and the observed Vitrine
state revision. Revision actions name one exact current revision head; concurrent
revision changes fail closed.

Comparison Reflection roles such as `baseline` and `later` are explicit target
semantics and are never inferred from timestamps or order.

Curation Review targets exact immutable curation revisions/states. Approval of
one Annotation/Reflection/Arrangement/Composition revision does not carry to a
successor revision. Curation Review does not authorize disclosure.

## Candidate conditions and authority

A non-ready Candidate condition is shown before positive Selection. Teacher UI
acknowledgement means only that the condition was reviewed. It does not clear or
satisfy rights, collaborator, accessibility, teacher-confirmation, or other
conditions.

Every mutation continues through the injected `CurationAuthorityGate` with
`allowed`, `denied`, or `unresolved`. Actor attribution is not authorization.
Denied/unresolved authority writes nothing.

## Concurrency

All guided mutation plans freeze the exact observed Vitrine state revision.
Arrangement-changing actions also freeze exact section Arrangement pointer
revisions. Execution uses those exact observations and never silently rereads,
replans, retries, or substitutes newer state.

Stable `curation.*` conflicts therefore remain visible to the teacher/caller.

## Interfaces

Teacher Portfolio menu:

```text
1. Overview / Subject Links
2. Profile Binding
3. Discover Candidates
4. Review Candidates / Selections
5. Working Composition
6. Snapshot
```

Task-level direct CLI:

```text
vitrine candidate review ENTRY_ID
vitrine candidate decide ENTRY_ID --decision select|decline --section-id SECTION_ID ...
vitrine candidate annotation add|revise ...
vitrine candidate reflection add|revise ...
vitrine candidate curation-review ...
```

The task-level CLI is noninteractive and shares the same orchestration plans and
executors as the teacher menu. Existing low-level `selection`, `arrangement`, and
other CLI commands remain available and retain their frozen semantics.

## Producer and grading boundaries

ScoreForm, Quillan, Concord, Portia, and Meridian are not runtime dependencies
of guided review. Opening or curating persisted Candidate state does not invoke
producer readers. Selection is Vitrine portfolio curation only and is not
Meridian grading-evidence selection.

The workflow performs no Candidate ranking, best/latest/highest inference,
automatic improvement/proficiency claim, automatic Selection, or automatic
disclosure permission.

## Validation

Run:

```powershell
python scripts/validate_candidate_review_selection.py
```

The complete repository validator also runs the #66 validator, package-content
guards, and an isolated Core+Vitrine guided-review wheel smoke with no sibling
producer packages installed.
