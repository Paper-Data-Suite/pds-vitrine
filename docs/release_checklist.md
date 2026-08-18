# Vitrine Release Checklist

This checklist separates release preparation from release publication. A green
release-preparation pull request is necessary but does not mean a release exists.

The v0.2.0 release process has four phases:

```text
1. release-preparation branch and PR qualification
2. post-merge exact-main qualification
3. immutable tag and GitHub Release publication
4. fresh-download post-release verification
```

Issue #40 and umbrella #26 remain open through phase 4.

## Fixed v0.2.0 qualification input

Authenticate this Core wheel before every authoritative Vitrine v0.2.0 qualification:

```text
pds_core-0.6.0-py3-none-any.whl
SHA-256:
be28c061b38463ef59ebc328ed1aa443767fe7f2c626babb769c2d8e5932f308
```

Do not substitute a locally rebuilt Core wheel.

---

## Phase 1 — Release-preparation branch and PR

### 1A. Branch starting state

- [ ] Branch is `40-v0-2-0-implementation-audit-release`.
- [ ] Starting `main` commit is recorded.
- [ ] Local branch starts from reconciled `origin/main`.
- [ ] Working tree is clean before release-preparation edits.
- [ ] Exact Core 0.6.0 wheel is present and authenticated.
- [ ] Complete pre-change repository baseline passes.
- [ ] Baseline timing summary is saved in the issue/PR evidence.

Authoritative baseline command:

```powershell
python scripts\validate_repository.py `
  --core-wheel "$coreWheel"
```

Do not use `--allow-dirty` for the clean pre-change baseline.

Recorded issue #40 baseline on 2026-08-17:

```text
PASS installed E2E end-to-end acceptance
installed-wheel acceptance: end-to-end: 126.621s
TOTAL: 706.117s
PASS complete repository validation
```

### 1B. Architecture/release audit

- [ ] ADRs 0001–0009 are dispositioned against executable v0.2 evidence.
- [ ] PF-AUD-001 through PF-AUD-012 are reconciled using the preserved findings register.
- [ ] Every #26 exit condition has implementation evidence.
- [ ] No unresolved release blocker or major finding remains.
- [ ] Fixture/live producer boundary remains explicit.
- [ ] Identity, provenance, persistence/concurrency, privacy, and Snapshot custody are audited.
- [ ] Intentionally deferred v0.3/later surfaces remain unclaimed.

### 1C. Release identity preparation

- [ ] Single source version is promoted from `0.2.0.dev0` to `0.2.0`.
- [ ] Package checker expects release version `0.2.0`.
- [ ] `vitrine.__version__`, installed metadata, CLI, wheel, and sdist identities agree.
- [ ] Core requirement remains `pds-core>=0.6,<0.7`.
- [ ] Console script remains `vitrine = vitrine.cli:main`.
- [ ] No `paper_data_suite.modules` entry point is added.
- [ ] No `paper_data_suite.publication_producers` entry point is added.
- [ ] No sibling PDS runtime dependency is added.
- [ ] Narrow release-compatibility checks are added without duplicating full pytest/E2E.

### 1D. Documentation/release records

- [ ] `docs/v0.2.0-release-audit.md` is current.
- [ ] `docs/v0.2.0-release-compatibility.md` is current.
- [ ] `docs/release_checklist.md` is current.
- [ ] `Security.md` reflects actual v0.2 behavior and limitations.
- [ ] `README.md` and `docs/README.md` reflect release-preparation state accurately.
- [ ] CHANGELOG has a dated `0.2.0` section and a new `Unreleased` section.
- [ ] `RELEASE_NOTES_v0.2.0.md` or equivalent reviewed release notes exist.
- [ ] Release notes do not claim live ScoreForm/Quillan/Concord integration.

### 1E. Focused validation while branch is dirty

Use focused checks after each slice. `--allow-dirty` is permitted only when running the
complete validator against intentional uncommitted issue #40 edits.

At minimum before PR preparation:

```powershell
python -m pytest
python -m ruff check .
python -m mypy
python scripts\check_documentation.py
git diff --check
git status --short
```

### 1F. Complete release-preparation qualification

Run exactly one complete repository qualification:

```powershell
python scripts\validate_repository.py `
  --core-wheel "$coreWheel" `
  --allow-dirty
```

Require:

```text
PASS complete repository validation
```

Confirm the topology still contains:

```text
full pytest once
five narrow installed-wheel smokes once each
installed end-to-end acceptance once
```

- [ ] Complete validator passes.
- [ ] Timing summary shows no unexplained material regression.
- [ ] Validation leaves working-tree status unchanged.
- [ ] `git diff --check` passes.
- [ ] Complete diff receives independent architectural/code audit.

### 1G. Pull request

The release-preparation PR must reference, not close, the release issues:

```text
Refs #40
Refs #26
```

Do **not** use `Closes #40` or `Closes #26` in this PR.

- [ ] PR contains only intended Vitrine changes.
- [ ] No built `dist/` artifacts are committed.
- [ ] Hosted CI is green on Ubuntu/Windows × Python 3.11–3.14 through the established matrix topology.
- [ ] No unresolved review/change request remains.
- [ ] PR is squash-merged before final tag/release work.

---

## Phase 2 — Post-merge exact-main qualification

After the release-preparation PR is merged:

- [ ] Fetch/prune and reconcile local `main`.
- [ ] Working tree is clean.
- [ ] Local `main == origin/main`.
- [ ] Exact release commit SHA is recorded.
- [ ] Exact release tree SHA is recorded.
- [ ] Core 0.6.0 wheel is re-authenticated.
- [ ] Complete validator is run **without** `--allow-dirty`.

```powershell
python scripts\validate_repository.py `
  --core-wheel "$coreWheel"
```

- [ ] `PASS complete repository validation` is observed on exact release `main`.
- [ ] Any post-merge correction goes through a new PR and restarts this phase.

### Build exact final artifacts

From that exact clean commit:

```powershell
Remove-Item build, dist, pds_vitrine.egg-info -Recurse -Force -ErrorAction SilentlyContinue
python -m build
python -m twine check dist\*
python scripts\check_package.py dist\*.whl dist\*.tar.gz
```

- [ ] Exactly one wheel exists.
- [ ] Exactly one sdist exists.
- [ ] Wheel filename/version is `0.2.0`.
- [ ] Sdist filename/version is `0.2.0`.
- [ ] Package-content check passes.
- [ ] Final exact wheel passes installed qualification with authenticated Core 0.6.0.
- [ ] Wheel SHA-256 is recorded.
- [ ] Sdist SHA-256 is recorded.
- [ ] `SHA256SUMS.txt` contains exactly the intended release-asset hashes.

Do not rebuild after recording hashes unless all downstream records are regenerated from
the new bytes.

---

## Phase 3 — Tag and GitHub Release publication

Only after Phase 2 is green:

- [ ] Create immutable tag `v0.2.0` at the exact qualified release commit.
- [ ] Confirm the tag resolves to that exact commit before publication.
- [ ] Do not move/rewrite the tag after publication.
- [ ] Create GitHub Release `pds-vitrine v0.2.0`.
- [ ] Attach only the exact verified assets:

```text
pds_vitrine-0.2.0-py3-none-any.whl
pds_vitrine-0.2.0.tar.gz
SHA256SUMS.txt
```

- [ ] Published release notes accurately describe the fixture-only producer boundary.
- [ ] Release notes identify Core 0.6 compatibility.
- [ ] Release notes do not claim production authorization, recipient delivery, regulated workflow, or live producer integration.
- [ ] No PyPI/package-index publication occurs without separate explicit authorization.

Issue #40 remains open.

---

## Phase 4 — Fresh-download release verification

Download the **published GitHub Release assets** into a fresh location. Do not substitute
local `dist/` files.

- [ ] Downloaded wheel SHA-256 matches the Phase 2 value.
- [ ] Downloaded sdist SHA-256 matches the Phase 2 value.
- [ ] `SHA256SUMS.txt` matches both assets.
- [ ] Fresh virtual environment contains no editable Vitrine install.
- [ ] Authenticated Core 0.6.0 wheel is installed.
- [ ] Downloaded Vitrine wheel is installed noneditably.
- [ ] `python -m pip check` passes.
- [ ] `importlib.metadata.version("pds-vitrine") == "0.2.0"`.
- [ ] `vitrine.__version__ == "0.2.0"`.
- [ ] `vitrine --version` reports `0.2.0`.
- [ ] `python -m vitrine --version` reports `0.2.0`.
- [ ] Vitrine and Core import from the fresh environment's `site-packages`.
- [ ] No sibling producer package is required.
- [ ] Help/import remain side-effect-free.
- [ ] Ordinary workflow dependencies remain fail-closed.
- [ ] Fixture/live non-masquerading checks pass.
- [ ] #39 installed end-to-end acceptance passes against the downloaded wheel.
- [ ] Installed Vitrine/Core package inventories remain unchanged after acceptance.

Only after these checks pass:

- [ ] Record final release commit/tree, asset hashes, and GitHub Release URL on #40.
- [ ] Close #40.
- [ ] Confirm every #26 sub-issue is complete.
- [ ] Close #26.
- [ ] Close the v0.2.0 milestone.

---

## Stop rules

Do not publish or close the release if any of these occurs:

```text
ADR/contract contradiction
unresolved blocker or major audit finding
Core wheel authentication mismatch
package metadata/version mismatch
sibling runtime dependency
fixture/live producer masquerading
permissive default workflow dependencies
Candidate -> Selection implication
Selection -> disclosure implication
cross-class name/bare-ID identity inference
Group/Author/Subject/contribution/Score-target collapse
max/newest current-state inference where an explicit pointer is required
Snapshot digest/custody inconsistency
issued history following source drift
actual Showcase Export privacy failure
working-tree mutation caused by validation
supported CI cell failure
release artifact hash mismatch
fresh downloaded release failure
```

A feature intentionally assigned to a later milestone is not itself a release blocker
unless current code or documentation falsely claims that feature is implemented.
