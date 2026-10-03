# Developing paper-native student Reflection

This document describes the implementation boundaries for Issue #99.

## Primary workflow

The Portfolio menu exposes `Student Reflection` before Working Composition.
Teacher-facing lifecycle states are:

```text
Prompt not issued
Prompt issued — awaiting return
Returned paper needs review
Authorship confirmed — recording incomplete
Reflection recorded — paper evidence preserved
Needs teacher review
```

The primary path is:

```text
prepare exact prompt
→ choose/review exact curated targets
→ choose exact class-qualified student link when necessary
→ issue immutable response pages
→ persist Core PDS2 routes
→ render printable PDF
→ scan through normal Core intake
→ capture immutable returned-page evidence
→ open digest-verified temporary preview
→ explicitly confirm student author
→ finalize canonical PortfolioReflection
```

Reprinting uses the existing immutable issuance and exact route identities. A
print/render failure must not cause a new prompt or different route set to be
invented.

## Authorship separation

`PortfolioReflection.author` represents the student whose response is being
captured. `ReflectionAuthorshipConfirmation.confirmed_by` and
`ReflectionPaperFinalization.recorded_by` represent the authorized adult
performing the teacher-mediated mutation. Authority checks apply to that adult,
not to the student author.

Manual typed fallback follows the same separation through
`manual_reflection_services`; typing a student-looking identifier into a teacher
actor must never be treated as student authorship.

## Returned evidence review

`paper_reflection_review` is a read-only projection over the exact issuance,
ordered response pages, and routed evidence occurrences. It does not select a
rescan automatically.

Before confirmation, selected retained-source bytes are containment-checked,
link/symlink unsafe paths are rejected, and SHA-256 must match canonical
provenance. The UI launches temporary copies for review.

If confirmation succeeds but final Reflection creation is interrupted or fails,
the canonical workflow state becomes `confirmed_needs_recording`. The menu
offers an explicit recovery action that finalizes from the existing confirmation
rather than asking the teacher to repeat or fabricate provenance.

## Printing dependencies

Printable Reflection PDFs use `qrcode[pil]` and `reportlab`. These are Vitrine `paper` extra dependencies for the paper-generation surface. They do not create a
dependency on Quillan, Concord, ScoreForm, Portia, or Meridian.

Install printable-paper support with `pds-vitrine[paper]`. The base Vitrine
distribution remains Core-only. The routing/profile modules, Portfolio menu,
and evidence/materialization path remain importable without the paper extra or
sibling PDS producer packages.

## Path-safety regression boundary

Issue #111 adds regression coverage around the existing paper path behavior.

`student_reflection_response.pdf` remains a fixed Vitrine-owned leaf. The
temporary render destination uses that fixed stem plus a bounded random token;
student display names and Reflection prompt text do not enter either name.

Returned-paper Current Portfolio materialization follows the exact persisted
Core `retained_source_relative_path`, reads bytes directly, and validates
SHA-256. The reader does not regenerate Core's writer filename and does not
require a native PDF/image library to open the retained path.

## Release qualification

Repository qualification for #99 includes:

```text
focused domain/menu/materialization tests
scripts/validate_paper_reflection.py
isolated Core + Vitrine routing-profile wheel smoke
package-content checks
documentation checks
full pytest / Ruff / MyPy
full repository validator
physical printer/scanner acceptance record
```

The isolated routing/profile smoke intentionally installs the Vitrine wheel
without sibling PDS modules. It verifies installed module-profile discovery and
package dependency boundaries. The final installed end-to-end acceptance should
add the full issuance → dispatch → evidence → confirmation → materialization
exercise using exact built wheels.
