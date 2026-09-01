# Installed Producer Reader Services v1

- **Issue:** #58 — Define installed producer-reader invocation and authorization services
- **Milestone:** v0.3.0 — Consume released producer evidence and guide real improvement/showcase portfolios
- **Status:** Implemented runtime contract
- **Service contract:** `vitrine_producer_reader_service_v1`
- **Installed reader contract:** `vitrine_installed_producer_reader_v1`

## Purpose

Issue #58 supplies the shared Vitrine runtime boundary between an exact Core
Publication Record and a producer-owned validated public manifest model.

The authoritative sequence is:

```text
canonical Core state
-> exact Vitrine adapter selection
-> source-read authorization
-> Core manifest containment/digest verification
-> exact immutable manifest bytes
-> installed producer public reader
-> validated producer public model
-> pure Vitrine projection
-> Candidate/Profile policy
```

This issue does not implement the ScoreForm, Quillan, or Concord live projection
adapters. Those remain #59, #60, and #61.

## Authoritative reader identities

Reader identity is derived only from `vitrine.released_producer_contracts`, the
machine-readable #57 audit. Vitrine does not maintain a second compatibility
table.

```text
scoreform
  distribution: scoreform
  module: scoreform.academic_result_reader
  symbol: read_academic_result_manifest

quillan
  distribution: quillan
  module: quillan.academic_result_reader
  symbol: read_academic_result_manifest

concord
  distribution: pds-concord
  module: concord.academic_result_reader
  symbol: read_academic_result_manifest
```

The audited release versions are reproducibility anchors only. Installed package
version is not a semantic adapter-selection key.

## Lazy installed-reader binding

`InstalledProducerManifestReader` implements the existing
`ProducerManifestReader` protocol.

`build_audited_installed_producer_reader()` and
`build_audited_installed_producer_readers()` construct bindings without importing
ScoreForm, Quillan, or Concord.

Producer distribution lookup, module import, and symbol resolution happen only
when `read(bytes)` is explicitly invoked.

```text
package installed != integration enabled
reader available != live adapter registered
live adapter registered != source read authorized
```

The ordinary `build_adapter_registry()` remains empty until #59-#61 register
producer-specific projection adapters.

## Reader failures

Stable reader distinctions are:

```text
reader.unavailable
  expected producer distribution cannot be resolved

reader.incompatible
  audited public module/symbol is missing or has the wrong API shape

reader.validation_failed
  producer public reader rejects or otherwise fails on the verified bytes
```

Underlying producer exception text is not copied into ordinary Vitrine
diagnostics. The original exception may remain chained internally.

There is no fallback to a fixture reader, alternate symbol, generic JSON parser,
newest package API, or producer-private parser.

## Source-read authorization

The shared authorization types are:

```text
SourceReadAuthorizationRequest
SourceReadAuthorizationDecision
SourceReadAuthorizationGate
```

Outcomes remain exactly:

```text
allowed
denied
unresolved
```

`authorize_source_read()` fails closed. Gate exceptions, invalid decisions, and
unresolved decisions do not permit source access.

Authorization occurs before manifest existence, containment, or digest checks.
A denied or unresolved request therefore cannot reveal whether the manifest
currently exists.

Candidate services continue to re-export backward-compatible authorization
types and map lower-level failures to the existing `candidate.*` family.

## Verified immutable manifest bytes

`read_verified_publication_manifest_bytes()` preserves the established Candidate
integrity contract:

1. reject symlink traversal in the lexical manifest path;
2. delegate canonical containment and bound-digest verification to Core;
3. read the verified file as immutable `bytes`;
4. independently SHA-256 hash the exact bytes that will be passed to the reader;
5. compare again with the canonical Publication Record digest.

The second hash closes the interval between Core verification and producer-reader
invocation.

No manifest body or absolute source path is persisted by this service.

## Shared authorized-read operation

`read_authorized_producer_manifest()` is the common runtime operation.

It returns transient `AuthorizedProducerManifestReadResult` containing:

```text
authorization decision
reader descriptor
exact manifest bytes
validated producer public model
```

The result is transient orchestration state, not a new durable Vitrine record.

Its order is fixed:

```text
authorize_source_read(...)
-> read_verified_publication_manifest_bytes(...)
-> reader.read(exact_bytes)
```

## Candidate integration

Candidate orchestration now consumes `read_authorized_producer_manifest()`
directly.

The Candidate path still owns:

```text
bounded catalog proposal
canonical Publication reload
exact registration reload
series/withdrawal policy
Core producer compatibility
exact adapter selection
Portfolio Subject resolution
Profile eligibility
Candidate Evaluation/persistence
final source-stability recheck
```

The shared #58 service does not choose a current publication, infer Candidate
worth, or persist anything.

## Core producer Profile discovery

`build_installed_producer_registry()` is the explicit Vitrine production-facing
constructor for installed Core Publication Producer Profiles.

It delegates to Core's `build_publication_producer_registry(...,
discover_installed=True)` rather than reimplementing Core entry-point discovery.

`default_workflow_dependencies()` remains fail-closed:

```text
empty producer Profile registry
empty live adapter registry
unresolved source-read authorization
unconfigured Snapshot providers
```

Importing or installing a producer does not auto-enable a Vitrine integration.

## Manifest authorization versus Artifact authorization

#58 authorizes and reads the Publication manifest only.

It does not authorize producer Artifacts.

Quillan Artifact authorization remains #60 through:

```text
quillan.academic_result_artifacts
```

Concord Artifact authorization remains #61 through:

```text
concord.academic_result_artifacts
```

Those producer-owned boundaries retain `allowed`, `denied`, and `unresolved`
outcomes for exact Artifact requests.

Vitrine Snapshot build authority remains separate again.

```text
manifest source-read authorization
!= producer Artifact authorization
!= Snapshot build authority
!= disclosure authorization
```

ScoreForm `retained_source_path` remains provenance only and is not an Artifact
access mechanism.

## Dependency and import boundary

Vitrine retains only its Core runtime dependency. ScoreForm, Quillan, and
pds-concord remain optional installed integrations.

Constructing the audited installed-reader catalog performs no sibling producer
imports. Actual import occurs only at explicit reader invocation.

## Downstream handoff

### #59

Receives the installed ScoreForm reader, exact authorized manifest bytes, and a
validated ScoreForm public model. #59 implements only ScoreForm-to-Vitrine
projection semantics.

### #60

Receives the installed Quillan manifest reader and validated Quillan public
model. #60 separately implements Quillan projection plus producer-owned Artifact
authorization/resolution.

### #61

Receives the installed Concord manifest reader and validated Concord public
model. #61 separately implements Concord projection plus producer-owned Artifact
authorization/rendering.

### #62

Receives stable distinctions for unsupported semantic contracts, Profile
compatibility, source authorization, manifest integrity, reader availability,
reader incompatibility, reader validation failure, and fixture/live separation.

## Validation

Run:

```powershell
python scripts/validate_producer_reader_services.py
python -m pytest tests/test_producer_reader_services.py
python -m pytest tests/test_workflow_context.py
python scripts/validate_candidate_discovery.py
```

The complete repository validator also runs the #58 contract validator.


## Exact-wheel qualification

Issue #58 also provides an explicit release-qualification harness:

```text
scripts/qualify_installed_producer_readers.py
```

This is a release/audit acceptance surface, not a runtime compatibility gate.

The harness:

1. locates the exact #57-audited Core 0.6.3, ScoreForm 0.11.0, Quillan 0.10.0,
   and Concord 0.3.0 wheel filenames;
2. verifies every wheel SHA-256 against `vitrine.released_producer_contracts`;
3. creates a fresh temporary virtual environment;
4. installs those exact wheels;
5. proves constructing Vitrine's audited installed-reader bindings performs no
   sibling producer import;
6. invokes the ScoreForm, Quillan, and Concord reader bindings on canonical
   synthetic Academic Result Manifest bytes;
7. requires each returned producer public model to preserve the exact producer
   and manifest-contract identity.

ScoreForm and Quillan qualification bytes are Vitrine-owned synthetic canonical
manifests shaped only to the released public contract. Concord canonical bytes
are produced in a separate fresh process using Concord's released public
manifest value/writer API, then consumed in a second fresh process so lazy-reader
import behavior remains observable.

Run from the repository root with the audited wheels in Downloads:

```powershell
python scripts/qualify_installed_producer_readers.py
```

or specify another directory:

```powershell
python scripts/qualify_installed_producer_readers.py --wheel-dir C:\path\to\wheels
```

The exact release-version assertions in this harness establish reproducibility
of the #57 audit anchor only. `InstalledProducerManifestReader` itself continues
to use semantic contracts rather than distribution-version equality.
