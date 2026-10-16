from __future__ import annotations

from scripts import validate_path_output_naming as validator
from scripts import verify_core_wheel


def test_issue111_validator_passes_without_nested_pytest() -> None:
    validator.validate(run_focused_tests=False)


def test_issue103_advances_issue111_core_qualification_to_released_066() -> None:
    assert verify_core_wheel.EXPECTED_CORE_VERSION == "0.6.6"
    assert (
        verify_core_wheel.EXPECTED_CORE_WHEEL_FILENAME
        == "pds_core-0.6.6-py3-none-any.whl"
    )
    assert verify_core_wheel.EXPECTED_CORE_WHEEL_SHA256 == (
        "d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301"
    )


def test_issue111_keeps_vitrine_core_dependency_floor_at_063() -> None:
    validator._validate_package_boundary()


def test_issue111_ci_uses_064_without_rewriting_frozen_issue71() -> None:
    validator._validate_ci_qualification_anchor()
