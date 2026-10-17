# Issue #117 Slice 6 — Windows viewer-handoff characterization

**Status: release gate OPEN; real Windows viewer accessibility not yet qualified.**

This slice preserves existing v0.4.0 runtime behavior and expands the active
Issue #102 installed-wheel smoke to capture four verified canonical targets.
The Core #232 reusable viewer-handoff correction is in progress and targets
Core v0.6.6; no unpublished API is presumed available today.

## Precisely what is established

The Core-only installed test constructs real, synthetic Vitrine Snapshot Editions,
verified technical Exports, and verified student Presentations. It uses Vitrine's
four opening methods. The original injected opener / tamper / canonical
verification tests remain intact. Optional real viewer mode creates a separately
retained, never-before-existing deep workspace so Windows applications can be
inspected after shell dispatch. **No student records are used.**

- Student HTML: genuine verified `portfolio.html`; check browser display and
  any local relative assets/navigation, not merely a blank tab or URL.
- Printable PDF: genuine verified `portfolio.pdf`; check actual page rendering.
- Presentation folder: use Explorer to browse/open files.
- Technical Export folder: use Explorer to browse/open files.

Each canonical path must exceed 260 characters. The report explicitly separates
`canonical_path`, `handoff_path`, `shell_handoff`, and `viewer_accessibility`.
A successful `os.startfile()` is **not proof of viewer accessibility**.

## Input / build prerequisites

Use an independently built `pds_vitrine-0.4.0-py3-none-any.whl` from the current
branch, the authenticated `pds_core-0.6.5-py3-none-any.whl`, and a graphical
Windows session with its configured browser, PDF viewer, and Explorer. The
installed acceptance is Core+Vitrine only; unrelated producers are absent.

The verifier intentionally remains **pending** after just creating a report.
Real on-screen observation and explicit interactive attestation are mandatory.

## Example workflow (PowerShell on graphical Windows)

```powershell
$ErrorActionPreference = "Stop"
$report = Join-Path $HOME ("Downloads\\vitrine117-viewer-report-" + [guid]::NewGuid().ToString("N") + ".json")
$workspace = Join-Path $HOME ("Downloads\\vitrine117-viewer-" + [guid]::NewGuid().ToString("N"))
for ($i = 0; $i -lt 3; $i++) {
    $workspace = Join-Path $workspace ("OneDrive-Synthetic-School-Year-2026-2027-Layer-{0:D2}" -f $i)
}

# Supply your existing candidate wheel and authenticated Core wheel paths.
python scripts/smoke_test_completed_portfolio_navigation_wheel.py `
    $candidate `
    "$HOME\Downloads\vitrine117-release-inputs\pds_core-0.6.5-py3-none-any.whl" `
    --viewer-workspace $workspace `
    --viewer-report $report
if ($LASTEXITCODE -ne 0) { throw "Viewer specimen construction/launch failed" }

# Inspect the actual opened browser, PDF viewer, and BOTH Explorer folders.
# Do not type VIEWED merely because the launching command succeeded.
python scripts/validate_issue117_windows_viewer_acceptance.py --attest-report $report
if ($LASTEXITCODE -ne 0) { throw "Viewer accessibility not qualified" }
```

Retained sample data and the report are outside the repository and outside
real student workspaces. Review and delete these **synthetic-only** files after
preserving the test result in the release audit. No canonical artifact is
rewritten or moved for the viewer probe.

### Baseline real-Windows observation (Core 0.6.5)

The first human-attested Core 0.6.5 run on October 14, 2026 (US Eastern) used
real Edge and Explorer after canonical Portfolio construction in a synthetic
deep Windows workspace. All four shell handoffs returned and the exact verified
canonical targets were handed over. The reported accessibility was:

- **FAILED:** student HTML at 302 characters; Microsoft Edge reported file not found.
- **FAILED:** printable PDF at 357 characters; Microsoft Edge reported file not found.
- **VIEWED:** Presentation directory at 287 characters in File Explorer.
- **VIEWED:** technical Export directory at 291 characters in File Explorer.

The HTML and PDF checks establish *viewer inaccessibility*, not a broken
Portfolio manifest. Core #232 / official qualified Core v0.6.6 adoption and a
fresh four-target real Windows pass are **required** for Vitrine v0.4.0.

The corrected local report is SHA-256 `06fd85bc01a31e54b0ffd2c5c1ed6cbbfd210cacf3fef82c43b108f777140224`. It and the initial
all-FAILED attestation remain **outside Git** and are not student data. The
original test exit code was 1 because the two Edge files were genuinely
inaccessible; that is the **expected blocking verdict**, not a test-harness
crash. Do not rewrite this failed baseline to manufacture a release pass.

## Safety and release qualification

- Canonical record lookup, first-party Presentation/Export/Edition verification,
  safe descendant checking, and immutable custody remain Vitrine-owned.
- Viewer mechanism changes must be made only after a qualified Core handoff
  exists, or through a separately reviewed narrow Vitrine remedy.
- No source mutation, bytes copied to untracked locations, unvalidated alias,
  or unauthorized disclosure is justified by long-path workarounds.
- A mocked opener, static source test, shell return, or Core v0.6.5 hash check
  is insufficient for final Windows viewer acceptance.
- Core v0.6.6 adoption, if necessary, requires a separate release qualification
  input update and actual installed viewer re-test, **not** unrelated producer
  updates or a second Vitrine release purely for coordination.

If the viewer fails or no real GUI is available, record the blocking result.
Do not mark Vitrine v0.4.0 `RELEASED — VERIFIED` until real viewer
accessibility is established and repeatable.
