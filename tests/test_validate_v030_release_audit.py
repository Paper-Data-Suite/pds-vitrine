from __future__ import annotations

from scripts import validate_v030_release_audit as validator


def test_v030_substantive_release_audit_validator_passes() -> None:
    validator.validate()


def test_v030_all_accepted_adrs_are_guarded() -> None:
    assert tuple(label for label, _ in validator.ADR_FILES) == tuple(
        f"ADR 000{number}" for number in range(1, 10)
    )


def test_v030_milestone_implementation_issues_are_guarded() -> None:
    assert validator.MILESTONE_ISSUES == tuple(range(57, 72))


def test_v030_substantive_audit_state_is_not_final_release_state() -> None:
    assert (
        validator.EXPECTED_AUDIT_STATE
        == "substantive_audit_complete_release_qualification_pending"
    )
