from __future__ import annotations

from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    SCOREFORM_0_12_0_AUDIT,
    SCOREFORM_0_12_1_AUDIT,
    SCOREFORM_LIVE_SUPPORT_KEY,
)


def test_issue103_refreshes_current_scoreform_release_anchor() -> None:
    assert SCOREFORM_0_12_1_AUDIT.release_version == "0.12.1"
    assert SCOREFORM_0_12_1_AUDIT.release_tag == "v0.12.1"
    assert SCOREFORM_0_12_1_AUDIT.wheel_filename == (
        "scoreform-0.12.1-py3-none-any.whl"
    )
    assert (
        SCOREFORM_0_12_1_AUDIT.wheel_sha256
        == "0f71b709eafe351052eac3e4f0d474b7bef36aeec347df05361b0a8995d44d32"
    )
    assert SCOREFORM_0_12_1_AUDIT.core_requirement == "pds-core>=0.6.4,<0.7"
    assert RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"] is SCOREFORM_0_12_1_AUDIT


def test_issue103_preserves_issue102_scoreform_release_evidence() -> None:
    assert SCOREFORM_0_12_0_AUDIT.release_version == "0.12.0"
    assert SCOREFORM_0_12_0_AUDIT.release_tag == "v0.12.0"
    assert SCOREFORM_0_12_0_AUDIT.wheel_filename == (
        "scoreform-0.12.0-py3-none-any.whl"
    )
    assert (
        SCOREFORM_0_12_0_AUDIT.wheel_sha256
        == "84ad10ada72a99bebd5455d8c18a0725f9406f8279e57156f3e424efa5678d20"
    )
    assert SCOREFORM_0_12_0_AUDIT is not SCOREFORM_0_12_1_AUDIT


def test_issue103_release_refresh_does_not_change_scoreform_semantic_support() -> None:
    assert SCOREFORM_0_12_0_AUDIT.support_key is SCOREFORM_LIVE_SUPPORT_KEY
    assert SCOREFORM_0_12_1_AUDIT.support_key is SCOREFORM_LIVE_SUPPORT_KEY
    assert SCOREFORM_0_12_1_AUDIT.public_reader_module == (
        "scoreform.academic_result_reader"
    )
    assert SCOREFORM_0_12_1_AUDIT.public_reader_symbol == (
        "read_academic_result_manifest"
    )
    assert SCOREFORM_0_12_1_AUDIT.artifact_access_mode == "none"
    assert not hasattr(SCOREFORM_LIVE_SUPPORT_KEY, "release_version")
