from __future__ import annotations

from scripts.validate_selection_placement_guidance import validate


def test_selection_placement_guidance_validator_without_nested_pytest() -> None:
    validate(run_focused_tests=False)
