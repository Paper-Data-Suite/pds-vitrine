"""Validate v0.4.0 release-preparation documents without claiming publication.

This gate deliberately does not authenticate official producer wheels or a future
GitHub Release. Later #117 slices must add exact-artifact qualification and advance
release-audit state only with independent evidence.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.4.0"
EXPECTED_CORE = "pds-core>=0.6.5,<0.7"
DOCUMENTS: tuple[str, ...] = (
    "RELEASE_NOTES_v0.4.0.md",
    "docs/v0.4.0-release-compatibility.md",
    "docs/v0.4.0-release-audit.md",
    "docs/v0.4.0-release-checklist.md",
)


def _check_markers(
    root: Path, relative: str, markers: tuple[str, ...], findings: list[str]
) -> str:
    try:
        content = (root / relative).read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(f"missing release document {relative}: {exc}")
        return ""
    for marker in markers:
        if marker not in content:
            findings.append(f"{relative} missing required marker: {marker}")
    return content


def validate(root: Path = ROOT) -> tuple[str, ...]:
    """Check current candidate documentation; preserve frozen historical assets."""
    findings: list[str] = []
    _check_markers(
        root,
        "RELEASE_NOTES_v0.4.0.md",
        (
            "# pds-vitrine v0.4.0",
            "NOT PUBLISHED",
            "Paper-native student Reflection",
            "Working Composition v2",
            "Student Portfolio Presentation",
            "Completed Portfolio navigation",
            "Completion-aware Attention",
            "Reader Contract v1",
            EXPECTED_CORE,
            "synthetic",
            "not automatically",
            "external disclosure or delivery",
        ),
        findings,
    )
    _check_markers(
        root,
        "docs/v0.4.0-release-compatibility.md",
        (
            "# Vitrine v0.4.0",
            "NOT YET QUALIFIED OR PUBLISHED",
            "scoreform_academic_result_reader_v1",
            "quillan_academic_result_reader_v1",
            "concord_academic_result_reader_v1",
            "0.6.5",
            "0.13.0",
            "0.10.6",
            "0.3.1",
            "Pending authentication",
            "not a substitute",
        ),
        findings,
    )
    audit = _check_markers(
        root,
        "docs/v0.4.0-release-audit.md",
        (
            "# Vitrine v0.4.0",
            "**PREPARATION — NOT RELEASED**",
            "95f29168f8b72007b606433da905a09faea3ca07",
            "eb08c974d9af0ed72918416178e75332dbba13bd",
            "c681074",
            "5c674d7",
            "v0.3.0",
            "**PENDING**",
            "**NOT PUBLISHED**",
        ),
        findings,
    )
    if "Final release verdict: **RELEASED — VERIFIED**" in audit:
        findings.append("candidate audit claims a final verified publication")
    _check_markers(
        root,
        "docs/v0.4.0-release-checklist.md",
        (
            "# Vitrine v0.4.0",
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4",
            "release/v0.4.0",
            "pds_vitrine-0.4.0-py3-none-any.whl",
            "pds_vitrine-0.4.0.tar.gz",
            "SHA256SUMS.txt",
            "fresh-download",
        ),
        findings,
    )
    for relative in DOCUMENTS:
        if not (root / relative).is_file():
            findings.append(f"v0.4.0 document missing from working tree: {relative}")

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
        if project.get("requires-python") != ">=3.11":
            findings.append("current release Python requirement drifted")
        if project.get("dependencies") != [EXPECTED_CORE]:
            findings.append("current Core-only dependency requirement drifted")
        if project.get("name") != "pds-vitrine":
            findings.append("distribution identity drifted")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        findings.append(f"cannot inspect active package requirements: {exc}")
    try:
        version = (root / "vitrine/_version.py").read_text(encoding="utf-8")
        if re.search(r'^__version__ = "0\.4\.0"$', version, re.MULTILINE) is None:
            findings.append("authoritative v0.4.0 version not promoted")
    except OSError as exc:
        findings.append(f"cannot inspect authoritative source version: {exc}")

    checks = (
        ("README.md", ("v0.4.0 release preparation", EXPECTED_CORE, "Core v0.6.5")),
        ("docs/README.md", ("v0.4.0 release preparation", "v0.3.0 release audit")),
        (
            "CHANGELOG.md",
            ("## Unreleased", "## 0.4.0 - 2026-10-13", "## 0.3.0 - 2026-09-17"),
        ),
        ("MANIFEST.in", ("RELEASE_NOTES_v0.3.0.md", "RELEASE_NOTES_v0.4.0.md")),
        (
            "scripts/check_package.py",
            ("RELEASE_NOTES_v0.4.0.md", "docs/v0.4.0-release-audit.md"),
        ),
        (
            "scripts/validate_repository.py",
            ("scripts/validate_issue117_release_documents.py",),
        ),
    )
    for relative, markers in checks:
        _check_markers(root, relative, markers, findings)

    return tuple(findings)


def main() -> int:
    findings = validate()
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("PASS issue #117 v0.4.0 candidate documentation / nonpublication guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
