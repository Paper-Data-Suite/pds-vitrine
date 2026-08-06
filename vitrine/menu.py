"""Minimal low-density teacher-facing menu for the Vitrine package baseline."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import (
    NavigationChoice,
    QuitPDS,
    ReturnToMainMenu,
    parse_navigation_choice,
)
from pds_core.workspace import WorkspaceRootError

from vitrine.workspace import (
    reset_workspace,
    set_workspace,
    show_workspace,
    validate_workspace,
)

InputFunction = Callable[[str], str]
ClearFunction = Callable[[], None]


def clear_screen() -> None:
    """Clear the active terminal using the platform's conventional command."""
    command = "cls" if os.name == "nt" else "clear"
    os.system(command)  # noqa: S605, S607 - fixed platform command, no user input


def _write_lines(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _pause(input_fn: InputFunction) -> None:
    input_fn("Press Enter to continue...")


def _read(input_fn: InputFunction, prompt: str) -> str:
    return input_fn(prompt).strip()


def _show_main_help(*, output: TextIO, input_fn: InputFunction) -> None:
    _write_lines(
        output,
        "Vitrine package baseline",
        "",
        "This release manages the shared Paper Data Suite workspace only.",
        "Portfolio creation, curation, and Snapshot building are not available yet.",
    )
    _pause(input_fn)


def _show_workspace_help(*, output: TextIO, input_fn: InputFunction) -> None:
    _write_lines(
        output,
        "Workspace Help",
        "",
        "Paper Data Suite Core owns workspace resolution and configuration.",
        "Reset clears only the saved preference and never deletes workspace data.",
    )
    _pause(input_fn)


def _render_workspace_status(output: TextIO, explicit_root: Path | None = None) -> None:
    status = show_workspace(explicit_root)
    _write_lines(
        output,
        f"Workspace: {status.root}",
        f"Source: {status.source}",
        f"Exists: {'yes' if status.exists else 'no'}",
        f"Writable: {'yes' if status.is_writable else 'no'}",
    )


def _confirm(
    *,
    input_fn: InputFunction,
    word: str,
    allow_main_menu: bool = True,
) -> bool:
    response = _read(input_fn, f"Type {word} to continue, or press Enter to cancel: ")
    if not response:
        return False
    navigation = parse_navigation_choice(
        response,
        allow_back=True,
        allow_main_menu=allow_main_menu,
        allow_quit=True,
    )
    if navigation is NavigationChoice.BACK:
        return False
    return response.casefold() == word.casefold()


def _workspace_menu(
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    while True:
        clear_fn()
        _write_lines(
            output,
            "Workspace Settings",
            "",
            "1. Show current workspace",
            "2. Set workspace folder",
            "3. Validate/create current workspace",
            "4. Reset saved workspace preference",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _show_workspace_help(output=output, input_fn=input_fn)
            continue
        navigation = parse_navigation_choice(choice)
        if navigation is NavigationChoice.BACK:
            return
        try:
            if choice == "1":
                clear_fn()
                _render_workspace_status(output)
                _pause(input_fn)
            elif choice == "2":
                clear_fn()
                raw_path = _read(input_fn, "Workspace folder: ")
                if not raw_path:
                    continue
                _write_lines(output, "", f"Selected workspace: {Path(raw_path)}")
                if _confirm(input_fn=input_fn, word="SET"):
                    result = set_workspace(raw_path)
                    action = "Created and saved" if result.created else "Saved"
                    _write_lines(output, "", f"{action}: {result.root}")
                    _pause(input_fn)
            elif choice == "3":
                clear_fn()
                _render_workspace_status(output)
                _write_lines(output, "")
                if _confirm(input_fn=input_fn, word="CREATE"):
                    result = validate_workspace()
                    action = "Created" if result.created else "Validated"
                    _write_lines(output, "", f"{action}: {result.root}")
                    _pause(input_fn)
            elif choice == "4":
                clear_fn()
                _write_lines(
                    output,
                    "Resetting the preference does not delete any workspace files.",
                    "",
                )
                if _confirm(input_fn=input_fn, word="RESET"):
                    removed = reset_workspace()
                    message = (
                        "Cleared saved workspace preference."
                        if removed
                        else "No saved workspace preference was set."
                    )
                    _write_lines(output, "", message)
                    _pause(input_fn)
            else:
                _write_lines(output, "Please choose 1-4, H, B, M, or Q.")
                _pause(input_fn)
        except WorkspaceRootError as exc:
            _write_lines(output, "", f"Workspace problem: {exc}")
            _pause(input_fn)


def run_menu(
    *,
    input_fn: InputFunction = input,
    output: TextIO | None = None,
    clear_fn: ClearFunction = clear_screen,
) -> int:
    """Run the minimal teacher-facing menu without creating workspace state."""
    stream = sys.stdout if output is None else output
    try:
        while True:
            clear_fn()
            _write_lines(
                stream,
                "Vitrine",
                "",
                "1. Workspace Settings",
                "H. Help",
                "Q. Quit",
            )
            choice = _read(input_fn, "Choice: ")
            if choice.casefold() == "h":
                clear_fn()
                _show_main_help(output=stream, input_fn=input_fn)
                continue
            if choice.casefold() == "q":
                return 0
            if choice == "1":
                try:
                    _workspace_menu(
                        input_fn=input_fn,
                        output=stream,
                        clear_fn=clear_fn,
                    )
                except ReturnToMainMenu:
                    continue
            else:
                _write_lines(stream, "Please choose 1, H, or Q.")
                _pause(input_fn)
    except (EOFError, KeyboardInterrupt, QuitPDS):
        return 0
