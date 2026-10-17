"""Issue #117: characterize real Windows viewer access separately from shell dispatch.

Static source checks are CI-safe. Actual viewer attestation is an opt-in,
interactive Windows release gate, never replaced by mocks or exit codes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "vitrine_issue117_windows_viewer_v1"
KINDS = (
    "student_html",
    "printable_pdf",
    "presentation_folder",
    "technical_export_folder",
)


def validate_source(root: Path = ROOT) -> tuple[str, ...]:
    """Check wiring and explicit pending status; never claim viewer success."""
    findings: list[str] = []
    required: dict[str, tuple[str, ...]] = {
        "vitrine/portfolio_output_opening.py": (
            "verify_portfolio_presentation(",
            "verify_snapshot_export(",
            "safe_vitrine_descendant",
            "open_local_path",
        ),
        "scripts/smoke_test_completed_portfolio_navigation_wheel.py": (
            'importlib.metadata.version("pds-vitrine") == "0.4.0"',
            "--viewer-workspace",
            "--viewer-report",
            CONTRACT,
            "opener=recorder",
            "open_student_portfolio_html(",
            "open_printable_student_portfolio(",
            "open_student_portfolio_folder(",
            "open_technical_export_folder(",
        ),
        "docs/v0.4.0-release-audit.md": (
            "Windows viewer-accessibility release gate",
            "PENDING real-Windows viewer acceptance",
        ),
        "docs/v0.4.0-release-checklist.md": (
            "real-Windows viewer acceptance",
        ),
        "docs/validation/issue117-slice6-windows-viewer-handoff.md": (
            "Core #232",
            "not proof of viewer accessibility",
            "four verified canonical targets",
        ),
    }
    for relative, markers in required.items():
        file = root / relative
        if not file.is_file():
            findings.append(f"missing {relative}")
            continue
        text = file.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                findings.append(f"{relative} missing {marker!r}")
    return tuple(findings)


def report_findings(
    report: object,
    *,
    require_attested: bool,
    expected_core_version: str = "0.6.5",
) -> tuple[str, ...]:
    """Fail closed on missing/invalid reports and unconfirmed viewer outcomes."""
    failures: list[str] = []
    if not isinstance(report, dict):
        return ("report is not a JSON object",)
    data: dict[str, Any] = report
    if data.get("contract") != CONTRACT:
        failures.append("incorrect viewer report contract")
    if data.get("platform") != "win32":
        failures.append("report was not produced on Windows")
    if expected_core_version not in {"0.6.5", "0.6.6"}:
        failures.append("unsupported expected Core viewer acceptance version")
    if data.get("core_version") != expected_core_version:
        failures.append("Core input version differs from requested viewer qualification")
    if data.get("vitrine_version") != "0.4.0":
        failures.append("Vitrine input version differs from v0.4.0")
    if data.get("canonical_verified") is not True:
        failures.append("canonical Edition/Export/Presentation verification missing")
    if data.get("synthetic_only") is not True:
        failures.append("report is not explicitly synthetic-only")
    targets = data.get("targets")
    if not isinstance(targets, list) or len(targets) != 4:
        return tuple(failures + ["expected exactly four viewer targets"])
    names = [target.get("kind") if isinstance(target, dict) else None for target in targets]
    if tuple(names) != KINDS:
        failures.append("viewer target kinds or order changed")
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            failures.append(f"target {index}: must be an object")
            continue
        name = str(target.get("kind", index))
        canonical = target.get("canonical_path")
        if not isinstance(canonical, str) or not canonical:
            failures.append(f"{name}: canonical path missing")
        elif len(canonical) <= 260:
            failures.append(f"{name}: canonical path does not exceed 260 characters")
        if target.get("canonical_path_length") != len(canonical or ""):
            failures.append(f"{name}: canonical path length mismatch")
        status = target.get("shell_handoff")
        if status not in ("returned", "failed"):
            failures.append(f"{name}: shell-handoff result missing")
        if status != "returned" and require_attested:
            failures.append(f"{name}: shell handoff did not return")
        if target.get("handoff_content_matches") is not True and require_attested:
            failures.append(f"{name}: verified handoff byte/inventory equivalence missing")
        handoff_path = target.get("handoff_path")
        if status == "returned" and (not isinstance(handoff_path, str) or not handoff_path):
            failures.append(f"{name}: returned handoff path missing")
        if isinstance(handoff_path, str):
            if target.get("handoff_path_length") != len(handoff_path):
                failures.append(f"{name}: handoff path length mismatch")
        if name in ("student_html", "printable_pdf"):
            digest = target.get("canonical_sha256")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                failures.append(f"{name}: canonical SHA-256 missing")
        outcome = target.get("viewer_accessibility")
        if outcome not in ("pending", "confirmed", "failed"):
            failures.append(f"{name}: viewer-accessibility outcome missing")
        if require_attested and outcome != "confirmed":
            failures.append(f"{name}: actual viewer access not confirmed")
    if require_attested and data.get("attestation_method") != "interactive_human":
        failures.append("no explicit interactive human attestation")
    return tuple(failures)


def attest(path: Path, *, core_version: str = "0.6.5") -> int:
    """Record human observations; a launch return can never auto-pass."""
    if sys.platform != "win32":
        print("Real viewer attestation requires Windows", file=sys.stderr)
        return 1
    report = json.loads(path.read_text(encoding="utf-8"))
    failures = report_findings(
        report, require_attested=False, expected_core_version=core_version
    )
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Check the FOUR actual applications opened on the Windows desktop.")
    print("Only enter VIEWED when the content is genuinely accessible, not when")
    print("the shell merely accepted the open request. Enter FAILED otherwise.")
    explanations = {
        "student_html": "Browser renders student HTML; follow local/relative navigation and assets",
        "printable_pdf": "PDF viewer displays actual printable PDF pages",
        "presentation_folder": "Explorer lists and opens the Presentation folder contents",
        "technical_export_folder": "Explorer lists and opens the technical Export contents",
    }
    for target in report["targets"]:
        print(f"\n{target['kind']}: {explanations[target['kind']]}")
        print(f"Shell handoff: {target['shell_handoff']}")
        print(f"Canonical path: {target['canonical_path']}")
        print(f"Returned path: {target.get('handoff_path')}")
        response = input("VIEWED / FAILED: ").strip()
        if response not in {"VIEWED", "FAILED"}:
            raise ValueError("Enter exactly VIEWED or FAILED for viewer evidence")
        target["viewer_accessibility"] = (
            "confirmed" if response == "VIEWED" else "failed"
        )
    report["attestation_method"] = "interactive_human"
    report["attested_utc"] = datetime.now(timezone.utc).isoformat()
    # This report lives outside custody and has synthetic-only paths; never
    # mutate or rewrite a canonical Portfolio/Presentation/Export artifact.
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failed = report_findings(
        report, require_attested=True, expected_core_version=core_version
    )
    if failed:
        print("BLOCKED: real Windows viewer accessibility not qualified:", file=sys.stderr)
        print("\n".join(failed), file=sys.stderr)
        return 1
    print("PASS Issue #117 four-target real-Windows viewer attestation")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-source", action="store_true")
    group.add_argument("--attest-report", type=Path)
    group.add_argument("--verify-report", type=Path)
    parser.add_argument(
        "--core-version", choices=("0.6.5", "0.6.6"), default="0.6.5"
    )
    args = parser.parse_args(argv)
    try:
        if args.attest_report is not None:
            return attest(args.attest_report, core_version=args.core_version)
        if args.verify_report is not None:
            report = json.loads(args.verify_report.read_text(encoding="utf-8"))
            findings = report_findings(
                report,
                require_attested=True,
                expected_core_version=args.core_version,
            )
            if findings:
                print("\n".join(findings), file=sys.stderr)
                return 1
            print("PASS Issue #117 recorded real-Windows viewer accessibility")
            return 0
        findings = validate_source()
        if findings:
            print("\n".join(findings), file=sys.stderr)
            return 1
        print("PASS Issue #117 Windows viewer characterization source boundary")
        print("NOTE real Windows viewer acceptance remains a separate release gate")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Issue #117 viewer qualification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
