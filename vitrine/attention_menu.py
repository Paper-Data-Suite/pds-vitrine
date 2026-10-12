"""Low-density teacher presentation for Vitrine attention summaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from pds_core.workspace import resolve_workspace_root

from vitrine.attention import (
    VitrineAttentionQuery,
    VitrineAttentionReportV2,
    VitrineAttentionSummaryV2,
    evaluate_vitrine_attention_v2,
)
from vitrine.candidate_inbox_menu import run_candidate_inbox_menu
from vitrine.candidate_review_menu import run_candidate_review_menu
from vitrine.completed_portfolio_menu import (
    BUILD_UPDATED_EDITION,
    run_completed_portfolio_menu,
)
from vitrine.current_portfolio_menu import (
    run_current_portfolio_build_export_menu,
)
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution
from vitrine.portfolio_services import list_portfolios
from vitrine.workflow_context import (
    VitrineWorkflowDependencies,
    default_workflow_dependencies,
)
from vitrine.working_composition_menu import run_working_composition_menu

_ACTION_LABELS: Final[dict[str, str]] = {
    "open_candidate_inbox": "Candidate Inbox",
    "open_candidate_review": "Review Candidates / Selections",
    "open_working_composition": "Working Composition",
    "open_build_export_current_portfolio": "Build and Export Current Portfolio",
    "open_completed_portfolio_editions": "Completed Portfolio Editions",
    "inspect_snapshot_recovery": "Snapshot recovery inspection",
    "inspect_snapshot_custody": "Snapshot custody inspection",
    "inspect_snapshot_edition": "Snapshot Edition inspection",
    "verify_snapshot_export": "Snapshot Export verification",
}

@dataclass(frozen=True, slots=True)
class _MenuActionChoice:
    action_id: str
    portfolio_id: str | None
    label: str


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


def _teacher_count(summary: VitrineAttentionSummaryV2) -> str:
    unit = summary.count_unit.replace("_", " ")
    if summary.count == 1:
        unit = _SINGULAR_COUNT_UNITS.get(summary.count_unit, unit)
    return f"{summary.count} {unit}"


def _teacher_action_label(summary: VitrineAttentionSummaryV2) -> str | None:
    if summary.next_action is None:
        return None
    return _ACTION_LABELS.get(
        summary.next_action.action_id,
        "Open the related Vitrine workflow",
    )


def _render_teacher_group(
    output: TextIO,
    heading: str,
    summaries: tuple[VitrineAttentionSummaryV2, ...],
    *,
    empty_message: str | None = None,
) -> None:
    _write(output, heading)
    if not summaries:
        if empty_message is not None:
            _write(output, empty_message)
        return

    for item in summaries:
        if item.requirement_level == "status" and item.count == 1:
            _write(output, f"- {item.label}")
        else:
            _write(output, f"- {item.label}: {_teacher_count(item)}")
        action_label = _teacher_action_label(item)
        if action_label is None:
            continue
        prefix = (
            "Next step"
            if item.requirement_level == "required"
            else "Open"
        )
        _write(output, f"  {prefix}: {action_label}")


def _render_teacher_attention(
    output: TextIO,
    report: VitrineAttentionReportV2,
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
        if report.notices:
            _write(output, "Notices")
            for notice in report.notices:
                _write(output, f"- {notice.summary}")
        return

    status = tuple(
        item
        for item in report.summaries
        if item.requirement_level == "status"
    )
    required = tuple(
        item
        for item in report.summaries
        if item.requirement_level == "required"
    )
    opportunities = tuple(
        item
        for item in report.summaries
        if item.requirement_level == "opportunity"
    )

    if status:
        _render_teacher_group(output, "Portfolio status", status)
        _write(output, "")

    _render_teacher_group(
        output,
        "Needs attention",
        required,
        empty_message="No required actions.",
    )

    if opportunities:
        _write(output, "")
        _render_teacher_group(
            output,
            "Optional opportunities",
            opportunities,
        )

    if report.notices:
        _write(output, "", "Notices")
        for notice in report.notices:
            _write(output, f"- {notice.summary}")


def _action_choices(
    report: VitrineAttentionReportV2,
) -> tuple[_MenuActionChoice, ...]:
    values: list[_MenuActionChoice] = []
    seen: set[tuple[str, str | None]] = set()
    for summary in report.summaries:
        if summary.next_action is None:
            continue
        key = (
            summary.next_action.action_id,
            summary.next_action.portfolio_id,
        )
        if key in seen:
            continue
        seen.add(key)
        values.append(
            _MenuActionChoice(
                action_id=summary.next_action.action_id,
                portfolio_id=summary.next_action.portfolio_id,
                label=_ACTION_LABELS.get(
                    summary.next_action.action_id,
                    "Open the related Vitrine workflow",
                ),
            )
        )
    return tuple(values)


def _portfolio_label(item: object) -> str:
    title = getattr(item, "title_snapshot", None)
    subject = getattr(item, "subject_display_label", None)
    if title and subject and subject.casefold() not in title.casefold():
        return f"{subject} — {title}"
    return str(title or subject or "Untitled Portfolio")


def _human_portfolio_labels(values: tuple[object, ...]) -> tuple[str, ...]:
    base = tuple(_portfolio_label(item) for item in values)
    totals = {label: base.count(label) for label in set(base)}
    seen: dict[str, int] = {}
    labels: list[str] = []
    for label in base:
        if totals[label] == 1:
            labels.append(label)
            continue
        occurrence = seen.get(label, 0) + 1
        seen[label] = occurrence
        labels.append(f"{label} — option {occurrence}")
    return tuple(labels)


def _portfolio_has_action(
    root: Path,
    portfolio_id: str,
    action_id: str,
) -> bool:
    report = evaluate_vitrine_attention_v2(
        root,
        VitrineAttentionQuery(portfolio_id=portfolio_id),
    )
    return any(
        item.next_action is not None
        and item.next_action.action_id == action_id
        for item in report.summaries
    )


def _select_workspace_portfolio_for_action(
    *,
    root: Path,
    action: _MenuActionChoice,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    matching = tuple(
        item
        for item in list_portfolios(root)
        if _portfolio_has_action(
            root,
            getattr(item, "portfolio_id"),
            action.action_id,
        )
    )
    clear_fn()
    _write(output, action.label, "")
    if not matching:
        _write(
            output,
            "No current Portfolio owns this action anymore.",
            "Attention will be refreshed.",
        )
        try:
            input_fn("Press Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return None
    if len(matching) == 1:
        return str(getattr(matching[0], "portfolio_id"))

    _write(output, "Choose a Portfolio", "")
    for index, label in enumerate(_human_portfolio_labels(matching), 1):
        _write(output, f"{index}. {label}")
    try:
        raw = input_fn("Portfolio number (B to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if raw.casefold() == "b" or not raw:
        return None
    if not raw.isdecimal():
        return None
    index = int(raw)
    if index < 1 or index > len(matching):
        return None
    return str(getattr(matching[index - 1], "portfolio_id"))


def _run_owner_action(
    *,
    root: Path,
    action: _MenuActionChoice,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    action_id = action.action_id

    if action_id == "open_candidate_inbox":
        run_candidate_inbox_menu(
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            dependencies=dependencies,
            actor=actor,
            workspace_root=root,
            portfolio_id=portfolio_id,
        )
        return

    if action_id == "open_candidate_review":
        run_candidate_review_menu(
            portfolio_id=portfolio_id,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            dependencies=dependencies,
            workspace_root=root,
            actor=actor,
        )
        return

    if action_id == "open_working_composition":
        run_working_composition_menu(
            portfolio_id=portfolio_id,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            dependencies=dependencies,
            workspace_root=root,
            actor=actor,
        )
        return

    if action_id in {
        "open_build_export_current_portfolio",
        "inspect_snapshot_recovery",
    }:
        run_current_portfolio_build_export_menu(
            root=root,
            portfolio_id=portfolio_id,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            dependencies=dependencies,
            actor=actor,
        )
        return

    if action_id in {
        "open_completed_portfolio_editions",
        "inspect_snapshot_custody",
        "inspect_snapshot_edition",
        "verify_snapshot_export",
    }:
        outcome = run_completed_portfolio_menu(
            root=root,
            portfolio_id=portfolio_id,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            actor=actor,
        )
        if outcome == BUILD_UPDATED_EDITION:
            run_current_portfolio_build_export_menu(
                root=root,
                portfolio_id=portfolio_id,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                actor=actor,
            )
        return

    raise ValueError(f"unsupported Attention action route: {action_id}")


def _render_attention_technical_details(
    output: TextIO,
    report: VitrineAttentionReportV2,
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
            f"  Requirement level: {item.requirement_level}",
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
    dependencies: VitrineWorkflowDependencies | None = None,
    actor: ActorAttribution | None = None,
) -> None:
    """Render current Attention and route explicit teacher-selected owner actions."""

    root = resolve_workspace_root(workspace_root)
    workflow_dependencies = dependencies or default_workflow_dependencies()

    while True:
        report = evaluate_vitrine_attention_v2(
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

        actions = _action_choices(report)
        if actions:
            _write(output, "", "Open a next action")
            for index, action in enumerate(actions, 1):
                _write(output, f"{index}. {action.label}")

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
        if not choice or choice.casefold() == "b":
            return
        if choice.casefold() == "t":
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
            return
        if not choice.isdecimal():
            continue
        index = int(choice)
        if index < 1 or index > len(actions):
            continue

        action = actions[index - 1]
        target_portfolio_id = action.portfolio_id or portfolio_id
        if target_portfolio_id is None:
            target_portfolio_id = _select_workspace_portfolio_for_action(
                root=root,
                action=action,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
        if target_portfolio_id is None:
            continue

        _run_owner_action(
            root=root,
            action=action,
            portfolio_id=target_portfolio_id,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            dependencies=workflow_dependencies,
            actor=actor,
        )
        # The child workflow may mutate canonical Vitrine state. Never reuse the
        # stale report; loop back and recompute from the exact current state.


__all__ = ["run_attention_menu"]
