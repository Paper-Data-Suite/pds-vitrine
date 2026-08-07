"""Authoritative descriptor registry for persisted Vitrine runtime records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vitrine.models.audiences import AudienceContext
from vitrine.models.candidates import CandidateEvaluation, PortfolioCandidate
from vitrine.models.curation import (
    PortfolioPlacement,
    PortfolioSelection,
    SectionArrangementRevision,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.identity import (
    Portfolio,
    PortfolioSubject,
    PortfolioSubjectClassLink,
)
from vitrine.models.profiles import (
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileRevision,
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
    graph_collection: str
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
        "candidate_evaluation",
        CandidateEvaluation,
        "candidate_evaluations",
        ("candidate_evaluation_id",),
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
)

DESCRIPTOR_BY_RECORD_TYPE = {item.record_type: item for item in RECORD_DESCRIPTORS}
DESCRIPTOR_BY_MODEL_TYPE = {item.model_type: item for item in RECORD_DESCRIPTORS}
DESCRIPTOR_BY_GRAPH_COLLECTION = {
    item.graph_collection: item for item in RECORD_DESCRIPTORS
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
