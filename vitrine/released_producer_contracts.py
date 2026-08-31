"""Audited released producer contracts for Vitrine live-adapter planning.

This module records contract facts only. It does not discover producer packages,
register live adapters, authorize publications, read manifests, or resolve
producer artifacts.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from vitrine.producer_adapters import ProducerAdapterSupportKey

RELEASED_PRODUCER_AUDIT_CONTRACT_VERSION: Final[str] = (
    "vitrine_released_producer_contract_audit_v1"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ACCESS_MODES: Final[frozenset[str]] = frozenset(
    {"none", "producer_authorized_bytes"}
)


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonempty string.")
    return value


def _require_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")
    return value


def _normalized_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"{field_name} must contain nonempty strings.")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicates.")
    return tuple(sorted(values))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReleasedCoreAudit:
    distribution_name: str
    release_version: str
    release_tag: str
    wheel_filename: str
    wheel_sha256: str
    requires_python: str

    def __post_init__(self) -> None:
        for field_name in (
            "distribution_name",
            "release_version",
            "release_tag",
            "wheel_filename",
            "requires_python",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_nonempty(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "wheel_sha256",
            _require_sha256(self.wheel_sha256, "wheel_sha256"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReleasedProducerContractAudit:
    producer_module_id: str
    distribution_name: str
    release_version: str
    release_tag: str
    wheel_filename: str
    wheel_sha256: str
    requires_python: str
    core_requirement: str
    publication_producer_entry_point: str
    public_reader_module: str
    public_reader_symbol: str
    advertised_capabilities: tuple[str, ...]
    support_key: ProducerAdapterSupportKey
    artifact_reader_module: str | None
    artifact_request_kinds: tuple[str, ...]
    artifact_representation_kinds: tuple[str, ...]
    artifact_authorization_outcomes: tuple[str, ...]
    artifact_access_mode: str

    def __post_init__(self) -> None:
        for field_name in (
            "producer_module_id",
            "distribution_name",
            "release_version",
            "release_tag",
            "wheel_filename",
            "requires_python",
            "core_requirement",
            "publication_producer_entry_point",
            "public_reader_module",
            "public_reader_symbol",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_nonempty(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "wheel_sha256",
            _require_sha256(self.wheel_sha256, "wheel_sha256"),
        )
        if not isinstance(self.support_key, ProducerAdapterSupportKey):
            raise ValueError("support_key must be ProducerAdapterSupportKey.")
        if self.support_key.producer_module_id != self.producer_module_id:
            raise ValueError("support_key producer_module_id must match the audit record.")
        object.__setattr__(
            self,
            "advertised_capabilities",
            _normalized_tuple(self.advertised_capabilities, "advertised_capabilities"),
        )
        object.__setattr__(
            self,
            "artifact_request_kinds",
            _normalized_tuple(self.artifact_request_kinds, "artifact_request_kinds"),
        )
        object.__setattr__(
            self,
            "artifact_representation_kinds",
            _normalized_tuple(
                self.artifact_representation_kinds,
                "artifact_representation_kinds",
            ),
        )
        object.__setattr__(
            self,
            "artifact_authorization_outcomes",
            _normalized_tuple(
                self.artifact_authorization_outcomes,
                "artifact_authorization_outcomes",
            ),
        )
        if self.artifact_reader_module is not None:
            object.__setattr__(
                self,
                "artifact_reader_module",
                _require_nonempty(self.artifact_reader_module, "artifact_reader_module"),
            )
        if self.artifact_access_mode not in _ARTIFACT_ACCESS_MODES:
            raise ValueError("artifact_access_mode is not a supported audit value.")
        if self.artifact_access_mode == "none":
            if self.artifact_reader_module is not None:
                raise ValueError("artifact_access_mode 'none' cannot name an artifact reader.")
            if (
                self.artifact_request_kinds
                or self.artifact_representation_kinds
                or self.artifact_authorization_outcomes
            ):
                raise ValueError("artifact_access_mode 'none' cannot advertise artifact contracts.")
        else:
            if self.artifact_reader_module is None:
                raise ValueError("producer_authorized_bytes requires an artifact reader module.")
            if not self.artifact_request_kinds:
                raise ValueError("producer_authorized_bytes requires artifact request kinds.")
            if self.artifact_authorization_outcomes != (
                "allowed",
                "denied",
                "unresolved",
            ):
                raise ValueError(
                    "producer_authorized_bytes requires allowed/denied/unresolved outcomes."
                )


CORE_0_6_3_AUDIT: Final[ReleasedCoreAudit] = ReleasedCoreAudit(
    distribution_name="pds-core",
    release_version="0.6.3",
    release_tag="v0.6.3",
    wheel_filename="pds_core-0.6.3-py3-none-any.whl",
    wheel_sha256="98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
    requires_python=">=3.11",
)

SCOREFORM_LIVE_SUPPORT_KEY: Final[ProducerAdapterSupportKey] = ProducerAdapterSupportKey(
    producer_module_id="scoreform",
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version="scoreform_academic_result_manifest_v1",
    producer_contract_version="scoreform_academic_work_v1",
    source_record_kind=None,
    source_record_contract_version=None,
    required_capabilities=("multiple_attempts", "points", "question_evidence"),
)

QUILLAN_LIVE_SUPPORT_KEY: Final[ProducerAdapterSupportKey] = ProducerAdapterSupportKey(
    producer_module_id="quillan",
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version="quillan_academic_result_manifest_v1",
    producer_contract_version="quillan_academic_work_v1",
    source_record_kind=None,
    source_record_contract_version=None,
    required_capabilities=("standards_ratings",),
)

CONCORD_LIVE_SUPPORT_KEY: Final[ProducerAdapterSupportKey] = ProducerAdapterSupportKey(
    producer_module_id="concord",
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version="concord_academic_result_manifest_v1",
    producer_contract_version="concord_academic_work_v1",
    source_record_kind="activity",
    source_record_contract_version="concord_activity_v1",
    required_capabilities=("criterion_scores",),
)

SCOREFORM_0_11_0_AUDIT: Final[ReleasedProducerContractAudit] = (
    ReleasedProducerContractAudit(
        producer_module_id="scoreform",
        distribution_name="scoreform",
        release_version="0.11.0",
        release_tag="v0.11.0",
        wheel_filename="scoreform-0.11.0-py3-none-any.whl",
        wheel_sha256="8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44",
        requires_python=">=3.11",
        core_requirement="pds-core>=0.6.2,<0.7",
        publication_producer_entry_point=(
            "scoreform=scoreform.pds_publication:get_publication_producer_profile"
        ),
        public_reader_module="scoreform.academic_result_reader",
        public_reader_symbol="read_academic_result_manifest",
        advertised_capabilities=("points", "question_evidence", "multiple_attempts"),
        support_key=SCOREFORM_LIVE_SUPPORT_KEY,
        artifact_reader_module=None,
        artifact_request_kinds=(),
        artifact_representation_kinds=(),
        artifact_authorization_outcomes=(),
        artifact_access_mode="none",
    )
)

QUILLAN_0_10_0_AUDIT: Final[ReleasedProducerContractAudit] = (
    ReleasedProducerContractAudit(
        producer_module_id="quillan",
        distribution_name="quillan",
        release_version="0.10.0",
        release_tag="v0.10.0",
        wheel_filename="quillan-0.10.0-py3-none-any.whl",
        wheel_sha256="5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9",
        requires_python=">=3.11",
        core_requirement="pds-core>=0.6.2,<0.7",
        publication_producer_entry_point=(
            "quillan=quillan.pds_publication:get_publication_producer_profile"
        ),
        public_reader_module="quillan.academic_result_reader",
        public_reader_symbol="read_academic_result_manifest",
        advertised_capabilities=("standards_ratings",),
        support_key=QUILLAN_LIVE_SUPPORT_KEY,
        artifact_reader_module="quillan.academic_result_artifacts",
        artifact_request_kinds=("student_work", "feedback_pdf", "feedback_markdown"),
        artifact_representation_kinds=(),
        artifact_authorization_outcomes=("allowed", "denied", "unresolved"),
        artifact_access_mode="producer_authorized_bytes",
    )
)

CONCORD_0_3_0_AUDIT: Final[ReleasedProducerContractAudit] = (
    ReleasedProducerContractAudit(
        producer_module_id="concord",
        distribution_name="pds-concord",
        release_version="0.3.0",
        release_tag="v0.3.0",
        wheel_filename="pds_concord-0.3.0-py3-none-any.whl",
        wheel_sha256="dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12",
        requires_python=">=3.11",
        core_requirement="pds-core>=0.6.3,<0.7",
        publication_producer_entry_point=(
            "concord=concord.pds_publication:get_publication_producer_profile"
        ),
        public_reader_module="concord.academic_result_reader",
        public_reader_symbol="read_academic_result_manifest",
        advertised_capabilities=(
            "criterion_scores",
            "standards_ratings",
            "moderated_scores",
        ),
        support_key=CONCORD_LIVE_SUPPORT_KEY,
        artifact_reader_module="concord.academic_result_artifacts",
        artifact_request_kinds=("artifact_instance", "artifact_page"),
        artifact_representation_kinds=("returned_artifact_pdf",),
        artifact_authorization_outcomes=("allowed", "denied", "unresolved"),
        artifact_access_mode="producer_authorized_bytes",
    )
)

RELEASED_PRODUCER_CONTRACTS: Final[tuple[ReleasedProducerContractAudit, ...]] = tuple(
    sorted(
        (
            SCOREFORM_0_11_0_AUDIT,
            QUILLAN_0_10_0_AUDIT,
            CONCORD_0_3_0_AUDIT,
        ),
        key=lambda item: item.producer_module_id,
    )
)

RELEASED_PRODUCER_CONTRACT_BY_MODULE: Final[
    Mapping[str, ReleasedProducerContractAudit]
] = MappingProxyType(
    {item.producer_module_id: item for item in RELEASED_PRODUCER_CONTRACTS}
)

LIVE_PRODUCER_SUPPORT_KEYS: Final[tuple[ProducerAdapterSupportKey, ...]] = tuple(
    item.support_key for item in RELEASED_PRODUCER_CONTRACTS
)


__all__ = [
    "CONCORD_0_3_0_AUDIT",
    "CONCORD_LIVE_SUPPORT_KEY",
    "CORE_0_6_3_AUDIT",
    "LIVE_PRODUCER_SUPPORT_KEYS",
    "QUILLAN_0_10_0_AUDIT",
    "QUILLAN_LIVE_SUPPORT_KEY",
    "RELEASED_PRODUCER_AUDIT_CONTRACT_VERSION",
    "RELEASED_PRODUCER_CONTRACT_BY_MODULE",
    "RELEASED_PRODUCER_CONTRACTS",
    "ReleasedCoreAudit",
    "ReleasedProducerContractAudit",
    "SCOREFORM_0_11_0_AUDIT",
    "SCOREFORM_LIVE_SUPPORT_KEY",
]
