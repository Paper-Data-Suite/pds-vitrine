#!/usr/bin/env python3
"""Offline validation for the Vitrine portfolio foundation audit."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/audits/portfolio-foundation-audit.json"
INVALID_SHA = "8202aeff46a6e3e30e4de07e4adc00ad" + "38cd5348"
EXPECTED_SCOREFORM = "c2fa06f1a4c33df01f3e0d9c8dd27702d4a06419"
REQUIRED_HEADINGS = {
    "docs/audits/portfolio-foundation-audit.md": ["# Portfolio Foundation Audit", "## Final verdict"],
    "docs/audits/portfolio-foundation-traceability.md": ["# Portfolio Foundation Traceability", "## Exit-condition traceability"],
    "docs/audits/portfolio-foundation-findings.md": ["# Portfolio Foundation Audit Findings", "## PF-AUD-001"],
    "docs/validation/issue-13-portfolio-foundation-validation.md": ["# Issue #13 Validation: Portfolio Foundation Audit", "## Result"],
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")


def walk_values(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


def safe_relative_path(raw: str) -> bool:
    if not raw or "\\" in raw or re.match(r"^[A-Za-z]:", raw) or raw.startswith("/"):
        return False
    parts = PurePosixPath(raw).parts
    return all(part not in {"", ".", ".."} for part in parts)


def validate_json_and_paths() -> int:
    count = 0
    for path in ROOT.rglob("*.json"):
        if ".git" in path.parts:
            continue
        data = load_json(path)
        count += 1
        if "fixtures" in path.parts and "negative" not in path.parts:
            for key, child in walk_values(data):
                if isinstance(child, str) and (key.endswith("path") or key.endswith("file")):
                    if child.startswith(("http://", "https://")):
                        continue
                    if not safe_relative_path(child):
                        fail(f"unsafe fixture path in {path.relative_to(ROOT)}: {child!r}")
    return count


def validate_no_links_or_fence_errors() -> tuple[int, int]:
    md_count = 0
    link_count = 0
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        md_count += 1
        text = path.read_text(encoding="utf-8")
        fences = sum(1 for line in text.splitlines() if line.startswith("```"))
        if fences % 2:
            fail(f"unbalanced code fences: {path.relative_to(ROOT)}")
        for target in link_re.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"relative link escapes repository: {path.relative_to(ROOT)} -> {target}")
            if not resolved.exists():
                fail(f"missing relative link: {path.relative_to(ROOT)} -> {target}")
            link_count += 1
    return md_count, link_count


def validate_required_docs() -> None:
    for rel, headings in REQUIRED_HEADINGS.items():
        path = ROOT / rel
        if not path.is_file():
            fail(f"missing required audit file: {rel}")
        text = path.read_text(encoding="utf-8")
        for heading in headings:
            if heading not in text:
                fail(f"missing heading {heading!r} in {rel}")


def validate_audit_manifest() -> tuple[int, int, str]:
    data = load_json(AUDIT)
    if data.get("audit_contract") != "pds-vitrine.portfolio-foundation-audit":
        fail("unexpected audit contract")
    verdict = data.get("verdict")
    if verdict not in {"ready_for_implementation", "not_ready"}:
        fail("invalid audit verdict")

    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        fail("audit findings must be a nonempty list")
    ids = [item.get("id") for item in findings]
    if len(ids) != len(set(ids)):
        fail("duplicate audit finding IDs")
    if verdict == "ready_for_implementation":
        unresolved = [
            item.get("id") for item in findings
            if item.get("severity") in {"blocker", "major"}
            and item.get("status") not in {"resolved", "closed"}
        ]
        if unresolved:
            fail(f"ready verdict has unresolved blocker/major findings: {unresolved}")

    exits = data.get("exit_conditions")
    if not isinstance(exits, list) or len(exits) != 18:
        fail("audit must contain exactly 18 exit conditions")
    exit_ids = [item.get("id") for item in exits]
    if len(exit_ids) != len(set(exit_ids)):
        fail("duplicate exit-condition IDs")
    for item in exits:
        if item.get("status") != "satisfied" or not item.get("evidence"):
            fail(f"unsatisfied or untraceable exit condition: {item.get('id')}")

    dispositions = data.get("adr_dispositions")
    if not isinstance(dispositions, list) or len(dispositions) != 9:
        fail("audit must disposition ADRs 0001 through 0009")
    expected = {f"{number:04d}" for number in range(1, 10)}
    observed = {item.get("adr") for item in dispositions}
    if observed != expected or any(item.get("status") != "Accepted" for item in dispositions):
        fail("ADR dispositions are incomplete or not Accepted")
    return len(findings), len(exits), verdict


def validate_adr_files() -> int:
    index = (ROOT / "docs/decisions/README.md").read_text(encoding="utf-8")
    count = 0
    for number in range(1, 10):
        prefix = f"{number:04d}-"
        matches = sorted((ROOT / "docs/decisions").glob(prefix + "*.md"))
        if len(matches) != 1:
            fail(f"expected exactly one ADR file for {number:04d}")
        text = matches[0].read_text(encoding="utf-8")
        if "- **Status:** Accepted" not in text or "- **Accepted:** 2026-08-06" not in text:
            fail(f"ADR {number:04d} is not audit-accepted")
        row_re = re.compile(rf"\| \[{number:04d}\]\([^)]*\) \|[^\n]*\| Accepted \|")
        if not row_re.search(index):
            fail(f"ADR index does not mark {number:04d} Accepted")
        count += 1
    return count


def validate_baselines() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if INVALID_SHA in text:
            fail(f"known invalid ScoreForm SHA remains in {path.relative_to(ROOT)}")
    corpus = load_json(ROOT / "fixtures/representative-portfolios/corpus.json")
    if corpus["reviewed_repositories"].get("pds-scoreform") != EXPECTED_SCOREFORM:
        fail("corpus ScoreForm baseline is not the audited reachable commit")
    policy = corpus.get("baseline_policy")
    if not isinstance(policy, dict) or policy.get("kind") != "historical_construction_snapshot":
        fail("corpus lacks explicit historical/current baseline policy")
    scoreform = load_json(ROOT / "fixtures/representative-portfolios/shared/producers/scoreform.json")
    if scoreform.get("reviewed_baseline") != EXPECTED_SCOREFORM:
        fail("ScoreForm producer fixture baseline mismatch")
    if scoreform.get("runtime_support") != "synthetic_consumer_projection_over_implemented_manifest_generation_only":
        fail("ScoreForm fixture overstates runtime support")


def validate_filesystem() -> None:
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_symlink():
            fail(f"symlink is not allowed: {path.relative_to(ROOT)}")
        if os.name == "nt" and path.exists() and path.stat().st_file_attributes & 0x400:
            fail(f"junction/reparse point is not allowed: {path.relative_to(ROOT)}")


def run_representative_validator() -> None:
    command = [sys.executable, str(ROOT / "scripts/validate_representative_portfolios.py")]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        fail("representative Portfolio validator failed")
    print(result.stdout.strip())


def main() -> int:
    try:
        run_representative_validator()
        validate_filesystem()
        json_count = validate_json_and_paths()
        md_count, link_count = validate_no_links_or_fence_errors()
        validate_required_docs()
        finding_count, exit_count, verdict = validate_audit_manifest()
        adr_count = validate_adr_files()
        validate_baselines()
    except ValueError as exc:
        print(f"FAIL portfolio foundation audit: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS portfolio foundation audit: "
        f"{adr_count} Accepted ADRs, {finding_count} findings, "
        f"{exit_count} satisfied exit conditions, {json_count} JSON files, "
        f"{md_count} Markdown files, {link_count} relative links, verdict {verdict}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
