"""Low-density teacher presentation for Vitrine attention summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Final, TextIO

from pds_core.workspace import resolve_workspace_root

from vitrine.attention import (
    VitrineAttentionQuery,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    evaluate_vitrine_attention,
)
from vitrine.menu_types import ClearFunction, InputFunction

_ACTION_LABELS: Final[dict[str, str]] = {
    "open_candidate_inbox": "Candidate Inbox",
    "open_candidate_review": "Review Candidates / Selections",
    "open_working_composition": "Working Composition",
    "open_build_export_current_portfolio": "Build and Export Current Portfolio",
    "inspect_snapshot_recovery": "Snapshot recovery inspection",
    "inspect_snapshot_custody": "Snapshot custody inspection",
    "inspect_snapshot_edition": "Snapshot Edition inspection",
    "verify_snapshot_export": "Snapshot Export verification",
}

_SINGULAR_COUNT_UNITS: Final[dict[str, str]] = {
    "candidates": "candidate",
    "candidate_entries": "candidate entry",
    "selection_proposals": "selection proposal",
    "selections": "selection",
    "profile_requirements": "profile requirement",
    "curation_reviews": "curation review",
    "portfolios": "portfolio",
    "obligation_codes": "obligation",
    "snapshot_builds": "snapshot build",
    "snapshot_findings": "snapshot finding",
    "snapshot_omissions": "snapshot omission",
    "snapshot_exports": "snapshot export",
}


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _teacher_count(summary: VitrineAttentionSummary) -> str:
    unit = summary.count_unit.replace("_", " ")
    if summary.count == 1:
        unit = _SINGULAR_COUNT_UNITS.get(summary.count_unit, unit)
    return f"{summary.count} {unit}"


def _teacher_action_label(summary: VitrineAttentionSummary) -> str | None:
    if summary.next_action is None:
        return None
    return _ACTION_LABELS.get(
        summary.next_action.action_id,
        "Open the related Vitrine workflow",
    )


def _render_teacher_attention(
    output: TextIO,
    report: VitrineAttentionReport,
    *,
    portfolio_id: str | None,
) -> None:
    title = (
        "Attention / Next Actions — All Portfolios"
        if portfolio_id is None
        else "Attention / Next Actions — Current Portfolio"
    )
    _write(output, title, "")
    if report.evaluation == "unavailable":
        _write(
            output,
            "Vitrine could not evaluate attention from the current state.",
            "",
        )
    if not report.summaries and report.evaluation == "evaluated":
        _write(output, "No current Vitrine attention summaries.")
    if report.summaries:
        _write(output, "What needs attention")
    for item in report.summaries:
        _write(output, f"- {item.label}: {_teacher_count(item)}")
        action_label = _teacher_action_label(item)
        if action_label is not None:
            _write(output, f"  Next action: {action_label}")
    if report.notices:
        _write(output, "", "Notices")
        for notice in report.notices:
            _write(output, f"- {notice.summary}")


def _render_attention_technical_details(
    output: TextIO,
    report: VitrineAttentionReport,
    *,
    portfolio_id: str | None,
) -> None:
    observed = (
        "(none)"
        if report.observed_state_revision is None
        else str(report.observed_state_revision)
    )
    _write(
        output,
        "Technical Details / Provenance",
        "",
        "Attention projection",
        f"Contract: {report.contract_version}",
        f"Evaluation: {report.evaluation}",
        f"Observed state revision: {observed}",
        (
            "Scope: workspace"
            if portfolio_id is None
            else "Scope: exact Portfolio"
        ),
    )
    if portfolio_id is not None:
        _write(output, f"Portfolio ID: {portfolio_id}")

    _write(output, "", "Attention summaries")
    if not report.summaries:
        _write(output, "- (none)")
    for item in report.summaries:
        action_id = (
            "(none)"
            if item.next_action is None
            else item.next_action.action_id
        )
        summary_portfolio = item.portfolio_id or "(workspace)"
        reasons = ", ".join(item.reason_codes) or "(none)"
        _write(
            output,
            f"- {item.label}",
            f"  Code: {item.code}",
            f"  Count: {item.count}",
            f"  Count unit: {item.count_unit}",
            f"  Class: {item.attention_class}",
            f"  Portfolio ID: {summary_portfolio}",
            f"  Reasons: {reasons}",
            f"  Action ID: {action_id}",
        )

    _write(output, "", "Notices")
    if not report.notices:
        _write(output, "- (none)")
    for notice in report.notices:
        _write(output, f"- {notice.code}: {notice.summary}")

    _write(
        output,
        "",
        "These fields are exact bounded projection provenance.",
        "Viewing them does not execute the owner action or mutate Vitrine state.",
    )


def run_attention_menu(
    *,
    output: TextIO,
    clear_fn: ClearFunction,
    workspace_root: Path | None = None,
    portfolio_id: str | None = None,
    input_fn: InputFunction | None = None,
) -> None:
    """Render one current read-only attention report and return to the caller."""

    root = resolve_workspace_root(workspace_root)
    report = evaluate_vitrine_attention(
        root,
        VitrineAttentionQuery(portfolio_id=portfolio_id),
    )
    clear_fn()
    _render_teacher_attention(
        output,
        report,
        portfolio_id=portfolio_id,
    )
    if input_fn is None:
        return

    _write(
        output,
        "",
        "T. Technical details / provenance",
        "B. Back",
    )
    try:
        choice = input_fn("Choice (Enter to return): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice.casefold() != "t":
        return

    clear_fn()
    _render_attention_technical_details(
        output,
        report,
        portfolio_id=portfolio_id,
    )
    try:
        input_fn("Press Enter to return...")
    except (EOFError, KeyboardInterrupt):
        return


__all__ = ["run_attention_menu"]
