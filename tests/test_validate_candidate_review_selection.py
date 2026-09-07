from __future__ import annotations

from scripts.validate_candidate_review_selection import validate


def test_candidate_review_selection_validator_contract_checks_without_nested_pytest() -> None:
    validate(run_focused_tests=False)
