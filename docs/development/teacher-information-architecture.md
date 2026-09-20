# Teacher Information Architecture Development

Issue #95 moves teacher-facing Vitrine screens onto a transient presentation
layer while retaining the exact canonical model underneath.

Branch:

```text
95-teacher-information-architecture-provenance-drilldown
```

## Runtime boundary

Slice 1 adds:

```text
vitrine/teacher_presentation.py
```

The module is read-only and composes existing application services. It does not
persist display state, cache alternate identity, or duplicate canonical
currentness logic.

Presentation code may humanize bounded enum/token values for display, but it must
not use those strings for matching or authority.

## Portfolio overview

The Portfolio menu now treats overview and Subject management as separate
actions.

```text
Portfolio
-> Portfolio Overview
   -> T. Technical details / provenance
   -> 1. View / manage Subject details
```

The default overview intentionally omits opaque Portfolio/Profile identifiers.
Technical details intentionally retain them.

The exact class-qualified link remains visible in the ordinary overview because
that relationship is meaningful teacher context and is the identity behavior the
Portfolio Subject model is designed to make explicit.

## Candidate Inbox

Slice 2 adds `TeacherCandidateDetail` and `TeacherCandidateSection` as transient
display projections over the existing `CandidateInboxDetail`.

The normal teacher surface is deliberately smaller than the canonical detail:

```text
CandidateInboxDetail
-> TeacherCandidateDetail
-> Candidate Evidence
   -> T. Technical details / provenance
```

Do not reimplement Candidate current-Evaluation resolution, staleness,
eligibility, attention, or Selection observation in the presentation module.
Those semantics remain owned by `vitrine.candidate_inbox`.

Eligible section display names are looked up by exact section ID on the exact
Profile Revision already carried by the Inbox detail. Do not infer roles from
labels and do not retarget eligibility.

The direct Candidate Inbox CLI remains an exact technical interface in this
slice. Issue #95 is changing the guided teacher information hierarchy, not
removing diagnostic detail from noninteractive tooling.

## Guided Candidate Review

Slice 3 applies the same split to the interactive #66 review surface:

```text
CandidateReviewDetail
-> TeacherCandidateDetail for primary context
-> exact review detail for Technical Details / Provenance
-> unchanged planners/executors for actions
```

The list and ordinary numbered pickers humanize stable state and prefer labels.
They must still pass the original exact objects/IDs into the existing planning
functions.

Final mutation reviews are a distinct layer: exact frozen IDs/revisions may
remain visible when they are part of the transaction the teacher is confirming.

## Working Composition

Slice 4 applies the hierarchy directly to the interactive #67 menu without
introducing another state projection:

```text
WorkingCompositionPreparation / CompositionView
-> teacher-first renderers
-> Technical Details / Provenance renderers
-> unchanged exact freeze preview
-> unchanged freeze executor
```

Use labels and stable humanized tokens already carried by the exact preparation.
Do not rederive Composition semantics or fetch a second curation truth.

The exact freeze preview is deliberately exempt from low-density hiding because
its identities, revisions, delta, and fingerprint are the reviewed transaction
guard.

## Build / Export Current Portfolio

Slice 5 preserves #68's shared exact surface for CLI/audit and adds a guided
teacher renderer beside it:

```text
CurrentPortfolioBuildPreparation
-> teacher renderer for ordinary guided review
-> exact renderer for Technical Details / Provenance and direct CLI
-> unchanged exact prepared execution
```

Use only human-readable values already present in the exact preparation.
`CurrentPortfolioPlannedItem.display_label` is an allowed safe label; richer
producer naming remains #96.

Audience Rule IDs may appear in ordinary choice presentation only when duplicate
human labels make exact disambiguation necessary.

Opening provenance must not reprepare, acquire source bytes, request authority,
or write Snapshot state.

## Portfolio context and Profile Binding

Slice 6 extends the transient presentation boundary to active Profile Binding:

```text
PortfolioProfileBinding + exact PortfolioProfileRevision
-> TeacherProfileBinding
-> teacher-first Profile view
-> Technical Details / Provenance
-> unchanged bind/migrate services
```

Portfolio list/open choices remove the opaque Portfolio ID from ordinary
presentation while retaining the selected exact `portfolio_id` as authority.

Bindable revision labels are presentation only. Duplicate display tuples expose
the exact Profile ID only for disambiguation; selection still returns the exact
`ProfileRevisionSummary.reference`.

Do not infer section names from IDs. Use canonical `ProfileSectionDefinition`
labels and purposes already present in the exact Profile Revision.

## Extension rule

Future #95 slices should extend `teacher_presentation.py` or adjacent transient
presentation modules instead of formatting canonical records ad hoc in each menu.

Keep the layers distinct:

```text
canonical service/read model
-> transient teacher presentation
-> low-density renderer
```

Do not change Candidate eligibility, Selection/Placement validity, Reflection
semantics, student Portfolio rendering, Edition management, or Attention
derivation while implementing this presentation issue; those belong to #96-#103.

## Focused validation

Run after Slice 6:

```powershell
python -m pytest -q `
  tests/test_portfolio_menu.py `
  tests/test_teacher_presentation.py `
  tests/test_profile_services.py

python -m ruff check `
  vitrine/teacher_presentation.py `
  vitrine/portfolio_menu.py `
  tests/test_teacher_presentation.py `
  tests/test_portfolio_menu.py

python -m mypy
python scripts/check_documentation.py
git diff --check
```

The complete repository gate remains authoritative before the issue is closed.
