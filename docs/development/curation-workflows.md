# Curation workflow development

## Application boundary

Runtime orchestration lives in:

```text
vitrine/curation_services.py
```

Pure canonical-state projection and cross-record validation live in:

```text
vitrine/curation_state.py
```

CLI and menu code must call these services rather than reproduce curation rules.
Teacher-facing curation UI remains deferred to issue #38.

## Main operations

The service layer provides operations equivalent to:

```text
propose_candidate_selection
decide_selection_proposal
select_candidate_directly
place_selection
replace_placement
reorder_section
withdraw_selection
invalidate_selection
replace_selection
create_annotation
revise_annotation
create_reflection
revise_reflection
review_curation_target
create_working_composition
```

Every mutation requires `expected_state_revision`. Arrangement and Composition
pointer changes additionally require the exact expected pointer revision.

## Authority gate

Provide a `CurationAuthorityGate` explicitly. The gate returns `allowed`,
`denied`, or `unresolved`. Tests may use the synthetic gate in
`scripts/curation_fixture_support.py`; production code does not enable it.

Conditional Candidate activation also requires the gate to acknowledge the
exact Candidate condition code. A gate decision does not imply disclosure
permission.

## Arrangement workflow

Placement activation, replacement, withdrawal, and section reorder create a
new complete `SectionArrangementRevision` and an append-preserving
`SectionArrangementPointerRevision` in the same semantic commit.

Do not derive order from Placement creation time.

## Annotation and Reflection

Annotations and Reflections are immutable revision series. Callers must supply
an exact expected revision when revising them. Comparison Reflection targets
must identify exact Selections and semantic roles explicitly.

Reflection must reference an exact Profile requirement of kind `reflection` and
preserves prompt ID, version, and snapshot because the current Profile runtime
has no prompt registry.

## Composition workflow

`create_working_composition` freezes current managed Selection/Placement state,
exact pointed Arrangements, current Annotation/Reflection revisions, applicable
Review Decisions, and unresolved obligations.

The existing `WorkingPortfolioCompositionRevision` remains frozen. Ancillary
curation state is stored in the one-to-one
`WorkingPortfolioCompositionInventory`.

Exact replay may return the current existing Composition when semantic curation
state is unchanged. A material curation change creates a successor revision.

## Fixture-backed validation

Issue #34 reuses the #33 Core/producer fixture setup and creates a distinct
curation Portfolio/Profile over the same exact Portfolio Subject. This avoids
changing Candidate-discovery fixture policy solely to satisfy curation tests.

Run:

```powershell
python -m pytest tests\test_curation_models.py tests\test_curation_state.py tests\test_curation_services.py tests\test_curation_workflows.py tests\test_validate_curation_workflows.py -q
python scripts\validate_curation_workflows.py
```

Then run Ruff, strict Mypy, and the complete authenticated-Core repository gate.

## Fixture status

ScoreForm-, Quillan-, and Concord-shaped data remain Vitrine development
fixtures. This implementation does not claim live producer integration and does
not add sibling runtime dependencies.
