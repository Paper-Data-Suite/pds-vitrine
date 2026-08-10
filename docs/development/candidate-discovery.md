# Candidate discovery development

Issue #33 implements fixture-backed Core-to-Vitrine Candidate discovery in
`vitrine.candidate_services`.

## Runtime construction

Candidate services do not discover installed producers or enable fixtures on
import. Callers supply both registries and an authorization gate explicitly.

Production-shaped construction starts with an ordinary adapter registry and an
application-owned Core producer registry:

```python
from vitrine.producer_adapters import build_adapter_registry

adapter_registry = build_adapter_registry()
assert adapter_registry.adapters == ()
```

The repository's fixture-backed validation opts in separately:

```python
from vitrine.development_adapters import (
    build_development_fixture_adapter_registry,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
```

These development registries contain only `vitrine_*_fixture` identities. They
are not live sibling integrations.

## Request discipline

`CandidateDiscoveryRequest` requires:

- exact `portfolio_id`;
- attributable requesting actor;
- requested purpose;
- typed `PublicationCatalogQuery` with explicit bounded `limit`;
- exact expected Vitrine state revision.

Use `state="current"` for normal Candidate discovery. Other Core catalog states
may be useful for diagnostics but cannot silently create a positive Candidate.

## Authorization gate

Implement `SourceReadAuthorizationGate.authorize()` without reading producer
content. Return `SourceReadAuthorizationDecision(outcome="allowed")` only for an
explicitly authorized request. `denied` and `unresolved` stop before manifest
byte access.

The gate is intentionally not a complete authorization system. Do not use
Profile Binding, filesystem readability, adapter compatibility, or discovery as
an implicit permission grant.

## Candidate-kind mapping

The runtime mapping lives in `CANDIDATE_KIND_BY_ARTIFACT_KIND`. Extend it only
when a validated Vitrine `SourceArtifactReference.artifact_kind` has a documented
Profile Candidate vocabulary. Never infer a kind from a title, filename, MIME
type alone, or producer name.

## Subject resolution

Only exact `core_student` projected relationships can be resolved directly in
this slice. Resolution combines canonical class school year, publication class,
and projected student ID with existing Vitrine Subject links. Other producer
subject kinds require future explicit authority/crosswalks.

Do not infer Concord Artifact authorship from Group Membership or documented
contribution.

## Persistence

All projected sources in one discovery call are evaluated from the same Vitrine
state revision. New negative Evaluations and positive Evaluation/Candidate pairs
are committed together using that exact expected revision.

Do not split a positive Evaluation and Candidate into separate commits.

## Focused validation

```powershell
python -m pytest `
  tests\test_candidate_services.py `
  tests\test_candidate_discovery.py `
  tests\test_validate_candidate_discovery.py `
  -q

python scripts\validate_candidate_discovery.py
```

The complete repository gate adds Ruff, strict Mypy, package checks, and an
isolated Core+Vitrine Candidate-service wheel smoke.

## Boundary reminders

```text
catalog row != canonical publication
compatibility != authorization
authorization != manifest integrity
Candidate != Selection
Candidate != disclosure authorization
Candidate != Grade/proficiency/mastery
```
