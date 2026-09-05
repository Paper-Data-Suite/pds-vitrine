# Starter Portfolio Profile development

The normative contract is [Starter Portfolio Profiles v1](../contracts/starter-portfolio-profiles-v1.md).
Starter Profiles are optional packaged convenience content layered over the
ordinary immutable Profile services.

## Runtime surfaces

The package-resource API is in `vitrine.starter_profiles`:

```python
list_starter_profile_packs()
get_starter_profile_pack(starter_profile_id)
validate_starter_profile_pack(starter_profile_id)
```

These operations are workspace-free and read-only.

Installation planning is also read-only:

```python
plan_starter_profile_install(
    starter_profile_id,
    workspace_root=workspace,
)
```

The returned plan freezes the observed Vitrine state revision, exact component
dispositions, lifecycle state, conflicts, and whether explicit activation is
required.

Installation is a separate guarded mutation:

```python
install_starter_profile(
    starter_profile_id,
    workspace_root=workspace,
    actor=teacher_actor,
    reason="Reviewed and approved for local use.",
    authority_reference="local_instructional_policy",
    expected_state_revision=plan.observed_state_revision,
)
```

The installer validates one proposed ordinary Profile aggregate and performs at
most one canonical batch commit. Never replace this with sequential calls to
`create_profile_family`, `create_profile_revision`, and
`activate_profile_revision`.

## Direct CLI

The power-user CLI exposes:

```text
vitrine profile starter list
vitrine profile starter show improvement_portfolio_v1
vitrine profile starter validate improvement_portfolio_v1
vitrine profile starter plan improvement_portfolio_v1 --workspace-root <workspace>
vitrine profile starter install improvement_portfolio_v1 \
  --actor-id <teacher-id> \
  --authority-reference <reference> \
  --reason <reason> \
  --confirm \
  --workspace-root <workspace>
```

`list`, `show`, and `validate` do not access workspace state. `plan` may read
canonical Profile state but does not write. `install` requires explicit
confirmation and uses expected-revision protection.

## Teacher menu

`Portfolio Profiles -> Starter Profiles` derives its choices from the packaged
catalog. The teacher can preview the complete starter policy, review the current
installation plan, return without writing at each review stage, and explicitly
type `INSTALL` before the atomic installer is invoked.

The confirmation flow records teacher identity, authority/reference, reason,
and activation time. It does not create a Portfolio or bind the starter to one.

## Editing and extension

Do not edit installed starter records in place. To customize policy:

1. author a successor immutable Revision when the same Profile series should
   evolve;
2. use a local Overlay and explicit Composition for bounded local additions or
   replacements; or
3. create a separate Profile Family/series for meaningfully distinct policy.

No mechanism should infer a local policy from `purpose_kind` alone.

## Candidate vocabulary

Starter section eligibility must use current Vitrine Candidate kinds rather than
producer package names. The v1 starter vocabulary is:

```text
assessment_summary
feedback
student_work
```

When Candidate/adaptor vocabulary changes, update the starter catalog only
through a reviewed contract change. Do not add producer imports or package
requirements to make a starter appear more specific.

## Validation

Run the focused starter validator:

```text
python scripts/validate_starter_profiles.py
```

Run starter-focused tests and static checks:

```text
python -m pytest tests/test_starter_profiles.py tests/test_profile_cli.py tests/test_profile_menu.py
python -m ruff check vitrine/starter_profiles.py vitrine/profile_cli.py vitrine/profile_menu.py scripts/validate_starter_profiles.py scripts/smoke_test_starter_profiles_wheel.py
python -m mypy vitrine/starter_profiles.py vitrine/profile_cli.py vitrine/profile_menu.py scripts/validate_starter_profiles.py scripts/smoke_test_starter_profiles_wheel.py
```

After building distributions, validate the isolated installed-wheel path with
only the exact Core wheel and Vitrine wheel:

```text
python scripts/smoke_test_starter_profiles_wheel.py <vitrine-wheel> <core-wheel>
```

The repository-level validator includes both checks. See
[Issue #63 starter Profile validation](../validation/issue-63-starter-profile-validation.md)
for the acceptance matrix.
