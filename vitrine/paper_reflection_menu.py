"""Portfolio-scoped teacher surface for paper-native Student Reflection."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import parse_navigation_choice
from pds_core.workspace import resolve_workspace_root

from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution
from vitrine.paper_reflection_workflow import (
    PaperReflectionRequirementStatus,
    PaperReflectionWorkflowView,
    build_paper_reflection_workflow_view,
)
from vitrine.workflow_context import VitrineWorkflowDependencies


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "B"


def _pause(input_fn: InputFunction) -> None:
    try:
        input_fn("Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        return


def _status_label(status: str) -> str:
    return {
        "not_issued": "Prompt not issued",
        "issued_awaiting_return": "Prompt issued — awaiting return",
        "returned_needs_review": "Returned paper needs review",
        "confirmed_needs_recording": "Authorship confirmed — recording incomplete",
        "recorded": "Reflection recorded — paper evidence preserved",
        "attention_required": "Needs teacher review",
    }[status]


def _render_requirement(
    output: TextIO,
    item: PaperReflectionRequirementStatus,
) -> None:
    _write(
        output,
        item.title,
        f"Requirement: {item.statement}",
        f"Status: {_status_label(item.status)}",
    )
    if item.prompt_snapshot is not None:
        _write(output, f"Prompt: {item.prompt_snapshot}")
    if item.issued_page_count:
        _write(
            output,
            f"Returned pages: {item.returned_page_count}/{item.issued_page_count}",
        )
    if item.rescan_choice_required:
        _write(
            output,
            "Returned paper includes multiple scan occurrences; "
            "an exact occurrence must be chosen during review.",
        )
    _write(output, item.explanation)


def _render_workflow(
    output: TextIO,
    view: PaperReflectionWorkflowView,
) -> None:
    _write(output, "Student Reflection", "")
    if not view.requirements:
        _write(output, "This Portfolio Profile has no Reflection requirement.")
        return
    for index, item in enumerate(view.requirements, 1):
        if index > 1:
            _write(output, "")
        _render_requirement(output, item)

    _write(
        output,
        "",
        "Paper is the primary Reflection workflow.",
        "Typed/manual Reflection remains a fallback in Candidate Review.",
    )


def _render_technical(
    output: TextIO,
    view: PaperReflectionWorkflowView,
) -> None:
    _write(
        output,
        "Student Reflection — Technical Details / Provenance",
        "",
        f"Observed Vitrine state revision: {view.observed_state_revision}",
        f"Portfolio ID: {view.portfolio_id}",
        f"Portfolio Subject ID: {view.portfolio_subject_id}",
        f"Profile Binding ID: {view.profile_binding_id}",
    )
    for item in view.requirements:
        _write(
            output,
            "",
            f"Requirement ID: {item.requirement_id}",
            f"Status: {item.status}",
            f"Issuance ID: {item.issuance_id or '(none)'}",
            f"Target count: {item.target_count}",
            f"Issued pages: {item.issued_page_count}",
            f"Returned page coverage: {item.returned_page_count}",
            f"Returned scan occurrences: {item.returned_occurrence_count}",
            "Authorship Confirmation ID: "
            f"{item.authorship_confirmation_id or '(none)'}",
            f"Reflection ID: {item.reflection_id or '(none)'}",
            "Reflection revision: "
            + (
                str(item.reflection_revision)
                if item.reflection_revision is not None
                else "(none)"
            ),
            f"Paper Finalization ID: {item.paper_finalization_id or '(none)'}",
        )


def run_paper_reflection_menu(
    *,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    workspace_root: Path | None = None,
    actor: ActorAttribution | None = None,
) -> None:
    """Show Portfolio-scoped paper Reflection status and next workflow boundary."""

    del dependencies, actor
    root = resolve_workspace_root(workspace_root)
    while True:
        view = build_paper_reflection_workflow_view(root, portfolio_id)
        clear_fn()
        _render_workflow(output, view)
        _write(
            output,
            "",
            "T. Technical details / provenance",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "t":
            clear_fn()
            _render_technical(output, view)
            _pause(input_fn)
            continue
        navigation = parse_navigation_choice(
            choice,
            allow_back=True,
            allow_main_menu=True,
            allow_quit=True,
        )
        if navigation is not None:
            return
        _write(
            output,
            "Preparation, printing, and returned-paper review actions are "
            "introduced at the next workflow slice.",
        )
        _pause(input_fn)


__all__ = ["run_paper_reflection_menu"]
