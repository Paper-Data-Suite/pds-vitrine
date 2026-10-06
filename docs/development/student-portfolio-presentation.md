# Student Portfolio presentation development

Issue #101 adds the human-facing layer above one exact verified Snapshot Edition and
technical directory Export. The presentation service does not reopen producer state.

The runtime path is:

```text
verified Snapshot Edition
-> verified technical Export
-> exact presentation preparation
-> bounded staging
-> create-only presentation publication
-> canonical PortfolioPresentationArtifact
-> verify_portfolio_presentation
```

`build_student_portfolio_presentation(...)` is the ordinary canonical creation/reuse
boundary. `resume_current_portfolio_presentation(...)` is the Current Portfolio recovery
boundary after durable Snapshot/Export success. Recovery never reacquires producer bytes.

The base Vitrine installation remains Core-only. Printable presentation rendering lives
behind the `paper` extra, which supplies ReportLab, PDFium, and Pillow through the existing
optional dependency surface. The HTML renderer remains offline and dependency-free.

A `student_portfolio` Audience Context must allow `portfolio_index`. Other presentation
classes, including `showcase`, do not inherit this contract automatically.

Use these focused checks while developing:

```text
python -m pytest -q tests/test_portfolio_presentation_*issue101.py
python scripts/validate_portfolio_presentation.py
python scripts/validate_student_portfolio_presentation_end_to_end.py
```

The isolated wheel smoke is:

```text
python scripts/smoke_test_portfolio_presentation_wheel.py <vitrine-wheel> <core-wheel>
```

The wheel smoke installs the Vitrine `paper` extra into a clean environment, authenticates
the exact Core 0.6.4 wheel first, proves no ScoreForm/Quillan/Concord/Portia/Meridian
installation is needed, builds an exact Reflection-only student Portfolio, verifies HTML
and PDF custody, and proves idempotent reuse.

Complete repository qualification remains:

```text
python scripts/validate_repository.py --core-wheel <authenticated-core-0.6.4-wheel>
```

Presentation creation, verification, opening, printing, disclosure, and delivery remain
separate actions. Issue #101 creates and verifies the artifact; later navigation is #102.
