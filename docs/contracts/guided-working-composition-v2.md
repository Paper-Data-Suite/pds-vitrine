# Guided Working Composition v2

Issue #100 versions the transient guided Working Composition contract so that
Portfolio content is represented by the canonical record type that actually
owns each fact. The durable Composition model is unchanged.

Contract identity:

```text
vitrine_guided_working_composition_v2
```

## Relationship to v1

Guided Working Composition v1 remains historical documentation for issue #67.
Version 2 preserves v1 preparation, ordering, source-currentness, Review,
audience-neutrality, concurrency, fingerprint, and prepared-freeze semantics.
It adds an explicit semantic content projection for requirement-backed Portfolio
content.

The version bump is transient only. It does not version or replace:

```text
WorkingPortfolioCompositionRevision
WorkingPortfolioCompositionInventory
WorkingPortfolioCompositionPointerRevision
```

## Governing content rule

```text
Placements are one way content enters a Portfolio.
They are not the definition of Portfolio content.
```

Working Composition v2 distinguishes:

```text
placement-backed Portfolio content
requirement-backed Portfolio content
non-content Profile policy/workflow requirements
```

A student Reflection remains `PortfolioReflection`. It is never converted to or
represented as `PortfolioPlacement` merely so that it can appear in a section.

## Requirement-backed content projection

`WorkingCompositionPreparation.requirement_contents` is a transient tuple of
`WorkingCompositionRequirementContentSummary` values.

The initial supported requirement-backed semantic is intentionally narrow:

```text
requirement_kind == reflection
satisfaction_class == reflection_presence
```

Each projected Reflection preserves, at minimum:

- exact canonical record kind, ID, and revision;
- exact Profile requirement ID and explicit requirement semantics;
- exact requirement scope and optional exact section mapping;
- Portfolio, Subject, Profile Binding, and Profile Revision context;
- bounded prompt/content-mode facts needed for explanation.

The projection is read-only and creates no durable Portfolio-content record
family.

## Exact resolution

A Reflection becomes Working Composition content only through the exact chain:

```text
frozen CurationRevisionRef
-> exact PortfolioReflection ID/revision
-> exact reflection_requirement_id
-> exact Profile requirement in the frozen Profile Revision
-> explicit requirement scope
```

Section mapping is allowed only when the requirement is explicitly
`scope_kind == section` with an exact `scope_reference` that resolves to one
section in that Profile Revision.

Titles, labels, statements, timestamps, opaque IDs, and prose are never used to
infer scope, priority, content type, or ordering.

## Current and historical content

`resolve_working_composition_requirement_contents(...)` provides one semantic
resolver for both:

```text
current preparation content
exact frozen Composition revision content
```

Historical resolution uses the exact `WorkingPortfolioCompositionInventory`
for the requested Composition revision. A later Reflection revision must not
retarget an older frozen Composition.

Missing or ambiguous Composition, Inventory, Profile Binding, Profile Revision,
Profile requirement, Reflection revision, or section scope fails closed.

Multiple exact Reflection records are preserved independently. The resolver does
not choose a latest, highest, newest, or otherwise preferred Reflection.

## Missing content versus non-content requirements

A required Reflection with no canonical Reflection record remains a visible
obligation. It is not presented as an empty 0/0 Placement section.

Approval, audience review, privacy, rights, accessibility, and unknown extension
requirements are not fabricated as student Portfolio content. They remain Profile
policy/workflow requirements unless an explicit supported content semantic says
otherwise.

## Teacher presentation

The guided teacher view is content-first:

```text
Portfolio content
  placement-backed evidence
  requirement-backed Reflection
  missing requirement-backed content

Other Profile requirements
  approvals, reviews, policy/workflow obligations
```

For a zero-capacity Reflection section, ordinary presentation shows the
Reflection as `Recorded` or `Needed` rather than reporting the section as empty
because it has zero Placements.

Exact Placement cardinality, Reflection ID/revision, requirement ID, scope,
prompt facts, and other implementation provenance remain available in Technical
Details / Provenance.

## Direct CLI

`vitrine composition prepare` exposes the same v2 semantic distinction in exact
text form. It reports requirement-backed content and its exact canonical
revision separately from Placement-backed section state, and reports other
non-content Profile requirements separately.

The CLI remains read-only for preparation. `composition freeze` still requires
explicit reviewed state/pointer/fingerprint expectations and invokes the same
canonical freeze path.

## Current Portfolio handoff

Current Portfolio planning consumes the shared Working Composition semantic
projection for Reflection requirement/scope meaning. It may still resolve the
exact canonical `PortfolioReflection` record for materialization-specific facts,
bytes, hashes, and paper evidence.

Current Portfolio must not reimplement a second Reflection-to-requirement or
Reflection-to-section semantic mapper.

Paper-native and typed Reflections therefore share the same Composition content
contract while retaining their existing materialization behavior.

## Ordering

Placement ordering remains authoritative only through exact
`SectionArrangementRevision.placement_ids`.

Requirement-backed Reflection content does not acquire a fabricated Placement or
Arrangement position. A section-scoped Reflection is associated with its section
through the explicit Profile requirement scope, not by timestamp or opaque ID.

## Non-goals

Version 2 does not add:

- a new durable Portfolio-content schema;
- Reflection-as-Placement;
- Profile prose interpretation;
- automatic Reflection creation;
- OCR or handwriting recognition;
- automatic evidence ranking or improvement claims;
- student-facing final Portfolio rendering;
- a new Core contract or sibling-producer runtime dependency.

## Qualification

Issue #100 qualification covers current and historical exact resolution,
revision pinning, multiple Reflection series, teacher presentation, CLI parity,
Current Portfolio shared handoff, installed Core+Vitrine wheel behavior, package
guards, and the complete repository validator.

See:

- [Guided Working Composition development](../development/guided-working-composition.md)
- [Issue #100 validation](../validation/issue-100-working-composition-requirement-content-validation.md)
- [Build and Export Current Portfolio v1](build-export-current-portfolio-v1.md)
