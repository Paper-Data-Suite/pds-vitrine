# Issue #71 validation — live installed cross-producer acceptance

## Scope

This validation record tracks issue #71 from reconciled Vitrine `main` baseline `c481ecd3f4c04fe31b8ee350a5a4b5c56f7c45aa` (completed #70). Issue #71 is an acceptance and qualification issue: it composes already accepted live producer, Candidate, curation, Working Composition, Snapshot, Export, attention, and suite-operation boundaries rather than defining new producer or Portfolio policy.

## Frozen acceptance infrastructure

The qualification contract freezes:

- acceptance identity `vitrine_live_installed_cross_producer_acceptance_v1`;
- exact Core 0.6.3, ScoreForm 0.11.0, Quillan 0.10.0, and Concord 0.3.0 wheel filenames and SHA-256 digests;
- live producer identities and semantic contract versions;
- ScoreForm `reference_only` materialization;
- Quillan and Concord `copied_source` capability through producer-owned Artifact APIs;
- explicit fixture/live identity separation;
- Ubuntu/Python 3.11 and Windows/Python 3.14 target qualification endpoints;
- all eight required heavy scenario families;
- Vitrine's unchanged Core-only runtime dependency.

The outer qualifier authenticates local release wheels, verifies the candidate remains Vitrine 0.2.0, creates a fresh live environment, installs the exact composition noneditably without package-index resolution, clears `PYTHONPATH`, checks dependency consistency, and executes an installed-origin/live-registry probe outside the repository. It also creates a second Core+Vitrine-only environment and proves that no producer distribution or module is present there.

## Slice 1 qualification

Slice 1 is accepted from local Windows/Python 3.11 qualification. The exact-wheel installation succeeded, `pip check` reported no broken requirements, the ordinary live Core producer registry exposed exactly ScoreForm/Quillan/Concord, the ordinary Vitrine adapter registry exposed exactly the corresponding live adapters, fixture identities were absent, default workflow dependencies remained fail-closed, and the Core+Vitrine verifier environment contained no producer package.

## Slice 2 accepted contract

Slice 2 adds an installed-only live scenario and keeps `FULL_ACCEPTANCE_READY = False`.

The scenario creates separate Core class contexts and explicit Vitrine Subject links for one synthetic learner, then uses the released producer production surfaces to create:

- ScoreForm native assignment state with two preserved attempts and one current Core Publication;
- Quillan printable-response routing, review, feedback exports, Registration, Manifest, and current Core Publication;
- Concord collaborative returned Artifact state, explicit collaborator/subject attribution, moderation, Criterion/Scale/Score evidence, Registration, Manifest, and current Core Publication.

After rebuilding Core's academic catalog, Slice 2 uses `build_publication_producer_registry`, ordinary `build_adapter_registry`, one exact source-read authorization gate, and `discover_and_evaluate_candidates`. It validates structural Candidate inventories without ranking or selecting them. The live scenario contains no development producer registry, development adapter registry, producer-adapter fixture path, or fixture producer identity.

Failure reporting is stage-bounded: it reports only the acceptance stage and exception type, not manifest bodies, student writing, feedback text, private notes, source bytes, or producer-native paths.


## Slice 3 delivered contract

Slice 3 adds explicit curation and the healthy immutable Snapshot/Export path while
keeping `FULL_ACCEPTANCE_READY = False`. The scenario chooses exact Candidate
identities only: ScoreForm attempt 1, Quillan selected student work, one Concord
collaborative Artifact, and Quillan PDF feedback. It creates the packaged Profile's
required student comparison Reflection and teacher approval before freezing the
Working Composition.

The Snapshot path uses the normal production Current Portfolio preparation and
execution services. It configures canonical Quillan and Concord Artifact context
resolvers and producer-authorized source providers, then verifies a five-item
materialization inventory: one ScoreForm `reference_only`, three `copied_source`,
and one `generated_vitrine`. Authorization boundaries are counted independently:
three Snapshot source-manifest reauthorizations, two Quillan Artifact decisions,
one Concord Artifact decision, and one Snapshot-build decision.

The installed output remains low-density and must not print student writing,
feedback text, private notes, manifest bodies, source bytes, or producer-native
paths.

## Slice 4A delivered contract

Slice 4A adds the pre-custody negative families while preserving the exact Slice 3
healthy scenario. It uses only installed release producer APIs plus intentional
mutation/removal of the exact producer source bytes under test.

- ScoreForm appends a real third attempt, generates producer revision 2, and
  explicitly supersedes the original Publication. The selected old Candidate is
  then read through the production Candidate inbox and must be stale without
  retargeting its persisted Evaluation.
- Quillan freezes the canonical Snapshot Build Plan before changing the exact
  manifest-bound review source. Execution must fail with materialization integrity
  failure, preserve the Plan, and create no Edition.
- Concord freezes a Plan before deleting the one retained scan source referenced
  by the represented Artifact. Execution must fail closed with no alternate source
  and no Edition.
- Separate pre-Candidate clones exercise denied and unresolved source-read
  authority, and a curated clone exercises denied producer Artifact authority.
  None may cross the persistence/materialization boundary its gate protects.

The heavy Slice 4A entry point is `--negative-matrix-only`. Full ticket acceptance
remains disabled.

## Focused validation

Run:

```powershell
python -m pytest `
  tests/test_live_installed_acceptance_contract.py `
  tests/test_validate_live_installed_acceptance.py

python .\scripts\validate_live_installed_acceptance.py

git diff --check
```

Then run the installed Slice 3 gate using the already prepared local wheelhouse:

```powershell
python .\scripts\qualify_installed_live_portfolio.py `
  --vitrine-wheel .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  --wheel-dir "$HOME\Downloads" `
  --portfolio-snapshot-only
```

The qualifier first repeats both Slice 1 isolation preflights, reruns the accepted producer-native/Candidate path, then performs exact curation and the authorized Current Portfolio build in the same isolated live environment. Successful output remains bounded to stage PASS lines and low-density structural counts and materialization kinds.

## Deliberate non-claim

Slice 3 does **not** claim issue #71 completion. It qualifies the healthy Portfolio/Snapshot path but does not yet qualify the drift/denial/removal/tamper/historical/producer-independent/post-seal cases. A full invocation without a slice flag still fails closed. CI heavy-gate wiring and final package-check inclusion remain deferred until the authoritative full scenario is present, preventing a partial slice from appearing as a green #71 completion gate.

## Slice 4B delivered contract

Slice 4B adds the remaining custody/tamper/historical/producer-independent proof while preserving `FULL_ACCEPTANCE_READY = False`. The heavy gate must demonstrate that export tampering is detected, an exact persisted state revision can be reloaded after it becomes historical, sealed custody remains verifiable after all three producer work roots disappear, and a separately installed Core+Vitrine verifier reproduces the exact Edition/Export digests without producer distributions or imports.

Run the slice gate with:

```powershell
python .\scripts\qualify_installed_live_portfolio.py `
  --vitrine-wheel .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  --wheel-dir "$HOME\Downloads" `
  --custody-verifier-only
```

The expected terminal marker is `PASS issue #71 Slice 4B custody, tamper, historical, and producer-independent verification acceptance`. Final combined orchestration and the required Ubuntu/Python 3.11 + Windows/Python 3.14 CI wiring remain a later completion gate.
