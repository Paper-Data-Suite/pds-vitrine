# Installed end-to-end acceptance

Issue #39 adds a deep installed-wheel acceptance layer above Vitrine's existing
source-tree validators and narrow installed-wheel smoke tests.

The acceptance is intentionally staged during implementation. Slice 1 established
isolation, provenance, content-inventory, fail-closed dependency, and live-contract
non-masquerading guarantees. Slice 2 extends that same isolated interpreter through
one external Core workspace, exact cross-class Portfolio Subject identity, two
independent Portfolio/Profile Bindings, Core-backed fixture publication, and
Candidate discovery/evaluation. Slice 3 extends the installed scenario through
explicit improvement/showcase curation, independent frozen Working Portfolio
Compositions, and exact Audience Contexts. Slice 4 adds both immutable installed
Snapshot issuance pipelines through verified directory-package Exports and explicit
current-Edition pointers. Slice 5 completes the acceptance with producer-source drift
and removal, fresh-process historical reload, full write-isolation verification, and
one final qualification-gate invocation. The subsequent audit correction tightens the
shared dependency boundary, makes pointer resolution discriminating, scans the actual
showcase Export for privacy markers, and hardens isolated execution against bytecode
writes.

## Why this is separate from existing validation

Source-tree validators prove individual runtime contracts and representative
vertical slices with development support code available from the checkout. The
existing installed-wheel smokes prove narrower package, Subject, Profile,
Candidate, curation, and Snapshot surfaces.

Issue #39 instead proves representative Portfolio behavior from a non-editable
Vitrine wheel and the exact Core 0.6.0 wheel in one external environment. It must
not re-run source validators inside the installed probe.

## Isolation contract

`scripts/smoke_test_end_to_end_wheel.py` owns host-side isolation. It creates one
fresh virtual environment, installs Core and Vitrine from supplied wheels, clears
`PYTHONPATH`, sets `PYTHONDONTWRITEBYTECODE=1`, and invokes the installed verifier
with Python isolated mode plus explicit no-bytecode mode (`-I -B`) from an external
working directory. `-B` is explicit because isolated mode ignores `PYTHON*` environment
variables, including `PYTHONDONTWRITEBYTECODE`.

Before importing Vitrine for help/read-only inspection, the host resolves installed
package roots from distribution metadata and inventories them. It then proves `vitrine
--help` creates neither workspace state nor package-tree mutations. The verifier proves
required `vitrine` and `pds_core` modules originate in that environment's
`site-packages` and not the source checkout. It also verifies that
ScoreForm, Quillan, Concord, Meridian, and Portia are not Vitrine runtime
dependencies or implicit imports.

Wheel SHA-256 identities are included in the acceptance report. Vitrine's version
is read from installed distribution metadata rather than hard-coded into the
probe.

## Write-isolation contract

Issue #39 uses content identity rather than modification timestamps.

The host harness inventories tracked and untracked nonignored checkout files using
`git ls-files --cached --others --exclude-standard` and records file type, byte size,
and SHA-256. It separately inventories the entire committed fixture root plus installed
Vitrine and Core package trees. Source status, checkout content, fixture content, and
installed-package content must be identical after acceptance.

All Core workspace, staged producer manifests, and later Snapshot/Export outputs
live beneath the temporary acceptance root. The source fixture files are read-only
inputs and are never used as mutable Core Publication manifest paths.

## Fixture boundary after real producer publication contracts

ScoreForm, Quillan, and Concord now expose Core 0.6 publication contracts. Vitrine
v0.2.0 nevertheless continues to use its own explicit development fixtures:

```text
vitrine_scoreform_fixture
vitrine_quillan_fixture
vitrine_concord_fixture
```

These are Vitrine-owned synthetic projections shaped to exercise producer
semantics; they are not live producer integrations.

The installed acceptance therefore contains a negative compatibility guard. It
constructs support requests shaped like the current public ScoreForm, Quillan,
and Concord contracts and proves none can select a Vitrine fixture adapter.
Selection remains exact across producer module, Academic Work contract, manifest
contract, source-record contract, and capabilities.

Core installed producer discovery is also kept separate from Vitrine's explicit
development fixture registry. Vitrine does not expose its fixture profiles through
`paper_data_suite.publication_producers`.

## Fail-closed workflow configuration

Ordinary `default_workflow_dependencies()` remains unconfigured:

- no producer profiles;
- no producer adapters;
- unresolved source-read authority;
- unresolved curation authority;
- unresolved Snapshot-build authority;
- no Snapshot source providers or renderers;
- unconfigured Snapshot planning;
- development fixture mode disabled.

Installed acceptance constructs exactly one `VitrineWorkflowDependencies` context for
each combined installed run. That one context carries the explicit fixture producer and
adapter registries, source-read authorization gate, curation authority gate, Snapshot
build authority, Snapshot source-provider slot, Snapshot renderer slot, and explicit
unconfigured planning provider. The source-provider and renderer slots are stable objects
that are configured with each Portfolio's exact planned contracts; workflow services do
not bypass the shared dependency context with ad-hoc replacement gates or registries.
Actor attribution is never treated as authorization.

## One exact Subject and two Portfolios

The installed scenario creates three synthetic Core class/roster contexts:

```text
class-ela10-syn / 2023-2024
class-ela11-syn / 2024-2025
class-ela12-syn / 2025-2026
```

Each contains `student-syn-001` plus a deliberately confusing same-display-name
student with a different local ID. Vitrine creates one Portfolio Subject from the
first class-qualified reference, then explicitly links the later two exact
class-qualified references through the existing Subject service.

No display-name or bare-local-ID matching is accepted. Every class-qualified
reference must resolve back to the same exact Portfolio Subject.

Two distinct Portfolios are then created for that Subject:

```text
Installed Improvement Portfolio
Installed Showcase Portfolio
```

Each receives its own exact activated Profile Revision and Profile Binding.
Revision choice is explicit; there is no latest/highest/newest inference.

## Core-backed fixture publication

The installed probe stages exact committed fixture bytes under temporary Core
module work roots and registers/publishes them through Core 0.6 services.
Publication records therefore point only to temporary workspace files, never into
the source checkout.

Slice 2 publishes:

- a dedicated installed-acceptance ScoreForm-shaped two-attempt manifest for the
  common Portfolio Subject;
- representative Quillan-shaped baseline work;
- representative Quillan-shaped later work plus student-facing feedback;
- representative Quillan-shaped polished showcase work;
- representative Concord-shaped collaborative Artifact/Score evidence.

After publishing, the probe rebuilds the Core academic catalog and confirms every
canonical Publication is discoverable. Vitrine Candidate discovery still treats
catalog rows as proposals: the Candidate service reloads canonical Publication and
registration state and verifies exact manifest paths/digests before invoking a
fixture reader.

## Candidate semantics established by Slice 2

Improvement discovery preserves five exact projected sources:

```text
baseline_argument
revised_argument
revised_feedback
argument_assessment_attempt_1
argument_assessment_attempt_2
```

The ScoreForm-shaped projections prove two attempts remain distinct, in native
revision order, with exact response states and points. They do not infer or expose
`latest`, `best`, `official`, proficiency/mastery, or Grade policy. Candidate
discovery creates no Selection.

Showcase discovery preserves the polished Quillan-shaped Candidate and Concord's
collaborative semantics. The Portfolio Subject may be a Group member, Artifact
Subject, and documented contributor without becoming the Artifact Author. The
Group remains the explicit Artifact Author/represented Group where the fixture
says so. Group Score projections remain unresolved non-Candidates targeted to the
Group and are never converted into individual student Scores.

The collaborative Artifact remains conditionally eligible with
`collaborator_review_required`; Candidate eligibility does not satisfy that later
curation-review obligation automatically.

## Curation and audience semantics established by Slice 3

The installed improvement Portfolio now uses the explicit Proposal -> Decision ->
Selection path for baseline work, later work, and student-facing feedback. It then
creates exact Placements/Arrangements and one student-authored Reflection that
references the baseline and later Selections. The two ScoreForm-shaped attempts
remain unselected: preserving multiple attempts is not an instruction to choose
latest, highest, best, official, or otherwise preferred evidence.

The installed showcase Portfolio separately exercises teacher Direct Selection.
The collaborative Candidate still enters curation with
`collaborator_review_required`; the explicit authority decision acknowledges that
condition for Selection without erasing its provenance. The Portfolio then records
separate audience-safe attribution and student rationale annotations and an exact
required collaborator-treatment Review. Review of curation is not recipient or
disclosure authorization.

Each Portfolio freezes its own Working Portfolio Composition Revision and
Composition Inventory. Improvement resolves its cardinality and Reflection
obligations. Showcase resolves section cardinality and the exact approval
requirement, while deliberately retaining `collaborator_review_required` as the
Selection's explicit frozen condition; the later Snapshot Plan must acknowledge
that code rather than pretending the Candidate condition disappeared. Each
Portfolio then freezes a separate Audience Context from the exact bound Profile
Revision. Improvement uses the student-facing audience rule; showcase uses the
external-review rule and retains its prohibited collaborator/private content
classes. Composition, Audience Context, curation review, and disclosure
authorization remain distinct concepts.

## Snapshot issuance semantics established by Slice 4

The installed probe stages five committed synthetic source artifacts into a
temporary producer-source root that is a sibling of, not a child of, the Core
workspace. The committed fixture tree remains read-only input. Every copied Entry
Plan binds the exact Selection, Placement, Candidate, Candidate Evaluation, Core
Publication, producer/projection contract, Artifact identity, and approved source
locator. Source providers accept only that predeclared inventory.

The improvement Snapshot contains exactly four Entries: baseline work, later work,
student-facing feedback, and the exact frozen student Reflection revision. The two
ScoreForm attempts remain outside the Snapshot because neither was selected. The
Reflection is generated by a Vitrine-owned deterministic renderer from its exact
canonical Reflection and Composition references; it does not fabricate producer
provenance.

The showcase Snapshot contains exactly five Entries: polished individual work, the
reviewed collaborative Artifact, audience-safe attribution, student curation
rationale, and a synthetic Portfolio index. The collaborative copied Entry and its
audience-safe attribution require the exact collaborator-treatment Review frozen by
the Build Request. The Build Plan explicitly acknowledges
`collaborator_review_required`; review permits issuance but does not erase the
condition from historical curation provenance. No assessment summary is inserted
into showcase output.

The showcase acceptance also scans the actual directory-package Export bytes—not merely
the staged producer inputs—for collaborator identifiers, private fixture markers, secure
assessment markers, or claims of recipient/consent authorization. The internal Snapshot
manifest must not appear in the audience-facing Export.

Both Portfolios execute the full control plane:

```text
Snapshot Series
-> Build Request
-> Build Plan
-> Build Attempt
-> materialization
-> Seal
-> immutable Edition
-> verification
-> directory_package Export
-> Export verification
-> explicit Current Edition pointer
```

Every planned Entry must prepare bytes; this acceptance permits no omission.
Edition manifest/logical-inventory digests and Export directory-inventory digests
must reproduce immediately. Snapshot custody must contain no errors or staging
residue. Improvement and showcase use distinct Series and Export identities. After promoting
improvement Edition 1, acceptance deliberately seals and verifies an additional
improvement Edition 2 **without** advancing the current pointer. The installed read view
must still report Edition 1 as current even though Edition 2 is numerically greatest.

## Source drift and immutable historical custody established by Slice 5

After both Editions and Exports are sealed and verified, the primary installed process
changes one temporary staged producer artifact and deletes another. It immediately
re-verifies all three sealed Editions (improvement Editions 1 and 2 plus showcase
Edition 1) and both Exports and compares complete path/size/SHA-256 byte inventories
with the pre-drift inventories. It then removes the entire temporary
`producer-source` tree and repeats Edition and Export verification. Canonical Vitrine
state revision and the exact Candidate/Selection canonical-record digests must remain
unchanged throughout. Source drift therefore cannot retarget curation or refresh sealed
bytes.

The primary process then emits a bounded historical expectation document containing
only canonical-record SHA-256 inventories, state revision, and exact Snapshot control
plane/digest identities. It never sends producer fixture bytes, display-name payloads,
or the removed producer-source path to the reload process.

The host starts a second `python -I` interpreter in the same isolated wheel environment.
That process receives only the Core workspace and bounded expectation file. It proves:

- Vitrine and Core reload from installed `site-packages`;
- the producer-source root is absent and unnecessary;
- the complete canonical historical record inventory is byte-for-byte identical under
  canonical JSON serialization;
- each historical Composition resolves its own exact frozen Profile Binding revision;
- exact Series, Request, Plan, Attempt, Attempt Result, Seal, Edition, Export, and
  Current Pointer records resolve;
- improvement current Edition resolves to pointed Edition 1 while the same Series has a
  verified, numerically greater Edition 2, proving the result is not inferred from the
  greatest Edition number;
- Edition and Export digests still reproduce; and
- reload/verification performs no repair or canonical-state write.

## Qualification topology

The completed installed E2E acceptance is invoked exactly once after the existing five
installed-wheel smokes in `scripts/validate_repository.py`. It reuses the already-built
Vitrine wheel and exact Core wheel supplied to the repository gate. The host uses one
combined E2E virtual environment for the primary and fresh reload processes.

The E2E harness does not nest pytest, Ruff, Mypy, package builds, source validators, or
the repository validator. This preserves the validation-performance architecture
introduced by issue #52 while adding the final `source_drift`, `historical_reload`, and
`write_isolation` stages.
