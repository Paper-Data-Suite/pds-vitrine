# Issue #62 Cross-Producer Compatibility Validation

This document records the acceptance boundaries and reproducible qualification
commands for issue #62.

## Frozen qualification provenance

The semantic support matrix is qualified against these audited releases:

```text
Core 0.6.3
ScoreForm 0.11.0
Quillan 0.10.0
Concord 0.3.0
```

These release numbers are reproducibility provenance. Runtime semantic support
continues to be determined by Core/Vitrine contract fields rather than package
version equality.

## Focused repository validator

```powershell
python scripts/validate_compatibility_diagnostics.py
```

The validator checks:

```text
diagnostic contract identity
exact ordinary live adapter registry
exact ScoreForm / Quillan / Concord support explanations
semantic mismatch preservation
fixture/live separation
ScoreForm Artifact not_applicable semantics
Quillan / Concord Artifact applicability
compatibility CLI parser surface
required issue #62 documentation
```

It deliberately does not require optional producer packages.

## Isolated wheel smoke

The complete repository validator builds the current Vitrine wheel and invokes:

```text
scripts/smoke_test_compatibility_wheel.py
```

The smoke installs only the Core wheel and Vitrine wheel. It proves that:

```text
issue #62 runtime modules are packaged
contract-only diagnostics work without sibling producers installed
known semantic mismatches remain unsupported
producer readiness can report absent optional packages safely
ScoreForm Artifact applicability remains not_applicable
no working-directory residue is created
```

## Complete repository gate

Use the same official Core wheel accepted by the repository validation flow:

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```

The complete gate covers the full pytest suite, Ruff, mypy, reusable validators,
documentation validation, representative Portfolio validation, package build,
twine check, distribution content validation, isolated wheel smokes, installed
end-to-end acceptance, and `git diff --check`.

If the repository's existing complete-validation command is intentionally pinned
to another accepted Core 0.6 wheel for a release-maintenance reason, use that
repository-authoritative wheel for the generic gate and run the exact issue #62
qualification below separately with Core 0.6.3.

## Exact released producer-wheel qualification

Place the exact #57-audited wheels in one directory, normally `Downloads`, then
run:

```powershell
python scripts/qualify_installed_producer_readers.py `
  --wheel-dir "$HOME\Downloads"
```

That qualification verifies the audited wheel filenames and SHA-256 digests,
constructs an isolated environment, exercises the installed public readers and
live adapters, executes the Quillan and Concord Artifact qualifications, and now
also requires the issue #62 installed-readiness diagnostics to report all three
producer integrations ready.

Expected audited producer wheels:

```text
scoreform-0.11.0-py3-none-any.whl
quillan-0.10.0-py3-none-any.whl
pds_concord-0.3.0-py3-none-any.whl
```

The qualifier also requires the audited Core 0.6.3 wheel recorded by
`vitrine.released_producer_contracts`.

## Acceptance invariants

The final issue gate must preserve all of the following:

```text
package version is not semantic compatibility
no nearest adapter/version fallback
no fixture substitution
Core compatibility codes remain authoritative
adapter.unsupported_contract remains authoritative
reader unavailable / incompatible / validation failure remain distinct
denied / unresolved authorization remain distinct
manifest missing / integrity failure remain distinct
Artifact unavailable / integrity failure remain distinct
no unauthorized source I/O
no raw producer exception text in CLI output
no Candidate / Selection / Snapshot creation or repair
```
