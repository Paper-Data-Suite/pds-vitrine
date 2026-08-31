from __future__ import annotations

from dataclasses import fields

import pytest

from vitrine.models.candidates import CandidateSourceEndpoint
from vitrine.models.snapshot_workflow import SnapshotEntryPlan
from vitrine.models.sources import (
    RELATIONSHIP_KINDS,
    AcademicWorkRegistrationSnapshot,
    CorePublicationSourceReference,
    PortfolioSubjectRelationshipAssertion,
    ProducerSourceReference,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)
from vitrine.producer_adapters import (
    ProjectedProducerRelationship,
    ProjectionDisplaySnapshot,
)
from vitrine.released_producer_schema_audit import (
    CONCORD_SEMANTIC_CROSSWALK,
    QUILLAN_SEMANTIC_CROSSWALK,
    RELEASED_PRODUCER_SCHEMA_AUDIT_CONTRACT_VERSION,
    RELEASED_PRODUCER_SEMANTIC_CROSSWALK,
    SCOREFORM_SEMANTIC_CROSSWALK,
    VITRINE_SCHEMA_SUFFICIENCY,
    VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE,
    semantic_crosswalk_for,
)
from vitrine.snapshot_materialization import SnapshotAuthorizedSourceBytesResult


def _field_names(model: type[object]) -> set[str]:
    return {item.name for item in fields(model)}


def test_schema_audit_contract_is_versioned_and_deterministic() -> None:
    assert (
        RELEASED_PRODUCER_SCHEMA_AUDIT_CONTRACT_VERSION
        == "vitrine_released_producer_schema_audit_v1"
    )
    assert tuple(VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE) == tuple(
        sorted(VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE)
    )
    assert {item.producer_module_id for item in RELEASED_PRODUCER_SEMANTIC_CROSSWALK} == {
        "scoreform",
        "quillan",
        "concord",
    }


@pytest.mark.parametrize(
    ("surface_id", "model"),
    (
        ("core_publication_source_reference", CorePublicationSourceReference),
        ("academic_work_registration_snapshot", AcademicWorkRegistrationSnapshot),
        ("producer_source_reference", ProducerSourceReference),
        ("source_artifact_reference", SourceArtifactReference),
        ("source_privacy_metadata", SourcePrivacyMetadata),
        ("projected_producer_relationship", ProjectedProducerRelationship),
        (
            "portfolio_subject_relationship_assertion",
            PortfolioSubjectRelationshipAssertion,
        ),
        ("candidate_source_endpoint", CandidateSourceEndpoint),
        ("projection_display_snapshot", ProjectionDisplaySnapshot),
        ("snapshot_copied_source_plan", SnapshotEntryPlan),
        ("snapshot_source_provider", SnapshotAuthorizedSourceBytesResult),
    ),
)
def test_schema_sufficiency_required_fields_exist(
    surface_id: str, model: type[object]
) -> None:
    decision = VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE[surface_id]
    assert set(decision.required_fields).issubset(_field_names(model))


def test_snapshot_extensions_are_the_only_required_schema_extensions() -> None:
    extended = {
        item.surface_id: item.extension_contract
        for item in VITRINE_SCHEMA_SUFFICIENCY
        if item.decision == "extended"
    }
    assert extended == {
        "snapshot_copied_source_plan": "copied_source_without_required_source_locator_v1",
        "snapshot_source_provider": "authorized_source_bytes_v1",
    }


def test_scoreform_crosswalk_freezes_attempt_and_response_distinctions() -> None:
    by_id = {item.semantic_id: item for item in SCOREFORM_SEMANTIC_CROSSWALK}
    assert by_id["every_exact_attempt"].disposition == "preserved_bounded_metadata"
    assert by_id["response_state"].disposition == "preserved_bounded_metadata"
    assert by_id["attempt_selection"].disposition == "deferred_consumer_policy"
    assert by_id["grade_or_proficiency"].disposition == "deferred_consumer_policy"
    assert by_id["retained_scan_path"].disposition == "intentionally_omitted"


def test_quillan_crosswalk_preserves_native_ratings_and_artifact_boundary() -> None:
    by_id = {item.semantic_id: item for item in QUILLAN_SEMANTIC_CROSSWALK}
    assert by_id["rating_scale_identity_ordinal"].disposition == (
        "preserved_bounded_metadata"
    )
    assert by_id["published_text_state"].disposition == "preserved_bounded_metadata"
    assert by_id["artifact_resolution_provenance"].disposition == (
        "authorized_artifact_only"
    )
    assert by_id["plain_paper_manual_digital_work"].disposition == (
        "unsupported_by_release"
    )
    assert by_id["rating_normalization"].disposition == "deferred_consumer_policy"


def test_concord_crosswalk_preserves_type_and_relationship_distinctions() -> None:
    by_id = {item.semantic_id: item for item in CONCORD_SEMANTIC_CROSSWALK}
    assert by_id["type_sensitive_scale_values"].disposition == (
        "preserved_bounded_metadata"
    )
    assert by_id["score_target"].disposition == "preserved_relationship_provenance"
    assert by_id["group_identity"].disposition == "preserved_relationship_provenance"
    assert by_id["author_relationships"].disposition == (
        "preserved_relationship_provenance"
    )
    assert by_id["subject_relationships"].disposition == (
        "preserved_relationship_provenance"
    )
    assert by_id["returned_artifact_pdf"].disposition == "authorized_artifact_only"


def test_relationship_model_has_required_concord_distinctions() -> None:
    assert {
        "artifact_author",
        "artifact_subject",
        "group_member",
        "documented_contributor",
        "recorder",
        "represented_group",
        "individual_score_target",
        "group_score_target",
    }.issubset(RELATIONSHIP_KINDS)


def test_candidate_provenance_is_sufficient_without_persisting_rich_native_detail() -> None:
    decision = VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE["candidate_source_endpoint"]
    assert decision.decision == "sufficient"
    assert set(decision.required_fields) == {
        "core_publication",
        "producer_source",
        "source_artifact",
        "subject_relationship_assertions",
        "source_privacy",
    }


def test_crosswalk_lookup_fails_closed_for_unaudited_producer() -> None:
    assert semantic_crosswalk_for("scoreform") is SCOREFORM_SEMANTIC_CROSSWALK
    with pytest.raises(KeyError, match="unsupported audited producer"):
        semantic_crosswalk_for("portia")
