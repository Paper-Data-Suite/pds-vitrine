"""Read-only teacher navigation over exact completed Portfolio history.

Issue #102 Slice 3: canonical browsing plus explicit verified local-use actions.
This module never discovers history from custody, repairs output, performs silent
printing, claims delivery, rebuilds, or advances the Current Pointer.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice

from vitrine.completed_portfolio import (
    CompletedPortfolioEdition,
    CompletedPortfolioExport,
    CompletedPortfolioHistory,
    CompletedPortfolioHistoryError,
    CompletedPortfolioPresentation,
    CompletedPortfolioSeries,
    project_completed_portfolio_history,
)
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.portfolio_output_opening import (
    PortfolioOutputOpenError,
    open_printable_student_portfolio,
    open_student_portfolio_folder,
    open_student_portfolio_html,
    open_technical_export_folder,
)
from vitrine.portfolio_services import show_portfolio
from vitrine.storage import VitrineStorageError, load_current_records_with_state
from vitrine.teacher_presentation import teacher_term


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "Q"


def _pause(input_fn: InputFunction) -> None:
    try:
        choice = input_fn("Press Enter to continue (B to back): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice:
        _navigation(choice)


def _navigation(raw: str) -> NavigationChoice | None:
    return parse_navigation_choice(
        raw, allow_back=True, allow_main_menu=True, allow_quit=True
    )


def _date(value: datetime) -> str:
    """Display the exact recorded date; never substitute wall-clock time."""
    return value.date().strftime("%B %d, %Y").replace(" 0", " ")


def _series_label(series: CompletedPortfolioSeries) -> str:
    # Audience purpose is frozen teacher-readable context, not an inferred class.
    purpose = series.audience_purpose.strip()
    if purpose:
        return purpose
    return (
        f"{teacher_term(series.audience_class)} — "
        f"{teacher_term(series.snapshot_purpose)}"
    )


def _labels(history: CompletedPortfolioHistory) -> dict[str, str]:
    """Disambiguate equal human labels without revealing opaque Series IDs."""
    bases = tuple(_series_label(item) for item in history.series)
    counts = Counter(bases)
    occurrences: Counter[str] = Counter()
    result: dict[str, str] = {}
    for series, base in zip(history.series, bases, strict=True):
        occurrences[base] += 1
        result[series.snapshot_series_id] = (
            base if counts[base] == 1 else f"{base} (Series {occurrences[base]})"
        )
    return result


def _load_history(root: Path, portfolio_id: str) -> CompletedPortfolioHistory:
    """One canonical read; no filesystem enumeration or derived catalog lookup."""
    _state, records = load_current_records_with_state(root)
    return project_completed_portfolio_history(records, portfolio_id=portfolio_id)


def _portfolio_label(root: Path, portfolio_id: str) -> str:
    summary = show_portfolio(root, portfolio_id).summary
    title = summary.title_snapshot or "Portfolio"
    subject = summary.subject_display_label
    if subject and subject.casefold() not in title.casefold():
        return f"{subject} — {title}"
    return title


def _student_presentations(
    edition: CompletedPortfolioEdition,
) -> tuple[CompletedPortfolioPresentation, ...]:
    return tuple(
        item
        for item in edition.presentations
        if item.presentation_class == "student_portfolio"
    )


def _edition_actions(
    edition: CompletedPortfolioEdition,
) -> tuple[tuple[str, str], ...]:
    actions: list[tuple[str, str]] = []
    if _student_presentations(edition):
        actions.extend(
            (
                ("view_student_portfolio", "View Student Portfolio"),
                ("print_portfolio", "Print Portfolio"),
                ("open_portfolio_folder", "Open Portfolio Folder"),
            )
        )
    if edition.exports:
        actions.append(("open_technical_export", "Open Technical Export Folder"))
    actions.extend(
        (
            ("artifact_history", "Export / Presentation History"),
            ("technical_details", "Technical Details / Provenance"),
        )
    )
    return tuple(actions)


def _render_list(
    output: TextIO,
    history: CompletedPortfolioHistory,
    portfolio_label: str,
) -> tuple[tuple[str, int], ...]:
    """Render a stable numbered selection index into *exact* Series/Edition pairs."""
    labels = _labels(history)
    selections: list[tuple[str, int]] = []
    _write(output, "Completed Portfolio Editions", "", portfolio_label, "")
    if not history.series:
        _write(output, "No Snapshot Series has been created for this Portfolio.")
    for series in history.series:
        _write(output, labels[series.snapshot_series_id])
        if not series.editions:
            _write(output, "  No completed Editions yet.")
        for edition in series.editions:
            selections.append((edition.snapshot_series_id, edition.edition_number))
            _write(
                output,
                f"  {len(selections)}. Edition {edition.edition_number}",
                f"     Built: {_date(edition.created_at)}",
                "     Student Portfolio: "
                + (
                    "recorded (verification required)"
                    if any(
                        item.presentation_class == "student_portfolio"
                        for item in edition.presentations
                    )
                    else "not recorded"
                ),
                "     Technical Export: "
                + (
                    "recorded (verification required)"
                    if edition.exports
                    else "not recorded"
                ),
                f"     Current: {'yes' if edition.is_current else 'no'}",
            )
        _write(output, "")
    if not selections:
        _write(output, "There are no completed Portfolio Editions to select.", "")
    _write(output, "B. Back", "M. Main Menu", "Q. Quit")
    return tuple(selections)



def _render_edition_detail(
    output: TextIO,
    *,
    edition: CompletedPortfolioEdition,
    series_label: str,
    portfolio_label: str,
) -> tuple[str, ...]:
    actions = _edition_actions(edition)
    _write(
        output,
        "Completed Portfolio Edition",
        "",
        portfolio_label,
        f"Audience / purpose: {series_label}",
        f"Edition {edition.edition_number}",
        f"Built: {_date(edition.created_at)}",
        f"Current: {'yes' if edition.is_current else 'no'}",
        f"Technical Exports: {len(edition.exports)} recorded",
        f"Portfolio Presentations: {len(edition.presentations)} recorded",
        "",
        "Local-use actions verify the exact saved artifact before opening it.",
        "",
    )
    for index, (_key, label) in enumerate(actions, 1):
        _write(output, f"{index}. {label}")
    _write(output, "B. Back", "M. Main Menu", "Q. Quit")
    return tuple(key for key, _label in actions)


def _render_artifact_history(
    output: TextIO,
    edition: CompletedPortfolioEdition,
) -> None:
    _write(
        output, "Export / Presentation History", "",
        f"Edition {edition.edition_number}",
    )
    _write(output, "", "Technical Exports")
    if not edition.exports:
        _write(output, "- None recorded.")
    for index, export in enumerate(edition.exports, 1):
        _write(
            output,
            f"{index}. {teacher_term(export.export_format)} "
            f"— {_date(export.generated_at)}",
            "   Recorded technical output; not independently verified now.",
        )
    _write(output, "", "Portfolio Presentations")
    if not edition.presentations:
        _write(output, "- None recorded.")
    for index, presentation in enumerate(edition.presentations, 1):
        _write(
            output,
            f"{index}. {teacher_term(presentation.presentation_class)} "
            f"— {_date(presentation.generated_at)}",
            "   Recorded student-facing output; not independently verified now.",
        )
    _write(output, "", "B. Back", "M. Main Menu", "Q. Quit")


def _render_technical(
    output: TextIO,
    *,
    edition: CompletedPortfolioEdition,
    series: CompletedPortfolioSeries,
) -> None:
    _write(
        output,
        "Completed Portfolio Technical Details / Provenance",
        "",
        f"Portfolio ID: {edition.portfolio_id}",
        f"Portfolio Subject ID: {edition.portfolio_subject_id}",
        f"Snapshot Series ID: {edition.snapshot_series_id}",
        f"Predecessor Series ID: {series.predecessor_series_id or '(none)'}",
        f"Edition number (Series-scoped): {edition.edition_number}",
        f"Predecessor Edition: {edition.predecessor_edition or '(none)'}",
        f"Profile Binding ID: {edition.profile_binding_id}",
        f"Profile ID: {edition.profile_revision.portfolio_profile_id}",
        f"Profile revision: {edition.profile_revision.profile_revision}",
        f"Composition revision: {edition.composition_revision}",
        f"Audience Context ID: {edition.audience_context_id}",
        f"Explicit current-pointer selection: {'yes' if edition.is_current else 'no'}",
        "",
        "Technical Export provenance",
    )
    if not edition.exports:
        _write(output, "- None recorded.")
    for export in edition.exports:
        _write(
            output,
            f"- Export ID: {export.snapshot_export_artifact_id}",
            f"  Export contract: {export.export_contract_version}",
            f"  Relative custody path: {export.relative_path}",
            "  Predecessor: "
            f"{export.predecessor_export_artifact_id or '(none)'}",
        )
    _write(output, "", "Presentation provenance")
    if not edition.presentations:
        _write(output, "- None recorded.")
    for presentation in edition.presentations:
        _write(
            output,
            f"- Presentation ID: {presentation.presentation_artifact_id}",
            f"  Source Export ID: {presentation.snapshot_export_artifact_id}",
            f"  Presentation contract: {presentation.presentation_contract_version}",
            f"  Renderer: {presentation.renderer_id} {presentation.renderer_version}",
            f"  Presentation root: {presentation.relative_path}",
            f"  HTML: {presentation.html_relative_path}",
            f"  Printable PDF: {presentation.printable_pdf_relative_path}",
            "  Predecessor: "
            f"{presentation.predecessor_presentation_artifact_id or '(none)'}",
        )
    _write(
        output,
        "",
        "Technical paths are recorded provenance, not permission to open files.",
        "B. Back",
        "M. Main Menu",
        "Q. Quit",
    )


def _exact_edition(
    history: CompletedPortfolioHistory,
    *,
    snapshot_series_id: str,
    edition_number: int,
) -> tuple[CompletedPortfolioSeries, CompletedPortfolioEdition] | None:
    for series in history.series:
        if series.snapshot_series_id != snapshot_series_id:
            continue
        for edition in series.editions:
            if edition.edition_number == edition_number:
                return series, edition
    return None


def _choose_presentation(
    *,
    edition: CompletedPortfolioEdition,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> CompletedPortfolioPresentation | None:
    values = _student_presentations(edition)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    clear_fn()
    _write(output, "Choose Student Portfolio", "")
    for index, item in enumerate(values, 1):
        _write(output, f"{index}. Generated {_date(item.generated_at)}")
    _write(output, "B. Back", "M. Main Menu", "Q. Quit")
    raw = _read(input_fn, "Student Portfolio number: ")
    navigation = _navigation(raw)
    if navigation is not None:
        return None
    if raw.isdecimal() and 1 <= int(raw) <= len(values):
        return values[int(raw) - 1]
    _write(output, "That Student Portfolio number is not available.")
    _pause(input_fn)
    return None


def _choose_export(
    *,
    edition: CompletedPortfolioEdition,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> CompletedPortfolioExport | None:
    values = edition.exports
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    clear_fn()
    _write(output, "Choose Technical Export", "")
    for index, item in enumerate(values, 1):
        _write(
            output,
            f"{index}. {teacher_term(item.export_format)} "
            f"— generated {_date(item.generated_at)}",
        )
    _write(output, "B. Back", "M. Main Menu", "Q. Quit")
    raw = _read(input_fn, "Technical Export number: ")
    navigation = _navigation(raw)
    if navigation is not None:
        return None
    if raw.isdecimal() and 1 <= int(raw) <= len(values):
        return values[int(raw) - 1]
    _write(output, "That Technical Export number is not available.")
    _pause(input_fn)
    return None


def _render_open_problem(output: TextIO, error: PortfolioOutputOpenError) -> None:
    if error.code == "portfolio_output.verification_failed":
        headline = "This Portfolio no longer matches its verified saved state."
    else:
        headline = "This saved Portfolio could not be opened safely."
    _write(
        output,
        headline,
        "",
        "Nothing was changed automatically.",
        "Open Technical Details / Provenance for diagnostics.",
    )


def _run_presentation_action(
    *,
    action: str,
    root: Path,
    edition: CompletedPortfolioEdition,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    presentation = _choose_presentation(
        edition=edition,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if presentation is None:
        return
    try:
        if action == "view_student_portfolio":
            open_student_portfolio_html(
                root,
                presentation_artifact_id=presentation.presentation_artifact_id,
            )
            message = (
                "Student Portfolio opened.",
                "This is a local view; no delivery or sharing is recorded.",
            )
        elif action == "print_portfolio":
            open_printable_student_portfolio(
                root,
                presentation_artifact_id=presentation.presentation_artifact_id,
            )
            message = (
                "Printable Portfolio opened.",
                "",
                "Use your PDF application's Print command to print the "
                "binder-ready Portfolio.",
                "Opening the PDF does not mean physical printing occurred.",
            )
        elif action == "open_portfolio_folder":
            open_student_portfolio_folder(
                root,
                presentation_artifact_id=presentation.presentation_artifact_id,
            )
            message = (
                "Portfolio folder opened.",
                "This is local file access; no delivery or sharing is recorded.",
            )
        else:
            raise AssertionError(f"unsupported presentation local-use action: {action}")
    except PortfolioOutputOpenError as error:
        clear_fn()
        _render_open_problem(output, error)
        _pause(input_fn)
        return
    clear_fn()
    _write(output, *message)
    _pause(input_fn)


def _run_export_open_action(
    *,
    root: Path,
    edition: CompletedPortfolioEdition,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    export = _choose_export(
        edition=edition,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if export is None:
        return
    try:
        open_technical_export_folder(
            root,
            snapshot_export_artifact_id=export.snapshot_export_artifact_id,
        )
    except PortfolioOutputOpenError as error:
        clear_fn()
        _render_open_problem(output, error)
        _pause(input_fn)
        return
    clear_fn()
    _write(
        output,
        "Technical Export folder opened.",
        "This is the technical Export, not the student Portfolio presentation.",
    )
    _pause(input_fn)



def _edition_workflow(
    *,
    root: Path,
    portfolio_id: str,
    snapshot_series_id: str,
    edition_number: int,
    portfolio_label: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    while True:
        # Reload canonical state instead of relying on an earlier selection index.
        history = _load_history(root, portfolio_id)
        exact = _exact_edition(
            history,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        )
        clear_fn()
        if exact is None:
            _write(output, "Selected Edition is no longer in canonical history.")
            _pause(input_fn)
            return
        series, edition = exact
        actions = _render_edition_detail(
            output,
            edition=edition,
            series_label=_labels(history)[snapshot_series_id],
            portfolio_label=portfolio_label,
        )
        choice = _read(input_fn, "Choice: ")
        if _navigation(choice) is not None:
            return
        if not choice.isdecimal() or not (1 <= int(choice) <= len(actions)):
            _write(output, "Please choose a listed action, B, M, or Q.")
            _pause(input_fn)
            continue
        action = actions[int(choice) - 1]
        if action == "artifact_history":
            clear_fn()
            _render_artifact_history(output, edition)
            _pause(input_fn)
        elif action == "technical_details":
            clear_fn()
            _render_technical(output, edition=edition, series=series)
            _pause(input_fn)
        elif action in {
            "view_student_portfolio",
            "print_portfolio",
            "open_portfolio_folder",
        }:
            _run_presentation_action(
                action=action,
                root=root,
                edition=edition,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
        elif action == "open_technical_export":
            _run_export_open_action(
                root=root,
                edition=edition,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
        else:
            raise AssertionError(f"unsupported completed Portfolio action: {action}")


def run_completed_portfolio_menu(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    """Browse canonical completed Editions in the selected Portfolio context."""
    while True:
        try:
            history = _load_history(root, portfolio_id)
            label = _portfolio_label(root, portfolio_id)
        except (CompletedPortfolioHistoryError, VitrineStorageError) as error:
            clear_fn()
            _write(
                output,
                "Completed Portfolio history unavailable",
                f"Reason: {getattr(error, 'code', 'canonical_storage_unavailable')}",
                "Inspect canonical Vitrine storage before continuing.",
            )
            _pause(input_fn)
            return
        clear_fn()
        selections = _render_list(output, history, label)
        choice = _read(input_fn, "Edition number (B to go back): ")
        if _navigation(choice) is not None:
            return
        if choice.isdecimal() and 1 <= int(choice) <= len(selections):
            series_id, number = selections[int(choice) - 1]
            try:
                _edition_workflow(
                    root=root,
                    portfolio_id=portfolio_id,
                    snapshot_series_id=series_id,
                    edition_number=number,
                    portfolio_label=label,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            except (CompletedPortfolioHistoryError, VitrineStorageError) as error:
                clear_fn()
                _write(
                    output,
                    "Completed Portfolio history unavailable",
                    "Reason: "
                    f"{getattr(error, 'code', 'canonical_storage_unavailable')}",
                )
                _pause(input_fn)
                return
            continue
        _write(output, "That Edition number is not available.")
        _pause(input_fn)


__all__ = ["run_completed_portfolio_menu"]
