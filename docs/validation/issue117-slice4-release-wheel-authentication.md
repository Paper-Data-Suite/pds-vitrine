# Issue #117 Slice 4 — Authenticated producer release inputs

**Status:** qualification infrastructure prepared; local official-wheel bytes must still
be authenticated before the corresponding installed acceptance can be claimed.

## Fixed input matrix

These values come from already recorded Core / producer release audits in
`vitrine/released_producer_contracts.py`. They are a reproducibility mechanism for
**test input artifacts**, not a Vitrine runtime compatibility allowlist.

| Distribution | Official tag | Filename | Expected SHA-256 |
| --- | --- | --- | --- |
| Core | `v0.6.5` | `pds_core-0.6.5-py3-none-any.whl` | `9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18` |
| ScoreForm | `v0.13.0` | `scoreform-0.13.0-py3-none-any.whl` | `4a4d158fda6e899f1835f3312ca8291622e2b1c7da219b349adf5e88b9b7c9b7` |
| Quillan | `v0.10.6` | `quillan-0.10.6-py3-none-any.whl` | `7dbe975c969e60cfda9a8489154450f95c4dc58a8d75afcfad92e7a3c026afbb` |
| Concord | `v0.3.2` | `pds_concord-0.3.2-py3-none-any.whl` | `825b27bc6142cc8bce8c3b9381a3337c4a55e983f6f3f2e7e4b1a10f980e83ce` |

Earlier candidate documentation named Concord v0.3.1. The active #103 audit and
current installed-reader qualification actually select v0.3.2. The 0.3.1 audit
remains intact as historical evidence; no producer release is required by this change.

## Verify downloaded bytes

Download only official GitHub Release assets from the four respective repositories
and tags. Run from the Vitrine checkout:

```powershell
python scripts/validate_issue117_release_wheels.py --wheel-dir "$HOME\Downloads"
```

The script requires all four exact filenames, compares each complete file's
SHA-256 against the pinned audit, checks ZIP integrity and embedded distribution
name/version/Python requirement. Failure stops qualification. Without
`--wheel-dir`, the source-checkout/repository gate validates the *static matrix only*
and explicitly does **not** claim that release bytes were authenticated.

This slice does not yet qualify an installed Vitrine v0.4.0 candidate wheel. The next
slice must consume a separately built Vitrine candidate wheel **noneditably** and
exercise the existing actual-reader qualification under isolated installed imports.
Keep issue #71's historical v0.3.0 replay unchanged.
