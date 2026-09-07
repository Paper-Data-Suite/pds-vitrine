# Create Portfolio for Student development

Issue #65 adds a planner-first student setup workflow without a canonical setup
record.

## Runtime

```text
vitrine/portfolio_setup.py
vitrine/portfolio_setup_menu.py
vitrine/workflow_cli.py
```

Reusable services:

```text
resolve_portfolio_setup_subject(...)
list_portfolio_setup_profiles(...)
plan_create_portfolio_for_student(...)
create_portfolio_for_student(...)
```

The `PortfolioSetupPlan` is the reviewed commit specification. Do not regenerate
its proposed IDs after review.

## Identity

Use exact `ClassQualifiedStudentRef` values only. Repeated student IDs and names
do not link classes. Identity conflicts route to existing Subject repair
workflows.

## Profile

Purpose filters Profile choices but never chooses policy. The exact selected
Revision must remain bindable and applicable. Setup reuses
`validate_profile_applicability(...)`.

## Atomic boundary

The executor revalidates Core/Vitrine state and performs one final
`commit_record_batch(...)`. Do not replace it with sequential Subject,
Portfolio, and Profile commits.

## CLI

```text
vitrine portfolio create-for-student ... --dry-run
```

Dry-run is a fully resolved preflight, not a partial permissive plan.

## Focused validation

```powershell
python scripts/validate_portfolio_setup.py
```
