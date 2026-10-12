from __future__ import annotations

from scripts import validate_portfolio_presentation as validator
from scripts import verify_core_wheel


def test_issue101_validator_passes_without_nested_pytest() -> None:
    validator.validate(run_focused_tests=False)


def test_issue103_advances_issue101_qualification_to_released_core_065() -> None:
    assert verify_core_wheel.EXPECTED_CORE_VERSION == "0.6.5"
    assert (
        verify_core_wheel.EXPECTED_CORE_WHEEL_FILENAME
        == "pds_core-0.6.5-py3-none-any.whl"
    )
    assert verify_core_wheel.EXPECTED_CORE_WHEEL_SHA256 == (
        "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
    )


def test_issue101_package_and_repository_wiring_is_complete() -> None:
    validator._validate_package_boundary()
    validator._validate_core_qualification()
