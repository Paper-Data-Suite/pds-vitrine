# Vitrine v0.3.0 Release Checklist

This checklist is the authoritative four-phase ceremony for issue #72 / umbrella #56.
A green release-preparation branch does not mean a release exists.

```text
1. release-preparation branch and PR qualification
2. post-merge exact-main qualification
3. immutable tag and GitHub Release publication
4. fresh-download post-release verification
```

Issue #72 and #56 remain open through Phase 4.

## Fixed qualification inputs

Authenticate the exact frozen PDS release artifacts:

```text
pds_core-0.6.3-py3-none-any.whl
98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5

scoreform-0.11.0-py3-none-any.whl
8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44

quillan-0.10.0-py3-none-any.whl
5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9

pds_concord-0.3.0-py3-none-any.whl
dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12
```

Do not substitute locally rebuilt same-version PDS artifacts for authoritative
release qualification.

---

## Phase 1 — Release-preparation branch and PR

### Starting state

- [ ] Branch is `72-v0-3-0-privacy-provenance-usability-release-audit`.
- [ ] Starting `main` commit is `d9ff8ed95215c6b89e4286a6da0085a84620c37a`.
- [ ] Starting tree is `0ad98deb513ca8a4661f68237f8b7e050ab04bae`.
- [ ] Branch starts from reconciled post-#71 `main`.
- [ ] Pre-change/early-slice evidence is recorded on #72.

### Architecture/privacy/provenance/usability audit

- [ ] ADR 0001 through ADR 0009 are explicitly dispositioned.
- [ ] #57 through #71 each have implementation evidence, teacher consequence,
  privacy/provenance implication, known limitation, and release status.
- [ ] Source-read authorization is before protected producer source content I/O.
- [ ] Quillan/Concord Artifact authorization remains separate from source-read auth.
- [ ] Candidate eligibility does not imply Selection authority.
- [ ] Selection does not imply Snapshot-build or disclosure authority.
- [ ] Audience Context does not imply recipient identity/relationship/consent.
- [ ] Local Export is never described as delivery.
- [ ] Suppression/negative state does not leak through rows/counts/facets/attention.
- [ ] Diagnostics remain minimum-necessary and path/content safe.
- [ ] Suite operations do not gain Vitrine record/policy authority.
- [ ] Repository/release evidence is synthetic-only and contains no private records.

### Release identity and package boundary

- [ ] `vitrine/_version.py` is `0.3.0`.
- [ ] Package checker expects `0.3.0`.
- [ ] `vitrine.__version__`, installed metadata, CLI, wheel, and sdist agree.
- [ ] Python remains `>=3.11`.
- [ ] Runtime dependency remains `pds-core>=0.6.3,<0.7`.
- [ ] Console remains `vitrine = vitrine.cli:main`.
- [ ] `paper_data_suite.module_operations` exposes only the Vitrine provider.
- [ ] `paper_data_suite.modules` remains undeclared.
- [ ] `paper_data_suite.publication_producers` remains undeclared.
- [ ] No unconditional ScoreForm/Quillan/Concord/Portia/Meridian dependency is added.

### #71 promoted-candidate acceptance

- [ ] The #71 acceptance contract expects `pds-vitrine 0.3.0`.
- [ ] Hosted live-acceptance CI builds exactly one `pds_vitrine-0.3.0-*.whl`.
- [ ] Exact producer filenames/hashes remain unchanged.
- [ ] Offline installation boundary remains unchanged.
- [ ] Fixture/live non-masquerading remains unchanged.
- [ ] Negative matrix remains unchanged.
- [ ] Custody/tamper/historical/source-disappearance proofs remain unchanged.
- [ ] Core+Vitrine-only verifier remains unchanged.

### Release records

- [ ] `docs/v0.3.0-release-audit.md` is complete with final dispositions.
- [ ] `docs/v0.3.0-release-compatibility.md` is current.
- [ ] `RELEASE_NOTES_v0.3.0.md` is reviewed.
- [ ] `CHANGELOG.md` contains a dated `0.3.0` section and fresh `Unreleased`.
- [ ] `README.md`, `docs/README.md`, and `Security.md` are current.
- [ ] Historical v0.2.0 release records remain intact.
- [ ] `MANIFEST.in` and package checks include the v0.3.0 release records.

### Focused branch validation

Run focused checks after each logical slice:

```powershell
python -m pytest `
  tests/test_metadata.py `
  tests/test_validate_release_contract.py `
  tests/test_live_installed_acceptance_contract.py `
  tests/test_validate_live_installed_acceptance.py

python .\scripts\validate_release_contract.py
python .\scripts\validate_live_installed_acceptance.py
python .\scripts\check_documentation.py
python -m ruff check .
python -m mypy
git diff --check
```

### Build and exact live-installed branch qualification

Build a candidate wheel from the branch:

```powershell
Remove-Item build, dist, pds_vitrine.egg-info -Recurse -Force -ErrorAction SilentlyContinue
python -m build
python -m twine check dist\*
python .\scripts\check_package.py dist\*.whl dist\*.tar.gz
```

Prepare the local wheelhouse exactly as required by #71, then run:

```powershell
python .\scripts\qualify_installed_live_portfolio.py `
  --vitrine-wheel .\dist\pds_vitrine-0.3.0-py3-none-any.whl `
  --wheel-dir "$HOME\Downloads"
```

Require the terminal marker:

```text
PASS issue #71 full live installed cross-producer acceptance
```

Then run the complete repository gate with the authenticated Core wheel:

```powershell
python .\scripts\validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty
```

- [ ] Complete repository validation passes.
- [ ] Live-installed acceptance passes with the promoted candidate.
- [ ] `git diff --check` passes.
- [ ] Validation does not introduce unintended working-tree changes.
- [ ] Hosted CI is green on its complete matrices.
- [ ] Independent diff/audit review finds no unresolved blocker/major issue.

The Phase 1 PR references #72/#56; it does not close them.

---

## Phase 2 — Post-merge exact-main qualification

After the release-preparation PR is squash-merged:

- [ ] Fetch/prune and reconcile local `main`.
- [ ] Working tree is clean.
- [ ] Local `main == origin/main`.
- [ ] Exact release commit SHA is recorded.
- [ ] Exact release tree SHA is recorded.
- [ ] Re-authenticate all four fixed PDS qualification artifacts.
- [ ] Run complete repository validation without `--allow-dirty`.
- [ ] Build the wheel/sdist exactly once from that exact clean commit.
- [ ] `twine check` and `scripts/check_package.py` pass.
- [ ] Run the full #71 live-installed acceptance against that exact final wheel.
- [ ] Record wheel and sdist SHA-256 values.
- [ ] Create `SHA256SUMS.txt` for exactly the intended release assets.
- [ ] Do not rebuild after recording hashes unless all downstream evidence is reset.

Expected final artifact names:

```text
pds_vitrine-0.3.0-py3-none-any.whl
pds_vitrine-0.3.0.tar.gz
SHA256SUMS.txt
```

Any post-merge correction goes through a new PR and restarts Phase 2.

---

## Phase 3 — Tag and GitHub Release publication

Only after Phase 2 is green:

- [ ] Create immutable tag `v0.3.0` at the exact qualified release commit.
- [ ] Confirm the tag resolves to that commit.
- [ ] Do not move/rewrite the tag after publication.
- [ ] Create GitHub Release `pds-vitrine v0.3.0`.
- [ ] Attach only the exact Phase 2 wheel, sdist, and `SHA256SUMS.txt`.
- [ ] Publish reviewed `RELEASE_NOTES_v0.3.0.md` content.
- [ ] Do not claim production institutional authorization or external delivery.
- [ ] Do not publish to PyPI/package index without separate explicit authorization.

Issue #72 remains open.

---

## Phase 4 — Fresh-download release verification

Download the **published GitHub Release assets** to a fresh location; do not substitute
local `dist/` bytes.

- [ ] Downloaded wheel hash matches Phase 2.
- [ ] Downloaded sdist hash matches Phase 2.
- [ ] `SHA256SUMS.txt` matches both.
- [ ] Fresh environment contains no editable Vitrine checkout.
- [ ] Install authenticated Core 0.6.3.
- [ ] Install downloaded Vitrine wheel noneditably.
- [ ] `python -m pip check` passes.
- [ ] `importlib.metadata.version("pds-vitrine") == "0.3.0"`.
- [ ] `vitrine.__version__ == "0.3.0"`.
- [ ] `vitrine --version` and `python -m vitrine --version` report `0.3.0`.
- [ ] Core/Vitrine imports resolve from the fresh environment.
- [ ] No sibling producer is required for ordinary Core+Vitrine install/use.
- [ ] Module-operations provider discovery works from the downloaded wheel.
- [ ] Package-content checks pass against downloaded artifacts.
- [ ] Fresh exact producer wheels are independently authenticated/downloaded.
- [ ] The authoritative no-flag #71 live-installed acceptance passes against the
  downloaded Vitrine wheel.
- [ ] Sealed Core+Vitrine-only verification still works.
- [ ] No release verification step mutates package/source inventories unexpectedly.

Only after all checks pass:

- [ ] Record release commit/tree, artifact hashes, and GitHub Release URL on #72.
- [ ] Record final audit verdict.
- [ ] Close #72.
- [ ] Confirm all #56 sub-issues are complete.
- [ ] Close #56 / v0.3.0 milestone.

---

## Stop rules

Do not publish or close the release for:

```text
accepted ADR / frozen contract contradiction
unresolved blocker or major audit finding
artifact authentication mismatch
version/metadata/package mismatch
sibling runtime dependency
fixture/live producer masquerading
source read before authorization
producer-private path/API fallback
Candidate -> Selection implication
Selection -> Snapshot/disclosure implication
suppression/privacy leakage
diagnostic protected-content/path leakage
Group/Author/Subject/contribution/Score-target collapse
Snapshot/Export custody or digest inconsistency
Export described/treated as delivery
suite operations gaining Vitrine policy/record authority
working-tree mutation caused by qualification
supported CI failure
release artifact hash mismatch
fresh downloaded release failure
```

A deliberately later feature is not itself a blocker unless v0.3.0 falsely claims it.
