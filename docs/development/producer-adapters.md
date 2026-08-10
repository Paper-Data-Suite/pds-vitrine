# Developing Producer Projection Adapters

Issue #32 implements the pure producer-reader and Vitrine projection boundary.

## Modules

- `vitrine/producer_adapters.py` — support request/key, declaration, reader and
  adapter protocols, transient projection models, structured errors, registry,
  and ordinary registry constructor.
- `vitrine/development_adapters.py` — strict ScoreForm-, Quillan-, and
  Concord-shaped development readers/adapters plus explicit fixture registry.
- `vitrine/adapter_cli.py` — non-mutating power-user diagnostics.
- `scripts/validate_producer_adapters.py` — synthetic boundary validator.
- `scripts/smoke_test_adapter_wheel.py` — isolated installed-wheel adapter smoke.

## Selection rule

Never select by module ID alone or introduce a fallback parser. Build an exact
`ProducerAdapterSupportRequest`, then call:

```python
adapter = registry.select_adapter(request)
```

Zero matches are unsupported. Multiple matches are a conflict. Do not add a
"most specific", newest, or highest-version tie-break.

## Reader rule

A reader accepts immutable bytes only. Path resolution, Core digest verification,
authorization, and producer package discovery belong outside this module.

Strict development readers require byte-for-byte canonical fixture JSON. Keep
producer validation separate from Vitrine projection when adding future live
integrations.

## Fixture rule

Ordinary runtime code uses:

```python
from vitrine.producer_adapters import build_adapter_registry

registry = build_adapter_registry()
```

Issue #32 intentionally returns an empty ordinary registry.

Development/test code must opt in:

```python
from vitrine.development_adapters import (
    build_development_fixture_adapter_registry,
)

registry = build_development_fixture_adapter_registry()
```

Never feed a fixture adapter through `build_adapter_registry()`. That fails with
`adapter.fixture_not_enabled` by design.

## Privacy checks

When extending a fixture, include negative markers for sensitive fields and prove
those markers never occur in `ProducerProjectionBatch` or diagnostics.

Current fixtures exercise:

- ScoreForm answer-key/detector/route/scan-review exclusions;
- Quillan private teacher feedback, notes, native paths, and routing exclusions;
- Concord relationship and Score-target distinctions.

## Foundational graph compatibility

Adapter declarations and projection batches are transient runtime configuration
and observations. Do not add them as required `VitrineRecordGraph` collections.
The issue #28 fixture bytes and hashes must remain unchanged.

## Focused validation

```powershell
python -m pytest `
  tests\test_producer_adapters.py `
  tests\test_adapter_cli.py `
  tests\test_validate_producer_adapters.py `
  -q
python scripts\validate_producer_adapters.py
python -m ruff check .
python -m mypy
```

The complete repository gate additionally builds the wheel/sdist, checks package
contents, and runs the isolated adapter wheel smoke without ScoreForm, Quillan,
or Concord installed.

## Fixture payload location

Synthetic JSON lives under:

```text
fixtures/producer-adapters/
  scoreform/manifest.json
  quillan/manifest.json
  concord/manifest.json
```

These files belong to the source distribution/repository, not the runtime wheel.

## Future live integrations

A future live adapter may bind an installed producer-owned public reader, but it
must define explicit package trust/discovery and exact support declarations in a
separate integration issue. Do not turn issue #32 fixture infrastructure into an
automatic plugin loader.

## Candidate consumer

Issue #33 now consumes this boundary through
[`candidate-discovery.md`](candidate-discovery.md). The Candidate service builds
support requests only from canonical Core Publication/registration state,
requires explicit source-read authorization, verifies the exact manifest bytes,
and only then invokes the selected reader/adapter. This does not change the #32
fixture isolation or establish a live producer integration.
