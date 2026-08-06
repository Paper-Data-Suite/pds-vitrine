"""Validate repository Markdown links, fences, encoding, and text hygiene."""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _iter_text_files(root: Path) -> list[Path]:
    suffixes = {".md", ".ps1", ".py", ".toml", ".yml", ".yaml", ".json"}
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path.suffix.lower() in suffixes
    )


def validate(root: Path) -> list[str]:
    findings: list[str] = []
    for path in _iter_text_files(root):
        relative = path.relative_to(root)
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"{relative}: not UTF-8")
            continue
        if b"\r\n" in data and path.suffix.lower() != ".ps1":
            findings.append(f"{relative}: contains CRLF")
        if text and not text.endswith("\n"):
            findings.append(f"{relative}: missing terminal newline")
        for number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip() != line:
                findings.append(f"{relative}:{number}: trailing whitespace")
            if "\t" in line:
                findings.append(f"{relative}:{number}: tab character")
        if path.suffix.lower() != ".md":
            continue
        if text.count("```") % 2:
            findings.append(f"{relative}: unbalanced fenced code blocks")
        for match in LINK_PATTERN.finditer(text):
            target = match.group(1).split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            destination = (path.parent / target).resolve(strict=False)
            if not destination.exists():
                findings.append(f"{relative}: missing relative link {target}")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = validate(root)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("PASS documentation validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
