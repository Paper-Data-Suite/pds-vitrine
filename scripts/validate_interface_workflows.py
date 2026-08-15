#!/usr/bin/env python3
"""Validate the interface boundary plus the representative immutable workflow."""

# ruff: noqa: E402

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_improvement_portfolio import validate as validate_improvement
from vitrine.cli import build_parser
from vitrine.menu import run_menu
from vitrine.workflow_context import default_workflow_dependencies


def validate() -> None:
    """Run the fixture chain once and assert package-safe interface seams."""
    report = validate_improvement()
    if report.edition_identity[1] < 1:
        raise RuntimeError("representative workflow did not seal an Edition")

    parser = build_parser()
    representative_commands = (
        ("portfolio", "show", "portfolio-improvement-syn-001"),
        ("candidate", "list", "portfolio-improvement-syn-001"),
        (
            "selection",
            "add",
            "portfolio-improvement-syn-001",
            "candidate-1",
            "--section-id",
            "baseline",
            "--actor-id",
            "teacher",
        ),
        (
            "arrangement",
            "show",
            "portfolio-improvement-syn-001",
            "--section-id",
            "baseline",
        ),
        ("composition", "show", "portfolio-improvement-syn-001"),
        ("audience", "list", "portfolio-improvement-syn-001"),
        ("snapshot", "series", "list", "portfolio-improvement-syn-001"),
        ("snapshot", "verify", "snapshot-series-1", "--edition", "1"),
    )
    for command in representative_commands:
        parser.parse_args(command)

    dependencies = default_workflow_dependencies()
    if (
        dependencies.adapter_registry.adapters
        or dependencies.producer_registry.profiles
    ):
        raise RuntimeError("ordinary runtime silently enabled development fixtures")
    output = io.StringIO()
    if (
        run_menu(input_fn=lambda _prompt: "Q", output=output, clear_fn=lambda: None)
        != 0
    ):
        raise RuntimeError("teacher menu did not unwind cleanly")
    if "Portfolios" not in output.getvalue():
        raise RuntimeError("teacher menu is not Portfolio-centered")


def main() -> int:
    validate()
    print("PASS interface workflow validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
