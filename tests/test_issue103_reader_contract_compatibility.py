from __future__ import annotations

from types import SimpleNamespace

import pytest
from pds_core.publication_compatibility import (
    PublicationContractSupport,
    PublicationProducerProfile,
    PublicationReaderSupport,
)

import vitrine.producer_reader_compatibility as compatibility
import vitrine.producer_reader_services as reader_services
from vitrine.producer_adapters import ProducerReaderError
from vitrine.producer_reader_compatibility import (
    LEGACY_INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
    VITRINE_LEGACY_EXACT_PRODUCER_RELEASES,
    VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS,
    normalize_persisted_reader_contract_version,
    resolve_installed_producer_reader_compatibility,
)
from vitrine.producer_reader_services import (
    build_audited_installed_producer_reader,
)
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    SCOREFORM_0_11_0_AUDIT,
)


def _profile(
    producer_module_id: str,
    *,
    reader_contract_version: str | None,
    distribution_name: str | None = None,
) -> PublicationProducerProfile:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE[producer_module_id]
    key = audit.support_key
    reader_support = ()
    if reader_contract_version is not None:
        reader_support = (
            PublicationReaderSupport(
                manifest_contract_version=key.manifest_contract_version,
                distribution_name=distribution_name or audit.distribution_name,
                reader_contract_version=reader_contract_version,
            ),
        )
    return PublicationProducerProfile(
        module_id=producer_module_id,
        display_name=f"{producer_module_id.title()} Test Producer",
        supported_core_publication_schema_versions=frozenset(
            {key.core_publication_schema_version}
        ),
        supported_academic_work_contract_versions=frozenset(
            {key.producer_contract_version}
            if key.producer_contract_version is not None
            else ()
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind=key.publication_kind,
                manifest_contract_versions=frozenset(
                    {key.manifest_contract_version}
                ),
                supported_capabilities=frozenset(
                    audit.advertised_capabilities
                ),
                reader_support=reader_support,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("producer_module_id", "expected"),
    (
        ("scoreform", "scoreform_academic_result_reader_v1"),
        ("quillan", "quillan_academic_result_reader_v1"),
        ("concord", "concord_academic_result_reader_v1"),
    ),
)
def test_reader_descriptor_uses_producer_owned_contract(
    producer_module_id: str,
    expected: str,
) -> None:
    reader = build_audited_installed_producer_reader(producer_module_id)

    assert reader.descriptor.reader_contract_version == expected
    assert VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS[
        producer_module_id
    ] == frozenset({expected})


def test_future_package_same_reader_contract_is_accepted() -> None:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]
    supported = "scoreform_academic_result_reader_v1"

    result = resolve_installed_producer_reader_compatibility(
        audit,
        installed_distribution_version="99.123.456",
        profiles=(
            _profile(
                "scoreform",
                reader_contract_version=supported,
            ),
        ),
    )

    assert result.compatibility_basis == "declared_reader_contract"
    assert result.installed_distribution_version == "99.123.456"
    assert result.reader_contract_version == supported


def test_same_manifest_unsupported_reader_contract_is_rejected() -> None:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]

    with pytest.raises(
        compatibility.InstalledProducerReaderCompatibilityError
    ) as caught:
        resolve_installed_producer_reader_compatibility(
            audit,
            installed_distribution_version="99.123.456",
            profiles=(
                _profile(
                    "scoreform",
                    reader_contract_version="scoreform_future_reader_v2",
                ),
            ),
        )

    assert caught.value.code == "reader.incompatible"
    assert caught.value.stage == "reader_contract"


def test_exact_legacy_release_is_supported_without_reader_metadata() -> None:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]
    exact = next(
        iter(VITRINE_LEGACY_EXACT_PRODUCER_RELEASES["scoreform"])
    )

    result = resolve_installed_producer_reader_compatibility(
        audit,
        installed_distribution_version=exact,
        profiles=(),
    )

    assert result.compatibility_basis == "legacy_exact_release"
    assert (
        result.reader_contract_version
        == "scoreform_academic_result_reader_v1"
    )


def test_old_exact_historical_scoreform_release_remains_supported() -> None:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]

    result = resolve_installed_producer_reader_compatibility(
        audit,
        installed_distribution_version=SCOREFORM_0_11_0_AUDIT.release_version,
        profiles=(),
    )

    assert result.compatibility_basis == "legacy_exact_release"
    assert (
        result.reader_contract_version
        == "scoreform_academic_result_reader_v1"
    )


def test_current_metadata_bearing_releases_are_not_legacy_fallbacks() -> None:
    for module_id, audit in RELEASED_PRODUCER_CONTRACT_BY_MODULE.items():
        assert (
            audit.release_version
            not in VITRINE_LEGACY_EXACT_PRODUCER_RELEASES[module_id]
        )


def test_metadata_absent_future_release_is_not_guessed_compatible() -> None:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]

    with pytest.raises(
        compatibility.InstalledProducerReaderCompatibilityError
    ) as caught:
        resolve_installed_producer_reader_compatibility(
            audit,
            installed_distribution_version="0.12.2",
            profiles=(
                _profile(
                    "scoreform",
                    reader_contract_version=None,
                ),
            ),
        )

    assert caught.value.code == "reader.incompatible"


def test_declared_reader_distribution_must_match_reader_binding() -> None:
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["concord"]

    with pytest.raises(
        compatibility.InstalledProducerReaderCompatibilityError
    ):
        resolve_installed_producer_reader_compatibility(
            audit,
            installed_distribution_version="99.0.0",
            profiles=(
                _profile(
                    "concord",
                    reader_contract_version=(
                        "concord_academic_result_reader_v1"
                    ),
                    distribution_name="wrong-concord",
                ),
            ),
        )


@pytest.mark.parametrize(
    ("producer_module_id", "stable"),
    (
        ("scoreform", "scoreform_academic_result_reader_v1"),
        ("quillan", "quillan_academic_result_reader_v1"),
        ("concord", "concord_academic_result_reader_v1"),
    ),
)
def test_persisted_legacy_generic_label_normalizes_without_rewrite(
    producer_module_id: str,
    stable: str,
) -> None:
    assert (
        normalize_persisted_reader_contract_version(
            producer_module_id,
            LEGACY_INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
        )
        == stable
    )
    assert (
        normalize_persisted_reader_contract_version(
            producer_module_id,
            stable,
        )
        == stable
    )


def test_live_reader_accepts_future_version_only_after_metadata_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = build_audited_installed_producer_reader("scoreform")
    seen: list[bytes] = []

    monkeypatch.setattr(
        reader_services.metadata,
        "version",
        lambda _name: "99.123.456",
    )
    monkeypatch.setattr(
        compatibility,
        "discover_publication_producer_profiles",
        lambda: (
            _profile(
                "scoreform",
                reader_contract_version=(
                    "scoreform_academic_result_reader_v1"
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        reader_services,
        "import_module",
        lambda _name: SimpleNamespace(
            read_academic_result_manifest=lambda value: (
                seen.append(value) or {"validated": True}
            )
        ),
    )

    assert reader.read(b'{"manifest":true}') == {"validated": True}
    assert seen == [b'{"manifest":true}']


def test_live_reader_rejects_future_version_with_unsupported_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = build_audited_installed_producer_reader("scoreform")

    monkeypatch.setattr(
        reader_services.metadata,
        "version",
        lambda _name: "99.123.456",
    )
    monkeypatch.setattr(
        compatibility,
        "discover_publication_producer_profiles",
        lambda: (
            _profile(
                "scoreform",
                reader_contract_version="scoreform_future_reader_v2",
            ),
        ),
    )

    with pytest.raises(ProducerReaderError) as caught:
        reader.read(b"{}")

    assert caught.value.code == "reader.incompatible"
    assert caught.value.stage == "reader_contract"
