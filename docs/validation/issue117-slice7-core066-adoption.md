# Issue #117 Slice 7 — Core 0.6.6 viewer-safe release adoption

**Slice 7 functional acceptance: PASSED; Vitrine v0.4.0 NOT PUBLISHED.**

This slice moves the active v0.4.0 Core dependency minimum and installed-release
qualification matrix to the official Core 0.6.6 release. The Core #232 Windows
handoff preserves `open_local_path()` and returns the canonical source path,
while using a short per-user directory junction for deep paths in the external
application. Calling Vitrine's existing open methods still requires canonical
lookup, first-party verification, workspace containment, and immutable custody.

## Authenticated Core #232 artifact

- GitHub Release: https://github.com/Paper-Data-Suite/pds-core/releases/tag/v0.6.6
- Official wheel: `pds_core-0.6.6-py3-none-any.whl`
- Published SHA-256: `d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301`
- Python: >=3.11
- Verified: official GitHub Release publication and downloaded wheel SHA-256,
  embedded distribution metadata, ZIP integrity, and expected local-open source.

## Qualification distinctions

- The v0.6.5 wheel `9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18`
  and its two failed Edge viewer outcomes are frozen **historical baseline**
  evidence, not relabeled as v0.6.6 success.
- Current #117 exact Core input is 0.6.6. ScoreForm 0.13.0, Quillan 0.10.6,
  Concord 0.3.2 remain unchanged and optional at runtime. No producer update
  is required solely to adopt Core's additive viewer-safe behavior.
- Existing historical #103 probe entry points retain their old default Core
  audit; the current #117 isolated driver explicitly selects Core 0.6.6.
- The local opening API's successful return proves an OS handoff request, **not
  that Edge or another browser/PDF viewer rendered content**.
- Core's per-user junctions persist for asynchronous viewers (up to eventual
  stale cleanup), expose existing filesystem privileges rather than creating
  new disclosure authority, and do not copy or modify canonical source bytes.

## Completed Slice 7 acceptance and remaining release gates

1. Run focused pytest, Ruff, strict MyPy, source/docs/package validators,
   and exact downloaded Core 0.6.6 wheel verification.
2. Build a fresh Vitrine 0.4.0 candidate wheel with `pds-core>=0.6.6,<0.7`;
   qualify it installed noneditably with Core 0.6.6 and the **same three**
   authenticated producer wheels. Verify `pip check`, projections, authorization,
   runtime provenance, and installed metadata.
3. Run the actual Core+Vitrine-only completed-Portfolio deep-root Windows test.
   Inspect HTML and relative resources in Microsoft Edge, rendered PDF pages,
   and both folders in Explorer. Use a **new** synthetic workspace and report;
   preserve the prior Core 0.6.5 failure report unchanged.
4. Attest/verify the new report with `--core-version 0.6.6`, record all four
   actual viewer outcomes. No auto-pass from successful shell return.
5. Re-run affected custody/authorization/immutability tests, then the normal
   full repository validation / CI / exact-main release procedure.

### Accepted local evidence

- Core 0.6.6 wheel: `d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301` (published release digest verified).
- Vitrine candidate wheel: `c9282176811be7a98499a3fb65ed99b0158d3b49fdb7c62cdc3a453113570973` (isolated installed acceptance passed).
- ScoreForm 0.13.0, Quillan 0.10.6, Concord 0.3.2: independently
  authenticated and qualified with the Core 0.6.6 runtime.
- Real Windows deep-root HTML, PDF, Presentation folder, technical Export
  folder: **VIEWED/VIEWED/VIEWED/VIEWED**, manual attestation exit code 0.
- JSON attestation SHA-256: `1f599a579f712efaa76398ce5393cddaf271d10aa2c7199f09532d21788a086b` (retained locally, not committed).
- Historical Core 0.6.5 HTML/PDF failures remain separately recorded.
- Focused tests: 50 passed / 1 skipped; Ruff and strict MyPy passed.

### Still required before v0.4.0 publication

- Complete clean-tree repository validation and supported GitHub CI.
- PR review/merge, followed by exact-main rebuild and independent artifacts.
- Immutable tag/Release and independent fresh-download acceptance.

The final v0.4.0 release verdict remains **PENDING** until these gates succeed.
