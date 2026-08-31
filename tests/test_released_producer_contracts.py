from __future__ import annotations

from dataclasses import replace

import pytest

from vitrine.development_adapters import (
    CONCORD_FIXTURE_SUPPORT_KEY,
    QUILLAN_FIXTURE_SUPPORT_KEY,
    SCOREFORM_FIXTURE_SUPPORT_KEY,
)
from vitrine.producer_adapters import (
    ProducerAdapterSupportKey,
    ProducerAdapterSupportRequest,
    build_adapter_registry,
)
from vitrine.released_producer_contracts import (
    CONCORD_0_3_0_AUDIT,
    CONCORD_LIVE_SUPPORT_KEY,
    CORE_0_6_3_AUDIT,
    LIVE_PRODUCER_SUPPORT_KEYS,
    QUILLAN_0_10_0_AUDIT,
    QUILLAN_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    RELEASED_PRODUCER_CONTRACTS,
    SCOREFORM_0_11_0_AUDIT,
    SCOREFORM_LIVE_SUPPORT_KEY,
)


def _request(
    key: ProducerAdapterSupportKey,
    *,
    capabilities: tuple[str, ...] | None = None,
) -> ProducerAdapterSupportRequest:
    return ProducerAdapterSupportRequest(
        producer_module_id=key.producer_module_id,
        core_publication_schema_version=key.core_publication_schema_version,
        publication_kind=key.publication_kind,
        manifest_contract_version=key.manifest_contract_version,
        producer_contract_version=key.producer_contract_version,
        source_record_kind=key.source_record_kind,
        source_record_contract_version=key.source_record_contract_version,
        capabilities=(
            key.required_capabilities if capabilities is None else capabilities
        ),
    )


def test_release_audit_pins_exact_phase_1_wheels() -> None:
    assert CORE_0_6_3_AUDIT.wheel_filename == "pds_core-0.6.3-py3-none-any.whl"
    assert (
        CORE_0_6_3_AUDIT.wheel_sha256
        == "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5"
    )
    assert SCOREFORM_0_11_0_AUDIT.wheel_filename == "scoreform-0.11.0-py3-none-any.whl"
    assert (
        SCOREFORM_0_11_0_AUDIT.wheel_sha256
        == "8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44"
    )
    assert QUILLAN_0_10_0_AUDIT.wheel_filename == "quillan-0.10.0-py3-none-any.whl"
    assert (
        QUILLAN_0_10_0_AUDIT.wheel_sha256
        == "5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9"
    )
    assert CONCORD_0_3_0_AUDIT.wheel_filename == "pds_concord-0.3.0-py3-none-any.whl"
    assert (
        CONCORD_0_3_0_AUDIT.wheel_sha256
        == "dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12"
    )


def test_release_audit_catalog_is_deterministic_and_complete() -> None:
    assert [item.producer_module_id for item in RELEASED_PRODUCER_CONTRACTS] == [
        "concord",
        "quillan",
        "scoreform",
    ]
    assert set(RELEASED_PRODUCER_CONTRACT_BY_MODULE) == {
        "scoreform",
        "quillan",
        "concord",
    }
    assert LIVE_PRODUCER_SUPPORT_KEYS == tuple(
        item.support_key for item in RELEASED_PRODUCER_CONTRACTS
    )


def test_release_versions_are_audit_provenance_not_support_key_fields() -> None:
    for audit in RELEASED_PRODUCER_CONTRACTS:
        assert audit.release_version
        assert audit.release_tag.startswith("v")
        assert not hasattr(audit.support_key, "release_version")
        assert not hasattr(audit.support_key, "distribution_name")
        assert not hasattr(audit.support_key, "wheel_sha256")


def test_scoreform_live_key_matches_only_full_released_capability_contract() -> None:
    exact = _request(
        SCOREFORM_LIVE_SUPPORT_KEY,
        capabilities=("question_evidence", "points", "multiple_attempts"),
    )
    assert SCOREFORM_LIVE_SUPPORT_KEY.matches(exact)

    for missing in SCOREFORM_LIVE_SUPPORT_KEY.required_capabilities:
        reduced = tuple(
            value
            for value in SCOREFORM_LIVE_SUPPORT_KEY.required_capabilities
            if value != missing
        )
        assert not SCOREFORM_LIVE_SUPPORT_KEY.matches(
            _request(SCOREFORM_LIVE_SUPPORT_KEY, capabilities=reduced)
        )


def test_quillan_live_key_requires_missing_publication_source_record() -> None:
    exact = _request(QUILLAN_LIVE_SUPPORT_KEY)
    assert exact.source_record_kind is None
    assert QUILLAN_LIVE_SUPPORT_KEY.matches(exact)

    registration_source_substitution = replace(
        exact,
        source_record_kind="assignment",
        source_record_contract_version="2",
    )
    assert not QUILLAN_LIVE_SUPPORT_KEY.matches(registration_source_substitution)


def test_concord_live_key_requires_activity_but_allows_conditional_capabilities() -> None:
    assert CONCORD_LIVE_SUPPORT_KEY.source_record_kind == "activity"
    assert CONCORD_LIVE_SUPPORT_KEY.source_record_contract_version == "concord_activity_v1"

    for capabilities in (
        ("criterion_scores",),
        ("criterion_scores", "standards_ratings"),
        ("criterion_scores", "moderated_scores"),
        ("criterion_scores", "standards_ratings", "moderated_scores"),
    ):
        assert CONCORD_LIVE_SUPPORT_KEY.matches(
            _request(CONCORD_LIVE_SUPPORT_KEY, capabilities=capabilities)
        )

    assert not CONCORD_LIVE_SUPPORT_KEY.matches(
        _request(CONCORD_LIVE_SUPPORT_KEY, capabilities=("standards_ratings",))
    )
    assert not CONCORD_LIVE_SUPPORT_KEY.matches(
        replace(_request(CONCORD_LIVE_SUPPORT_KEY), source_record_kind=None, source_record_contract_version=None)
    )


def test_near_future_contracts_do_not_fall_back_to_v1() -> None:
    cases = (
        replace(
            _request(SCOREFORM_LIVE_SUPPORT_KEY),
            manifest_contract_version="scoreform_academic_result_manifest_v2",
        ),
        replace(
            _request(QUILLAN_LIVE_SUPPORT_KEY),
            producer_contract_version="quillan_academic_work_v2",
        ),
        replace(
            _request(CONCORD_LIVE_SUPPORT_KEY),
            source_record_contract_version="concord_activity_v2",
        ),
        replace(
            _request(CONCORD_LIVE_SUPPORT_KEY),
            core_publication_schema_version="2",
        ),
    )
    keys = (
        SCOREFORM_LIVE_SUPPORT_KEY,
        QUILLAN_LIVE_SUPPORT_KEY,
        CONCORD_LIVE_SUPPORT_KEY,
        CONCORD_LIVE_SUPPORT_KEY,
    )
    for key, request in zip(keys, cases, strict=True):
        assert not key.matches(request)


def test_fixture_and_live_support_identities_remain_disjoint() -> None:
    assert SCOREFORM_LIVE_SUPPORT_KEY != SCOREFORM_FIXTURE_SUPPORT_KEY
    assert QUILLAN_LIVE_SUPPORT_KEY != QUILLAN_FIXTURE_SUPPORT_KEY
    assert CONCORD_LIVE_SUPPORT_KEY != CONCORD_FIXTURE_SUPPORT_KEY
    assert {item.producer_module_id for item in LIVE_PRODUCER_SUPPORT_KEYS}.isdisjoint(
        {
            SCOREFORM_FIXTURE_SUPPORT_KEY.producer_module_id,
            QUILLAN_FIXTURE_SUPPORT_KEY.producer_module_id,
            CONCORD_FIXTURE_SUPPORT_KEY.producer_module_id,
        }
    )


def test_audited_contract_catalog_does_not_activate_live_adapters() -> None:
    assert build_adapter_registry().adapters == ()


def test_artifact_access_is_separate_from_manifest_support() -> None:
    assert SCOREFORM_0_11_0_AUDIT.artifact_access_mode == "none"
    assert SCOREFORM_0_11_0_AUDIT.artifact_reader_module is None

    assert QUILLAN_0_10_0_AUDIT.artifact_access_mode == "producer_authorized_bytes"
    assert QUILLAN_0_10_0_AUDIT.artifact_reader_module == "quillan.academic_result_artifacts"
    assert QUILLAN_0_10_0_AUDIT.artifact_authorization_outcomes == (
        "allowed",
        "denied",
        "unresolved",
    )

    assert CONCORD_0_3_0_AUDIT.artifact_access_mode == "producer_authorized_bytes"
    assert CONCORD_0_3_0_AUDIT.artifact_reader_module == "concord.academic_result_artifacts"
    assert CONCORD_0_3_0_AUDIT.artifact_representation_kinds == (
        "returned_artifact_pdf",
    )


def test_release_audit_records_exact_public_reader_boundaries() -> None:
    assert SCOREFORM_0_11_0_AUDIT.public_reader_module == "scoreform.academic_result_reader"
    assert QUILLAN_0_10_0_AUDIT.public_reader_module == "quillan.academic_result_reader"
    assert CONCORD_0_3_0_AUDIT.public_reader_module == "concord.academic_result_reader"
    assert {
        audit.public_reader_symbol for audit in RELEASED_PRODUCER_CONTRACTS
    } == {"read_academic_result_manifest"}


def test_audit_dataclass_rejects_invalid_hash_on_replacement() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        replace(SCOREFORM_0_11_0_AUDIT, wheel_sha256="not-a-digest")
