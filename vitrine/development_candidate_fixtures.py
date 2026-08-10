"""Explicit Core compatibility Profiles for Vitrine development fixtures.

These values describe only the Vitrine-owned producer-shaped fixture contracts.
They are not installed producer profiles and never claim ScoreForm, Quillan, or
Concord live integration.
"""

from __future__ import annotations

from typing import Final

from pds_core.publication_compatibility import (
    PublicationContractSupport,
    PublicationProducerProfile,
    PublicationProducerRegistry,
    SourceRecordContractSupport,
)

from vitrine.development_adapters import (
    CONCORD_FIXTURE_MANIFEST_CONTRACT,
    QUILLAN_FIXTURE_MANIFEST_CONTRACT,
    SCOREFORM_FIXTURE_MANIFEST_CONTRACT,
)

SCOREFORM_FIXTURE_PRODUCER_PROFILE: Final[PublicationProducerProfile] = (
    PublicationProducerProfile(
        module_id="vitrine_scoreform_fixture",
        display_name="Vitrine ScoreForm-shaped development fixture",
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset(
            {"vitrine_fixture_scoreform_academic_work_v1"}
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind="academic_result_set",
                manifest_contract_versions=frozenset(
                    {SCOREFORM_FIXTURE_MANIFEST_CONTRACT}
                ),
                supported_capabilities=frozenset(
                    {"multiple_attempts", "points", "question_evidence"}
                ),
                source_record_contracts=(),
                allows_missing_source_record=True,
            ),
        ),
    )
)

QUILLAN_FIXTURE_PRODUCER_PROFILE: Final[PublicationProducerProfile] = (
    PublicationProducerProfile(
        module_id="vitrine_quillan_fixture",
        display_name="Vitrine Quillan-shaped development fixture",
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset(
            {"vitrine_fixture_quillan_academic_work_v1"}
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind="academic_result_set",
                manifest_contract_versions=frozenset(
                    {QUILLAN_FIXTURE_MANIFEST_CONTRACT}
                ),
                supported_capabilities=frozenset(),
                source_record_contracts=(
                    SourceRecordContractSupport(
                        record_kind="submission",
                        contract_versions=frozenset(
                            {"vitrine_fixture_quillan_submission_v1"}
                        ),
                    ),
                ),
                allows_missing_source_record=False,
            ),
        ),
    )
)

CONCORD_FIXTURE_PRODUCER_PROFILE: Final[PublicationProducerProfile] = (
    PublicationProducerProfile(
        module_id="vitrine_concord_fixture",
        display_name="Vitrine Concord-shaped development fixture",
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset(
            {"vitrine_fixture_concord_academic_work_v1"}
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind="academic_result_set",
                manifest_contract_versions=frozenset(
                    {CONCORD_FIXTURE_MANIFEST_CONTRACT}
                ),
                supported_capabilities=frozenset({"criterion_scores"}),
                source_record_contracts=(
                    SourceRecordContractSupport(
                        record_kind="artifact_instance",
                        contract_versions=frozenset(
                            {"vitrine_fixture_concord_artifact_v1"}
                        ),
                    ),
                ),
                allows_missing_source_record=False,
            ),
        ),
    )
)


def build_development_fixture_producer_registry() -> PublicationProducerRegistry:
    """Return the explicit Core Profile registry for #32/#33 development fixtures."""

    return PublicationProducerRegistry(
        profiles=(
            SCOREFORM_FIXTURE_PRODUCER_PROFILE,
            QUILLAN_FIXTURE_PRODUCER_PROFILE,
            CONCORD_FIXTURE_PRODUCER_PROFILE,
        )
    )


__all__ = [
    "CONCORD_FIXTURE_PRODUCER_PROFILE",
    "QUILLAN_FIXTURE_PRODUCER_PROFILE",
    "SCOREFORM_FIXTURE_PRODUCER_PROFILE",
    "build_development_fixture_producer_registry",
]
