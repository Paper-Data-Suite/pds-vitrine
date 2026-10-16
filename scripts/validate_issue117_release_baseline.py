"""Issue #117: validate the frozen v0.3.0 release evidence during v0.4.0 work.

The initial source version may be 0.3.0 or the later 0.4.0 release candidate.
This is a guard, not a v0.4.0 publication or released-wheel qualification.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = "docs/development/issue117-v040-release-baseline.json"
BASELINE_COMMIT = "95f29168f8b72007b606433da905a09faea3ca07"
FROZEN_PATHS = (
    "RELEASE_NOTES_v0.3.0.md",
    "docs/release_checklist.md",
    "docs/v0.3.0-release-audit.md",
    "docs/v0.3.0-release-compatibility.md",
    "scripts/live_installed_acceptance_contract.py",
    "scripts/qualify_installed_live_portfolio.py",
    "scripts/validate_v030_release_audit.py",
    "tests/test_validate_v030_release_audit.py",
)
CORE_REQUIREMENT = "pds-core>=0.6.6,<0.7"
FORBIDDEN_DEPENDENCIES = frozenset(
    {"pds-vitrine", "scoreform", "quillan", "pds-concord", "pds-meridian", "pds-portia"}
)
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _source_version(root: Path) -> str:
    source = (root / "vitrine/_version.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', source, flags=re.MULTILINE)
    if match is None:
        raise ValueError("vitrine/_version.py lacks the authoritative version")
    return match.group(1)


def validate(root: Path = ROOT) -> tuple[str, ...]:
    """Return all observed release-baseline violations, without editing files."""
    findings: list[str] = []
    try:
        raw = json.loads((root / SNAPSHOT_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return (f"baseline manifest unavailable/invalid: {exc}",)
    if not isinstance(raw, dict):
        return ("baseline manifest must be a JSON object",)

    if raw.get("contract") != "vitrine_issue117_release_baseline_v1":
        findings.append("baseline contract changed")
    if raw.get("starting_commit") != BASELINE_COMMIT:
        findings.append("starting commit differs from merged #104 baseline")
    tree = raw.get("starting_tree")
    if not isinstance(tree, str) or _SHA.fullmatch(tree) is None:
        findings.append("starting tree must be a recorded 40-character Git tree SHA")
    if raw.get("target_version") != "0.4.0":
        findings.append("target release version changed")
    if raw.get("initial_source_version") != "0.3.0":
        findings.append("initial release identity is not recorded as v0.3.0")

    hashes = raw.get("historical_sha256")
    if not isinstance(hashes, dict) or set(hashes) != set(FROZEN_PATHS):
        findings.append("historical release file inventory was changed")
    else:
        for relative in FROZEN_PATHS:
            expected = hashes[relative]
            if not isinstance(expected, str) or _SHA256.fullmatch(expected) is None:
                findings.append(f"invalid frozen SHA-256: {relative}")
                continue
            try:
                actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            except OSError as exc:
                findings.append(
                    f"historical release evidence missing: {relative}: {exc}"
                )
                continue
            if actual != expected:
                findings.append(f"historical release evidence modified: {relative}")

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
        dependencies = project["dependencies"]
        assert isinstance(dependencies, list)
        if project["requires-python"] != ">=3.11":
            findings.append("release Python floor changed")
        if dependencies != [CORE_REQUIREMENT]:
            findings.append(
                "runtime dependency inventory deviates from Core-only v0.6.6"
            )
        for dependency in dependencies:
            if not isinstance(dependency, str):
                findings.append("invalid runtime dependency declaration")
                continue
            name = re.split(r"[<=>!~;\[\s]", dependency.strip(), maxsplit=1)[0]
            if name.lower().replace("_", "-") in FORBIDDEN_DEPENDENCIES:
                findings.append(f"forbidden unconditional sibling dependency: {name}")
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        findings.append(f"package requirements unreadable: {exc}")

    try:
        if _source_version(root) not in {"0.3.0", "0.4.0"}:
            findings.append("authoritative source version outside #117 promotion range")
    except (OSError, ValueError) as exc:
        findings.append(f"source version unavailable: {exc}")

    return tuple(findings)


def main() -> int:
    findings = validate()
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print(
        "PASS issue #117 baseline: preserved v0.3.0 evidence "
        "and Core-only requirements"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
