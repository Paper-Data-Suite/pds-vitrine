"""Presentation-independent wrappers over the released Core workspace API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pds_core.workspace import (
    WorkspaceRootError,
    WorkspaceStatus,
    clear_saved_workspace_root,
    ensure_workspace_root,
    inspect_workspace_root,
    save_workspace_root,
)


@dataclass(frozen=True, slots=True)
class WorkspaceMutationResult:
    """Result of one explicit workspace mutation."""

    root: Path
    created: bool
    saved: bool


def show_workspace(explicit_root: str | Path | None = None) -> WorkspaceStatus:
    """Inspect the Core-owned workspace without creating or changing it."""
    return inspect_workspace_root(explicit_root)


def validate_workspace(
    explicit_root: str | Path | None = None,
) -> WorkspaceMutationResult:
    """Validate or create the resolved Core workspace without saving a preference."""
    before = inspect_workspace_root(explicit_root)
    root = ensure_workspace_root(before.root, create=True)
    return WorkspaceMutationResult(root=root, created=not before.exists, saved=False)


def set_workspace(path: str | Path) -> WorkspaceMutationResult:
    """Validate/create and save a Core-owned workspace root."""
    before = inspect_workspace_root(path)
    root = ensure_workspace_root(before.root, create=True)
    saved_root = save_workspace_root(root)
    return WorkspaceMutationResult(
        root=saved_root,
        created=not before.exists,
        saved=True,
    )


def reset_workspace() -> bool:
    """Clear only the saved Core workspace preference."""
    return clear_saved_workspace_root()


__all__ = [
    "WorkspaceMutationResult",
    "WorkspaceRootError",
    "WorkspaceStatus",
    "reset_workspace",
    "set_workspace",
    "show_workspace",
    "validate_workspace",
]
