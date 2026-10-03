from __future__ import annotations

from scripts import validate_path_output_naming as validator
from scripts import verify_core_wheel


def test_issue111_validator_passes_without_nested_pytest() -> None:
    validator.validate(run_focused_tests=False)


def test_issue111_core_qualification_is_exact_released_064() -> None:
    assert verify_core_wheel.EXPECTED_CORE_VERSION == "0.6.4"
    assert (
        verify_core_wheel.EXPECTED_CORE_WHEEL_FILENAME
        == "pds_core-0.6.4-py3-none-any.whl"
    )
    assert verify_core_wheel.EXPECTED_CORE_WHEEL_SHA256 == (
        "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
    )


def test_issue111_keeps_vitrine_core_dependency_floor_at_063() -> None:
    validator._validate_package_boundary()


def test_issue111_ci_uses_064_without_rewriting_frozen_issue71() -> None:
    validator._validate_ci_qualification_anchor()
