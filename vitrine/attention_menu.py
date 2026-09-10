"""Low-density teacher presentation for Vitrine attention summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Final, TextIO

from pds_core.workspace import resolve_workspace_root

from vitrine.attention import VitrineAttentionQuery, evaluate_vitrine_attention
from vitrine.menu_types import ClearFunction

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


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def run_attention_menu(
    *,
    output: TextIO,
    clear_fn: ClearFunction,
    workspace_root: Path | None = None,
    portfolio_id: str | None = None,
) -> None:
    """Render one current read-only attention report and return to the caller."""
    root = resolve_workspace_root(workspace_root)
    report = evaluate_vitrine_attention(
        root,
        VitrineAttentionQuery(portfolio_id=portfolio_id),
    )
    clear_fn()
    title = (
        "Attention / Next Actions"
        if portfolio_id is None
        else f"Attention / Next Actions — {portfolio_id}"
    )
    _write(
        output,
        title,
        "",
        f"Evaluation: {report.evaluation}",
        "Observed state revision: "
        + (
            str(report.observed_state_revision)
            if report.observed_state_revision is not None
            else "unavailable"
        ),
        "",
    )
    if not report.summaries:
        _write(output, "No current Vitrine attention summaries.")
    for item in report.summaries:
        _write(
            output,
            f"{item.label}: {item.count} {item.count_unit}",
            f"  Code: {item.code}",
            f"  Class: {item.attention_class}",
        )
        if item.reason_codes:
            _write(output, f"  Reasons: {', '.join(item.reason_codes)}")
        if item.next_action is not None:
            action_id = item.next_action.action_id
            action_label = _ACTION_LABELS.get(action_id, action_id)
            _write(
                output,
                f"  Next action: {action_label}",
                f"  Action ID: {action_id}",
            )
        _write(output, "")
    for notice in report.notices:
        _write(output, f"{notice.code}: {notice.summary}")


__all__ = ["run_attention_menu"]
