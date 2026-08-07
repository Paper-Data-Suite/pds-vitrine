"""Shared callable types for Vitrine teacher-facing menus."""

from collections.abc import Callable

InputFunction = Callable[[str], str]
ClearFunction = Callable[[], None]

__all__ = ["ClearFunction", "InputFunction"]
