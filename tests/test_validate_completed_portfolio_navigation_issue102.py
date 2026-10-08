from __future__ import annotations

from scripts import validate_completed_portfolio_navigation as validator
from vitrine import released_producer_contracts as released


def test_issue102_validator_passes_without_nested_pytest() -> None:
    validator.validate(run_focused_tests=False)


def test_issue102_current_release_anchors_are_exact() -> None:
    assert released.CORE_0_6_4_AUDIT.release_version == "0.6.4"
    assert released.SCOREFORM_0_12_0_AUDIT.release_version == "0.12.0"
    assert released.QUILLAN_0_10_5_AUDIT.release_version == "0.10.5"
    assert released.CONCORD_0_3_0_AUDIT.release_version == "0.3.0"


def test_issue102_package_and_repository_wiring_is_complete() -> None:
    validator._validate_package_boundary()
    validator._validate_release_anchors()
