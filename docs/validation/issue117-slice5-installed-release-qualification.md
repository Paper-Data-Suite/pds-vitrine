# Issue #117 — Slice 5 noneditable official-producer installed qualification

**Candidate phase only. Not v0.4.0 publication or post-release verification.**

## Preconditions

- Clean `release/v0.4.0` at Slice 4 commit `6d5c140` before applying this slice.
- All four actual GitHub Release input wheels have passed the independent Slice 4 `--wheel-dir` byte-hash and metadata authenticator.
- An independently built *candidate* Vitrine wheel `pds_vitrine-0.4.0-py3-none-any.whl` exists. Do not use an editable wheel or a previous published wheel.

## Accepted process

1. Verify Slice 4 static wheel identities and authenticate the **four actual local input wheels** anew.
2. Check the candidate filename, ZIP integrity, `pds-vitrine` name, version `0.4.0`, Python floor, and Core-only unconditional dependency. Record its candidate-only SHA-256; no release SHA is asserted.
3. Copy the already accepted current-producer fixture/projection and authorized Artifact bridge *qualification scripts*, not the Vitrine runtime, into a disposable probe directory.
4. Create a fresh isolated Python environment, install the four original authenticated wheels and the candidate Vitrine wheel noneditably, resolve their ordinary declared dependencies, and require `pip check`.
5. Run child Python with **`-I -B`**, no `PYTHONPATH`, no `PYTHONHOME`, and a working directory outside the repository. Confirm all five installed distributions and package imports come from within the disposable environment, no editable `direct_url.json` is present, and `vitrine --version` resolves to 0.4.0.
6. Execute the existing actual released-producer reader and projection test fixture under the installed Vitrine package. It checks Core Reader Contract v1 metadata, reader identities, public ScoreForm/Quillan/Concord model projections, source attribution, and native source distinctions.
7. Run existing Concord and Quillan authorized Artifact source-bridge qualification on synthetic teacher/workspace records, with no real student data or producer-private access.
8. Fail closed for any wrong/missing wheel, changed hash, unsupported metadata, source checkout import, editable install, failed artifact boundary, or residual work directory output.

The original #71 v0.3.0 exact installed replay remains frozen, and the #104 *synthetic future producer* matrix remains a separate release-number-resilience acceptance. This qualification reuses current live reader code and exact authenticated official producer wheels. The fixed audit SHA-256 list authenticates **test inputs only**, never Vitrine runtime compatibility policy.

## Commands (PowerShell from repository root)

```powershell
$ErrorActionPreference = "Stop"
$inputs = Join-Path $HOME "Downloads\vitrine117-release-inputs"
$dist = Join-Path $HOME "Downloads\vitrine117-candidate-dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null

python -m build --wheel --no-isolation --outdir $dist
if ($LASTEXITCODE -ne 0) { throw "Candidate build failed" }

$candidate = Join-Path $dist "pds_vitrine-0.4.0-py3-none-any.whl"
python scripts/qualify_issue117_installed_release.py `
    --wheel-dir $inputs `
    --vitrine-wheel $candidate
if ($LASTEXITCODE -ne 0) { throw "Current official-producer installed acceptance failed" }
```

Build from a known source tree and avoid reusing an old wheel in the output directory. Before definitive release qualification, run the complete repository validator and the installed qualifier on the exact merged clean `main` commit. A passing branch candidate does **not** establish a publishable immutable release artifact.
