# Completed Portfolio Navigation v1

Issue #102 defines durable teacher navigation and local use of completed Vitrine
Portfolio Editions after the build session has ended.

## Semantic distinctions

These distinctions are normative:

```text
completed Edition != current Edition
newest Edition != current Edition

Snapshot Edition != technical Export != student Presentation

canonical record discovery != filesystem discovery

view != verify
verify != repair

local print/open != delivery

historical Presentation generation != historical producer reread

Build Updated Edition != mutate historical Edition
```

A completed Edition is a sealed immutable Snapshot Edition discoverable from
canonical Vitrine records. Currentness comes only from the explicit
`SnapshotCurrentPointerRevision` head for that exact Snapshot Series. A newer
Edition is never promoted implicitly.

## Read model

`vitrine_completed_portfolio_history_v1` projects:

```text
Portfolio
  -> Snapshot Series
      -> sealed Editions
          -> technical Exports
          -> Portfolio Presentations
      -> explicit Current Pointer state
```

Edition numbers are Series-scoped. Multiple Series for one Portfolio remain
distinct. Export and Presentation history are joined by exact canonical
Snapshot Edition identity. Filesystem directories are never catalog authority.

## Teacher surface

Completed Portfolio Editions are identified primarily by Portfolio/student
context, audience/purpose, Edition number, build date, current/historical
status, and artifact availability. Opaque IDs, digests, and custody paths stay
under Technical Details / Provenance.

Available actions are conditional and truthful:

- View Student Portfolio
- Print Portfolio
- Open Portfolio Folder
- Open Technical Export Folder
- Verify Portfolio Now
- Create Student Portfolio Presentation, when the exact frozen audience permits
  it and no canonical student Presentation already exists
- Build Updated Edition
- Export / Presentation History
- Technical Details / Provenance

## Local-open safety

View/Print/Open resolve only canonical Vitrine relative paths after exact
first-party verification. Targets must remain inside the active workspace,
exist, and have the expected file/directory type. URL-like and escaping paths
fail closed.

Print opens the verified binder-ready PDF in the local PDF application. It does
not perform silent OS printing and does not claim physical printing occurred.

The local-open boundary accepts an injectable `LocalOpener` for controlled
automated acceptance. Production calls default to Core
`pds_core.local_open.open_local_path`.

## Verification and integrity

`Verify Portfolio Now` verifies the exact Edition plus every recorded technical
Export and student Presentation for that Edition. Successful verification is
read-only and does not advance current-pointer state. Missing, changed,
unexpected, or unsafe custody fails closed; Vitrine does not rebuild, repair,
replace, delete, or rewrite immutable history automatically.

## Historical Presentation creation

For a historical `student_portfolio` Edition with a compatible verified
technical Export and no canonical student Presentation, Vitrine delegates to
the existing Issue #101 Presentation service. The exact sealed Edition/Export
are inputs. Current Working Composition and producer state are not reread.
Existing Presentation failure is an integrity problem, not permission to
overwrite immutable Presentation custody.

## Build Updated Edition

Build Updated Edition is a route back to the existing Build and Export Current
Portfolio workflow. That workflow uses the current Working Composition and
current exact reviewed policy. The historical Edition is not cloned, mutated,
or passed as build authority.

## Disclosure boundary

Build, verify, presentation generation, local view, local print/open,
disclosure authorization, and delivery remain separate events. Nothing in this
contract proves recipient identity, consent, external authorization, sending,
submission, or delivery.

## Handoffs

Issue #103 owns completion-aware Attention / Next Actions semantics. Issue #102
does not reinterpret unused Candidates or other attention meaning.

Issue #104 remains the umbrella synthetic Improvement Portfolio acceptance.
Issue #102 supplies the completed-history/local-use contract that #104 can
compose with later completion semantics.
