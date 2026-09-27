# Paper-native student Reflection contract v1

Issue #99 makes paper the primary capture path for student Portfolio Reflection.

## Ownership

Vitrine owns Reflection meaning: Portfolio, Portfolio Subject, Profile Binding and
Revision, Reflection requirement, immutable prompt identity/snapshot, frozen
curation targets, expected class-qualified student identity, authorship
confirmation, canonical `PortfolioReflection`, and paper-evidence linkage.

PDS Core owns physical routing and retained source custody: PDS2 payload parsing,
route registration, route resolution, source-scan identity/digest, retained source
bytes, and module dispatch.

The normal lineage is:

```text
ReflectionPromptIssuance
→ ReflectionResponsePage
→ Core PDS2 RouteRegistration
→ Core RetainedSourceScan
→ ReflectionReturnedPaperEvidence
→ ReflectionAuthorshipConfirmation
→ ReflectionPaperFinalization
→ PortfolioReflection
```

## Required invariants

Paper routing identifies which issued response returned. It does not prove who
authored the handwriting. Canonical student authorship therefore requires an
explicit teacher confirmation after the exact returned paper has been reviewed.

The student author and authorized adult recorder are distinct provenance facts.
A paper-backed canonical Reflection uses `core_student` authorship for the exact
student from the issuance's `PortfolioSubjectClassLink` /
`ClassQualifiedStudentRef`. The adult confirming/recording the association is
preserved separately.

Prompt identity is immutable at issuance: `prompt_id`, `prompt_version`, and
`prompt_snapshot` must not be rewritten by later prompt edits. Curation targets
are likewise frozen as exact `CurationTargetRef` values at issuance. Vitrine
must not infer improvement merely because earlier and later work are compared.

Class selection is cardinality-driven only: zero usable current links blocks
issuance, one may be carried forward and shown, and multiple exact links require
an explicit teacher choice. Names, recency, alphabetical order, or bare student
IDs cannot substitute for exact class-qualified identity.

Returned paper is evidence before it is a Reflection. Normal routing records an
immutable occurrence and does not create a canonical Reflection. Rescans are
preserved as additional occurrences. When more than one occurrence exists for
one issued page, the teacher must explicitly choose the occurrence used for
authorship confirmation.

Every selected page is digest-verified against the Core-retained source before
preview. Preview uses a temporary copy so the retained original is not opened as
a mutable working file.

The ordinary confirmation phrase is `CONFIRM STUDENT AUTHOR`. A wrong phrase,
Back, Main Menu, Quit, failed preview, state conflict, or authority denial must
not silently persist authorship or substitute targets/evidence.

Multi-page response ordering is the immutable logical issuance order. Normal
paper finalization requires one selected returned occurrence for every issued
page.

No OCR or handwriting transcription is required. The student's returned paper
is sufficient evidence. Typed/manual Reflection remains an explicit fallback and
must still persist student authorship separately from adult recorder provenance.

## Printing and routing

Each routable response page contains human-readable classroom context, writing
space, page numbering, fallback identifiers, and one canonical PDS2 route. QR
payloads contain only Core routing identity and must not add unnecessary student
PII.

The installed Vitrine distribution exposes a `paper_data_suite.modules` profile
for module ID `vitrine`. Core contract, QR schema, registration schema, route
status, target shape, and handler validation remain exact.

## Current Portfolio materialization

A confirmed paper Reflection has a typed evidence/finalization relationship.
Current Portfolio preparation resolves that relationship and copies exact
digest-verified paper bytes. It does not parse arbitrary display text or pretend
a Reflection is a `PortfolioPlacement`.

Final polished student-facing presentation remains owned by #101. Working
Composition representation of non-Placement requirements remains owned by #100.
Global Attention remains owned by #103.
