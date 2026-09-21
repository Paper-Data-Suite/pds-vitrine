# Issue #95 Teacher Information Architecture validation

## Scope

This validation freezes and qualifies:

```text
vitrine_teacher_information_architecture_v1
```

Issue #95 is accepted only when teacher-first presentation, bounded
Technical Details / Provenance, exact-authority preservation, privacy/read-only
boundaries, package content, isolated installed-wheel presentation, and the
complete repository gate all pass.

## Acceptance matrix

`tests/test_teacher_information_architecture_acceptance.py` maps issue criteria
A-J to concrete behavior tests spanning:

```text
Portfolio overview and explicit Subject navigation
Profile Binding and duplicate-label disambiguation
Candidate Inbox default/provenance detail
guided Candidate Review
Working Composition
Build / Export preparation and successful result
Attention / Next Actions
exact identity/currentness/provenance/authority behavior
read-only observation
suppression/privacy boundaries
```

The matrix is traceability only; the dedicated validator runs the referenced
behavior files as focused pytest.

## Dedicated validator

Run:

```powershell
python scripts/validate_teacher_information_architecture.py
```

The validator freezes:

- `vitrine_teacher_information_architecture_v1`;
- the transient presentation-model boundary;
- absence of mutation/authority imports and calls from
  `vitrine/teacher_presentation.py`;
- teacher-first and Technical Details / Provenance markers across current guided
  Portfolio/Profile/Candidate/Composition/build/Attention surfaces;
- intentionally exact direct CLI presentation;
- acceptance-matrix presence;
- package guards;
- repository-validator wiring;
- required issue documentation.

The complete repository gate invokes the validator with
`--skip-focused-tests` because full pytest has already run.

## Successful Build / Export result

Issue #95 also applies the presentation hierarchy to the immediate successful
guided build result.

The normal result retains useful teacher facts:

```text
build completed
Portfolio Edition number
Export disposition
Export location
current-pointer non-advancement
non-delivery boundary
```

Opaque Snapshot Series and Export Artifact identifiers are available through
`T. Technical details / provenance`.

This does not implement Edition discovery, open/print/manage actions, or
post-build history. Those remain issue #102.

## Display-label ambiguity

Portfolio labels are display-only. When two Portfolio choices have the same
recognizable display label, the normal list adds the exact Portfolio ID only as
the required disambiguator. The numbered choice still returns the original exact
Portfolio object/ID.

The same principle already applies to duplicate Profile and Audience Rule labels.

## Installed-wheel smoke

After building the Vitrine wheel, run:

```powershell
python scripts/smoke_test_teacher_information_architecture_wheel.py `
  .\dist\pds_vitrine-0.3.0-py3-none-any.whl `
  .\pds_core-0.6.3-py3-none-any.whl
```

The smoke creates a fresh isolated virtual environment containing only the Core
and Vitrine wheels. From installed `site-packages`, it imports the #95
presentation contract, renders one representative teacher Portfolio overview
and its technical drill-down, and asserts that known exact fixture identifiers
are hidden from the primary view while preserved in provenance.

## Package boundary

`check_package.py` requires the source distribution to contain:

```text
vitrine/teacher_presentation.py
docs/contracts/teacher-information-architecture-v1.md
docs/development/teacher-information-architecture.md
docs/validation/issue-95-teacher-information-architecture-validation.md
scripts/validate_teacher_information_architecture.py
scripts/smoke_test_teacher_information_architecture_wheel.py
tests/test_teacher_presentation.py
tests/test_teacher_information_architecture_acceptance.py
tests/test_validate_teacher_information_architecture.py
```

The wheel still contains only runtime package files; validation/docs/tests stay
out of the wheel.

## Complete repository qualification

Use the authenticated Core v0.6.3 wheel:

```powershell
python scripts/validate_repository.py `
  --core-wheel .\pds_core-0.6.3-py3-none-any.whl `
  --reuse-static-caches
```

The complete gate must include full pytest, Ruff, strict MyPy, all existing
validators, the #95 validator, documentation, representative Portfolios,
package build/Twine/package-content validation, all installed-wheel smokes,
the #95 isolated presentation smoke, end-to-end installed acceptance,
`git diff --check`, and working-tree isolation.

Final acceptance requires these lines from the authoritative complete run:

```text
PASS teacher information architecture validation
PASS isolated teacher information architecture wheel smoke test
PASS complete repository validation
```

Do not record those lines as achieved until the complete repository run actually
produces them.

## Sibling boundaries

This validation does not absorb issues #96-#104. In particular it does not
change Candidate source naming/preview, Selection/Placement validity, guided
transition mechanics, paper-native Reflection, non-Placement Composition
semantics, student rendering, Edition management, Attention completion
semantics, or the final umbrella synthetic acceptance.
