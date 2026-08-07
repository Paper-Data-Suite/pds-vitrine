# Portfolio Subject Workflow Development

Use `vitrine.subject_services` for application behavior. CLI and teacher menus
must not implement separate identity rules.

## Exact resolution

```python
from vitrine.models import ClassQualifiedStudentRef
from vitrine.subject_services import resolve_roster_student

reference = ClassQualifiedStudentRef(
    school_year="2026-2027",
    class_id="english10_p2",
    student_id="00107",
)
resolution = resolve_roster_student(workspace_root, reference)
```

Never fall back to a name or a repeated `student_id` in another class.

## Mutations

Build an `IdentityDecisionContext`, observe the current Vitrine state revision,
then call the applicable service:

```python
from vitrine.subject_services import (
    create_portfolio_subject,
    observe_state_revision,
)

expected = observe_state_revision(workspace_root)
result = create_portfolio_subject(
    workspace_root,
    reference,
    context=context,
    expected_state_revision=expected,
)
```

The services persist all related records through `commit_record_batch()`.

## Direct CLI

```text
vitrine subject list
vitrine subject show SUBJECT_ID
vitrine subject create ...
vitrine subject link SUBJECT_ID ...
vitrine subject correct-link LINK_ID ...
vitrine subject invalidate-link LINK_ID ...
vitrine subject merge SUBJECT_A SUBJECT_B ...
vitrine subject split SUBJECT_ID --group LINK_A --group LINK_B ...
```

Use `vitrine subject <command> --help` for exact options. Mutating commands are
noninteractive and require attribution, authority source, basis type, and basis
summary.

## Teacher menu

Bare `vitrine` or `vitrine menu` launches the menu interface. Portfolio Subject
workflows use the same service functions as the CLI.

Teacher-facing screens are intentionally low density. Clear after selections and
show only next-action context. Use Core `menu_navigation` primitives for B/M/Q;
use H for contextual help.

## Validation

```powershell
python scripts\validate_subject_workflows.py
python -m pytest tests\test_subject_identity_models.py tests\test_subject_services.py tests\test_subject_cli.py tests\test_subject_menu.py -q
```

The complete repository gate remains:

```powershell
.\run_tests.ps1 -CoreWheel C:\path\to\pds_core-0.6.0-py3-none-any.whl
```
