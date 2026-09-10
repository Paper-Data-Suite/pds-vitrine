# Snapshot Build Workflows v1

## Status

Implemented by issue #35 for the v0.2.0 runtime foundation.

This contract describes Vitrine's executable immutable Snapshot build pipeline.
It is subordinate to accepted ADR 0007 and preserves the frozen Snapshot record
shapes introduced by issue #28.

## Scope

One exact working curation state is transformed through:

```text
WorkingPortfolioCompositionRevision
+ WorkingPortfolioCompositionInventory
+ AudienceContext
  -> SnapshotSeries
  -> SnapshotBuildRequest
  -> SnapshotBuildPlan
  -> SnapshotBuildAttempt
  -> exact source acquisition / deterministic rendering
  -> final verification
  -> SnapshotMaterializationRecord
  -> SnapshotEntry / SnapshotOmission
  -> deterministic internal SnapshotManifest
  -> SnapshotSeal
  -> immutable SnapshotEdition
  -> SnapshotExportArtifact(directory_package)
  -> optional explicit SnapshotCurrentPointerRevision
```

The builder freezes curation; it does not recalculate curation, grading,
proficiency, recipient authorization, disclosure permission, or producer-native
state.

## Frozen compatibility

The serialized shapes of these issue #28 records remain unchanged:

```text
SnapshotMaterializationRecord
SnapshotEntry
SnapshotOmission
SnapshotManifest
SnapshotSeal
SnapshotEdition
```

Snapshot workflow/history is additive through records including:

```text
SnapshotSeries
SnapshotBuildRequest
SnapshotBuildPlan
SnapshotBuildAttempt
SnapshotBuildAttemptResult
SnapshotMaterializationProvenance
SnapshotEditionBuildProvenance
SnapshotExportArtifact
SnapshotCurrentPointerRevision
```

Additive Snapshot workflow records are validated by `vitrine.snapshot_state` and
are not added to the frozen graph envelope.

## Governing distinctions

```text
Composition != Snapshot
Build Request != Build Plan
Build Plan != Build Attempt
Build Attempt != Edition

producer manifest != source Artifact
source Artifact != acquired source bytes
acquired source bytes != copied Snapshot bytes

Materialization != Entry
Entry != Manifest
Manifest != Seal
Seal != Edition
Edition != Export Artifact

Audience Context != recipient authorization
curation approval != disclosure authorization

producer digest claim != acquired-source digest
acquired-source digest != output digest
output digest != Manifest digest
Manifest digest != logical-inventory digest
logical-inventory digest != Export inventory digest
```

A checksum is an integrity claim only. It is not a signature, authorization
decision, consent decision, or proof of lawful disclosure.

## Exact curation input

A Build Request binds one exact:

```text
Portfolio
Portfolio Subject
Profile Binding
Profile Revision
Working Portfolio Composition Revision
Working Portfolio Composition Inventory
Audience Context
```

The Composition is the sole curation input. After a Plan is persisted, the
builder does not follow current Selection, Placement, Arrangement, Annotation,
Reflection, Review, Candidate, or Composition pointers to choose replacements.

A material change requires a successor Request/Plan and, if sealed, a successor
Edition.

## Series

`SnapshotSeries` provides durable Snapshot identity for one exact Portfolio,
Subject, Profile/Audience purpose context.

Edition identity is:

```text
snapshot_series_id + edition_number
```

It is not a content hash. Distinct Editions may contain identical bytes.

## Build Request

`SnapshotBuildRequest` records build intent without source bytes or an Edition
claim. It preserves exact Composition/Audience/Profile context, requested export
formats, actor/time, curation Review references, and optional idempotency.

For v0.2 the supported requested export format is:

```text
directory_package
```

Exact reuse of one idempotency key returns the existing Request. The same key
with changed intent is a conflict.

## Build Plan

`SnapshotBuildPlan` is immutable and freezes every execution decision:

- exact Request and Series;
- exact Composition revision;
- exact producer-backed Entry Plans;
- exact generated Entry Plans;
- explicit output paths and media types;
- explicit renderer identity/configuration/template digests;
- exact generated input references;
- explicit permitted omission behavior;
- explicit Export Plans;
- required curation Review references;
- acknowledged unresolved obligations;
- path/digest/builder contracts;
- predecessor Plan where applicable;
- deterministic SHA-256 Plan fingerprint.

A material Plan change creates a successor Plan. Persisted Plans are never
edited.

## Ordering

Placement-bound logical order is validated from:

```text
Profile section order
-> exact Arrangement IDs frozen by the Composition
-> Placement order within each Arrangement
-> explicit plan_position
```

Opaque IDs, timestamps, filenames, storage order, and filesystem enumeration are
not ordering authority.

Generated unbound Entries use explicit `plan_position`; they do not retarget
mutable curation.

## Path policy

Snapshot content paths are normalized relative POSIX paths.

Reject:

- empty paths;
- leading/trailing whitespace;
- empty, `.` or `..` components;
- backslashes;
- NUL;
- colon/drive/URI syntax;
- absolute or rooted Windows paths;
- containment escapes;
- Unicode-normalization/case-fold collisions.

Canonical custody paths must not use student names or other PII.

## Byte custody

Snapshot bytes are outside canonical JSON state:

```text
<workspace>/vitrine/
  state/
  snapshots/
    staging/<attempt-id>/
      content/
      internal/
    editions/<series-id>/<edition-number>/
      content/
      internal/manifest.json
    exports/<series-id>/<edition-number>/<export-artifact-id>/
    .locks/<series-id>.json
```

Staging is noncanonical and never proves successful materialization or sealing.

Edition and Export destinations are exclusively published and never merged or
overwritten.

## Series/build lock

Snapshot source acquisition/rendering uses a Series/build lock distinct from the
short #29 canonical-state write lock.

The lock:

- is created exclusively;
- contains only Series, Plan, Attempt, acquisition timestamp, and contract data;
- is canonical JSON with an independently inspectable SHA-256;
- belongs to one exact Attempt/Plan;
- is never cleared because of age;
- is released only when exact identity and expected lock digest match;
- remains for explicit recovery if safe release cannot be established.

Only one incomplete Attempt may exist in one Series.

Read-only inspection can distinguish lock absence, malformed lock state,
ownership mismatch, unresolved staging, and terminal Attempt state.

## Build authority

`SnapshotBuildAuthorityGate` is injected and fail-closed.

Outcomes:

```text
allowed
denied
unresolved
```

`allowed` requires an authority reference.

This decision permits only the local Snapshot build/custody operation. It does
not establish recipient authentication, disclosure authorization, consent,
issuance, submission, or delivery.

Denied or unresolved authority is evaluated before source access and produces no
copied source bytes or Edition.

## Source providers

Producer-backed copying uses an exact `SnapshotSourceProviderRegistry`.

Provider selection matches:

```text
producer_module_id
projection_kind
projection_contract_version
artifact_kind
representation_kind
```

No wildcard or generic private-file provider is used.

A provider may return exactly one of two bounded runtime result shapes:

```text
SnapshotSourceResult
  -> approved canonical filesystem root + exact relative locator
  -> Vitrine performs containment, regular-file, reread, and stability checks

SnapshotAuthorizedSourceBytesResult
  -> producer-authorized immutable bytes + bounded media/digest/size metadata
  -> Vitrine never receives or reconstructs a producer-native source path
```

Authorized-byte results use one of two exact runtime acquisition contracts:

```text
authorized_source_bytes_v1
authorized_source_bytes_deferred_media_v1
```

`authorized_source_bytes_v1` preserves the original exact-media rule. The
second contract is a narrow post-#61 extension for producers such as released
Quillan 0.10.0 whose public manifest cannot expose exact Artifact media before a
separate producer-owned authorization step.

`SnapshotAuthorizedSourceBytesResult` is an additive runtime boundary, not a new
persisted Snapshot record. `SourceArtifactReference.source_locator` was already
nullable, so a copied-source Plan may preserve exact Artifact identity without
fabricating a path when the producer owns artifact resolution.

Build authority remains outside producer artifact authorization. Vitrine checks
Snapshot build authority before provider resolution; a live Quillan or Concord
provider must then perform its producer-owned artifact authorization before native
I/O and return bytes only after an `allowed` decision.

Development fixture providers are explicit test infrastructure, not production
producer readers.

## Exact-byte copying

For every copied Entry:

1. validate Plan/Attempt/Entry binding;
2. require build authority;
3. select one exact provider;
4. resolve one exact planned Publication/Artifact;
5. verify provider, Publication, Artifact, and representation identity;
6. acquire source bytes through one approved result mode;
7. independently SHA-256 acquired bytes;
8. verify producer/provider digest claims when supplied;
9. verify declared sizes when supplied;
10. exclusively write staging bytes;
11. close/reopen and SHA-256 staged output;
12. verify staged size and digest.

Filesystem result mode additionally:

1. requires the frozen Artifact to carry the exact approved source locator;
2. rejects unsafe/link/reparse/nonregular paths;
3. confirms provider stability;
4. rereads/re-hashes the original source;
5. fails closed if that source changed.

Authorized immutable-byte mode instead:

1. requires one supported authorized-byte acquisition contract;
2. validates any provider-returned digest and byte size;
3. performs no Vitrine-side producer filesystem lookup or reread;
4. records source stability as `not_applicable` because the acquired value is the
   producer-authorized immutable byte sequence itself.

For `authorized_source_bytes_v1`, provider-returned, Entry-Plan, and source-Artifact
media types must remain exactly equal.

For `authorized_source_bytes_deferred_media_v1`:

1. the immutable `SnapshotEntryPlan.media_type` and
   `SourceArtifactReference.media_type` must both be exactly
   `application/octet-stream`;
2. that value means "not knowable before authorization" and is not a wildcard;
3. the exact source provider descriptor must declare a nonempty closed
   `concrete_media_types` allowlist;
4. the producer-returned media type must belong to that allowlist;
5. the planned target path must be suffix-neutral so the Plan does not claim a
   representation it cannot yet know;
6. the concrete returned media type is carried in `SnapshotCopiedBytesResult` and
   persisted as the existing `SnapshotEntry.media_type` and internal
   Manifest/logical-inventory media type.

No frozen Snapshot record shape changes. Existing filesystem, generated,
ScoreForm, Concord, and `authorized_source_bytes_v1` semantics remain unchanged.

The producer digest claim, acquired-source digest, and output digest remain
distinct provenance values even when exact copying makes the latter two equal.

No source successor is followed after planning, and no temporary native-looking
path may be fabricated to bridge a producer-owned artifact API.


## Deterministic renderers

Structured/canonical Vitrine content uses an exact `SnapshotRendererRegistry`.

Renderer selection matches:

```text
renderer_id
renderer_version
renderer_contract_version
```

Generated Entry Plans preserve exact input references and mandatory
configuration digest; template digest is preserved where applicable.

A generated renderer must return the exact planned media type and exact
renderer/configuration/template identities. Output is written exclusively,
reopened, and independently SHA-256 verified.

Generated Vitrine Entries do not fabricate producer Artifact provenance.

Because frozen `SnapshotOmission` requires Candidate/Selection/Placement
provenance, generated Entries do not use permitted-omission behavior in v0.2.
Renderer failure is blocking.

## Attempts

The Attempt start is canonical before staging/source execution.

`SnapshotBuildAttempt` preserves Plan, attempt number, builder, actor/time, and
staging reference.

Completion is a separate immutable `SnapshotBuildAttemptResult`.

Terminal outcomes:

```text
failed
sealed
partial_success_after_seal
durability_uncertain
abandoned_after_explicit_recovery
```

Failed Attempt numbers are consumed. An Attempt without a terminal Result is
incomplete; age does not classify it.

## Prepared pre-seal state

Successful source acquisition/rendering produces transient typed prepared state.
It does not fabricate frozen `SnapshotMaterializationRecord`,
`SnapshotEntry`, or `SnapshotOmission` before a real Edition identity exists.

Prepared dispositions are internal execution state. Final sealed per-item
dispositions are:

```text
included
reference_only
omitted_permitted
failed_blocking
```

Every planned item must be accounted for. Silent absence is invalid.

## Permitted omissions

A source-backed failure becomes an Omission only when the exact Plan permits that
specific v0.2 omission reason.

Examples include explicitly preplanned:

```text
source_unavailable
representation_unavailable
audience_prohibited
```

Integrity failures are not converted into convenient omissions.

Sealed Omissions reuse frozen `SnapshotOmission` and retain exact
Candidate/Selection/Placement and Audience Context provenance.

## Final verification and sealing

Before sealing, Vitrine reopens staging and proves:

- the Attempt is open and owns the exact Series lock;
- staged file inventory exactly matches prepared byte Entries;
- there are no unexpected files;
- paths are safe and unique;
- every staged byte size/digest still matches;
- every planned item has one final disposition;
- every Omission was explicitly permitted;
- copied/generated provenance is complete;
- Request/Plan/Composition/Profile/Audience contexts agree.

Only then may Vitrine allocate the real Edition identity and create frozen
Materialization/Entry/Omission records.

## Internal Manifest

Every sealed Edition has one deterministic internal manifest byte sequence at:

```text
internal/manifest.json
```

Canonical policy:

```text
UTF-8
JSON object
deterministic key ordering
compact separators
no NaN/infinity
LF terminal newline
explicit ordered logical inventory
lowercase SHA-256
```

The internal manifest does not contain its own digest.

It includes exact Build/Edition context and a mapping from every Entry Plan to
its final disposition and applicable Materialization/Entry/Omission IDs.

The internal manifest is Vitrine-owned metadata and is not exported by default.

## Digest layers

`SnapshotSeal.manifest_digest` hashes exact canonical `manifest.json` bytes.

`SnapshotSeal.logical_inventory_digest` hashes an Edition-independent canonical
logical projection containing byte-bearing Entry identity/path/media/class/size/
output digest and explicit Omission inventory.

The logical digest excludes filesystem metadata and Edition-incidental timestamp
data.

`SnapshotExportArtifact.directory_inventory_digest` independently hashes the
exported regular-file inventory:

```text
relative POSIX path
byte size
SHA-256
```

These are separate integrity claims.

## Edition publication and partial success

Sealing and filesystem publication are separate durability boundaries.

The implementation verifies staging, computes Manifest/Seal/Edition state,
commits canonical sealed records, then exclusively publishes immutable Edition
custody and terminalizes the Attempt.

If Edition custody publication or later lock cleanup fails after canonical
sealing, durable Edition history is preserved and the Attempt records:

```text
partial_success_after_seal
```

If canonical persistence reports uncertain durability, Vitrine reports
`durability_uncertain`, preserves ambiguous targets for explicit recovery, and
does not safely reuse the identity.

## Historical Edition verification

`verify_snapshot_edition(...)` is producer-independent.

It verifies from Vitrine canonical state plus Vitrine-owned sealed custody:

- the complete pure Snapshot-state projection, including Edition build provenance,
  Materialization provenance, Omissions, and exact Request/Plan/Attempt context;
- Edition/Manifest/Seal identity;
- canonical internal Manifest bytes;
- Manifest digest;
- logical-inventory digest;
- exact Entry inventory;
- canonical Materialization presence;
- path containment and no links/reparse objects;
- each Entry byte size and output SHA-256;
- no unexpected Edition content/internal files.

Producer correction, withdrawal, supersession, or unavailability after sealing
does not prevent verification of the historical bytes Vitrine sealed.

## Directory Export Artifact

v0.2 implements only:

```text
directory_package
```

An Export is distinct from the Edition.

`create_snapshot_directory_export(...)` derives the exact Export Plan from
immutable Edition build provenance and Build Plan state, verifies the Edition,
copies only intended Entry bytes, verifies staging and final file inventory, and
persists `SnapshotExportArtifact` after publication verification.

The internal Manifest is not part of the default Export.

Exact semantic replay returns the already persisted immutable Export Artifact;
it does not rewrite bytes or create a duplicate Artifact.

## Export verification

`verify_snapshot_export(...)` is read-only and producer-independent.

It verifies:

- exact persisted Export Artifact;
- underlying Edition verification;
- included/excluded canonical Entry partition;
- expected custody path;
- no missing, unexpected, linked, or unsafe files;
- deterministic directory-inventory SHA-256.

## Current Edition pointer

Current Edition selection is explicit through append-preserving
`SnapshotCurrentPointerRevision`.

It is not inferred from:

- greatest Edition number;
- seal time;
- latest Export;
- filename/directory order;
- digest.

Promotion requires expected canonical state plus expected pointer predecessor and
current Edition. A pointer only advances to a newer Edition.

Sealing and promotion are separate. Pointer failure never invalidates an already
sealed Edition.

## Recovery

Read-only recovery inspection reports:

- whether an Attempt is terminal;
- staging presence/residue;
- matching or conflicting Series build lock;
- canonical sealed Edition association, including post-seal publication failure
  where the canonical Edition's manifest remains in staging.

Explicit abandonment is allowed only for an unresolved unsealed Attempt and
produces:

```text
abandoned_after_explicit_recovery
```

Staging residue is preserved. An exact matching lock may be released; an
ambiguous or foreign lock is preserved with a finding.

There is no age-based auto-clear, auto-adopt, auto-delete, auto-promote, or
auto-repair. If Attempt staging already contains `internal/manifest.json`,
explicit abandonment is refused even when the allocated Edition is not visible
in current canonical state; this quarantines durability uncertainty and prevents
Edition-number reuse.

`inspect_snapshot_custody(...)` provides a broader producer-independent audit.
Its privacy-minimal findings distinguish incomplete and failed Attempts, orphan
staging, build locks, ambiguous Edition targets, canonical Editions missing
custody, custody Editions missing canonical state, corrupt Manifest/Entry
custody, orphan/corrupt Exports, and durability uncertainty. The audit never
adopts, deletes, promotes, or repairs a target.

## Producer boundaries

### ScoreForm-shaped fixture

Structured attempt summaries are explicitly rendered. In the committed fixture
slice the renderer configuration envelope includes the exact structured-input
SHA-256, while Plan input references bind the exact Candidate/Selection/Placement/
Evaluation. A changed structured payload therefore fails the Plan-bound renderer
configuration check rather than silently changing output. Attempts remain
distinct; Vitrine does not infer best/latest/official/grading attempt, Grade,
proficiency, or mastery. Private scans, answer keys, detector data, routes, and
review notes are not rendered.

### Quillan-shaped fixture

Only exact approved student-work and student-facing feedback projections may be
copied by the development fixture provider. Work and feedback are distinct
Candidates, Selections, Placements, Materializations, and Entries.

Private teacher notes, private feedback, unselected evidence, and arbitrary
native files remain outside the provider inventory.

### Concord-shaped fixture

The generic Snapshot contracts preserve producer source/projection identity and
do not infer Group membership as authorship or Group Score as individual Score.

### Portia

Issue #35 adds no ordinary Portia materialization and no suppressed-source
existence disclosure.

### Meridian

Issue #35 adds no Meridian dependency, grading policy, Grade, proficiency,
mastery, or reporting behavior.

## Fixture-backed validation

`scripts/validate_snapshot_workflows.py` executes a development-only
representative slice with committed deterministic bytes:

- copied Quillan-shaped selected student work;
- copied Quillan-shaped student-facing feedback;
- rendered structured ScoreForm-shaped attempt summary;
- generated exact student Reflection revision;
- one exact preplanned source-unavailable Omission;
- one separate unpermitted blocking source failure;
- one sealed immutable Edition;
- one independently verified directory Export Artifact;
- explicit Current Pointer;
- producer-independent verification after the source fixture is removed.

It also verifies the two locked issue #28 fixture SHA-256 values.

The fixtures are synthetic and do not establish live producer integration.

## Installed-wheel boundary

`scripts/smoke_test_snapshot_wheel.py` installs only the authenticated Core 0.6
wheel plus the built Vitrine wheel, imports the generic Snapshot runtime, verifies
that sibling producer packages are absent, and confirms import has no
current-directory side effects.

## Non-goals

Issue #35 does not implement:

- recipient authentication/authorization;
- consent;
- production redaction;
- Issuance;
- Submission;
- upload/delivery;
- external receipts/outcomes;
- ZIP/PDF/HTML bundle formats;
- public hosting;
- Meridian grading policy;
- Grade/proficiency/mastery;
- automatic grading-attempt selection;
- producer mutation;
- ordinary Portia ingestion;
- Snapshot CLI/menu workflows.

Those remain separate downstream concerns.

## Upstream guided Working Composition boundary

Issue #67 freezes audience-neutral curation before this Snapshot contract
begins. Its Profile audience-rule projection is explanatory only: it creates no
Audience Context and makes no item-level Snapshot inclusion/omission decision.
Snapshot construction continues to require an exact immutable Composition plus
the exact downstream Audience Context and build-plan authority defined here.

## First-party Current Portfolio orchestration

Issue #68 adds a task layer over these canonical services; it does not replace
or collapse them. The contract is
`vitrine_build_export_current_portfolio_v1`. It requires #67
`reuse_exact_current`, selects one exact Profile audience rule, resolves an
exact Audience Context and Snapshot Series, freezes one deterministic Build
Plan, then uses the existing Request/Attempt/materialization/seal/verification
and directory Export services in order.

The first-party task keeps ScoreForm assessment summaries `reference_only`,
copies Quillan/Concord bytes only through an exact configured source provider,
and may generate bytes only for exact frozen supported Portfolio Reflection
revisions. Audience-prohibited content is an explicit planned omission; source
or authorization failures are not silently converted into omissions.

Successful Issue #68 build/export does not create a
`SnapshotCurrentPointerRevision`. Promotion remains an explicit separate
Snapshot operation. Export creation is also not disclosure authorization or
delivery. See [Build and Export Current Portfolio v1]
(build-export-current-portfolio-v1.md).

## Issue #69 attention handoff

Issue #69 consumes Snapshot state/custody as a read-only diagnostic projection.
Current Attempt selection follows explicit Series/Request/Plan predecessor heads
and the unique greatest canonical `attempt_number` for that exact Plan. Custody
findings are not all current attention: retained terminal failure is historical,
while incomplete Attempt, durability uncertainty, current integrity findings,
and exact current Export verification failures may require teacher follow-up.
Unscoped orphan custody is workspace-level unless canonical state establishes an
exact Portfolio owner.
