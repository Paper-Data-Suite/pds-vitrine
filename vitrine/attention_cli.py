"""Direct read-only CLI for Vitrine attention and next-action summaries."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TextIO

from vitrine.attention import (
    VitrineAttentionQuery,
    VitrineAttentionReport,
    evaluate_vitrine_attention,
)
from vitrine.workspace import show_workspace


def configure_attention_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the direct `vitrine attention ...` CLI surface."""
    attention = subparsers.add_parser(
        "attention",
        help="Inspect Vitrine attention and next-action summaries.",
    )
    commands = attention.add_subparsers(
        dest="attention_command",
        required=True,
    )
    listing = commands.add_parser(
        "list",
        help="List current read-only Vitrine attention summaries.",
    )
    listing.add_argument("--portfolio-id")
    listing.add_argument("--workspace-root", type=Path)


def _scope_label(portfolio_id: str | None) -> str:
    if portfolio_id is None:
        return "workspace"
    return f"portfolio:{portfolio_id}"


def print_attention_report(
    report: VitrineAttentionReport,
    *,
    portfolio_id: str | None,
    output: TextIO,
) -> None:
    """Print bounded stable attention data without scraping teacher prose."""
    print("Vitrine attention", file=output)
    print(f"Contract: {report.contract_version}", file=output)
    print(f"Evaluation: {report.evaluation}", file=output)
    observed = (
        "(none)"
        if report.observed_state_revision is None
        else str(report.observed_state_revision)
    )
    print(f"Observed state revision: {observed}", file=output)
    print(f"Scope: {_scope_label(portfolio_id)}", file=output)
    if not report.summaries:
        print("Summaries: (none)", file=output)
    for item in report.summaries:
        action_id = "(none)" if item.next_action is None else item.next_action.action_id
        summary_portfolio = item.portfolio_id or "(workspace)"
        reasons = ",".join(item.reason_codes) or "(none)"
        print(
            "\t".join(
                (
                    item.code,
                    item.label,
                    f"count={item.count}",
                    f"unit={item.count_unit}",
                    f"class={item.attention_class}",
                    f"portfolio={summary_portfolio}",
                    f"action={action_id}",
                    f"reasons={reasons}",
                )
            ),
            file=output,
        )
    for notice in report.notices:
        print(
            f"notice\t{notice.code}\t{notice.summary}",
            file=output,
        )


def run_attention_command(
    args: argparse.Namespace,
    *,
    output: TextIO,
) -> int:
    """Run one direct attention command without mutation or prompting."""
    if args.attention_command != "list":
        raise AssertionError(f"Unhandled attention command: {args.attention_command}")
    root = show_workspace(args.workspace_root).root
    query = VitrineAttentionQuery(portfolio_id=args.portfolio_id)
    report = evaluate_vitrine_attention(root, query)
    print_attention_report(
        report,
        portfolio_id=args.portfolio_id,
        output=output,
    )
    return 0 if report.evaluation == "evaluated" else 1


__all__ = [
    "configure_attention_parser",
    "print_attention_report",
    "run_attention_command",
]
