"""Validate Issue #98 guided menu interaction standardization."""

from __future__ import annotations

import argparse
import subprocess
import sys
from io import StringIO
from pathlib import Path

from vitrine.menu_interactions import (
    GUIDED_MENU_INTERACTION_CONTRACT_VERSION,
    confirm_exact_phrase,
    resolve_required_choice,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_menu_interactions.py",
    "tests/test_candidate_review_menu.py",
    "tests/test_candidate_discovery_menu.py",
    "tests/test_portfolio_setup_menu.py",
    "tests/test_working_composition_menu.py",
    "tests/test_current_portfolio_menu.py",
    "tests/test_portfolio_menu.py",
    "tests/test_profile_menu.py",
    "tests/test_subject_menu.py",
    "tests/test_menu.py",
)

REQUIRED_DOCS = (
    "docs/contracts/guided-menu-interactions-v1.md",
    "docs/development/guided-menu-interactions.md",
    "docs/validation/issue-98-guided-menu-interactions-validation.md",
)

ACTIVE_SURFACE_MARKERS: dict[str, tuple[str, ...]] = {
    "vitrine/candidate_review_menu.py": (
        "confirm_exact_phrase(",
        "resolve_required_choice(",
    ),
    "vitrine/portfolio_menu.py": (
        "confirm_exact_phrase(",
        "resolve_required_choice(",
        "Review Candidates now",
    ),
    "vitrine/portfolio_setup_menu.py": (
        "confirm_exact_phrase(",
        "Opening this Portfolio now.",
    ),
    "vitrine/working_composition_menu.py": (
        "confirm_exact_phrase(",
        'expected_phrase="FREEZE COMPOSITION"',
    ),
    "vitrine/current_portfolio_menu.py": (
        "confirm_exact_phrase(",
        "resolve_required_choice(",
        "handle_review_action=",
    ),
    "vitrine/profile_menu.py": (
        "confirm_exact_phrase(",
        "ReviewRenderer",
    ),
    "vitrine/subject_menu.py": (
        "confirm_exact_phrase(",
        "ReviewRenderer",
    ),
    "vitrine/menu.py": (
        "confirm_exact_phrase(",
        "ReviewRenderer",
    ),
}


def _require_text(path: Path, *markers: str) -> None:
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing required #98 marker: {marker}"
            )


def _validate_interaction_contract() -> None:
    if (
        GUIDED_MENU_INTERACTION_CONTRACT_VERSION
        != "vitrine_guided_menu_interaction_v1"
    ):
        raise RuntimeError("guided-menu interaction contract identity changed")

    empty_choices: tuple[object, ...] = ()
    unavailable = resolve_required_choice(empty_choices)
    if unavailable.disposition != "unavailable" or unavailable.selected is not None:
        raise RuntimeError("zero-choice guided-menu contract changed")

    exact = object()
    carried = resolve_required_choice((exact,))
    if carried.disposition != "carried_forward" or carried.selected is not exact:
        raise RuntimeError("one-choice guided-menu identity contract changed")

    first = object()
    second = object()
    multiple = resolve_required_choice((first, second))
    if multiple.disposition != "requires_choice" or multiple.selected is not None:
        raise RuntimeError("multi-choice guided-menu contract changed")
    if multiple.choices != (first, second):
        raise RuntimeError("multi-choice guided-menu ordering changed")

    output = StringIO()
    clear_calls: list[str] = []
    review_calls: list[str] = []
    responses = iter(("WRONG", "confirm action"))

    def render_review() -> None:
        review_calls.append("review")
        print("Current Review", file=output)

    confirmed = confirm_exact_phrase(
        expected_phrase="CONFIRM ACTION",
        input_fn=lambda _prompt: next(responses),
        output=output,
        clear_fn=lambda: clear_calls.append("clear"),
        render_review=render_review,
    )
    if not confirmed:
        raise RuntimeError("case-insensitive exact confirmation contract changed")
    if clear_calls != ["clear", "clear"] or review_calls != ["review", "review"]:
        raise RuntimeError("confirmation clear/redraw retry contract changed")
    if "Confirmation not accepted." not in output.getvalue():
        raise RuntimeError("confirmation mismatch feedback contract changed")

    output = StringIO()
    responses = iter(("T", "CONFIRM ACTION"))
    action_calls: list[str] = []

    def handle_review_action(value: str) -> bool:
        action_calls.append(value)
        return value.casefold() == "t"

    confirmed = confirm_exact_phrase(
        expected_phrase="CONFIRM ACTION",
        input_fn=lambda _prompt: next(responses),
        output=output,
        clear_fn=lambda: None,
        render_review=lambda: None,
        handle_review_action=handle_review_action,
    )
    if not confirmed or action_calls != ["T"]:
        raise RuntimeError("confirmation review-action contract changed")
    if "Confirmation not accepted." in output.getvalue():
        raise RuntimeError("review action was misclassified as confirmation mismatch")


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_interaction_contract()

    interaction_path = ROOT / "vitrine" / "menu_interactions.py"
    _require_text(
        interaction_path,
        'GUIDED_MENU_INTERACTION_CONTRACT_VERSION = "vitrine_guided_menu_interaction_v1"',
        "class RequiredChoiceResolution",
        "def resolve_required_choice(",
        "def confirm_exact_phrase(",
        "Confirmation not accepted.",
        "handle_review_action",
        "parse_navigation_choice(",
    )

    for relative, markers in ACTIVE_SURFACE_MARKERS.items():
        _require_text(ROOT / relative, *markers)

    portfolio_source = (ROOT / "vitrine" / "portfolio_menu.py").read_text(
        encoding="utf-8"
    )
    if portfolio_source.count("_curation_workflow(") != 1:
        raise RuntimeError(
            "legacy Portfolio curation helper unexpectedly became reachable or changed"
        )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #98 documentation: {relative}")

    package_check = ROOT / "scripts" / "check_package.py"
    _require_text(
        package_check,
        '"vitrine/menu_interactions.py"',
        '"docs/contracts/guided-menu-interactions-v1.md"',
        '"docs/development/guided-menu-interactions.md"',
        '"docs/validation/issue-98-guided-menu-interactions-validation.md"',
        '"scripts/validate_guided_menu_interactions.py"',
        '"scripts/smoke_test_guided_menu_interactions_wheel.py"',
        '"tests/test_validate_guided_menu_interactions.py"',
    )

    repository_validator = ROOT / "scripts" / "validate_repository.py"
    _require_text(
        repository_validator,
        "scripts/validate_guided_menu_interactions.py",
        "scripts/smoke_test_guided_menu_interactions_wheel.py",
    )

    pyproject = ROOT / "pyproject.toml"
    _require_text(
        pyproject,
        '"scripts/validate_guided_menu_interactions.py"',
        '"scripts/smoke_test_guided_menu_interactions_wheel.py"',
    )

    docs_index = ROOT / "docs" / "README.md"
    _require_text(
        docs_index,
        "contracts/guided-menu-interactions-v1.md",
        "development/guided-menu-interactions.md",
        "validation/issue-98-guided-menu-interactions-validation.md",
    )

    if run_focused_tests:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", *FOCUSED_TESTS, "-q"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                f"guided-menu interaction focused validation failed: {detail}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-focused-tests",
        action="store_true",
        help=(
            "Skip focused pytest when an enclosing repository gate already ran "
            "the complete suite."
        ),
    )
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS guided-menu interaction validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Guided-menu interaction validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
