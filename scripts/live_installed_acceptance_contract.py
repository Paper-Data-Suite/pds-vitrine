"""Frozen contract metadata for Vitrine issue #71 installed acceptance.

This module is acceptance support, not Vitrine runtime code.  It centralizes the
release artifacts and static topology that the heavy qualifier must authenticate
before it is allowed to execute the live cross-producer scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

ACCEPTANCE_IDENTITY: Final[str] = "vitrine_live_installed_cross_producer_acceptance_v1"
ISSUE_NUMBER: Final[int] = 71
BASELINE_COMMIT: Final[str] = "c481ecd3f4c04fe31b8ee350a5a4b5c56f7c45aa"
EXPECTED_VITRINE_VERSION: Final[str] = "0.3.0"

# Slices 1-4B are individually qualified. The final gate composes the accepted
# negative matrix and healthy sealed-custody path, then repeats producer-independent
# verification. Supported CI runs that same no-flag gate on both frozen endpoints.
CANDIDATE_DISCOVERY_SLICE_READY: Final[bool] = True
CURATED_SNAPSHOT_SLICE_READY: Final[bool] = True
NEGATIVE_MATRIX_SLICE_READY: Final[bool] = True
CUSTODY_VERIFIER_SLICE_READY: Final[bool] = True
FULL_ACCEPTANCE_READY: Final[bool] = True


@dataclass(frozen=True, slots=True)
class WheelSpec:
    distribution_name: str
    version: str
    filename: str
    sha256: str
    release_tag: str
    repository: str

    @property
    def release_url(self) -> str:
        return (
            f"https://github.com/{self.repository}/releases/download/"
            f"{self.release_tag}/{self.filename}"
        )


CORE_WHEEL: Final[WheelSpec] = WheelSpec(
    distribution_name="pds-core",
    version="0.6.3",
    filename="pds_core-0.6.3-py3-none-any.whl",
    sha256="98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
    release_tag="v0.6.3",
    repository="Paper-Data-Suite/pds-core",
)
SCOREFORM_WHEEL: Final[WheelSpec] = WheelSpec(
    distribution_name="scoreform",
    version="0.11.0",
    filename="scoreform-0.11.0-py3-none-any.whl",
    sha256="8248c6a1cc8254b5f9df46440131d524f80da8662a0dc7864fdc982e501b4c44",
    release_tag="v0.11.0",
    repository="Paper-Data-Suite/pds-scoreform",
)
QUILLAN_WHEEL: Final[WheelSpec] = WheelSpec(
    distribution_name="quillan",
    version="0.10.0",
    filename="quillan-0.10.0-py3-none-any.whl",
    sha256="5dd4ed62b8bf39f7e11e6538d1c094929c6428dba81b254fe80d03c60d5114e9",
    release_tag="v0.10.0",
    repository="Paper-Data-Suite/pds-quillan",
)
CONCORD_WHEEL: Final[WheelSpec] = WheelSpec(
    distribution_name="pds-concord",
    version="0.3.0",
    filename="pds_concord-0.3.0-py3-none-any.whl",
    sha256="dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12",
    release_tag="v0.3.0",
    repository="Paper-Data-Suite/pds-concord",
)
AUDITED_RELEASE_WHEELS: Final[tuple[WheelSpec, ...]] = (
    CORE_WHEEL,
    SCOREFORM_WHEEL,
    QUILLAN_WHEEL,
    CONCORD_WHEEL,
)


@dataclass(frozen=True, slots=True)
class ProducerAcceptanceContract:
    producer_module_id: str
    distribution_name: str
    producer_contract_version: str
    publication_kind: str
    manifest_contract_version: str
    source_record_kind: str | None
    source_record_contract_version: str | None
    required_capabilities: tuple[str, ...]
    materialization: Literal["reference_only", "copied_source"]
    artifact_module: str | None


SCOREFORM_CONTRACT: Final[ProducerAcceptanceContract] = ProducerAcceptanceContract(
    producer_module_id="scoreform",
    distribution_name="scoreform",
    producer_contract_version="scoreform_academic_work_v1",
    publication_kind="academic_result_set",
    manifest_contract_version="scoreform_academic_result_manifest_v1",
    source_record_kind=None,
    source_record_contract_version=None,
    required_capabilities=("multiple_attempts", "points", "question_evidence"),
    materialization="reference_only",
    artifact_module=None,
)
QUILLAN_CONTRACT: Final[ProducerAcceptanceContract] = ProducerAcceptanceContract(
    producer_module_id="quillan",
    distribution_name="quillan",
    producer_contract_version="quillan_academic_work_v1",
    publication_kind="academic_result_set",
    manifest_contract_version="quillan_academic_result_manifest_v1",
    source_record_kind=None,
    source_record_contract_version=None,
    required_capabilities=("standards_ratings",),
    materialization="copied_source",
    artifact_module="quillan.academic_result_artifacts",
)
CONCORD_CONTRACT: Final[ProducerAcceptanceContract] = ProducerAcceptanceContract(
    producer_module_id="concord",
    distribution_name="pds-concord",
    producer_contract_version="concord_academic_work_v1",
    publication_kind="academic_result_set",
    manifest_contract_version="concord_academic_result_manifest_v1",
    source_record_kind="activity",
    source_record_contract_version="concord_activity_v1",
    required_capabilities=("criterion_scores",),
    materialization="copied_source",
    artifact_module="concord.academic_result_artifacts",
)
LIVE_PRODUCERS: Final[tuple[ProducerAcceptanceContract, ...]] = (
    SCOREFORM_CONTRACT,
    QUILLAN_CONTRACT,
    CONCORD_CONTRACT,
)

FIXTURE_PRODUCER_IDS: Final[frozenset[str]] = frozenset(
    {
        "vitrine_scoreform_fixture",
        "vitrine_quillan_fixture",
        "vitrine_concord_fixture",
    }
)
FORBIDDEN_RUNTIME_DISTRIBUTIONS: Final[frozenset[str]] = frozenset(
    {"scoreform", "quillan", "pds-concord", "pds-meridian", "pds-portia"}
)
EXPECTED_VITRINE_RUNTIME_DEPENDENCY: Final[str] = "pds-core>=0.6.3,<0.7"

CI_ENDPOINTS: Final[tuple[tuple[str, str], ...]] = (
    ("ubuntu-latest", "3.11"),
    ("windows-latest", "3.14"),
)

REQUIRED_ACCEPTANCE_FILES: Final[tuple[str, ...]] = (
    "scripts/live_installed_acceptance_contract.py",
    "scripts/live_installed_acceptance_probe.py",
    "scripts/live_installed_acceptance_support.py",
    "scripts/live_installed_acceptance_portfolio.py",
    "scripts/live_installed_acceptance_negative.py",
    "scripts/live_installed_acceptance_custody.py",
    "scripts/live_installed_acceptance_verifier.py",
    "scripts/live_installed_acceptance_scenario.py",
    "scripts/qualify_installed_live_portfolio.py",
    "scripts/validate_live_installed_acceptance.py",
    "tests/test_live_installed_acceptance_contract.py",
    "tests/test_validate_live_installed_acceptance.py",
    "docs/development/live-installed-cross-producer-acceptance.md",
    "docs/validation/issue-71-live-installed-cross-producer-acceptance-validation.md",
)

HEAVY_SCENARIO_FAMILIES: Final[tuple[str, ...]] = (
    "healthy_cross_producer_portfolio",
    "publication_currentness_drift",
    "quillan_derived_source_drift",
    "concord_exact_source_removal",
    "denied_authorization",
    "export_tamper",
    "historical_reload",
    "producer_independent_sealed_verification",
)


def validate_contract_constants() -> None:
    """Fail if duplicated contract metadata becomes internally inconsistent."""

    if EXPECTED_VITRINE_VERSION != "0.3.0":
        raise RuntimeError("issue #72 Vitrine release-candidate version drifted")

    filenames = tuple(item.filename for item in AUDITED_RELEASE_WHEELS)
    distributions = tuple(item.distribution_name for item in AUDITED_RELEASE_WHEELS)
    if len(set(filenames)) != len(filenames):
        raise RuntimeError("audited wheel filenames must be unique")
    if len(set(distributions)) != len(distributions):
        raise RuntimeError("audited wheel distribution names must be unique")
    for wheel in AUDITED_RELEASE_WHEELS:
        if len(wheel.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in wheel.sha256):
            raise RuntimeError(f"invalid frozen SHA-256 for {wheel.filename}")
        if wheel.version not in wheel.filename:
            raise RuntimeError(f"wheel filename/version mismatch for {wheel.filename}")

    producer_ids = tuple(item.producer_module_id for item in LIVE_PRODUCERS)
    if producer_ids != ("scoreform", "quillan", "concord"):
        raise RuntimeError("live producer ordering/identity drifted")
    if FIXTURE_PRODUCER_IDS.intersection(producer_ids):
        raise RuntimeError("fixture identity entered live producer contract")
    if SCOREFORM_CONTRACT.materialization != "reference_only":
        raise RuntimeError("ScoreForm must remain reference_only")
    if SCOREFORM_CONTRACT.artifact_module is not None:
        raise RuntimeError("ScoreForm must not acquire an Artifact-byte API")
    if QUILLAN_CONTRACT.materialization != "copied_source":
        raise RuntimeError("Quillan must remain copied_source-capable")
    if CONCORD_CONTRACT.materialization != "copied_source":
        raise RuntimeError("Concord must remain copied_source-capable")
    if QUILLAN_CONTRACT.artifact_module != "quillan.academic_result_artifacts":
        raise RuntimeError("Quillan Artifact API identity drifted")
    if CONCORD_CONTRACT.artifact_module != "concord.academic_result_artifacts":
        raise RuntimeError("Concord Artifact API identity drifted")


__all__ = [
    "ACCEPTANCE_IDENTITY",
    "AUDITED_RELEASE_WHEELS",
    "BASELINE_COMMIT",
    "CANDIDATE_DISCOVERY_SLICE_READY",
    "CURATED_SNAPSHOT_SLICE_READY",
    "CUSTODY_VERIFIER_SLICE_READY",
    "CI_ENDPOINTS",
    "CONCORD_CONTRACT",
    "CORE_WHEEL",
    "EXPECTED_VITRINE_RUNTIME_DEPENDENCY",
    "EXPECTED_VITRINE_VERSION",
    "FIXTURE_PRODUCER_IDS",
    "FORBIDDEN_RUNTIME_DISTRIBUTIONS",
    "FULL_ACCEPTANCE_READY",
    "HEAVY_SCENARIO_FAMILIES",
    "ISSUE_NUMBER",
    "LIVE_PRODUCERS",
    "NEGATIVE_MATRIX_SLICE_READY",
    "ProducerAcceptanceContract",
    "QUILLAN_CONTRACT",
    "REQUIRED_ACCEPTANCE_FILES",
    "SCOREFORM_CONTRACT",
    "WheelSpec",
    "validate_contract_constants",
]
