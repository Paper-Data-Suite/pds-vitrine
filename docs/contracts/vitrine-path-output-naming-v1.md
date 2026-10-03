# Vitrine Path and Output Naming v1

Issue #111 establishes a shared prospective filesystem naming policy before issue
#101 adds student-facing Portfolio filenames and presentation packages.

Contract identity:

```text
vitrine_path_policy_v1
```

Slice 1 defines the policy primitives and audits existing path surfaces. It does
**not** change any persisted canonical-storage, Snapshot, Export, or paper
Reflection path.

## Governing distinctions

```text
identifier-safe
!=
filesystem-budget-safe

durable semantic identity
!=
filesystem component

display label
!=
canonical filename

historical stored path
!=
prospective writer serialization

human-readable
!=
unbounded
```

Exact identity remains in canonical structured state. Generated filesystem
components are bounded representations of that identity.

## Opaque custody token

`build_bounded_custody_token(...)` derives a deterministic token from:

```text
contract version
domain
canonical JSON semantic identity
```

using SHA-256.

The v1 token is:

```text
vp1_<24 lowercase hexadecimal characters>
```

and therefore has one fixed writer length regardless of the size of the semantic
identity.

Domain separation is mandatory. Two subsystems must not reuse the same semantic
tuple under an implicit shared namespace.

The token is a filesystem representation only. It is not a replacement for a
Portfolio ID, Profile ID, Snapshot ID, record key, or any other durable semantic
identity.

## Human-readable presentation filename

`build_bounded_presentation_filename(...)` is the initial shared policy for
future student-facing output.

It combines:

```text
bounded normalized readable stem
-
16-character semantic disambiguator
exact lowercase media extension
```

The v1 final filename maximum is:

```text
96 ASCII / UTF-8 bytes
```

The readable portion is capped at 64 characters before the final filename budget
is applied.

The semantic disambiguator comes from the exact structured semantic identity,
not from the display label. Two distinct items with the same readable label
therefore do not silently collide.

Display labels are normalized through Unicode NFKD and reduced to lowercase
portable ASCII. A nonempty label with no portable ASCII representation uses:

```text
item
```

as the readable fallback. The full human-readable label remains available in
structured Portfolio presentation metadata/content.

Supported extensions use the contract:

```text
.<lowercase alphanumeric extension>
```

with a maximum total extension length of 10 characters.

Compound extensions are intentionally not part of v1.

## Generated component validator

`require_generated_component(...)` validates prospective Vitrine-generated
components independently from generic PDS identifier validation.

The v1 validator requires:

- one lowercase portable ASCII filesystem component;
- no traversal or separators;
- no trailing dot/space;
- no Windows reserved device basename;
- an explicit caller-supplied byte budget.

This validator is for **new Vitrine-generated components**. It is not a legacy
reader rule and must not be applied retroactively to reject historically valid
stored paths.

## Reader/writer compatibility

The issue #111 compatibility rule is:

```text
reader:
    accept valid historical + new bounded forms

writer:
    create only the bounded prospective form
```

Slice 1 supplied the writer primitives.

Slice 2 applies the bounded custody token to **new canonical record identities**
under:

```text
state/records-bounded-v1/<record_type>/<bounded-token>/revisions/1.json
```

The historical direct-identity `state/records/...` layout remains readable and
is not migrated. A semantic key found in both layouts fails closed. Canonical
record envelopes and state references retain the exact `VitrineStorageRecordKey`;
the token never becomes domain identity.

Canonical inventory and catalog rebuilds resolve the exact stored revision path
rather than reconstructing the historical writer serialization.

Slice 3 applies the same reader/writer asymmetry to Snapshot-owned custody.

New staging, Edition, Series-lock, and directory-Export custody uses versioned
bounded namespaces:

```text
snapshots/staging-bounded-v1/
snapshots/editions-bounded-v1/
snapshots/.locks-bounded-v1/
snapshots/exports-bounded-v1/
```

Historical direct-identity custody remains readable without migration. Exact
Snapshot IDs remain canonical state.

`SnapshotExportArtifact.relative_path` is treated as persisted historical
custody. Verification resolves that exact stored path instead of requiring a
historical Export to equal today's writer serialization. New bounded-v1 Export
paths additionally verify their deterministic custody token.

## Relationship to Core 0.6.4

Core owns Core retained-source filenames and `source_scan_id`.

Vitrine must consume stored Core retained-source provenance as opaque historical
state. It must not reconstruct, shorten, rename, or independently version Core
retained-source names.

Final issue #111 qualification uses the exact published Core 0.6.4 artifact, but
the Vitrine path policy is a Vitrine-owned contract.

## Slice 4 regression boundary

Issue #111 Slice 4 deliberately adds no new custody schema.

It locks in the path surfaces that were already structurally safe:

- Current Portfolio source Entry paths use a fixed 16-hex semantic digest leaf;
- Current Portfolio Reflection paths use a fixed 16-hex semantic digest leaf;
- display labels, Candidate IDs, Placement IDs, source locators, and other long
  semantic values may affect the digest input but do not expand the generated
  filename;
- paper Reflection output remains the fixed
  `student_reflection_response.pdf` leaf;
- the paper renderer's temporary leaf remains fixed-stem plus a bounded random
  token;
- Core retained-source provenance is consumed from the exact persisted
  `retained_source_relative_path` with Python byte I/O and SHA-256 verification,
  without reconstructing or renaming the Core-owned filename.

Representative deep Windows path geometry is tested without making correctness
depend on the host actually exceeding a platform path-length threshold.

## Final #101 presentation naming handoff

Slice 5 finalizes the reusable naming contract that issue #101 must consume.

### Student-facing filenames

`build_bounded_presentation_filename(...)` is the authoritative #101 filename
primitive. It accepts only:

```text
preferred human-readable label
semantic domain
exact semantic identity/disambiguator
exact lowercase media extension
```

The output is deterministic, portable ASCII, semantically disambiguated, and
bounded to 96 bytes. Label truncation never removes the semantic disambiguator.
Semantic identity contributes only through the digest and is not rendered into
the readable name.

### Student-facing section directories

`build_bounded_presentation_directory_name(...)` provides the corresponding
directory primitive.

The v1 directory budget is 80 bytes. An optional ordinal is limited to 1..9999
and is rendered as a minimum two-digit prefix, for example:

```text
01-selected-work-<16-hex>
02-reflection-<16-hex>
12-writing-growth-<16-hex>
```

The readable stem is normalized and truncated before the semantic
disambiguator. Exact section identity remains structured state.

### Collision handling

`require_unique_presentation_components(...)` validates one sibling inventory
using NFC + case-fold collision keys. A collision fails closed; callers must not
silently overwrite, append randomness, or select one colliding item.

The digest disambiguator resolves ordinary collisions caused by equal or
truncated readable labels. The inventory check remains the final guard against
an actual generated-component collision.

### Privacy boundary

The semantic identity may include student, source, Snapshot, or Artifact
identifiers, but those values are never copied into the readable component.
Only the deliberately supplied `preferred_label` is human-readable.

Issue #101 should therefore use work/section labels that are intentionally
student-facing and keep student identifiers, source locators, and custody IDs in
structured manifests/index metadata unless a product requirement explicitly
calls for their display.

## Relationship to issue #101

Issue #101 may use readable filenames, but must consume this bounded policy
rather than placing unrestricted display text into filesystem names.

Meaningful output may therefore look conceptually like:

```text
revised-argument-a83f0291.pdf
student-reflection-72ce184d.pdf
```

while exact labels and identities remain in the Portfolio index, manifest, and
canonical records.
