"""Shared interaction primitives for Vitrine teacher-facing menus.

This module is intentionally UI-only. It standardizes controlled confirmation
and zero/one/many required-choice behavior without owning Portfolio domain
validity, authorization, canonical identity, or persistence.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, Literal, TextIO, TypeVar

from pds_core.menu_navigation import (
    NavigationChoice,
    navigation_labels,
    parse_navigation_choice,
)

from vitrine.menu_types import ClearFunction, InputFunction

GUIDED_MENU_INTERACTION_CONTRACT_VERSION = "vitrine_guided_menu_interaction_v1"

_ChoiceValue = TypeVar("_ChoiceValue")
RequiredChoiceDisposition = Literal[
    "unavailable",
    "carried_forward",
    "requires_choice",
]
ReviewRenderer = Callable[[], None]


@dataclass(frozen=True, slots=True)
class RequiredChoiceResolution(Generic[_ChoiceValue]):
    """Cardinality-only resolution for one required exact choice."""

    disposition: RequiredChoiceDisposition
    selected: _ChoiceValue | None
    choices: tuple[_ChoiceValue, ...]


def resolve_required_choice(
    choices: Sequence[_ChoiceValue],
) -> RequiredChoiceResolution[_ChoiceValue]:
    """Resolve zero/one/many required choices without preference inference.

    Zero values are unavailable, one exact value is carried forward, and two or
    more values require an explicit teacher choice. The exact supplied object is
    preserved when one value is carried forward.
    """

    exact_choices = tuple(choices)
    if not exact_choices:
        return RequiredChoiceResolution(
            disposition="unavailable",
            selected=None,
            choices=(),
        )
    if len(exact_choices) == 1:
        return RequiredChoiceResolution(
            disposition="carried_forward",
            selected=exact_choices[0],
            choices=exact_choices,
        )
    return RequiredChoiceResolution(
        disposition="requires_choice",
        selected=None,
        choices=exact_choices,
    )


def _read(input_fn: InputFunction, prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "Q"


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def confirm_exact_phrase(
    *,
    expected_phrase: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    render_review: ReviewRenderer,
) -> bool:
    """Confirm one consequential write with current-state redraw semantics.

    Matching is capitalization-insensitive after surrounding whitespace is
    stripped, but otherwise exact. Blank input or Back cancels. Main Menu and
    Quit retain Core-owned unwind behavior. A wrong nonblank phrase is never
    treated as silent cancellation; the review is redrawn with explicit bounded
    feedback and the teacher may retry.
    """

    phrase = expected_phrase.strip()
    if not phrase:
        raise ValueError("expected_phrase must contain non-whitespace text.")

    mismatch = False
    while True:
        clear_fn()
        render_review()
        _write(output, "")
        if mismatch:
            _write(
                output,
                "Confirmation not accepted.",
                "",
            )
        _write(
            output,
            f"Type {phrase} to confirm.",
            "Capitalization does not matter.",
            "Press Enter or B to cancel.",
            *navigation_labels(back=True, main_menu=True, quit=True),
        )
        response = _read(input_fn, "Confirmation: ")
        if not response:
            return False
        navigation = parse_navigation_choice(
            response,
            allow_back=True,
            allow_main_menu=True,
            allow_quit=True,
        )
        if navigation is NavigationChoice.BACK:
            return False
        if response.casefold() == phrase.casefold():
            return True
        mismatch = True


__all__ = [
    "GUIDED_MENU_INTERACTION_CONTRACT_VERSION",
    "RequiredChoiceDisposition",
    "RequiredChoiceResolution",
    "ReviewRenderer",
    "confirm_exact_phrase",
    "resolve_required_choice",
]
