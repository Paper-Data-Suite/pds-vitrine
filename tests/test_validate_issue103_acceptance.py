from __future__ import annotations

import scripts.validate_issue103_acceptance as validator
import scripts.validate_repository as repository_validator


def test_issue103_static_acceptance_validation_passes() -> None:
    validator.validate(run_focused_tests=False)


def test_issue103_focused_inventory_covers_required_journey_surfaces() -> None:
    assert validator.FOCUSED_TESTS == (
        "tests/test_portfolio_completion_issue103.py",
        "tests/test_attention_completion_issue103.py",
        "tests/test_attention_menu.py",
        "tests/test_issue103_reader_contract_compatibility.py",
        "tests/test_issue103_release_baseline.py",
        "tests/test_released_producer_contracts.py",
        "tests/test_producer_reader_services.py",
        "tests/test_scoreform_adapter.py",
    )


def test_repository_gate_runs_issue103_without_nested_pytest() -> None:
    commands = dict(repository_validator.VALIDATOR_COMMANDS)
    assert commands["issue #103 completion / reader compatibility"] == (
        "scripts/validate_issue103_acceptance.py",
        "--skip-focused-tests",
    )
