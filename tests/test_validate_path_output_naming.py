from __future__ import annotations

from scripts import validate_path_output_naming as validator
from scripts import verify_core_wheel


def test_issue111_validator_passes_without_nested_pytest() -> None:
    validator.validate(run_focused_tests=False)


def test_issue103_advances_issue111_core_qualification_to_released_065() -> None:
    assert verify_core_wheel.EXPECTED_CORE_VERSION == "0.6.5"
    assert (
        verify_core_wheel.EXPECTED_CORE_WHEEL_FILENAME
        == "pds_core-0.6.5-py3-none-any.whl"
    )
    assert verify_core_wheel.EXPECTED_CORE_WHEEL_SHA256 == (
        "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
    )


def test_issue111_keeps_vitrine_core_dependency_floor_at_063() -> None:
    validator._validate_package_boundary()


def test_issue111_ci_uses_064_without_rewriting_frozen_issue71() -> None:
    validator._validate_ci_qualification_anchor()
