from __future__ import annotations

from scripts.validate_guided_menu_interactions import validate


def test_guided_menu_interaction_validator_without_nested_pytest() -> None:
    validate(run_focused_tests=False)
