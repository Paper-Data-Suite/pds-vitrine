from __future__ import annotations

from scripts.validate_paper_reflection import validate


def test_issue99_paper_reflection_validation_wiring() -> None:
    validate(run_focused_tests=False)
