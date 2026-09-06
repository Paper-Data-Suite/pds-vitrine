"""Authoritative descriptor registry for persisted Vitrine runtime records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vitrine.models.audiences import AudienceContext
from vitrine.models.candidates import (
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    PortfolioCandidate,
)
from vitrine.models.curation import (
    PortfolioPlacement,
    PortfolioSelection,
    SectionArrangementRevision,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.curation_workflow import (
    CurationAnnotation,
    CurationRationale,
    CurationReviewDecision,
    PlacementLifecycleEvent,
    PortfolioReflection,
    SectionArrangementPointerRevision,
    SelectionDecision,
    SelectionLifecycleEvent,
    SelectionProposal,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
)
from vitrine.models.identity import (
    Portfolio,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
    PortfolioSubjectIdentityTransition,
)
from vitrine.models.profiles import (
    PortfolioProfileBinding,
    PortfolioProfileComposition,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileMigration,
    PortfolioProfileOverlayRevision,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
)
from vitrine.models.snapshot_workflow import (
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotEditionBuildProvenance,
    SnapshotExportArtifact,
    SnapshotMaterializationProvenance,
    SnapshotSeries,
)
from vitrine.models.snapshots import (
    SnapshotEdition,
    SnapshotEntry,
    SnapshotManifest,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
)


@dataclass(frozen=True, slots=True)
class RecordDescriptor:
    """Stable metadata for one top-level Vitrine runtime record family."""

    record_type: str
    model_type: type[Any]
    graph_collection: str | None
    identity_fields: tuple[str, ...]
    integer_identity_fields: tuple[str, ...] = ()


RECORD_DESCRIPTORS: tuple[RecordDescriptor, ...] = (
    RecordDescriptor("portfolio", Portfolio, "portfolios", ("portfolio_id",)),
    RecordDescriptor(
        "portfolio_subject",
        PortfolioSubject,
        "portfolio_subjects",
        ("portfolio_subject_id",),
    ),
    RecordDescriptor(
        "portfolio_subject_class_link",
        PortfolioSubjectClassLink,
        "subject_links",
        ("subject_link_id",),
    ),
    RecordDescriptor(
        "portfolio_subject_display_snapshot",
        PortfolioSubjectDisplaySnapshot,
        None,
        ("display_snapshot_id",),
    ),
    RecordDescriptor(
        "portfolio_subject_identity_decision",
        PortfolioSubjectIdentityDecision,
        None,
        ("identity_decision_id",),
    ),
    RecordDescriptor(
        "portfolio_subject_identity_transition",
        PortfolioSubjectIdentityTransition,
        None,
        ("subject_identity_transition_id",),
    ),
    RecordDescriptor(
        "portfolio_profile_family",
        PortfolioProfileFamily,
        "profile_families",
        ("profile_family_id",),
    ),
    RecordDescriptor(
        "portfolio_profile_revision",
        PortfolioProfileRevision,
        "profile_revisions",
        ("portfolio_profile_id", "profile_revision"),
        ("profile_revision",),
    ),
    RecordDescriptor(
        "portfolio_profile_binding",
        PortfolioProfileBinding,
        "profile_bindings",
        ("profile_binding_id",),
    ),
    RecordDescriptor(
        "portfolio_profile_requirement",
        PortfolioProfileRequirement,
        None,
        ("portfolio_profile_id", "profile_revision", "requirement_id"),
        ("profile_revision",),
    ),
    RecordDescriptor(
        "portfolio_profile_lifecycle_event",
        PortfolioProfileLifecycleEvent,
        None,
        ("profile_lifecycle_event_id",),
    ),
    RecordDescriptor(
        "portfolio_profile_overlay_revision",
        PortfolioProfileOverlayRevision,
        None,
        ("overlay_id", "overlay_revision"),
        ("overlay_revision",),
    ),
    RecordDescriptor(
        "portfolio_profile_composition",
        PortfolioProfileComposition,
        None,
        ("profile_composition_id",),
    ),
    RecordDescriptor(
        "portfolio_profile_migration",
        PortfolioProfileMigration,
        None,
        ("profile_migration_id",),
    ),
    RecordDescriptor(
        "candidate_evaluation",
        CandidateEvaluation,
        "candidate_evaluations",
        ("candidate_evaluation_id",),
    ),
    RecordDescriptor(
        "candidate_current_evaluation_pointer_revision",
        CandidateCurrentEvaluationPointerRevision,
        None,
        ("candidate_id", "pointer_revision"),
        ("pointer_revision",),
    ),
    RecordDescriptor(
        "portfolio_candidate",
        PortfolioCandidate,
        "candidates",
        ("candidate_id",),
    ),
    RecordDescriptor(
        "portfolio_selection",
        PortfolioSelection,
        "selections",
        ("selection_id",),
    ),
    RecordDescriptor(
        "portfolio_placement",
        PortfolioPlacement,
        "placements",
        ("placement_id",),
    ),
    RecordDescriptor(
        "section_arrangement_revision",
        SectionArrangementRevision,
        "arrangements",
        ("arrangement_id",),
    ),
    RecordDescriptor(
        "working_portfolio_composition_revision",
        WorkingPortfolioCompositionRevision,
        "compositions",
        ("portfolio_id", "composition_revision"),
        ("composition_revision",),
    ),
    RecordDescriptor(
        "selection_proposal",
        SelectionProposal,
        None,
        ("selection_proposal_id",),
    ),
    RecordDescriptor(
        "selection_decision",
        SelectionDecision,
        None,
        ("selection_decision_id",),
    ),
    RecordDescriptor(
        "selection_lifecycle_event",
        SelectionLifecycleEvent,
        None,
        ("selection_lifecycle_event_id",),
    ),
    RecordDescriptor(
        "placement_lifecycle_event",
        PlacementLifecycleEvent,
        None,
        ("placement_lifecycle_event_id",),
    ),
    RecordDescriptor(
        "section_arrangement_pointer_revision",
        SectionArrangementPointerRevision,
        None,
        ("arrangement_pointer_id", "pointer_revision"),
        ("pointer_revision",),
    ),
    RecordDescriptor(
        "curation_rationale",
        CurationRationale,
        None,
        ("rationale_id",),
    ),
    RecordDescriptor(
        "curation_annotation",
        CurationAnnotation,
        None,
        ("annotation_id", "annotation_revision"),
        ("annotation_revision",),
    ),
    RecordDescriptor(
        "portfolio_reflection",
        PortfolioReflection,
        None,
        ("reflection_id", "reflection_revision"),
        ("reflection_revision",),
    ),
    RecordDescriptor(
        "curation_review_decision",
        CurationReviewDecision,
        None,
        ("curation_review_decision_id",),
    ),
    RecordDescriptor(
        "working_portfolio_composition_inventory",
        WorkingPortfolioCompositionInventory,
        None,
        ("portfolio_id", "composition_revision"),
        ("composition_revision",),
    ),
    RecordDescriptor(
        "working_portfolio_composition_pointer_revision",
        WorkingPortfolioCompositionPointerRevision,
        None,
        ("composition_pointer_id", "pointer_revision"),
        ("pointer_revision",),
    ),
    RecordDescriptor(
        "audience_context",
        AudienceContext,
        "audience_contexts",
        ("audience_context_id",),
    ),
    RecordDescriptor(
        "snapshot_materialization",
        SnapshotMaterializationRecord,
        "materializations",
        ("materialization_id",),
    ),
    RecordDescriptor(
        "snapshot_entry",
        SnapshotEntry,
        "snapshot_entries",
        ("snapshot_entry_id",),
    ),
    RecordDescriptor(
        "snapshot_omission",
        SnapshotOmission,
        "snapshot_omissions",
        ("snapshot_omission_id",),
    ),
    RecordDescriptor(
        "snapshot_manifest",
        SnapshotManifest,
        "snapshot_manifests",
        ("manifest_id",),
    ),
    RecordDescriptor(
        "snapshot_seal",
        SnapshotSeal,
        "snapshot_seals",
        ("seal_id",),
    ),
    RecordDescriptor(
        "snapshot_edition",
        SnapshotEdition,
        "snapshot_editions",
        ("snapshot_series_id", "edition_number"),
        ("edition_number",),
    ),
    RecordDescriptor(
        "snapshot_series",
        SnapshotSeries,
        None,
        ("snapshot_series_id",),
    ),
    RecordDescriptor(
        "snapshot_build_request",
        SnapshotBuildRequest,
        None,
        ("snapshot_build_request_id",),
    ),
    RecordDescriptor(
        "snapshot_build_plan",
        SnapshotBuildPlan,
        None,
        ("snapshot_build_plan_id",),
    ),
    RecordDescriptor(
        "snapshot_build_attempt",
        SnapshotBuildAttempt,
        None,
        ("snapshot_build_attempt_id",),
    ),
    RecordDescriptor(
        "snapshot_build_attempt_result",
        SnapshotBuildAttemptResult,
        None,
        ("snapshot_build_attempt_result_id",),
    ),
    RecordDescriptor(
        "snapshot_materialization_provenance",
        SnapshotMaterializationProvenance,
        None,
        ("snapshot_materialization_provenance_id",),
    ),
    RecordDescriptor(
        "snapshot_edition_build_provenance",
        SnapshotEditionBuildProvenance,
        None,
        ("snapshot_edition_build_provenance_id",),
    ),
    RecordDescriptor(
        "snapshot_export_artifact",
        SnapshotExportArtifact,
        None,
        ("snapshot_export_artifact_id",),
    ),
    RecordDescriptor(
        "snapshot_current_pointer_revision",
        SnapshotCurrentPointerRevision,
        None,
        ("snapshot_current_pointer_id", "pointer_revision"),
        ("pointer_revision",),
    ),
)

DESCRIPTOR_BY_RECORD_TYPE = {item.record_type: item for item in RECORD_DESCRIPTORS}
DESCRIPTOR_BY_MODEL_TYPE = {item.model_type: item for item in RECORD_DESCRIPTORS}
DESCRIPTOR_BY_GRAPH_COLLECTION: dict[str, RecordDescriptor] = {
    item.graph_collection: item
    for item in RECORD_DESCRIPTORS
    if item.graph_collection is not None
}


def descriptor_for_record_type(record_type: str) -> RecordDescriptor:
    try:
        return DESCRIPTOR_BY_RECORD_TYPE[record_type]
    except (KeyError, TypeError) as error:
        raise ValueError(f"unsupported Vitrine record_type {record_type!r}.") from error


def descriptor_for_record(record: object) -> RecordDescriptor:
    try:
        return DESCRIPTOR_BY_MODEL_TYPE[type(record)]
    except KeyError as error:
        raise ValueError(
            f"unsupported Vitrine record type {type(record).__name__}."
        ) from error


def identity_segments_for_record(record: object) -> tuple[str, ...]:
    descriptor = descriptor_for_record(record)
    integer_fields = set(descriptor.integer_identity_fields)
    segments: list[str] = []
    for field_name in descriptor.identity_fields:
        value = getattr(record, field_name)
        if field_name in integer_fields:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{field_name} must be a positive integer.")
            segments.append(str(value))
        else:
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string.")
            segments.append(value)
    return tuple(segments)


__all__ = [
    "DESCRIPTOR_BY_GRAPH_COLLECTION",
    "DESCRIPTOR_BY_MODEL_TYPE",
    "DESCRIPTOR_BY_RECORD_TYPE",
    "RECORD_DESCRIPTORS",
    "RecordDescriptor",
    "descriptor_for_record",
    "descriptor_for_record_type",
    "identity_segments_for_record",
]
