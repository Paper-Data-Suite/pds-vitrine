# Build and Export Current Portfolio v1

Issue #68 defines Vitrine's first-party task for turning one exact current
Working Composition into one verified immutable Snapshot Edition and one verified
directory Export Artifact.

Contract identity:

```text
vitrine_build_export_current_portfolio_v1
```

## Scope

The canonical task pipeline is:

```text
current Working Composition
-> exact Profile Audience Rule
-> exact Audience Context
-> Snapshot Series
-> Snapshot Build Request
-> immutable Snapshot Build Plan
-> Snapshot Build Attempt
-> exact source acquisition / deterministic Vitrine rendering
-> final verification
-> Snapshot Seal
-> immutable Snapshot Edition
-> Edition verification
-> directory Export Artifact
-> Export verification
```

The task composes existing durable records and services. It does not add a
second durable Build/Export wizard or a synthetic portfolio-export record.

## Governing distinctions

```text
working curation != Working Composition
Working Composition != Audience Context
Working Composition != Snapshot

Build preparation != Build Request
Build Request != Build Plan
Build Plan != Build Attempt
Build Attempt != Snapshot Edition
Snapshot Edition != Export Artifact
Export Artifact != delivery

Profile Audience Rule != recipient authorization
Curation Review != disclosure authorization
Snapshot build authority != producer Artifact authorization
verification != disclosure permission

reference_only != omitted
omitted_permitted != silently absent
source unavailable != successor source
historical source != invalid source

Reflection != proof of improvement
Score != proficiency
checksum != signature
checksum != authorization
```

The task creates and verifies one exact package. It does not decide whether that
package may be disclosed to a particular person.

## Exact current Working Composition

The task begins only from the Portfolio's explicit current
`WorkingPortfolioCompositionPointerRevision`.

It reuses the issue #67 preparation boundary and requires:

```text
Working Composition exists
AND
guided Working Composition disposition == reuse_exact_current
```

If #67 preparation predicts `create_initial` or `create_successor`, preparation
fails before the first write and directs the caller back to Working Composition.

Every active Selection represented by the current Composition must have an exact
Placement. Any `unplaced_selection_ids` block the first-party task. The planner
does not invent a section, fabricate an unplaced section, or silently omit the
Selection.

## Read-only preparation

`prepare_current_portfolio_build(...)` returns transient
`CurrentPortfolioBuildPreparation` state.

Preparation:

- writes no canonical Vitrine record;
- reads no producer Artifact bytes;
- requests no Snapshot build authority;
- requests no producer Artifact authorization;
- creates no Audience Context, Series, Request, Plan, Attempt, Edition, or Export.

The preparation exposes the exact observed Vitrine state revision, Portfolio,
Subject, Profile Binding/Revision, current Composition pointer/revision, #67
preparation fingerprint/disposition, Composition Inventory, ordered sections and
Placements, active Selections, Audience Rule, Context/Series resolution, Reviews,
obligations, item-level materialization policy, generated Reflections, Export
partition, warnings, blockers, and deterministic preparation fingerprint.

No durable record family such as `CurrentPortfolioBuildSession`,
`PortfolioExportDraft`, `SnapshotWizard`, or `BuildPreparationRecord` exists.

## Audience Rule and Audience Context

The teacher chooses one exact `ProfileAudienceRule` from the Profile Revision
bound to the current Composition.

The preparation surface exposes:

```text
audience_rule_id
audience_class
purpose
allowed_content_classes
prohibited_content_classes
required_review_classes
presentation_class
retention_policy_reference when present
```

The rule constrains content. It is not recipient identity, authentication,
authorization, consent, disclosure permission, or delivery permission.

Existing immutable Audience Contexts are matched only against the exact
Portfolio, Subject, Profile Binding/Revision, audience rule, and frozen rule
values:

```text
0 exact matches -> create
1 exact match   -> reuse
>1 exact matches -> requires_choice
```

No latest/greatest/opaque-ID heuristic resolves ambiguity. Execution creates a
new Context only through `create_audience_context(...)`.

## Snapshot Series

The first-party `snapshot_purpose` is the exact Audience Context purpose.

Existing Series are matched only against the exact Portfolio, Subject, Audience
Context, and purpose:

```text
0 exact matches -> create
1 exact match   -> reuse
>1 exact matches -> requires_choice
```

Ambiguity requires an explicit exact Series ID. Execution creates a Series only
through `create_snapshot_series(...)`.

## Required Reviews

The selected Audience Rule's exact `required_review_classes` are checked against
Review Decisions frozen by the current Composition Inventory.

Only an applicable Review of the exact immutable current curation target/revision
may satisfy the requirement. Reviews of predecessor or superseded targets do not
silently satisfy successors.

Missing required Review classes block before Build Request creation.

Review satisfaction remains curation approval, not disclosure authorization.

## Unresolved obligations

`unresolved_obligation_codes` from the exact current Composition Inventory are
shown before execution.

They do not automatically invalidate the Composition. If they exist, the
first-party workflow requires a separate exact acknowledgement before final
build confirmation.

`SnapshotBuildPlan.acknowledged_obligation_codes` contains only the exact codes
reviewed and acknowledged. Acknowledgement does not satisfy, clear, waive, or
approve the underlying obligation and does not authorize disclosure.

## Ordering authority

Logical ordering is:

```text
bound Profile section order
-> exact Arrangement frozen by the Composition
-> exact Arrangement placement_ids order
-> explicit representation position where needed
```

Opaque IDs, timestamps, publication times, scores, ratings, filenames, and
filesystem enumeration are not ordering authority.

## Source-backed materialization

Each placed Selection becomes one logical Snapshot item for its exact Placement.
The plan preserves exact Candidate, Candidate Evaluation, Core Publication,
producer projection, source Artifact, and current-use observations.

### Quillan and Concord

When an exact selected Quillan or Concord Artifact representation has one exact
configured Snapshot source provider, the first-party plan uses:

```text
materialization_kind = copied_source
```

The existing provider boundary owns acquisition and producer-native Artifact
authorization. Vitrine does not reconstruct private paths, fabricate a temporary
source locator, skip producer authorization, or follow a source successor.

Provider identity/version and support semantics are bound into deterministic plan
identity. A different provider cannot silently substitute after review.

### ScoreForm

A selected live ScoreForm attempt is an `assessment_summary` without a released
consumer-neutral Artifact byte resolver. Therefore first-party planning uses:

```text
materialization_kind = reference_only
provider_disposition = reference_only_by_producer_contract
```

Vitrine does not inspect `retained_source_path`, infer a retained scan, reread
ScoreForm private state, or synthesize a Vitrine-owned summary document.

### Other valid sources without an exact provider

A valid selected source with no exact byte-capable provider remains represented
as:

```text
materialization_kind = reference_only
```

The preparation explanation distinguishes producer-contract reference-only state
from absence of an exact configured provider. Reference-only Entries preserve
Edition provenance and contribute no file bytes to the directory Export.

## Audience-prohibited content

Content deterministically prohibited by the exact Audience Context may use the
existing explicit permitted omission reason:

```text
audience_prohibited
```

The omission is planned, displayed, and represented after sealing. It is never
silent absence.

Source unavailability, representation unavailability, integrity failure, and
authorization denial are not automatically converted into convenient omissions
by this first-party workflow.

## Vitrine-owned Reflection rendering

Issue #68 may generate bytes only from exact immutable `PortfolioReflection`
revisions frozen in the current Composition Inventory.

Supported first-party output uses:

```text
materialization_kind = generated_vitrine
content_class = reflection
renderer_id = vitrine_portfolio_reflection
renderer_version = 1
renderer_contract_version = vitrine_portfolio_reflection_renderer_v1
media_type = text/plain
```

The v1 renderer supports exact `inline_text` + `plain_text` Reflection content.
It emits the exact UTF-8 content without normalization or reinterpretation.

The plan/preview freezes exact Reflection ID/revision, content digest, content
mode/format/language, prompt identity/version/snapshot digest, target scope and
references, renderer identity/configuration, output media, byte size, and
SHA-256.

The renderer does not follow later Reflection revisions and does not dereference
external references, URLs, filesystem paths, or foreign document identifiers.
Unsupported content/placement modes fail closed.

`CurationAnnotation` and `CurationReviewDecision` remain curation/provenance
inputs. The task does not fabricate teacher-note documents, review reports,
approval certificates, or caption documents from them.

## Deterministic preparation fingerprint

The SHA-256 preparation fingerprint binds the exact reviewed task semantics,
including:

- contract identity;
- observed initial Vitrine state revision;
- current Composition pointer/revision and #67 fingerprint;
- Portfolio/Subject/Profile identities;
- exact Audience Rule values;
- Context and Series create/reuse/choice state and chosen IDs;
- ordered logical item plan;
- materialization/provider/renderer descriptors;
- target paths and media types;
- required Review state;
- acknowledged obligation set;
- planned audience omissions;
- directory Export partition.

It excludes display names, clocks used only for uniqueness, filesystem order,
and random future canonical IDs.

The fingerprint is replay/concurrency evidence, not a signature, authorization
token, consent, or disclosure approval.

## Deterministic identities and paths

Entry and Export plan identities are deterministic, domain-separated, and
PII-free. Target paths are derived from stable task semantics rather than student
display names.

Deferred-media copied sources use suffix-neutral paths until the authorized
producer result supplies one exact permitted concrete media type.

## Prepared execution

`execute_prepared_current_portfolio_plan(...)` revalidates one exact reviewed
preparation before the first write and persists only the canonical pre-Attempt
stages:

```text
Audience Context create/reuse
Snapshot Series create/reuse
Snapshot Build Request
immutable Snapshot Build Plan
```

No silent refresh, reprepare, provider substitution, or retry is permitted.
Every mutation threads the exact state revision returned by the preceding
canonical stage.

`execute_prepared_current_portfolio_build(...)` composes that Plan execution with
the canonical build/distribution services:

```text
start_snapshot_build_attempt
execute_snapshot_build_attempt
seal_snapshot_build_attempt
verify_snapshot_edition
create_snapshot_directory_export
verify_snapshot_export
```

The task does not construct synthetic replacements for these records/services.

## Authority boundaries

Snapshot build authority is checked by the existing injected
`SnapshotBuildAuthorityGate`.

For copied Quillan/Concord Artifact sources, producer Artifact authorization
remains inside the exact configured producer provider.

These decisions remain distinct from each other and from recipient/disclosure
authorization.

Denied/unresolved Snapshot authority and denied/unresolved producer Artifact
authorization have distinct task diagnostics.

## Concurrency and partial success

Execution revalidates reviewed state before the first write and then uses exact
returned state revisions sequentially.

If a later stage fails, already-persisted canonical history is preserved. Task
errors may report the exact durable Attempt, Edition, or Export Artifact identity
and one bounded `next_safe_action`.

No greatest/latest inference is used for recovery. Recovery helpers identify only
an exact unique durable artifact consistent with the interrupted stage.

A post-seal conflict does not invalidate an already sealed Edition. Export
failure does not erase the Edition. Export verification failure does not erase
the persisted Export Artifact.

`resume_current_portfolio_export(...)` can verify one exact sealed Edition and
create/reuse/verify its exact directory Export without reacquiring producer
bytes.

## Edition and Export verification

Historical Edition verification and Export verification are producer-independent
and remain governed by the Snapshot build workflow contract.

A `reference_only` Entry remains in Edition provenance but has no Export file.
A byte-bearing Entry is exported only when included by the immutable Export Plan.
Every planned Entry is explicitly partitioned as included/excluded.

Issue #68 supports only:

```text
directory_package
```

## Current Edition pointer

Successful Build and Export Current Portfolio execution does **not** advance the
current Edition pointer.

`SnapshotCurrentPointerRevision` remains a separate explicit advanced operation.
No latest/greatest Edition inference is introduced.

## Teacher menu

Portfolio option 6 is the ordinary first-party task:

```text
Build and Export Current Portfolio
```

The menu:

1. proves #67 `reuse_exact_current` state;
2. blocks unplaced Selections;
3. requires one exact Audience Rule;
4. requires explicit Context/Series choice when ambiguous;
5. shows the exact materialization/export preparation;
6. separately acknowledges unresolved obligations when present;
7. requires final `BUILD AND EXPORT CURRENT PORTFOLIO` confirmation;
8. executes the exact reviewed preparation.

Expected partial failures surface privacy-safe durable identities and bounded
recovery guidance rather than tracebacks or source-private data.

## Direct CLI

Task-level commands are:

```text
vitrine portfolio build-export prepare PORTFOLIO_ID \
  --audience-rule-id RULE_ID

vitrine portfolio build-export execute PORTFOLIO_ID \
  --audience-rule-id RULE_ID \
  --preparation-fingerprint SHA256 \
  --expected-state-revision REVISION \
  --actor-id ACTOR
```

When exact-match ambiguity requires it:

```text
--audience-context-id CONTEXT_ID
--snapshot-series-id SERIES_ID
```

Unresolved obligations are passed as the exact reviewed set using repeatable:

```text
--acknowledge-obligation CODE
```

The execute command reconstructs current preparation, requires the exact reviewed
fingerprint and observed state revision, and fails before writes on mismatch.

## Advanced Snapshot commands

Issue #68 replaces the ordinary Portfolio option-6 Snapshot wizard, not the
advanced Snapshot primitives.

The direct `vitrine snapshot ...` Request/Plan/Build/Verify/Export/Custody
commands remain available for custom planning, verification, and recovery.

## Runtime dependency boundary

The first-party task requires only Vitrine and the released Core runtime.

ScoreForm, Quillan, Concord, Portia, and Meridian remain optional integrations,
not hard Vitrine dependencies. When installed/configured, exact Snapshot source
providers may participate through their existing bounded provider contracts.

## Validation

The dedicated reusable validator is:

```text
python scripts/validate_current_portfolio_build_export.py
```

Installed-wheel acceptance is:

```text
python scripts/smoke_test_current_portfolio_build_export_wheel.py \
  dist/pds_vitrine-0.2.0-py3-none-any.whl \
  /path/to/pds_core-0.6.3-py3-none-any.whl
```

The complete repository gate wires both checks and must pass before issue #68 is
closed.
