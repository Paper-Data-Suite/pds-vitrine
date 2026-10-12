"""Stable installed producer-reader compatibility for Vitrine.

Core owns producer-declared PublicationReaderSupport metadata. Vitrine owns the
consumer policy that decides which producer reader contracts it understands.

Historical Vitrine Candidate records may contain the former generic
``vitrine_installed_producer_reader_v1`` provenance label. That label remains
readable history; it is not a semantic compatibility authority for new reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast

from pds_core.publication_compatibility import (
    PublicationProducerProfile,
    discover_publication_producer_profiles,
    lookup_publication_reader_support,
)
from pds_core.publication_records import PublicationKind

from vitrine.released_producer_contracts import (
    CONCORD_0_3_0_AUDIT,
    QUILLAN_0_10_0_AUDIT,
    QUILLAN_0_10_5_AUDIT,
    SCOREFORM_0_11_0_AUDIT,
    SCOREFORM_0_12_0_AUDIT,
    SCOREFORM_0_12_1_AUDIT,
    ReleasedProducerContractAudit,
)

LEGACY_INSTALLED_PRODUCER_READER_CONTRACT_VERSION: Final[str] = (
    "vitrine_installed_producer_reader_v1"
)

VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS: Final[
    dict[str, frozenset[str]]
] = {
    "concord": frozenset({"concord_academic_result_reader_v1"}),
    "quillan": frozenset({"quillan_academic_result_reader_v1"}),
    "scoreform": frozenset({"scoreform_academic_result_reader_v1"}),
}

VITRINE_LEGACY_EXACT_PRODUCER_RELEASES: Final[
    dict[str, frozenset[str]]
] = {
    "concord": frozenset(
        {
            CONCORD_0_3_0_AUDIT.release_version,
        }
    ),
    "quillan": frozenset(
        {
            QUILLAN_0_10_0_AUDIT.release_version,
            QUILLAN_0_10_5_AUDIT.release_version,
        }
    ),
    "scoreform": frozenset(
        {
            SCOREFORM_0_11_0_AUDIT.release_version,
            SCOREFORM_0_12_0_AUDIT.release_version,
            SCOREFORM_0_12_1_AUDIT.release_version,
        }
    ),
}

READER_COMPATIBILITY_BASES: Final[frozenset[str]] = frozenset(
    {"declared_reader_contract", "legacy_exact_release"}
)


class InstalledProducerReaderCompatibilityError(RuntimeError):
    """Privacy-safe installed-reader compatibility failure."""

    def __init__(self, code: str, stage: str, message: str) -> None:
        if code not in {"reader.unavailable", "reader.incompatible"}:
            raise ValueError("unsupported installed-reader compatibility code")
        if stage not in {"reader_distribution", "reader_contract"}:
            raise ValueError("unsupported installed-reader compatibility stage")
        self.code = code
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class InstalledProducerReaderCompatibility:
    producer_module_id: str
    distribution_name: str
    installed_distribution_version: str
    manifest_contract_version: str
    reader_contract_version: str
    compatibility_basis: str

    def __post_init__(self) -> None:
        if self.compatibility_basis not in READER_COMPATIBILITY_BASES:
            raise ValueError("unsupported reader compatibility basis")


def _single_supported_reader_contract(producer_module_id: str) -> str:
    contracts = VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS.get(
        producer_module_id
    )
    if contracts is None or len(contracts) != 1:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Vitrine does not have one unambiguous reader contract for this producer.",
        )
    return next(iter(contracts))


def supported_reader_contract_for_module(producer_module_id: str) -> str:
    """Return Vitrine's one current producer-owned reader contract."""

    return _single_supported_reader_contract(producer_module_id)


def normalize_persisted_reader_contract_version(
    producer_module_id: str,
    reader_contract_version: str,
) -> str:
    """Normalize only the historical generic Vitrine reader provenance label.

    This is for persisted semantic comparison. It does not rewrite stored state
    and does not broaden compatibility for arbitrary reader contracts.
    """

    if (
        reader_contract_version
        == LEGACY_INSTALLED_PRODUCER_READER_CONTRACT_VERSION
        and producer_module_id in VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS
    ):
        return _single_supported_reader_contract(producer_module_id)
    return reader_contract_version


def _profile_for_module(
    profiles: tuple[PublicationProducerProfile, ...],
    producer_module_id: str,
) -> PublicationProducerProfile:
    matching = tuple(
        item for item in profiles if item.module_id == producer_module_id
    )
    if len(matching) != 1:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Installed producer reader metadata is unavailable or ambiguous.",
        )
    return matching[0]


def resolve_installed_producer_reader_compatibility(
    audit: ReleasedProducerContractAudit,
    *,
    installed_distribution_version: str,
    profiles: tuple[PublicationProducerProfile, ...] | None = None,
) -> InstalledProducerReaderCompatibility:
    """Resolve semantic reader support separately from package provenance."""

    accepted = VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS.get(
        audit.producer_module_id
    )
    legacy = VITRINE_LEGACY_EXACT_PRODUCER_RELEASES.get(
        audit.producer_module_id
    )
    if accepted is None or legacy is None:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Vitrine has no installed reader compatibility policy for this producer.",
        )

    # The legacy list is intentionally exact and bounded. These immutable
    # releases predate Core reader metadata and were independently qualified by
    # Vitrine. Do not infer ranges, same-major/minor support, or nearest versions.
    if installed_distribution_version in legacy:
        return InstalledProducerReaderCompatibility(
            producer_module_id=audit.producer_module_id,
            distribution_name=audit.distribution_name,
            installed_distribution_version=installed_distribution_version,
            manifest_contract_version=audit.support_key.manifest_contract_version,
            reader_contract_version=_single_supported_reader_contract(
                audit.producer_module_id
            ),
            compatibility_basis="legacy_exact_release",
        )

    try:
        discovered = (
            discover_publication_producer_profiles()
            if profiles is None
            else profiles
        )
        profile = _profile_for_module(
            tuple(discovered),
            audit.producer_module_id,
        )
        support = lookup_publication_reader_support(
            profile,
            cast(PublicationKind, audit.support_key.publication_kind),
            audit.support_key.manifest_contract_version,
        )
    except InstalledProducerReaderCompatibilityError:
        raise
    except Exception as error:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Installed producer reader metadata could not be established safely.",
        ) from error

    if support is None:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Installed producer does not declare reader metadata for this manifest.",
        )
    if support.distribution_name != audit.distribution_name:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Producer reader metadata identifies an unexpected distribution.",
        )
    if support.reader_contract_version not in accepted:
        raise InstalledProducerReaderCompatibilityError(
            "reader.incompatible",
            "reader_contract",
            "Producer reader contract is not supported by this Vitrine release.",
        )

    return InstalledProducerReaderCompatibility(
        producer_module_id=audit.producer_module_id,
        distribution_name=audit.distribution_name,
        installed_distribution_version=installed_distribution_version,
        manifest_contract_version=audit.support_key.manifest_contract_version,
        reader_contract_version=support.reader_contract_version,
        compatibility_basis="declared_reader_contract",
    )


__all__ = [
    "InstalledProducerReaderCompatibility",
    "InstalledProducerReaderCompatibilityError",
    "LEGACY_INSTALLED_PRODUCER_READER_CONTRACT_VERSION",
    "READER_COMPATIBILITY_BASES",
    "VITRINE_LEGACY_EXACT_PRODUCER_RELEASES",
    "VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS",
    "normalize_persisted_reader_contract_version",
    "resolve_installed_producer_reader_compatibility",
    "supported_reader_contract_for_module",
]
