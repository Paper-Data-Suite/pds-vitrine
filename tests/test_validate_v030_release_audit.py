from __future__ import annotations

from scripts import validate_v030_release_audit as validator


def test_v030_final_release_audit_validator_passes() -> None:
    validator.validate()


def test_v030_all_accepted_adrs_are_guarded() -> None:
    assert tuple(label for label, _ in validator.ADR_FILES) == tuple(
        f"ADR 000{number}" for number in range(1, 10)
    )


def test_v030_milestone_issues_are_guarded() -> None:
    assert validator.MILESTONE_ISSUES == tuple(range(57, 73))


def test_v030_final_audit_state_and_release_evidence_are_frozen() -> None:
    assert validator.EXPECTED_AUDIT_STATE == "released_verified"
    assert validator.EXPECTED_RELEASE_VERDICT == "RELEASED — VERIFIED"
    assert validator.EXPECTED_RELEASE_COMMIT == "27d28933c645cea1d57b5504362e8798eacee8fe"
    assert validator.EXPECTED_RELEASE_TREE == "9c6081f07a4e72098e1c8c7e0897f8ab87cb6710"
    assert validator.EXPECTED_TAG_OBJECT == "547527b083fcb0b302f1870906ab4434462f4f74"
    assert validator.EXPECTED_WHEEL_SHA256 == (
        "69d2d1ea8a90b5d25c813da3c852232a0e0a9e7094e2b4d217f22662022596b8"
    )
    assert validator.EXPECTED_SDIST_SHA256 == (
        "e93ee5d9e8d706c29923b3ee8e38b37574873d5f2dd87e3dcd9e67e4713389b9"
    )
    assert validator.EXPECTED_SUMS_SHA256 == (
        "cb62552f07cee5540b25d8d9392106f915ddbdfcbf7d9b9ae7fa57ef1f2b54e5"
    )
