"""Low-density Portfolio-centered teacher workflow."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice
from pds_core.workspace import resolve_workspace_root

from vitrine.curation_services import select_candidate_directly
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution
from vitrine.portfolio_services import (
    create_portfolio,
    list_portfolios,
    observe_portfolio_state_revision,
    show_portfolio,
)
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import (
    list_active_selections,
    list_candidate_summaries,
    list_snapshot_series,
    show_composition,
    show_snapshot_series,
)


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    return input_fn(prompt).strip()


def _pause(input_fn: InputFunction) -> None:
    input_fn("Press Enter to continue...")


def _navigation(value: str) -> NavigationChoice | None:
    return parse_navigation_choice(
        value, allow_back=True, allow_main_menu=True, allow_quit=True
    )


def _actor(input_fn: InputFunction) -> ActorAttribution | None:
    actor_id = _read(input_fn, "Teacher/actor ID (B to cancel): ")
    if _navigation(actor_id) is NavigationChoice.BACK:
        return None
    if not actor_id:
        return None
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id=actor_id,
        owning_system="local",
        role_snapshot="teacher",
    )


def _choose_portfolio(
    *,
    root: Path,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    values = list_portfolios(root)
    clear_fn()
    _write(output, "Open Portfolio", "")
    if not values:
        _write(output, "No Portfolios exist yet.")
        _pause(input_fn)
        return None
    for index, item in enumerate(values, 1):
        _write(
            output,
            f"{index}. {item.title_snapshot or item.subject_display_label or '(untitled)'}",
            f"   {item.portfolio_id}",
        )
    raw = _read(input_fn, "Portfolio number (B to go back): ")
    if _navigation(raw) is NavigationChoice.BACK:
        return None
    try:
        return values[int(raw) - 1].portfolio_id
    except (ValueError, IndexError):
        _write(output, "That Portfolio number is not available.")
        _pause(input_fn)
        return None


def _overview(root: Path, portfolio_id: str, output: TextIO) -> None:
    x = show_portfolio(root, portfolio_id).summary
    _write(
        output,
        "Portfolio Overview",
        "",
        f"Portfolio ID: {x.portfolio_id}",
        f"Subject: {x.subject_display_label or x.portfolio_subject_id}",
        f"Profile Binding: {x.profile_binding_id or 'not bound'}",
        f"Candidates: {x.candidate_count}",
        f"Active Selections: {x.active_selection_count}",
        f"Working Composition: {x.current_composition_revision or 'not frozen'}",
        f"Snapshot Series: {x.snapshot_series_count}",
    )


def _portfolio_context(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    while True:
        detail = show_portfolio(root, portfolio_id)
        clear_fn()
        _write(
            output,
            f"Portfolio — {detail.summary.title_snapshot or detail.summary.subject_display_label or portfolio_id}",
            "",
            "1. Overview",
            "2. Review Candidates",
            "3. Curate Selections",
            "4. Working Composition",
            "5. Snapshot",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _write(
                output,
                "Portfolio Help",
                "",
                "Candidate review does not create a Selection.",
                "Working Composition is not a Snapshot.",
                "Audience Context is not disclosure authorization.",
            )
            _pause(input_fn)
            continue
        if _navigation(choice) is NavigationChoice.BACK:
            return
        clear_fn()
        if choice == "1":
            _overview(root, portfolio_id, output)
        elif choice == "2":
            _write(output, "Review Candidates", "")
            observed_revision = observe_portfolio_state_revision(root)
            candidates = list_candidate_summaries(root, portfolio_id)
            if not candidates:
                _write(
                    output,
                    "No Candidates. Discovery requires configured source-read integration and authority.",
                )
            for index, candidate_item in enumerate(candidates, 1):
                _write(
                    output,
                    f"{index}. {candidate_item.display_snapshot}",
                    f"   {candidate_item.candidate_id} — {candidate_item.condition_state}",
                )
            if candidates:
                raw = _read(
                    input_fn,
                    "Candidate number to review (Enter to leave unchanged): ",
                )
                if raw:
                    try:
                        candidate_item = candidates[int(raw) - 1]
                    except (ValueError, IndexError):
                        _write(output, "That Candidate number is not available.")
                    else:
                        clear_fn()
                        _write(
                            output,
                            "Candidate Review",
                            "",
                            candidate_item.display_snapshot,
                            f"Candidate ID: {candidate_item.candidate_id}",
                            f"Condition: {candidate_item.condition_state}",
                            f"Eligible sections: {', '.join(candidate_item.eligible_section_ids)}",
                            "",
                            "Reviewing a Candidate does not select it.",
                        )
                        if (
                            _read(
                                input_fn,
                                "Type SELECT to select this Candidate, or Enter to leave unchanged: ",
                            )
                            == "SELECT"
                        ):
                            mutation_actor = actor or _actor(input_fn)
                            if (
                                mutation_actor is not None
                                and observed_revision is not None
                            ):
                                sections = tuple(
                                    item.strip()
                                    for item in _read(
                                        input_fn,
                                        "Section IDs (comma-separated): ",
                                    ).split(",")
                                    if item.strip()
                                )
                                result = select_candidate_directly(
                                    root,
                                    portfolio_id=portfolio_id,
                                    candidate_id=candidate_item.candidate_id,
                                    selected_by=mutation_actor,
                                    proposed_section_ids=sections,
                                    expected_state_revision=observed_revision,
                                    authority_gate=dependencies.curation_authority_gate,
                                )
                                _write(
                                    output,
                                    "",
                                    f"Selection recorded at state revision {result.state_revision}.",
                                )
        elif choice == "3":
            _write(output, "Curate Selections", "")
            selections = list_active_selections(root, portfolio_id)
            if not selections:
                _write(
                    output,
                    "No active Selections. Selecting a Candidate always requires explicit confirmation and curation authority.",
                )
            for selection_item in selections:
                _write(
                    output,
                    f"{selection_item.selection_id} — Candidate {selection_item.candidate_id}",
                )
        elif choice == "4":
            _write(output, "Working Composition", "")
            composition_view = show_composition(root, portfolio_id)
            if composition_view.composition is None:
                _write(output, "No Working Composition has been frozen.")
            else:
                _write(
                    output,
                    f"Revision: {composition_view.composition.composition_revision}",
                    f"Placements: {len(composition_view.composition.placement_ids)}",
                    f"Unresolved: {', '.join(composition_view.inventory.unresolved_obligation_codes) if composition_view.inventory else 'inventory missing'}",
                )
        elif choice == "5":
            _write(output, "Snapshot", "")
            series_values = list_snapshot_series(root, portfolio_id)
            if not series_values:
                _write(
                    output,
                    "No Snapshot Series. A Snapshot requires an exact Audience Context and frozen Composition.",
                )
            for series_item in series_values:
                series_view = show_snapshot_series(root, series_item.snapshot_series_id)
                _write(
                    output,
                    f"{series_item.snapshot_series_id} — {series_item.snapshot_purpose}",
                    f"  Editions: {len(series_view.editions)}; current pointer: {series_view.current_edition.edition_number if series_view.current_edition else 'none'}",
                )
        else:
            _write(output, "Please choose 1-5, H, B, M, or Q.")
        _pause(input_fn)


def run_portfolio_menu(
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    workspace_root: Path | None = None,
    actor: ActorAttribution | None = None,
) -> None:
    """Run Portfolio navigation; canonical facts are reloaded before every action."""
    root = resolve_workspace_root(workspace_root)
    session_actor = actor
    while True:
        clear_fn()
        _write(
            output,
            "Portfolios",
            "",
            "1. Create Portfolio",
            "2. Open Portfolio",
            "3. List Portfolios",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _write(
                output,
                "Portfolio Help",
                "",
                "Create a Portfolio for one exact current Portfolio Subject.",
                "Choosing a Profile remains a separate action.",
            )
            _pause(input_fn)
            continue
        if _navigation(choice) is NavigationChoice.BACK:
            return
        try:
            if choice == "1":
                clear_fn()
                _write(output, "Create Portfolio", "")
                subject_id = _read(
                    input_fn, "Exact Portfolio Subject ID (B to cancel): "
                )
                if _navigation(subject_id) is NavigationChoice.BACK:
                    continue
                title = _read(input_fn, "Title (optional): ") or None
                if session_actor is None:
                    session_actor = _actor(input_fn)
                if session_actor is None:
                    continue
                confirmation = _read(input_fn, "Type CREATE to create this Portfolio: ")
                if confirmation != "CREATE":
                    continue
                # Observe once after the decision, then commit against that exact revision.
                result = create_portfolio(
                    root,
                    portfolio_subject_id=subject_id,
                    created_by=session_actor,
                    expected_state_revision=observe_portfolio_state_revision(root),
                    title_snapshot=title,
                )
                clear_fn()
                _write(output, "Portfolio Created", "", result.portfolio.portfolio_id)
                _pause(input_fn)
            elif choice == "2":
                selected = _choose_portfolio(
                    root=root,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
                if selected:
                    _portfolio_context(
                        root=root,
                        portfolio_id=selected,
                        input_fn=input_fn,
                        output=output,
                        clear_fn=clear_fn,
                        dependencies=dependencies,
                        actor=session_actor,
                    )
            elif choice == "3":
                clear_fn()
                _write(output, "Portfolios", "")
                values = list_portfolios(root)
                if not values:
                    _write(output, "No Portfolios exist yet.")
                for x in values:
                    _write(
                        output,
                        f"{x.title_snapshot or x.subject_display_label or '(untitled)'}",
                        f"  {x.portfolio_id}",
                    )
                _pause(input_fn)
            else:
                _write(output, "Please choose 1-3, H, B, M, or Q.")
                _pause(input_fn)
        except (ValueError, RuntimeError) as exc:
            clear_fn()
            _write(
                output,
                "Portfolio workflow problem",
                "",
                f"{getattr(exc, 'code', exc.__class__.__name__)}: {exc}",
            )
            _pause(input_fn)


__all__ = ["run_portfolio_menu"]
