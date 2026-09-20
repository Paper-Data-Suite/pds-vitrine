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

Run after Slice 1:

```powershell
python -m pytest -q tests/test_teacher_presentation.py tests/test_portfolio_menu.py
python -m ruff check vitrine/teacher_presentation.py vitrine/portfolio_menu.py tests/test_teacher_presentation.py tests/test_portfolio_menu.py
python -m mypy
python scripts/check_documentation.py
git diff --check
```

The complete repository gate remains authoritative before the issue is closed.
