from __future__ import annotations

from scripts.validate_portfolio_setup import validate


def test_portfolio_setup_validator_contract_checks_without_nested_pytest() -> None:
    validate(run_focused_tests=False)
