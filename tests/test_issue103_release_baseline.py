from __future__ import annotations

from vitrine.released_producer_contracts import (
    CONCORD_0_3_0_AUDIT,
    CONCORD_0_3_1_AUDIT,
    CONCORD_0_3_2_AUDIT,
    CONCORD_LIVE_SUPPORT_KEY,
    CORE_0_6_4_AUDIT,
    CORE_0_6_5_AUDIT,
    QUILLAN_0_10_5_AUDIT,
    QUILLAN_0_10_6_AUDIT,
    QUILLAN_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    SCOREFORM_0_12_0_AUDIT,
    SCOREFORM_0_12_1_AUDIT,
    SCOREFORM_0_13_0_AUDIT,
    SCOREFORM_LIVE_SUPPORT_KEY,
)


def test_issue103_refreshes_current_core_release_anchor() -> None:
    assert CORE_0_6_5_AUDIT.release_version == "0.6.5"
    assert CORE_0_6_5_AUDIT.release_tag == "v0.6.5"
    assert CORE_0_6_5_AUDIT.wheel_filename == (
        "pds_core-0.6.5-py3-none-any.whl"
    )
    assert (
        CORE_0_6_5_AUDIT.wheel_sha256
        == "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
    )
    assert CORE_0_6_4_AUDIT.release_version == "0.6.4"


def test_issue103_activates_current_metadata_bearing_producer_releases() -> None:
    expected = {
        "scoreform": (
            SCOREFORM_0_13_0_AUDIT,
            "0.13.0",
            "scoreform-0.13.0-py3-none-any.whl",
            "4a4d158fda6e899f1835f3312ca8291622e2b1c7da219b349adf5e88b9b7c9b7",
        ),
        "quillan": (
            QUILLAN_0_10_6_AUDIT,
            "0.10.6",
            "quillan-0.10.6-py3-none-any.whl",
            "7dbe975c969e60cfda9a8489154450f95c4dc58a8d75afcfad92e7a3c026afbb",
        ),
        "concord": (
            CONCORD_0_3_2_AUDIT,
            "0.3.2",
            "pds_concord-0.3.2-py3-none-any.whl",
            "825b27bc6142cc8bce8c3b9381a3337c4a55e983f6f3f2e7e4b1a10f980e83ce",
        ),
    }
    for module_id, (audit, version, wheel, digest) in expected.items():
        assert RELEASED_PRODUCER_CONTRACT_BY_MODULE[module_id] is audit
        assert audit.release_version == version
        assert audit.release_tag == f"v{version}"
        assert audit.wheel_filename == wheel
        assert audit.wheel_sha256 == digest
        assert audit.core_requirement == "pds-core>=0.6.5,<0.7"


def test_issue103_preserves_historical_release_evidence() -> None:
    assert SCOREFORM_0_12_0_AUDIT.release_version == "0.12.0"
    assert SCOREFORM_0_12_1_AUDIT.release_version == "0.12.1"
    assert QUILLAN_0_10_5_AUDIT.release_version == "0.10.5"
    assert CONCORD_0_3_0_AUDIT.release_version == "0.3.0"
    assert CONCORD_0_3_1_AUDIT.release_version == "0.3.1"
    assert (
        CONCORD_0_3_1_AUDIT.wheel_sha256
        == "c9b95b1a543b4e74f5ed5ca339e3aad68d180df4082e7c0f0b5b840d7dc8e47b"
    )


def test_issue103_release_refresh_does_not_change_semantic_support_keys() -> None:
    assert SCOREFORM_0_12_1_AUDIT.support_key is SCOREFORM_LIVE_SUPPORT_KEY
    assert SCOREFORM_0_13_0_AUDIT.support_key is SCOREFORM_LIVE_SUPPORT_KEY
    assert QUILLAN_0_10_5_AUDIT.support_key is QUILLAN_LIVE_SUPPORT_KEY
    assert QUILLAN_0_10_6_AUDIT.support_key is QUILLAN_LIVE_SUPPORT_KEY
    assert CONCORD_0_3_1_AUDIT.support_key is CONCORD_LIVE_SUPPORT_KEY
    assert CONCORD_0_3_2_AUDIT.support_key is CONCORD_LIVE_SUPPORT_KEY
    assert not hasattr(SCOREFORM_LIVE_SUPPORT_KEY, "release_version")
    assert not hasattr(QUILLAN_LIVE_SUPPORT_KEY, "release_version")
    assert not hasattr(CONCORD_LIVE_SUPPORT_KEY, "release_version")
