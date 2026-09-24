"""Focused tests for the shared guided-menu interaction contract."""

from __future__ import annotations

from io import StringIO
from typing import NoReturn

import pytest
from pds_core.menu_navigation import QuitPDS, ReturnToMainMenu

from vitrine.menu_interactions import (
    GUIDED_MENU_INTERACTION_CONTRACT_VERSION,
    confirm_exact_phrase,
    resolve_required_choice,
)


def test_contract_version_is_stable() -> None:
    assert (
        GUIDED_MENU_INTERACTION_CONTRACT_VERSION
        == "vitrine_guided_menu_interaction_v1"
    )


def test_required_choice_zero_is_unavailable() -> None:
    resolution = resolve_required_choice(())

    assert resolution.disposition == "unavailable"
    assert resolution.selected is None
    assert resolution.choices == ()


def test_required_choice_one_carries_forward_exact_object() -> None:
    value = object()

    resolution = resolve_required_choice((value,))

    assert resolution.disposition == "carried_forward"
    assert resolution.selected is value
    assert resolution.choices == (value,)


def test_required_choice_many_requires_teacher_choice_without_ranking() -> None:
    first = object()
    second = object()

    resolution = resolve_required_choice((first, second))

    assert resolution.disposition == "requires_choice"
    assert resolution.selected is None
    assert resolution.choices == (first, second)


@pytest.mark.parametrize(
    "response",
    (
        "CONFIRM ACTION",
        "confirm action",
        "Confirm Action",
        "  confirm action  ",
    ),
)
def test_confirmation_is_case_insensitive_but_exact(response: str) -> None:
    output = StringIO()
    clear_calls: list[str] = []
    review_calls: list[str] = []

    def input_fn(prompt: str) -> str:
        assert prompt == "Confirmation: "
        return response

    def render_review() -> None:
        review_calls.append("review")
        print("Final Review", file=output)

    confirmed = confirm_exact_phrase(
        expected_phrase="CONFIRM ACTION",
        input_fn=input_fn,
        output=output,
        clear_fn=lambda: clear_calls.append("clear"),
        render_review=render_review,
    )

    assert confirmed is True
    assert clear_calls == ["clear"]
    assert review_calls == ["review"]
    assert "Confirmation not accepted." not in output.getvalue()


def test_confirmation_rejects_nonmatching_phrase_and_redraws_review() -> None:
    output = StringIO()
    clear_calls: list[str] = []
    review_calls: list[str] = []
    responses = iter(("CONFIRM", "confirm action"))

    def input_fn(prompt: str) -> str:
        assert prompt == "Confirmation: "
        return next(responses)

    def render_review() -> None:
        review_calls.append("review")
        print("Final Review", file=output)

    confirmed = confirm_exact_phrase(
        expected_phrase="CONFIRM ACTION",
        input_fn=input_fn,
        output=output,
        clear_fn=lambda: clear_calls.append("clear"),
        render_review=render_review,
    )

    assert confirmed is True
    assert clear_calls == ["clear", "clear"]
    assert review_calls == ["review", "review"]
    assert output.getvalue().count("Final Review") == 2
    assert output.getvalue().count("Confirmation not accepted.") == 1


@pytest.mark.parametrize("response", ("", "B", "b"))
def test_confirmation_blank_or_back_cancels_without_write(response: str) -> None:
    output = StringIO()

    confirmed = confirm_exact_phrase(
        expected_phrase="CONFIRM ACTION",
        input_fn=lambda _: response,
        output=output,
        clear_fn=lambda: None,
        render_review=lambda: None,
    )

    assert confirmed is False


@pytest.mark.parametrize(
    ("response", "error"),
    (
        ("M", ReturnToMainMenu),
        ("m", ReturnToMainMenu),
        ("Q", QuitPDS),
        ("q", QuitPDS),
    ),
)
def test_confirmation_preserves_core_navigation_unwinds(
    response: str,
    error: type[BaseException],
) -> None:
    output = StringIO()

    with pytest.raises(error):
        confirm_exact_phrase(
            expected_phrase="CONFIRM ACTION",
            input_fn=lambda _: response,
            output=output,
            clear_fn=lambda: None,
            render_review=lambda: None,
        )


def test_confirmation_eof_maps_to_core_quit() -> None:
    output = StringIO()

    def input_fn(_: str) -> NoReturn:
        raise EOFError

    with pytest.raises(QuitPDS):
        confirm_exact_phrase(
            expected_phrase="CONFIRM ACTION",
            input_fn=input_fn,
            output=output,
            clear_fn=lambda: None,
            render_review=lambda: None,
        )


def test_confirmation_rejects_blank_expected_phrase() -> None:
    output = StringIO()

    with pytest.raises(
        ValueError,
        match="expected_phrase must contain non-whitespace text",
    ):
        confirm_exact_phrase(
            expected_phrase="   ",
            input_fn=lambda _: "",
            output=output,
            clear_fn=lambda: None,
            render_review=lambda: None,
        )
