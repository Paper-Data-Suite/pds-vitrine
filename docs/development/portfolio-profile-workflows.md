# Developing Portfolio Profile workflows

Issue #31 implements the application layer for immutable improvement and showcase
Portfolio Profiles.

## Modules

- `vitrine/models/profiles.py` — foundational and supplemental Profile records.
- `vitrine/profile_state.py` — pure canonical Profile-history projection and
  validation.
- `vitrine/profile_services.py` — presentation-independent application services.
- `vitrine/profile_cli.py` — noninteractive power-user commands.
- `vitrine/profile_menu.py` — low-density teacher workflows.
- `scripts/validate_profile_workflows.py` — disposable end-to-end validation.

## Service rule

CLI and menu code must not reimplement Profile semantics. All mutation goes
through `profile_services` and #29 guarded persistence.

Mutating services receive the exact observed Vitrine state revision. A stale
actor decision fails rather than being replayed against a changed Profile state.

## No latest rule

Never add helper code that selects a Profile or Binding by `max(revision)`,
newest timestamp, filename, or catalog ordering. Use explicit lifecycle and
Binding predecessor heads.

## Requirements

Stable requirement continuity uses policy-bearing fields. Labels may change
without changing identity, while semantic policy changes require a new ID or an
explicit replacement.

The current slice does not evaluate complete Requirement findings.

## Overlay composition

Composition always references exact component and Overlay Revisions and writes a
self-contained effective Revision. Runtime consumers must never resolve a live
parent chain.

Conflict detection must run before canonical mutation. Weakening a controlling
required/prohibited rule is rejected rather than last-write-wins.

## Teacher UI density

After each teacher choice, clear the screen and redraw only the next decision's
context. Keep detailed history behind a separate explicit action. Profile JSON
is a CLI/import surface, not a default teacher screen.

## Validation

During development run:

```powershell
python -m pytest tests\test_profile_models.py tests\test_profile_services.py tests\test_profile_cli.py tests\test_profile_menu.py tests\test_validate_profile_workflows.py -q
python scripts\validate_profile_workflows.py
python -m ruff check .
python -m mypy
git diff --check
```

The full repository gate must also pass before merge.
