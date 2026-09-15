# Live installed cross-producer acceptance

Issue #71 adds Vitrine's authoritative installed acceptance for the released ScoreForm, Quillan, and Concord producer integrations. The completed qualification is deliberately separate from ordinary unit tests because it authenticates and installs exact release wheels, creates producer-native synthetic state, exercises live Vitrine discovery and curation, builds and verifies a real Portfolio Snapshot/Export, and qualifies the required negative and historical cases.

## Frozen release composition

The acceptance identity is `vitrine_live_installed_cross_producer_acceptance_v1`. The dependency artifacts are fixed to PDS Core 0.6.3, ScoreForm 0.11.0, Quillan 0.10.0, and Concord 0.3.0. The qualifier consumes local wheels and authenticates each filename and SHA-256 digest before installation. It never resolves a floating `latest` release or substitutes a same-version PDS artifact from another source.

Vitrine is built from the issue branch and installed noneditably. Issue #71 does not promote Vitrine's package version and does not add ScoreForm, Quillan, or Concord to Vitrine's runtime dependencies.

## Isolation topology

The outer repository harness creates a fresh virtual environment outside the repository, removes `PYTHONPATH`, installs the authenticated PDS wheels by exact path with `--no-index --find-links` against the caller-prepared local wheelhouse, runs `pip check`, copies the acceptance runners outside the source checkout, and executes them from that external working directory. The installed probes require Core, all three producers, and Vitrine to resolve from the isolated environment's `site-packages`.

A second environment contains only exact Core and the candidate Vitrine wheel. The final issue acceptance uses that environment after a successful seal to prove that historical Vitrine custody can be loaded and verified without importing or reinstalling any producer.

## Producer boundaries

The final live scenario preserves the deliberately different source-access rules:

- ScoreForm evidence is live but Snapshot materialization is `reference_only`. Vitrine must not open `retained_source_path`, reconstruct an answer sheet, or invent a ScoreForm Artifact resolver.
- Quillan source bytes may be copied only through `quillan.academic_result_artifacts` after a separate exact Artifact authorization decision.
- Concord source bytes may be copied only through `concord.academic_result_artifacts` after a separate exact Artifact authorization decision.
- Vitrine-owned Reflection content uses Vitrine's generated-content renderer path.

Publication compatibility, Candidate source-read authority, curation authority, Snapshot-build authority, Quillan Artifact authority, and Concord Artifact authority remain separate decisions.

## Slice 3 healthy Portfolio boundary

Slice 2 is accepted from installed exact-wheel qualification: all three released
producer-native Publications, explicit three-class Subject linking, and live
Candidate discovery passed. Slice 3 extends the same installed scenario through
explicit representative curation and Vitrine's production Current Portfolio
build path while deliberately leaving `FULL_ACCEPTANCE_READY = False`.

Curation is exact and teacher/student controlled rather than ranked. The synthetic
Portfolio explicitly selects ScoreForm attempt 1 as baseline, Quillan selected
student work and one Concord collaborative Artifact as later evidence, and the
Quillan PDF feedback capability as supporting feedback. It then creates one
student comparison Reflection, records the required teacher approval, and freezes
one Working Composition. No score, date, rating, `latest`, `highest`, or `best`
heuristic selects evidence.

Snapshot preparation configures only the production Quillan and Concord authorized
Artifact providers. Source-manifest reauthorization, Quillan Artifact authority,
Concord Artifact authority, and Snapshot-build authority remain distinct gates.
The expected immutable materialization inventory is exactly five logical items:

- one ScoreForm `reference_only` assessment summary;
- one copied Quillan student-work Artifact;
- one copied Concord collaborative Artifact;
- one copied Quillan PDF feedback Artifact; and
- one Vitrine-generated student Reflection.

The high-level `execute_prepared_current_portfolio_build` path must build, seal,
verify, and export the exact Edition. The ScoreForm materialization must carry no
output digest or byte size, proving that no answer-sheet bytes were invented or
read. Quillan and Concord copied sources must be acquired only after their
producer-specific authorization gates.

Run Slice 3 after the exact-wheel preflight succeeds:

```powershell
python .\scripts\qualify_installed_live_portfolio.py `
  --vitrine-wheel .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  --wheel-dir "$HOME\Downloads" `
  --portfolio-snapshot-only
```

The local wheelhouse must contain the four exact audited PDS release wheels plus
compatible binary wheels for ordinary third-party dependencies. No network access
is used by the qualifier.

## Slice 4A negative/currentness boundary

Slice 4A keeps the healthy Slice 3 contract frozen and adds isolated destructive
qualification on cloned synthetic workspaces. ScoreForm creates a real producer
revision 2 and explicitly supersedes the exact original Core Publication; Vitrine
must report the selected original Candidate as stale with
`candidate_inbox.publication_superseded` while preserving its original source
Publication identity. Quillan freezes an immutable Snapshot Plan before its
manifest-bound review source changes; execution of that old Plan must fail rather
than reread a successor or rewrite the Plan. Concord freezes the same kind of Plan
before the exact retained scan source named by its historical Artifact disappears;
execution must fail without substituting another source.

Authorization failures are independent cases. Denied and unresolved Candidate
source-read decisions must produce bounded findings without Candidate persistence.
Denied producer Artifact authority occurs only after an immutable Plan exists and
must stop materialization before any Snapshot Edition is sealed. Each destructive
case runs on its own workspace clone so no mutation can satisfy another case.

Run Slice 4A with `--negative-matrix-only`. `FULL_ACCEPTANCE_READY` remains false;
Export tamper, historical reload, producer-independent verification, and post-seal
custody remain for the final slice.

## Remaining full-issue work

Slice 4A is not the full #71 gate. The remaining work adds Export tamper,
historical reload, producer-independent verification, and post-seal custody cases.
Only after those pass on the supported CI endpoints may `FULL_ACCEPTANCE_READY`
become true.
