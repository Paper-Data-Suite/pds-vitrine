"""Command-line entry point for the Vitrine package baseline."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from pds_core.workspace import WorkspaceRootError

from vitrine import __version__
from vitrine import menu as menu_module
from vitrine.workspace import (
    reset_workspace,
    set_workspace,
    show_workspace,
    validate_workspace,
)


def _add_workspace_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Explicit Paper Data Suite workspace root for this command.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the parser without resolving a workspace or touching the filesystem."""
    parser = argparse.ArgumentParser(
        prog="vitrine",
        description=(
            "Vitrine is the Paper Data Suite portfolio module. This package "
            "baseline currently provides workspace management only."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("menu", help="Launch the teacher-facing menu.")

    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Manage the shared Paper Data Suite workspace.",
    )
    workspace_subparsers = workspace_parser.add_subparsers(
        dest="workspace_command",
        required=True,
    )

    show_parser = workspace_subparsers.add_parser(
        "show",
        help="Show the resolved workspace without changing it.",
    )
    _add_workspace_root_argument(show_parser)

    set_parser = workspace_subparsers.add_parser(
        "set",
        help="Validate/create and save a workspace root.",
    )
    set_parser.add_argument("path", type=Path)

    validate_parser = workspace_subparsers.add_parser(
        "validate",
        help="Validate/create the resolved workspace without saving it.",
    )
    _add_workspace_root_argument(validate_parser)

    workspace_subparsers.add_parser(
        "reset",
        help="Clear only the saved workspace preference.",
    )
    return parser


def _print_workspace_status(*, explicit_root: Path | None, output: TextIO) -> int:
    status = show_workspace(explicit_root)
    print(f"Workspace: {status.root}", file=output)
    print(f"Source: {status.source}", file=output)
    print(f"Exists: {'yes' if status.exists else 'no'}", file=output)
    print(f"Directory: {'yes' if status.is_dir else 'no'}", file=output)
    print(f"Writable: {'yes' if status.is_writable else 'no'}", file=output)
    print(f"Config: {status.config_path}", file=output)
    print(f"Default: {status.default_root}", file=output)
    return 0


def _run_workspace_command(
    args: argparse.Namespace,
    *,
    output: TextIO,
) -> int:
    if args.workspace_command == "show":
        return _print_workspace_status(
            explicit_root=args.workspace_root,
            output=output,
        )
    if args.workspace_command == "set":
        result = set_workspace(args.path)
        action = "Created and saved" if result.created else "Validated and saved"
        print(f"{action} workspace: {result.root}", file=output)
        return 0
    if args.workspace_command == "validate":
        result = validate_workspace(args.workspace_root)
        action = "Created" if result.created else "Validated"
        print(f"{action} workspace: {result.root}", file=output)
        return 0
    if args.workspace_command == "reset":
        removed = reset_workspace()
        message = (
            "Cleared saved workspace preference."
            if removed
            else "No saved workspace preference was set."
        )
        print(message, file=output)
        return 0
    raise AssertionError(f"Unhandled workspace command: {args.workspace_command}")


def main(
    argv: Sequence[str] | None = None,
    *,
    output: TextIO | None = None,
    error: TextIO | None = None,
) -> int:
    """Run Vitrine and return a stable process exit status."""
    stdout = sys.stdout if output is None else output
    stderr = sys.stderr if error is None else error
    effective_argv = tuple(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    if not effective_argv:
        return menu_module.run_menu(output=stdout)

    args = parser.parse_args(effective_argv)
    try:
        if args.command == "menu":
            return menu_module.run_menu(output=stdout)
        if args.command == "workspace":
            return _run_workspace_command(args, output=stdout)
    except WorkspaceRootError as exc:
        print(f"Workspace error: {exc}", file=stderr)
        return 1

    parser.print_help(file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
