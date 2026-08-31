"""Released-producer semantic crosswalk and Vitrine schema-sufficiency audit.

Issue #57 records integration facts only.  This module does not discover producer
packages, import sibling producer modules, register live adapters, authorize
sources, read manifests, or evaluate Candidate worth.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping

RELEASED_PRODUCER_SCHEMA_AUDIT_CONTRACT_VERSION: Final[str] = (
    "vitrine_released_producer_schema_audit_v1"
)

SEMANTIC_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {
        "preserved_directly",
        "preserved_bounded_metadata",
        "preserved_relationship_provenance",
        "authorized_artifact_only",
        "intentionally_omitted",
        "deferred_consumer_policy",
        "unsupported_by_release",
    }
)
SCHEMA_DECISIONS: Final[frozenset[str]] = frozenset(
    {"sufficient", "extended", "deferred", "not_applicable"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerSemanticCrosswalkEntry:
    producer_module_id: str
    semantic_id: str
    disposition: str
    vitrine_surfaces: tuple[str, ...]
    producer_owner: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.producer_module_id or self.producer_module_id.lower() != self.producer_module_id:
            raise ValueError("producer_module_id must be nonempty lowercase text.")
        if not self.semantic_id or self.semantic_id.lower() != self.semantic_id:
            raise ValueError("semantic_id must be nonempty lowercase text.")
        if self.disposition not in SEMANTIC_DISPOSITIONS:
            raise ValueError("unsupported semantic disposition.")
        if not self.producer_owner or not self.rationale:
            raise ValueError("producer_owner and rationale must be nonempty.")
        surfaces = tuple(self.vitrine_surfaces)
        if len(set(surfaces)) != len(surfaces):
            raise ValueError("vitrine_surfaces must not contain duplicates.")
        if self.disposition in {
            "preserved_directly",
            "preserved_bounded_metadata",
            "preserved_relationship_provenance",
            "authorized_artifact_only",
        } and not surfaces:
            raise ValueError("preserved semantics require at least one Vitrine surface.")
        object.__setattr__(self, "vitrine_surfaces", surfaces)


@dataclass(frozen=True, slots=True, kw_only=True)
class VitrineSchemaSufficiencyDecision:
    surface_id: str
    decision: str
    reason: str
    required_fields: tuple[str, ...] = ()
    extension_contract: str | None = None

    def __post_init__(self) -> None:
        if not self.surface_id or self.surface_id.lower() != self.surface_id:
            raise ValueError("surface_id must be nonempty lowercase text.")
        if self.decision not in SCHEMA_DECISIONS:
            raise ValueError("unsupported schema decision.")
        if not self.reason:
            raise ValueError("reason must be nonempty.")
        fields = tuple(self.required_fields)
        if len(set(fields)) != len(fields):
            raise ValueError("required_fields must not contain duplicates.")
        object.__setattr__(self, "required_fields", fields)
        if self.decision == "extended" and self.extension_contract is None:
            raise ValueError("extended decisions require extension_contract.")
        if self.decision != "extended" and self.extension_contract is not None:
            raise ValueError("extension_contract is reserved for extended decisions.")


def _entry(
    producer: str,
    semantic: str,
    disposition: str,
    surfaces: tuple[str, ...],
    owner: str,
    rationale: str,
) -> ProducerSemanticCrosswalkEntry:
    return ProducerSemanticCrosswalkEntry(
        producer_module_id=producer,
        semantic_id=semantic,
        disposition=disposition,
        vitrine_surfaces=surfaces,
        producer_owner=owner,
        rationale=rationale,
    )


SCOREFORM_SEMANTIC_CROSSWALK: Final[tuple[ProducerSemanticCrosswalkEntry, ...]] = (
    _entry("scoreform", "core_work_identity", "preserved_directly",
           ("CorePublicationSourceReference",), "scoreform",
           "Core publication work identity remains the authoritative cross-module work identity."),
    _entry("scoreform", "assignment_identity_title_snapshot", "preserved_directly",
           ("AcademicWorkRegistrationSnapshot", "ProjectionDisplaySnapshot"), "scoreform",
           "Registration identity and title snapshot remain provenance; display text is bounded."),
    _entry("scoreform", "student_identity", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "scoreform",
           "The represented student is related explicitly rather than inferred from filenames or attempt order."),
    _entry("scoreform", "every_exact_attempt", "preserved_bounded_metadata",
           ("ProjectedProducerSource", "ProjectionDisplaySnapshot"), "scoreform",
           "Each represented attempt remains independently projectable; the adapter must not collapse attempts."),
    _entry("scoreform", "attempt_number", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Attempt number is producer-native display/projection metadata, not a selection rule."),
    _entry("scoreform", "native_attempt_provenance", "preserved_directly",
           ("ProducerSourceReference",), "scoreform",
           "Native revision, lifecycle, disposition, lineage, reader contract, and projection contract are retained."),
    _entry("scoreform", "attempt_origin_time", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Origin and time may be projected without becoming ordering or selection authority."),
    _entry("scoreform", "points_earned_possible", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Native points remain producer evidence and are not converted into Vitrine grading semantics."),
    _entry("scoreform", "question_identity_order", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Question identity and producer order may be retained as bounded projection fields."),
    _entry("scoreform", "question_standard_alignment", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Question standard IDs remain assignment alignment and are not promoted to standards ratings."),
    _entry("scoreform", "response_state", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "selected, blank, and ambiguous remain distinct producer-native states."),
    _entry("scoreform", "selected_answer_presence", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Presence may be represented without exposing or inferring an answer key."),
    _entry("scoreform", "native_correctness_evidence", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "scoreform",
           "Correctness remains native evidence; Vitrine does not reinterpret it as proficiency."),
    _entry("scoreform", "manifest_source_snapshots", "preserved_directly",
           ("CorePublicationSourceReference", "ProducerSourceReference"), "scoreform",
           "Exact publication and producer lineage carry the bounded source snapshots required by the reader."),
    _entry("scoreform", "bounded_lineage", "preserved_directly",
           ("ProducerSourceReference",), "scoreform",
           "Lineage remains bounded producer provenance rather than an invitation to inspect private storage."),
    _entry("scoreform", "retained_scan_path", "intentionally_omitted",
           (), "scoreform",
           "retained_source_path is provenance only; ScoreForm exposes no consumer-neutral artifact resolver."),
    _entry("scoreform", "attempt_selection", "deferred_consumer_policy",
           (), "vitrine",
           "Latest, highest, best, or official attempt selection belongs to explicit Candidate/Profile policy."),
    _entry("scoreform", "grade_or_proficiency", "deferred_consumer_policy",
           (), "vitrine",
           "Vitrine does not derive Grade, mastery, or proficiency from ScoreForm question evidence."),
    _entry("scoreform", "answer_key_inference", "intentionally_omitted",
           (), "scoreform",
           "The adapter must not infer or expose answer keys from response/correctness evidence."),
)

QUILLAN_SEMANTIC_CROSSWALK: Final[tuple[ProducerSemanticCrosswalkEntry, ...]] = (
    _entry("quillan", "work_assignment_identity", "preserved_directly",
           ("CorePublicationSourceReference", "AcademicWorkRegistrationSnapshot"), "quillan",
           "Core work and registration snapshots retain the exact assignment context."),
    _entry("quillan", "represented_student_identity", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "quillan",
           "The represented student remains an explicit relationship assertion."),
    _entry("quillan", "assignment_submission_review_snapshots", "preserved_directly",
           ("ProducerSourceReference", "ProjectionDisplaySnapshot"), "quillan",
           "Exact source revisions and bounded display metadata retain review context without private-state access."),
    _entry("quillan", "review_unit_identity_order", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Review-unit identity and native order remain producer metadata."),
    _entry("quillan", "observations", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Native observations may be projected without Vitrine reinterpreting their meaning."),
    _entry("quillan", "applicability_evidence_states", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Applicability and evidence states remain distinct native states."),
    _entry("quillan", "overall_native_ratings", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Overall ratings remain on Quillan's native scale."),
    _entry("quillan", "standard_specific_ratings", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Standard ratings remain producer-owned ratings and are not normalized by Vitrine."),
    _entry("quillan", "rating_scale_identity_ordinal", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Scale identity and ordinal meaning remain intact; minimum rating is a real rating, not missingness."),
    _entry("quillan", "standard_feedback", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "Student-facing standard feedback can be projected as bounded producer metadata."),
    _entry("quillan", "published_text_state", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "quillan",
           "absent, withheld, and included remain distinct states."),
    _entry("quillan", "selected_pds2_evidence", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot", "SourceArtifactReference"), "quillan",
           "Only producer-selected PDS2 evidence references are eligible for projection; selection is not duplicated or expanded."),
    _entry("quillan", "review_source_revision_lineage", "preserved_directly",
           ("ProducerSourceReference",), "quillan",
           "Exact historical revision lineage remains producer provenance."),
    _entry("quillan", "student_feedback_relationships", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "quillan",
           "Feedback relationships remain explicit rather than inferred from proximity or filenames."),
    _entry("quillan", "artifact_resolution_provenance", "authorized_artifact_only",
           ("SourceArtifactReference", "SnapshotAuthorizedSourceBytesResult"), "quillan",
           "Artifact bytes may enter Vitrine only through Quillan's authorization-gated bounded artifact API."),
    _entry("quillan", "plain_paper_manual_digital_work", "unsupported_by_release",
           (), "quillan",
           "plain_paper_manual does not fabricate digital student_work; absence must remain absence."),
    _entry("quillan", "private_teacher_notes", "intentionally_omitted",
           (), "quillan",
           "Private teacher notes and hidden text remain outside the public publication/artifact contract."),
    _entry("quillan", "unselected_or_private_evidence", "intentionally_omitted",
           (), "quillan",
           "Unselected, duplicate, excluded, and producer-private evidence is not widened by Vitrine."),
    _entry("quillan", "rating_normalization", "deferred_consumer_policy",
           (), "vitrine",
           "Vitrine preserves native ordinal ratings and does not silently normalize them into a common scale."),
)

CONCORD_SEMANTIC_CROSSWALK: Final[tuple[ProducerSemanticCrosswalkEntry, ...]] = (
    _entry("concord", "activity_work_identity", "preserved_directly",
           ("CorePublicationSourceReference", "ProducerSourceReference"), "concord",
           "The exact Activity source and work identity remain explicit and versioned."),
    _entry("concord", "activity_scoring_orientation", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Scoring orientation remains producer-native interpretation metadata."),
    _entry("concord", "standards_profile_focus_standards", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Standards profile and ordered Focus Standards remain producer-native context."),
    _entry("concord", "criterion_set_identity_revision", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot", "ProducerSourceReference"), "concord",
           "Criterion Set identity/revision remains exact producer provenance."),
    _entry("concord", "criterion_identity", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Criterion identity remains distinct across Score revisions."),
    _entry("concord", "criterion_standard_or_local_status", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Standard-backed and local criteria remain distinguishable."),
    _entry("concord", "scoring_scale_revision", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Exact Scale revision remains part of native scoring semantics."),
    _entry("concord", "ordered_scale_levels", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Scale-level order remains producer-defined."),
    _entry("concord", "type_sensitive_scale_values", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Values retain type identity; 1, 1.0, '1', and true must not be collapsed."),
    _entry("concord", "score_identity", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot", "ProducerSourceReference"), "concord",
           "Every represented Score revision remains independently identifiable."),
    _entry("concord", "score_target", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Individual and Group Score targets remain explicit relationship kinds."),
    _entry("concord", "score_disposition", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Non-score disposition remains absence of a value, never synthetic zero."),
    _entry("concord", "score_value", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Applicable Score values remain native values on the exact Scale."),
    _entry("concord", "scoring_basis_scorer_time", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Scoring basis, scorer, and time remain bounded native metadata."),
    _entry("concord", "current_superseded_score_state", "preserved_bounded_metadata",
           ("ProducerSourceReference", "ProjectionDisplaySnapshot"), "concord",
           "Current and superseded Score states remain distinct; Vitrine does not choose a best/latest Score."),
    _entry("concord", "score_evidence_link_identity", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot", "SourceArtifactReference"), "concord",
           "Evidence links remain exact represented evidence references."),
    _entry("concord", "external_evidence_ownership_reference", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot", "SourceArtifactReference"), "concord",
           "External evidence ownership/reference remains provenance and does not grant arbitrary access."),
    _entry("concord", "moderation_semantics", "preserved_bounded_metadata",
           ("ProjectionDisplaySnapshot",), "concord",
           "Moderation identity, status, and permitted-use semantics remain producer-owned."),
    _entry("concord", "standards_result_relationships", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Standards relationships remain explicit and are not converted into Vitrine proficiency."),
    _entry("concord", "group_identity", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Group remains Group; Vitrine must not silently individualize a group result."),
    _entry("concord", "artifact_and_page_identity", "authorized_artifact_only",
           ("SourceArtifactReference", "SnapshotAuthorizedSourceBytesResult"), "concord",
           "artifact_instance and artifact_page resolve only through Concord's authorized represented-evidence API."),
    _entry("concord", "author_relationships", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Author is explicit and must not be inferred to equal Subject."),
    _entry("concord", "subject_relationships", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Subject is explicit and remains distinct from Author, recorder, and contributor."),
    _entry("concord", "contribution_relationships", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Documented contribution remains explicit rather than inferred from group membership."),
    _entry("concord", "recorder_relationships", "preserved_relationship_provenance",
           ("ProjectedProducerRelationship", "PortfolioSubjectRelationshipAssertion"), "concord",
           "Recorder remains distinct from Author and Subject."),
    _entry("concord", "returned_artifact_pdf", "authorized_artifact_only",
           ("SourceArtifactReference", "SnapshotAuthorizedSourceBytesResult"), "concord",
           "Producer-approved returned_artifact_pdf bytes may be copied without exposing Concord storage paths."),
    _entry("concord", "producer_private_paths", "intentionally_omitted",
           (), "concord",
           "Concord's public artifact boundary accepts bounded identity, not arbitrary paths or native selectors."),
    _entry("concord", "grade_or_proficiency", "deferred_consumer_policy",
           (), "vitrine",
           "Vitrine does not derive Grade, mastery, proficiency, or portfolio quality from Concord Scores."),
)

RELEASED_PRODUCER_SEMANTIC_CROSSWALK: Final[
    tuple[ProducerSemanticCrosswalkEntry, ...]
] = (
    *SCOREFORM_SEMANTIC_CROSSWALK,
    *QUILLAN_SEMANTIC_CROSSWALK,
    *CONCORD_SEMANTIC_CROSSWALK,
)

_seen = {(item.producer_module_id, item.semantic_id) for item in RELEASED_PRODUCER_SEMANTIC_CROSSWALK}
if len(_seen) != len(RELEASED_PRODUCER_SEMANTIC_CROSSWALK):
    raise RuntimeError("released producer semantic crosswalk identities must be unique.")

RELEASED_PRODUCER_SEMANTICS_BY_MODULE: Final[
    Mapping[str, tuple[ProducerSemanticCrosswalkEntry, ...]]
] = MappingProxyType(
    {
        "concord": CONCORD_SEMANTIC_CROSSWALK,
        "quillan": QUILLAN_SEMANTIC_CROSSWALK,
        "scoreform": SCOREFORM_SEMANTIC_CROSSWALK,
    }
)

VITRINE_SCHEMA_SUFFICIENCY: Final[tuple[VitrineSchemaSufficiencyDecision, ...]] = (
    VitrineSchemaSufficiencyDecision(
        surface_id="core_publication_source_reference",
        decision="sufficient",
        reason="Carries exact Core publication/work/source/capability/manifest/registration and lifecycle identity.",
        required_fields=(
            "core_publication_schema_version",
            "publication_id",
            "work",
            "source_record",
            "publication_kind",
            "capabilities",
            "manifest_contract_version",
            "manifest_digest",
            "registration_snapshot",
            "observed_series_state",
            "observed_withdrawal_state",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="academic_work_registration_snapshot",
        decision="sufficient",
        reason="Preserves producer contract, title/work intent, lifecycle, and exact registration source records.",
        required_fields=(
            "registration_revision",
            "producer_contract_version",
            "title_snapshot",
            "work_kind",
            "academic_intent",
            "lifecycle",
            "source_records",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="producer_source_reference",
        decision="sufficient",
        reason="Carries native revision/lifecycle/disposition/lineage plus reader and projection contract identity.",
        required_fields=(
            "producer_module_id",
            "producer_contract_version",
            "source_record_kind",
            "source_record_id",
            "source_record_contract_version",
            "native_revision",
            "native_lifecycle",
            "native_disposition",
            "lineage_reference",
            "reader_contract_version",
            "projection_contract_version",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="source_artifact_reference",
        decision="sufficient",
        reason="Carries bounded artifact identity/representation/media/digest/size while source_locator remains optional.",
        required_fields=(
            "artifact_id",
            "artifact_kind",
            "representation_kind",
            "media_type",
            "source_locator",
            "native_revision",
            "source_digest",
            "byte_size",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="source_privacy_metadata",
        decision="sufficient",
        reason="Already separates classification, subject scope, collaborator/third-party signals, and review requirements.",
        required_fields=(
            "classification",
            "subject_scope",
            "metadata_visibility",
            "collaborator_information_present",
            "third_party_information_present",
            "rights_review_required",
            "redaction_review_required",
            "multi_subject_review_required",
            "minimum_necessary_projection_required",
            "policy_reference",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="projected_producer_relationship",
        decision="sufficient",
        reason="Carries explicit source subject, relationship kind/authority, and bounded supporting provenance.",
        required_fields=(
            "source_subject_kind",
            "source_subject_id",
            "relationship_kind",
            "relationship_authority",
            "supporting_source_reference",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="portfolio_subject_relationship_assertion",
        decision="sufficient",
        reason="Persists explicit subject-link assertions without conflating Author, Subject, group, contributor, recorder, or Score target.",
        required_fields=(
            "assertion_id",
            "portfolio_subject_id",
            "subject_link_id",
            "source_subject_kind",
            "source_subject_id",
            "relationship_kind",
            "relationship_authority",
            "supporting_source_reference",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="candidate_source_endpoint",
        decision="sufficient",
        reason="Persists exact Core, producer, optional Artifact, relationship, and privacy provenance; rich producer detail may remain transient.",
        required_fields=(
            "core_publication",
            "producer_source",
            "source_artifact",
            "subject_relationship_assertions",
            "source_privacy",
        ),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="projection_display_snapshot",
        decision="sufficient",
        reason="Provides bounded title/summary/keyed fields for producer-native semantic display without widening persistent Candidate schema.",
        required_fields=("title", "summary", "fields"),
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="snapshot_copied_source_plan",
        decision="extended",
        reason="Issue #57 removed the path-only requirement so exact source provenance can be planned when a producer owns artifact acquisition.",
        required_fields=("source_artifact", "target_relative_path", "media_type"),
        extension_contract="copied_source_without_required_source_locator_v1",
    ),
    VitrineSchemaSufficiencyDecision(
        surface_id="snapshot_source_provider",
        decision="extended",
        reason="Issue #57 added an immutable authorized-byte result while preserving the existing filesystem reread provider path.",
        required_fields=(
            "provider_id",
            "provider_version",
            "source_publication_id",
            "source_artifact_id",
        ),
        extension_contract="authorized_source_bytes_v1",
    ),
)

VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE: Final[
    Mapping[str, VitrineSchemaSufficiencyDecision]
] = MappingProxyType(
    {
        item.surface_id: item
        for item in sorted(
            VITRINE_SCHEMA_SUFFICIENCY,
            key=lambda decision: decision.surface_id,
        )
    }
)

if len(VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE) != len(VITRINE_SCHEMA_SUFFICIENCY):
    raise RuntimeError("schema sufficiency surface identities must be unique.")


def semantic_crosswalk_for(
    producer_module_id: str,
) -> tuple[ProducerSemanticCrosswalkEntry, ...]:
    """Return the frozen semantic crosswalk for one audited producer."""

    try:
        return RELEASED_PRODUCER_SEMANTICS_BY_MODULE[producer_module_id]
    except KeyError as error:
        raise KeyError(f"unsupported audited producer: {producer_module_id}") from error


__all__ = [
    "CONCORD_SEMANTIC_CROSSWALK",
    "QUILLAN_SEMANTIC_CROSSWALK",
    "RELEASED_PRODUCER_SCHEMA_AUDIT_CONTRACT_VERSION",
    "RELEASED_PRODUCER_SEMANTIC_CROSSWALK",
    "RELEASED_PRODUCER_SEMANTICS_BY_MODULE",
    "SCHEMA_DECISIONS",
    "SCOREFORM_SEMANTIC_CROSSWALK",
    "SEMANTIC_DISPOSITIONS",
    "ProducerSemanticCrosswalkEntry",
    "VITRINE_SCHEMA_SUFFICIENCY",
    "VITRINE_SCHEMA_SUFFICIENCY_BY_SURFACE",
    "VitrineSchemaSufficiencyDecision",
    "semantic_crosswalk_for",
]
