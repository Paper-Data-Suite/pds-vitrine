from __future__ import annotations

from scripts import validate_portfolio_presentation as validator
from scripts import verify_core_wheel


def test_issue101_validator_passes_without_nested_pytest() -> None:
    validator.validate(run_focused_tests=False)


def test_issue101_qualifies_against_exact_released_core_064() -> None:
    assert verify_core_wheel.EXPECTED_CORE_VERSION == "0.6.4"
    assert (
        verify_core_wheel.EXPECTED_CORE_WHEEL_FILENAME
        == "pds_core-0.6.4-py3-none-any.whl"
    )
    assert verify_core_wheel.EXPECTED_CORE_WHEEL_SHA256 == (
        "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
    )


def test_issue101_package_and_repository_wiring_is_complete() -> None:
    validator._validate_package_boundary()
    validator._validate_core_qualification()
