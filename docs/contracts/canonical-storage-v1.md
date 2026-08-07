# Canonical Storage v1

- **Issue:** #29
- **Milestone:** v0.2.0 — Runtime Foundations and Fixture-Backed Portfolio Slice
- **Status:** Implemented persistence contract
- **Storage schema version:** `1`
- **Catalog schema version:** `1`

## Purpose

Vitrine persists the immutable runtime records defined by the foundational model
contract as workspace-scoped canonical JSON. Persistence preserves runtime
identity and graph meaning; it does not introduce mutable replacements for
Profile, Composition, Arrangement, Candidate, Selection, or Snapshot domain
revision semantics.

Vitrine identity may span classes and school years, so canonical Vitrine state is
owned beneath the resolved PDS workspace rather than any one Core class work root.

## Canonical layout

```text
<PDS workspace>/
  vitrine/
    state/
      store.json
      records/
        <record_type>/
          <identity segment>/...
            revisions/
              1.json
      revisions/
        <state_revision>.json
      current.json
      derived/
        catalog.sqlite
      .locks/
        write.lock
        catalog.lock
```

Paths use opaque record identities only. Display names, student names, source
text, assignment titles, and privacy metadata never form canonical paths.

## Record keys and revisions

`VitrineStorageRecordKey` binds one runtime `record_type` to its exact logical
identity segments. Composite domain identities preserve their domain revision
component, for example:

```text
portfolio_profile_revision/<portfolio_profile_id>/<profile_revision>
working_portfolio_composition_revision/<portfolio_id>/<composition_revision>
snapshot_edition/<snapshot_series_id>/<edition_number>
```

`VitrineRecordRevision` wraps the exact `record_to_dict()` body, runtime schema
version, logical key, and storage revision. Path, envelope, and body identity must
agree on every read.

Under storage schema v1, runtime records are immutable semantic facts. An
existing key with identical content is replay; an existing key with different
content conflicts. Corrections and replacements therefore create new domain
successor records rather than a second storage revision of the old semantic key.
Ordinary v1 canonical history contains storage revision `1` for every key.

## State revisions and current selection

`VitrineStateRevision` is one complete accepted graph selection. It is not a
delta and is deliberately not called a Snapshot because Snapshot has an existing
domain meaning in Vitrine.

State revisions are contiguous. Every revision after 1 stores the exact previous
revision and SHA-256 of the predecessor's canonical bytes. Record references are
sorted, unique, and digest-bound.

Accepted v1 state is append-preserving: later states may add semantic keys but
may not silently remove or replace an already accepted key.

`current.json` contains one `VitrineCurrentState` and is the sole mutable
canonical JSON file. Current state is never inferred from the largest revision,
mtime, timestamp, directory order, or derived catalog.

## Strict reads

Canonical reads reject malformed UTF-8 or JSON, duplicate JSON keys, unsupported
schemas, unsafe or symlinked canonical paths, invalid revision filenames,
unexpected visible canonical entries, path/envelope/body identity disagreement,
digest disagreement, state-chain gaps, and invalid reconstructed graphs.

Loading state N proves every declared predecessor and digest through state 1 and
verifies every selected record revision before reconstructing and validating the
`VitrineRecordGraph`.

Reads create no directories, locks, catalogs, repairs, or workspace metadata.

## Guarded commits

`commit_record_batch()` requires an existing writable Core workspace.

Bootstrap uses:

```text
expected_state_revision = None
```

Every later advancing commit supplies the exact current state revision. A stale
writer conflicts even if some supplied record bodies happen to match current
state.

Before mutation the writer:

1. validates candidate types and logical identities;
2. rejects duplicate candidate keys;
3. strictly loads current canonical state;
4. verifies the expected state revision;
5. proves canonical history has no gaps, orphans, collisions, or unexplained
   identities;
6. merges new records with current state in memory;
7. rejects changed content for an existing semantic key; and
8. validates the complete resulting runtime graph.

An exact replay creates no record revision, state revision, or current-pointer
rewrite.

## Publication and durability boundary

A commit writes in this order:

1. acquire `write.lock` exclusively;
2. write new immutable record revisions exclusively and verify them;
3. write the next immutable state revision and verify its complete graph;
4. write and synchronize a temporary current pointer;
5. atomically install `current.json` with `os.replace()`;
6. reload the published graph exactly; and
7. release the lock.

This provides logical atomicity for current readers, not a claim of
filesystem-wide transactional atomicity. Before pointer publication, prior
current state remains authoritative. After pointer publication, the new state is
accepted even if final verification or cleanup later reports an error.

Files are flushed and `fsync` is used where supported. Directory `fsync` is not
claimed on Windows.

## Partial success and recovery

Structured partial-success errors distinguish whether the current pointer was
published and report only privacy-safe relative paths plus accepted state
revision/digest when applicable.

Recovery is conservative:

- never edit record or state revisions in place;
- never infer current state from the highest filename or timestamp;
- never alter bytes to satisfy a digest;
- never automatically adopt or delete orphan canonical history;
- never clear a lock because it appears old;
- never roll an accepted pointer backward automatically;
- diagnose ambiguous history before any later write.

Lock clearing is an explicit low-level recovery action protected by the exact
previously inspected lock SHA-256 fingerprint.

## Derived catalog

`state/derived/catalog.sqlite` is disposable nonauthoritative lookup state.
Canonical loading never consults it.

Catalog rebuilding captures a deterministic inventory of every canonical JSON
source as:

```text
POSIX relative path
byte size
SHA-256
```

A rebuild creates a complete temporary database, runs SQLite integrity checks,
recaptures the canonical inventory, and installs the database atomically only if
canonical source did not change.

Catalog metadata records schema/application identity, source digest and counts,
and exact current-state identity. Rows store minimized lookup metadata only;
complete runtime bodies, student work, names, notes, and source privacy content
are not copied into SQLite.

Missing, stale, incompatible, or corrupt catalog state fails catalog queries
specifically but never changes canonical results and never triggers silent
rebuilding.

## Diagnostics and privacy

`audit_canonical_storage()` is read-only and returns deterministic privacy-safe
storage findings. Runtime graph failures preserve the existing model validation
codes.

Diagnostics omit record bodies, source content, private notes, display names,
credentials, and absolute workstation paths.

Filesystem readability is not authorization. Persistence does not authorize
source access, disclosure, recipient access, public issue, or regulated
submission.

## Deferred behavior

This contract does not implement producer discovery, Candidate discovery,
curation workflows, Snapshot byte construction, exports, issuance, recipient
verification, redaction, delivery, external submission, retention execution,
automatic canonical repair, backup/restore, or cross-workspace transactions.
