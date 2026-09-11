from __future__ import annotations

from scripts.validate_suite_operations_integration import validate


def test_suite_operations_integration_contract_is_frozen() -> None:
    validate(run_focused_tests=False)
