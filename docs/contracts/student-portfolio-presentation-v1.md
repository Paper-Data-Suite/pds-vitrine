# Student Portfolio Presentation v1

Issue #101 adds a derived student-facing presentation layer above one exact,
verified immutable Snapshot Edition and its exact verified technical directory
Export. The presentation is a new artifact family; it does not replace Snapshot
custody, the technical Export, or canonical provenance.

Contract identity:

```text
vitrine_student_portfolio_presentation_v1
```

## Slice 1 boundary

Slice 1 establishes only the immutable artifact contract and read-only
preparation. It does **not** render HTML, create the presentation file package,
or create the printable PDF yet.

Preparation begins from explicit exact identities:

```text
Snapshot Series ID
+ Edition number
+ Snapshot Export Artifact ID
```

It first invokes producer-independent Export verification. That verification
already re-verifies the sealed Edition. Preparation then resolves the exact
canonical Portfolio, Subject, Profile Binding/Revision, Audience Context,
Working Composition revision, Snapshot build provenance, Build Plan, Attempt
Result, materializations, Entries, and permitted Omissions.

No ScoreForm, Quillan, Concord, Portia, or Meridian package is imported or
queried. No producer is contacted. No Vitrine record or file is written.

## Why the inventory is Plan-based

A sealed Snapshot has three semantically different outcomes:

```text
included          -> exact immutable bytes + SnapshotEntry
reference_only    -> exact provenance, intentionally no portable file
omitted_permitted -> exact SnapshotOmission under the frozen audience policy
```

`SnapshotEntry` alone therefore cannot reconstruct the complete student
Portfolio. Slice 1 derives the presentation inventory from the exact frozen
`SnapshotBuildPlan` and exact sealed `SnapshotBuildAttemptResult`, then joins
canonical materialization provenance, Entries, and Omissions.

This preserves ScoreForm-style reference-only evidence as visible Portfolio
meaning without inventing a document that never existed.

## Exact presentation context

The prepared presentation freezes:

- exact Snapshot Edition and technical Export identities;
- exact Portfolio and Portfolio Subject;
- exact Profile Binding and Profile Revision;
- exact Working Composition revision;
- exact Audience Context and its original `presentation_class`;
- the derived output class `student_portfolio`;
- student display-name snapshot when present;
- Portfolio title snapshot, falling back to the exact Profile label;
- Profile section label, purpose, order, and obligation;
- exact item disposition and byte/reference/omission provenance;
- bounded prospective section directory and item filename components.

The source Audience Context `presentation_class` is not overwritten. The
student-facing artifact class is a separate derived-output concept.

## Student-facing labels

Item-title precedence is intentionally presentation-only:

```text
SnapshotEntry.display_title
-> exact frozen Placement Presentation display_title
-> exact immutable Candidate display snapshot
-> humanized semantic role
```

Placement caption, source credit, and presentation note are preserved where
available. Reference-only and omitted items receive concise student-facing
status language when no explicit presentation note exists.

These labels are never execution authority and never replace canonical IDs.

## Path and filename contract

Issue #101 **does not implement another slug/truncation/hash scheme**.
It consumes the exact issue #111 helpers:

```text
build_bounded_custody_token(...)
build_bounded_presentation_filename(...)
build_bounded_presentation_directory_name(...)
require_unique_presentation_components(...)
```

Prospective artifact custody is:

```text
presentations-bounded-v1/
  vp1_<24-hex bounded custody token>/
```

The custody token is derived from the exact presentation artifact ID under a
presentation-specific semantic domain. Student names, student database IDs,
Subject IDs, Profile IDs, source locators, and work labels do not appear in the
custody component.

Student-facing section directories and file names are readable but bounded.
Their readable stems come only from deliberately presentation-facing section or
work labels. Exact semantic identity contributes through issue #111's opaque
16-hex disambiguator and remains structured metadata.

Ordinary examples are conceptually:

```text
01-selected-work-<16-hex>/
  revised-argument-<16-hex>.pdf
  lab-investigation-<16-hex>.docx
```

Portable sibling collision checks fail closed. No random suffix, silent
overwrite, or raw-ID fallback is allowed.

Historical Snapshot/Export paths remain historical facts. Presentation code
must not rename, shorten, reconstruct, or migrate them.

## Presentation Artifact

`PortfolioPresentationArtifact` is a distinct immutable runtime record. Its
contract includes:

```text
presentation_artifact_id
snapshot_edition
snapshot_export_artifact_id
portfolio / subject / Profile / Audience identities
presentation_class
presentation_contract_version
renderer identity + configuration digest
bounded artifact relative_path
manifest relative path + digest
HTML relative path + digest
printable PDF relative path + digest
package inventory digest
generated_at / generated_by
optional predecessor presentation artifact ID
```

The manifest, HTML, and printable PDF must live beneath the artifact's persisted
custody root. Slice 1 makes this model serialization-ready but adds no writer.

## Visual-quality boundary for later slices

Later rendering must make the student work—not Vitrine internals—the visual
focus. The intended presentation system uses restrained typography, generous
spacing, clear section hierarchy, meaningful work titles, readable captions,
and consistent print geometry. Raw IDs, hashes, source paths, renderer names,
and technical provenance belong in the machine manifest or an explicit
technical detail surface, not the ordinary student cover, navigation, or work
pages.

The HTML and printable PDF must tell the same Portfolio story from the same
prepared inventory. The PDF is not a screenshot of the website; it is a
binder-ready print rendering with stable margins, section starts, captions, and
page flow.

## Slice 2 — human-readable digital file package

Slice 2 consumes the exact prepared inventory and creates one bounded, create-only
student file package. Immediately before copying, Vitrine independently re-verifies
the exact technical Snapshot Export. Every byte-bearing presentation item must still
appear in that verified Export inventory, and its copied payload must match the exact
frozen materialization SHA-256 and byte size. The student-facing copy is therefore a
rename/reorganization of exact Snapshot bytes, never a conversion.

The package writes Profile sections under the already-planned #111 bounded section
directories and exact byte-bearing items under the already-planned #111 meaningful
filenames. Reference-only and permitted-omission items remain manifest entries only;
no placeholder document is fabricated for either disposition.

Unknown media types now fail closed during preparation. Vitrine does not infer a
student-facing extension from a technical filename and does not invent `.bin`. The
controlled mapping is the only extension authority for this presentation contract.

`portfolio-presentation-manifest.json` is deterministic UTF-8 JSON and records the
exact Edition, sealed manifest/logical-inventory digests, technical Export identity
and inventory digest, frozen Profile/Audience context, ordered sections, exact item
identity/disposition, and presentation-relative paths/digests for byte-bearing files.
It deliberately omits producer-private source paths and technical Export custody
paths. The physical package inventory digest covers presentation payload files and
excludes the manifest itself, avoiding a self-digest cycle.

Slice 2 does not persist `PortfolioPresentationArtifact`. That record requires HTML
and printable-PDF paths/digests, so publishing it before Slices 3–4 would canonize a
partial presentation. Slice 2 custody is create-only and ordinary failures roll back
partial output; crash/recovery and idempotent canonical publication remain Slice 5.

## Slice 3 — static offline HTML Portfolio

Slice 3 renders `portfolio.html` from the same exact frozen preparation used by the
student file package. HTML generation is deterministic and producer-independent. It
uses no current clock, network lookup, live producer state, external stylesheet,
remote font, CDN asset, or JavaScript.

The document presents the Portfolio as a student product rather than a technical
index: a cover treatment, student display name when present, Profile label and
purpose, ordered section navigation, exact Profile section labels/purposes, meaningful
work cards, readable captions/source credit, and clear local file actions. Optional
empty sections may be omitted from human navigation; required empty sections remain
visible so required Portfolio structure never disappears silently.

All dynamic human text is HTML-escaped. Package links are formed only from #111-
validated bounded section/file components. Ordinary HTML contains no canonical IDs,
SHA-256 values, technical Export paths, renderer names, or custody terminology.

For browser-safe PNG/JPEG work, HTML may show the exact copied file as an inline local
preview while preserving the file itself unchanged. For exact frozen text/Markdown
Reflection, Vitrine decodes the already-verified copied bytes as UTF-8 and presents the
escaped exact text inline; Markdown is not interpreted as active HTML. A byte-bearing
item always retains an ordinary local link to its exact student-facing source file.
Reference-only and permitted-omission items remain honest status cards with no fake
attachment.

`portfolio.html` is created inside the same all-or-nothing create-only package
operation as the human-readable source copies. The machine manifest now records the
HTML path, byte size, SHA-256, renderer identity/version/contract, and deterministic
renderer-configuration digest. The package inventory digest includes HTML plus the
exact copied source files and still excludes the manifest itself to avoid a self-
digest cycle.

Slice 3 still does not persist `PortfolioPresentationArtifact`, because that canonical
record also requires the printable-PDF output owned by Slice 4.

## Next slice

Slice 4 should add the explicit deterministic binder-ready PDF renderer and supported
media matrix, preserving exact digital originals separately from derived printable
pages.
