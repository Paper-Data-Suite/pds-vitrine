# Vitrine Path-Surface Audit — Issue #111

This audit records the issue #111 Slice 1 baseline at reconciled commit
`fde06a4b5add3b3987d46f1d7676cb32f0f9f1aa`.

Slice 1 does not rewrite any listed path. The classifications below determine
which later slice owns each change.

## Classification

```text
A. fixed leaf / already bounded
B. bounded Vitrine-generated identity
C. durable semantic identifier currently used directly in a path
D. external/shared/Core-owned path component
E. human-readable/display text
F. stored legacy path requiring backward-compatible reads
```

## Canonical Vitrine storage

Current shape:

```text
<vitrine-root>/
  state/
    records/
      <record_type>/
        <identity segment>/
          ...
            revisions/
              <storage revision>.json
```

Relevant code:

```text
vitrine/storage/paths.py
vitrine/storage/models.py
vitrine/storage/store.py
vitrine/record_registry.py
```

Classification:

```text
record_type:                         A
storage revision filename:           A
identity segments:                   C
existing direct-identity histories:  F
```

`VitrineStorageRecordKey` validates non-integer identity segments through generic
PDS identifier validation. Character safety is not a fixed filesystem-length
budget.

**Slice 2 status:** implemented. New semantic record identities use
`state/records-bounded-v1/<record_type>/<bounded-token>/...`; historical
direct-identity histories remain readable in place. Mixed legacy/new workspaces
are supported, while duplicate custody for one semantic key fails closed.

## Snapshot staging

Current shape:

```text
snapshots/staging/<snapshot_build_attempt_id>/
```

Classification:

```text
snapshots/staging:             A
snapshot_build_attempt_id:     C in the custody contract
ordinary generated IDs today: B in normal service execution
existing staging paths:        F
```

The current service factory normally emits a bounded prefix + UUID identity, but
the path helper accepts the broader generic identifier contract.

**Slice 3 status:** implemented. New Attempt staging uses
`staging-bounded-v1/<bounded-token>`. Historical direct-identity staging is
reopened in place; dual custody fails closed.

## Snapshot Edition custody

Current shape:

```text
snapshots/editions/<snapshot_series_id>/<edition_number>/
```

Classification:

```text
snapshots/editions:       A
snapshot_series_id:       C in the custody contract
edition_number:           A
existing Edition paths:   F
```

Ordinary generated Series IDs are currently bounded in practice, but path safety
must be a writer contract rather than an implementation coincidence.

**Slice 3 status:** implemented. New Edition custody uses
`editions-bounded-v1/<bounded-token>`. Historical direct-identity Editions
remain resolvable without migration.

## Snapshot Series locks

Current shape:

```text
snapshots/.locks/<snapshot_series_id>.json
```

Classification:

```text
snapshots/.locks:         A
snapshot_series_id leaf:  C in the custody contract
existing lock paths:      transient F where present
```

**Slice 3 status:** implemented. New Series locks use the
`.locks-bounded-v1/<bounded-token>.json` namespace; historical locks remain
inspectable/releasable in place.

## Snapshot directory Exports

Current shape:

```text
snapshots/exports/
  <snapshot_series_id>/
    <edition_number>/
      <snapshot_export_artifact_id>/
```

Classification:

```text
snapshots/exports:                    A
snapshot_series_id:                  C
edition_number:                      A
snapshot_export_artifact_id:         C
SnapshotExportArtifact.relative_path: F
```

`verify_snapshot_export()` currently reconstructs the custody path from current
identity serialization. That must be revisited before prospective writer
serialization changes.

**Slice 3 status:** implemented. New directory Exports use
`exports-bounded-v1/<bounded-token>`. Verification resolves the persisted
`SnapshotExportArtifact.relative_path`; historical direct-identity Exports are
not reserialized with the current writer.

## Current Portfolio Snapshot entry paths

Current shape:

```text
section-<bounded order>/
  <bounded position>-entry-<16-char semantic digest><media suffix>
```

Relevant code:

```text
vitrine/current_portfolio_build.py
```

Classification:

```text
section/position components: B
semantic digest token:       B
media suffix:                A
display labels:              E, deliberately excluded
```

This is an existing good pattern. Display text does not enter deterministic
entry IDs, target paths, or preparation fingerprints.

**Slice 4 status:** regression-qualified. Current Portfolio source Entry
paths remain semantic-digest paths with fixed 16-hex tokens; extreme semantic
identifiers and display labels do not expand the generated leaf. #101 must not
replace these custody paths with presentation labels.

## Paper Reflection printable PDF

Current shape:

```text
classes/
  <class_id>/
    modules/
      vitrine/
        work/
          <reflection_work_id>/
            templates/
              student_reflection_response.pdf
```

Classification:

```text
classes/<class_id>:                 D
modules/vitrine/work:               D/shared hierarchy + fixed module
reflection_work_id:                 B
templates:                          A
student_reflection_response.pdf:    A
temporary render leaf:              B
```

`reflection_work_id` is generated by Vitrine as prefix + UUID. The final PDF
leaf is fixed. `class_id` belongs to the shared/Core class hierarchy and must not
be remapped by Vitrine.

**Slice 4 status:** regression-qualified. The final paper Reflection PDF
leaf remains fixed, the temporary render leaf remains bounded, and student
display names do not enter either filesystem name.

## Paper Reflection retained-source materialization

Relevant code:

```text
vitrine/paper_reflection_materialization.py
```

Stored Core provenance includes:

```text
retained_source_relative_path
source_sha256
source_filename
```

Classification:

```text
retained_source_relative_path: D + F
source filename:                external provenance, not Vitrine output
```

Vitrine reads the persisted retained path and verifies exact bytes/digest. It
does not reconstruct the Core retained-source writer filename.

**Disposition:** Preserve. Qualify historical Core 0.6.3 provenance and fresh
Core 0.6.4 provenance in later acceptance.

## Candidate Artifact preview

Relevant code:

```text
vitrine/candidate_evidence_artifact_preview.py
```

Vitrine obtains producer-authorized bytes through public Artifact boundaries.
Producer source filenames are not used as Vitrine-generated preview custody
names.

**Disposition:** Preserve.

## Future student-facing presentation output (#101)

Not implemented at the Slice 1 baseline.

Classification:

```text
student/work/section display labels: E
future generated output names:       must become bounded A/B forms
```

Issue #101 explicitly requires meaningful filenames and human-readable section
presentation. Display labels must pass through the bounded presentation policy
rather than becoming filesystem components verbatim.

**Slice 5 status:** implemented. The reusable #101 handoff now provides bounded
readable filenames, bounded ordered section-directory names, deterministic
semantic disambiguation, exact lowercase extension validation, Unicode-normalized
portable output, privacy-minimized opaque identity, and fail-closed sibling
collision validation. Issue #101 consumes these helpers and owns the actual
Portfolio presentation.

## Slice ownership summary

```text
Slice 1:
    shared policy + this audit + contract + focused tests

Slice 2:
    canonical record storage reader/writer compatibility

Slice 3:
    Snapshot custody / Export compatibility

Slice 4:
    lock in already-safe Current Portfolio and paper paths

Slice 5:
    finalize #101 human-readable filename/directory contract

Slice 6:
    installed Core 0.6.4 / package / repository qualification
```

## Governing rule

```text
Canonical identity belongs in canonical records.

Human meaning belongs in presentation and structured metadata.

Filesystem components are bounded custody/presentation representations.

Historical paths remain historical facts.

New writers create only the bounded prospective form.
```
