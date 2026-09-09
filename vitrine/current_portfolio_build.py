"""Read-only preparation for Build and Export Current Portfolio."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, TypeVar

from vitrine.current_portfolio_reflection import (
    CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
    current_portfolio_reflection_bytes,
    current_portfolio_reflection_configuration_digest,
    current_portfolio_reflection_output_digest,
    current_portfolio_reflection_supported,
)
from vitrine.models import (
    AudienceContext,
    CandidateEvaluation,
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioReflection,
    PortfolioSelection,
    SnapshotEntryPlan,
    SnapshotInputReference,
    SnapshotSeries,
    SourceArtifactReference,
)
from vitrine.snapshot_materialization import (
    SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE,
    SnapshotMaterializationError,
    SnapshotSourceProviderRegistry,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)
from vitrine.working_composition import (
    WorkingCompositionAudienceSummary,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPlacementSummary,
    WorkingCompositionPreparation,
    WorkingCompositionRequirementSummary,
    WorkingCompositionReviewSummary,
    WorkingCompositionSectionSummary,
    WorkingCompositionSelectionSummary,
    WorkingCompositionSourceObservation,
    prepare_working_composition,
)

CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION: Final[str] = (
    "vitrine_build_export_current_portfolio_v1"
)
CURRENT_PORTFOLIO_EXPORT_FORMAT: Final[str] = "directory_package"

_ENTRY_ID_DOMAIN: Final[str] = "vitrine_current_portfolio_entry_plan_v1"
_EXPORT_ID_DOMAIN: Final[str] = "vitrine_current_portfolio_export_plan_v1"
_EXPORT_CONFIG_DOMAIN: Final[str] = "vitrine_current_portfolio_export_config_v1"
_PATH_ID_DOMAIN: Final[str] = "vitrine_current_portfolio_entry_path_v1"

_BYTE_CAPABLE_FIRST_PARTY_PRODUCERS: Final[frozenset[str]] = frozenset(
    {"quillan", "concord"}
)

_CONTENT_CLASS_BY_ARTIFACT_KIND: Final[dict[str, str]] = {
    "assessment_summary": "assessment_summary",
    "collaborative_artifact": "student_work",
    "original_student_work": "student_work",
    "rendered_feedback": "feedback",
}
_MEDIA_SUFFIX_BY_TYPE: Final[dict[str, str]] = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
        ".pptx"
    ),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        ".docx"
    ),
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "text/markdown": ".md",
    "text/plain": ".txt",
}

CURRENT_PORTFOLIO_BUILD_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "current_portfolio_build.invalid_request",
        "current_portfolio_build.context_not_found",
        "current_portfolio_build.state_changed",
        "current_portfolio_build.audience_rule_not_found",
        "current_portfolio_build.audience_context_invalid_choice",
        "current_portfolio_build.snapshot_series_invalid_choice",
        "current_portfolio_build.source_context_invalid",
        "current_portfolio_build.reflection_context_invalid",
    }
)

CURRENT_PORTFOLIO_BUILD_BLOCKING_REASONS: Final[frozenset[str]] = frozenset(
    {
        "working_composition_requires_freeze",
        "unplaced_selections",
        "audience_context_choice_required",
        "snapshot_series_choice_required",
        "missing_required_reviews",
        "unresolved_obligations_acknowledgement_required",
        "source_artifact_unavailable",
        "source_provider_conflict",
        "unsupported_reflection_rendering",
        "unsupported_reflection_placement",
        "reflection_audience_prohibited",
        "directory_export_empty",
    }
)

SATISFYING_REVIEW_DECISIONS: Final[frozenset[str]] = frozenset(
    {"approved", "acknowledged", "waived"}
)
T = TypeVar("T")


class CurrentPortfolioBuildError(RuntimeError):
    """Expected read-only Current Portfolio preparation failure."""

    def __init__(self, code: str, message: str) -> None:
        if code not in CURRENT_PORTFOLIO_BUILD_ERROR_CODES:
            raise ValueError(f"unsupported Current Portfolio build error code: {code}")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CurrentPortfolioAudienceContextResolution:
    disposition: str
    matching_audience_context_ids: tuple[str, ...]
    selected_audience_context_id: str | None

    def __post_init__(self) -> None:
        if self.disposition not in {"create", "reuse", "requires_choice"}:
            raise ValueError("unsupported Audience Context disposition")
        if self.disposition == "reuse" and self.selected_audience_context_id is None:
            raise ValueError("reuse requires one selected Audience Context")
        if (
            self.disposition != "reuse"
            and self.selected_audience_context_id is not None
        ):
            raise ValueError("only reuse may identify a selected Audience Context")


@dataclass(frozen=True, slots=True)
class CurrentPortfolioSnapshotSeriesResolution:
    disposition: str
    matching_snapshot_series_ids: tuple[str, ...]
    selected_snapshot_series_id: str | None
    resolution_deferred_for_audience_context: bool = False

    def __post_init__(self) -> None:
        if self.disposition not in {"create", "reuse", "requires_choice"}:
            raise ValueError("unsupported Snapshot Series disposition")
        if self.disposition == "reuse" and self.selected_snapshot_series_id is None:
            raise ValueError("reuse requires one selected Snapshot Series")
        if self.disposition != "reuse" and self.selected_snapshot_series_id is not None:
            raise ValueError("only reuse may identify a selected Snapshot Series")
        if self.resolution_deferred_for_audience_context:
            if self.disposition != "requires_choice":
                raise ValueError(
                    "deferred Snapshot Series resolution requires requires_choice"
                )
            if self.matching_snapshot_series_ids:
                raise ValueError(
                    "deferred Snapshot Series resolution cannot claim exact matches"
                )


@dataclass(frozen=True, slots=True)
class CurrentPortfolioRequiredReview:
    review_class: str
    profile_requirement_ids: tuple[str, ...]
    satisfying_review_decision_ids: tuple[str, ...]

    @property
    def satisfied(self) -> bool:
        return bool(self.satisfying_review_decision_ids)


@dataclass(frozen=True, slots=True)
class CurrentPortfolioPlannedItem:
    """One transient first-party source-backed logical Snapshot item."""

    entry_plan_id: str
    plan_position: int
    section_id: str
    section_label: str
    section_order: int
    position_in_section: int
    placement_id: str
    selection_id: str
    candidate_id: str
    candidate_evaluation_id: str
    source_publication_id: str
    producer_module_id: str
    projection_kind: str
    projection_contract_version: str
    source_artifact: SourceArtifactReference | None
    source_current_use_state: str
    content_class: str
    materialization_kind: str
    provider_disposition: str
    provider_id: str | None
    provider_version: str | None
    provider_support_key: tuple[str, ...] | None
    provider_concrete_media_types: tuple[str, ...]
    target_relative_path: str | None
    media_type: str | None
    export_file: bool
    permitted_omission_reason: str | None
    display_label: str
    explanation: str
    entry_plan: SnapshotEntryPlan | None


@dataclass(frozen=True, slots=True)
class CurrentPortfolioGeneratedReflection:
    """One exact frozen Reflection planned as deterministic Vitrine bytes."""

    entry_plan_id: str
    plan_position: int
    section_id: str | None
    section_label: str | None
    section_order: int | None
    position_in_section: int | None
    reflection_id: str
    reflection_revision: int
    reflection_requirement_id: str
    prompt_id: str
    prompt_version: str
    prompt_snapshot_sha256: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    content_mode: str
    content_format: str
    language: str
    content_sha256: str
    content_class: str
    materialization_kind: str
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    renderer_configuration_sha256: str
    renderer_template_sha256: str | None
    target_relative_path: str | None
    media_type: str | None
    output_byte_size: int | None
    output_sha256: str | None
    export_file: bool
    supported: bool
    explanation: str
    entry_plan: SnapshotEntryPlan | None


@dataclass(frozen=True, slots=True)
class CurrentPortfolioDirectoryExportPreview:
    """Transient deterministic directory-package partition."""

    export_plan_id: str
    export_format: str
    export_contract_version: str
    included_entry_plan_ids: tuple[str, ...]
    excluded_entry_plan_ids: tuple[str, ...]
    configuration_sha256: str


@dataclass(frozen=True, slots=True)
class CurrentPortfolioBuildPreparation:
    contract_version: str
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision_id: str
    profile_revision_number: int
    current_composition_pointer_revision: int | None
    current_composition_revision: int | None
    working_composition_preparation_fingerprint: str
    working_composition_disposition: str
    composition_inventory: WorkingCompositionPayloadPreview
    sections: tuple[WorkingCompositionSectionSummary, ...]
    selections: tuple[WorkingCompositionSelectionSummary, ...]
    unplaced_selection_ids: tuple[str, ...]
    selected_audience_rule: WorkingCompositionAudienceSummary
    audience_context: CurrentPortfolioAudienceContextResolution
    snapshot_series: CurrentPortfolioSnapshotSeriesResolution
    required_reviews: tuple[CurrentPortfolioRequiredReview, ...]
    applicable_review_decisions: tuple[WorkingCompositionReviewSummary, ...]
    missing_required_review_classes: tuple[str, ...]
    unresolved_obligation_codes: tuple[str, ...]
    acknowledged_obligation_codes: tuple[str, ...]
    obligation_acknowledgement_complete: bool
    planned_items: tuple[CurrentPortfolioPlannedItem, ...]
    generated_reflections: tuple[CurrentPortfolioGeneratedReflection, ...]
    directory_export: CurrentPortfolioDirectoryExportPreview
    warnings: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    preparation_fingerprint: str

    @property
    def ready_for_plan_execution(self) -> bool:
        """Whether this preparation has no known first-party blocker."""
        return not self.blocking_reasons

    @property
    def snapshot_entry_plans(self) -> tuple[SnapshotEntryPlan, ...]:
        """Return exact executable Entry Plans in reviewed logical order."""

        values: list[SnapshotEntryPlan] = []
        for item in self.planned_items:
            if item.entry_plan is not None:
                values.append(item.entry_plan)
        for reflection in self.generated_reflections:
            if reflection.entry_plan is not None:
                values.append(reflection.entry_plan)
        return tuple(sorted(values, key=lambda item: item.plan_position))


def _hash_value(domain: str, value: object) -> str:
    encoded = json.dumps(
        {"domain": domain, "value": value},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selected_audience_rule(
    preparation: WorkingCompositionPreparation,
    audience_rule_id: str,
) -> WorkingCompositionAudienceSummary:
    matches = tuple(
        rule
        for rule in preparation.audience_rules
        if rule.audience_rule_id == audience_rule_id
    )
    if len(matches) != 1:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.audience_rule_not_found",
            "Audience rule is not in the exact Profile Revision bound to the "
            "current Working Composition.",
        )
    return matches[0]


def _context_matches_rule(
    context: AudienceContext,
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
) -> bool:
    return (
        context.portfolio_id == preparation.portfolio_id
        and context.portfolio_subject_id == preparation.portfolio_subject_id
        and context.profile_binding_id == preparation.profile_binding_id
        and context.profile_revision.portfolio_profile_id
        == preparation.profile_revision_id
        and context.profile_revision.profile_revision
        == preparation.profile_revision_number
        and context.audience_rule_id == rule.audience_rule_id
        and context.audience_class == rule.audience_class
        and context.purpose == rule.purpose
        and context.subject_scope == "portfolio_subject"
        and context.allowed_content_classes == rule.allowed_content_classes
        and context.prohibited_content_classes == rule.prohibited_content_classes
        and context.required_review_classes == rule.required_review_classes
        and context.presentation_class == rule.presentation_class
        and context.retention_policy_reference == rule.retention_policy_reference
    )


def _resolve_audience_context(
    records: tuple[object, ...],
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
    requested_audience_context_id: str | None,
) -> CurrentPortfolioAudienceContextResolution:
    matches = tuple(
        item
        for item in records
        if isinstance(item, AudienceContext)
        and _context_matches_rule(item, preparation, rule)
    )
    match_ids = tuple(sorted(item.audience_context_id for item in matches))

    if requested_audience_context_id is not None:
        if requested_audience_context_id not in match_ids:
            raise CurrentPortfolioBuildError(
                "current_portfolio_build.audience_context_invalid_choice",
                "Chosen Audience Context is not an exact match for the reviewed "
                "Portfolio, Profile Revision, and audience rule.",
            )
        return CurrentPortfolioAudienceContextResolution(
            disposition="reuse",
            matching_audience_context_ids=match_ids,
            selected_audience_context_id=requested_audience_context_id,
        )

    if not matches:
        return CurrentPortfolioAudienceContextResolution(
            disposition="create",
            matching_audience_context_ids=(),
            selected_audience_context_id=None,
        )
    if len(matches) == 1:
        return CurrentPortfolioAudienceContextResolution(
            disposition="reuse",
            matching_audience_context_ids=match_ids,
            selected_audience_context_id=match_ids[0],
        )
    return CurrentPortfolioAudienceContextResolution(
        disposition="requires_choice",
        matching_audience_context_ids=match_ids,
        selected_audience_context_id=None,
    )


def _resolve_snapshot_series(
    records: tuple[object, ...],
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
    audience_context: CurrentPortfolioAudienceContextResolution,
    requested_snapshot_series_id: str | None,
) -> CurrentPortfolioSnapshotSeriesResolution:
    if audience_context.disposition == "create":
        if requested_snapshot_series_id is not None:
            raise CurrentPortfolioBuildError(
                "current_portfolio_build.snapshot_series_invalid_choice",
                "A Snapshot Series cannot be chosen before the exact new Audience "
                "Context exists.",
            )
        return CurrentPortfolioSnapshotSeriesResolution(
            disposition="create",
            matching_snapshot_series_ids=(),
            selected_snapshot_series_id=None,
        )

    audience_context_id = audience_context.selected_audience_context_id
    if audience_context_id is None:
        if requested_snapshot_series_id is not None:
            raise CurrentPortfolioBuildError(
                "current_portfolio_build.snapshot_series_invalid_choice",
                "Choose the exact Audience Context before choosing a Snapshot Series.",
            )
        return CurrentPortfolioSnapshotSeriesResolution(
            disposition="requires_choice",
            matching_snapshot_series_ids=(),
            selected_snapshot_series_id=None,
            resolution_deferred_for_audience_context=True,
        )

    matches = tuple(
        item
        for item in records
        if isinstance(item, SnapshotSeries)
        and item.portfolio_id == preparation.portfolio_id
        and item.portfolio_subject_id == preparation.portfolio_subject_id
        and item.audience_context_id == audience_context_id
        and item.snapshot_purpose == rule.purpose
    )
    match_ids = tuple(sorted(item.snapshot_series_id for item in matches))

    if requested_snapshot_series_id is not None:
        if requested_snapshot_series_id not in match_ids:
            raise CurrentPortfolioBuildError(
                "current_portfolio_build.snapshot_series_invalid_choice",
                "Chosen Snapshot Series does not exactly match this Portfolio, "
                "Subject, Audience Context, and Snapshot purpose.",
            )
        return CurrentPortfolioSnapshotSeriesResolution(
            disposition="reuse",
            matching_snapshot_series_ids=match_ids,
            selected_snapshot_series_id=requested_snapshot_series_id,
        )

    if not matches:
        return CurrentPortfolioSnapshotSeriesResolution(
            disposition="create",
            matching_snapshot_series_ids=(),
            selected_snapshot_series_id=None,
        )
    if len(matches) == 1:
        return CurrentPortfolioSnapshotSeriesResolution(
            disposition="reuse",
            matching_snapshot_series_ids=match_ids,
            selected_snapshot_series_id=match_ids[0],
        )
    return CurrentPortfolioSnapshotSeriesResolution(
        disposition="requires_choice",
        matching_snapshot_series_ids=match_ids,
        selected_snapshot_series_id=None,
    )


def _required_reviews(
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
) -> tuple[CurrentPortfolioRequiredReview, ...]:
    summaries: list[CurrentPortfolioRequiredReview] = []
    for review_class in rule.required_review_classes:
        requirement_ids = tuple(
            requirement.requirement_id
            for requirement in preparation.requirements
            if requirement.satisfaction_class == review_class
        )
        satisfying_review_ids = tuple(
            review.curation_review_decision_id
            for review in preparation.reviews
            if review.approval_requirement_id in requirement_ids
            and review.decision in SATISFYING_REVIEW_DECISIONS
            and not review.requires_attention
        )
        summaries.append(
            CurrentPortfolioRequiredReview(
                review_class=review_class,
                profile_requirement_ids=requirement_ids,
                satisfying_review_decision_ids=satisfying_review_ids,
            )
        )
    return tuple(summaries)


def _required_review_ids(
    required_reviews: tuple[CurrentPortfolioRequiredReview, ...],
) -> tuple[str, ...]:
    values: list[str] = []
    for review in required_reviews:
        for review_id in review.satisfying_review_decision_ids:
            if review_id not in values:
                values.append(review_id)
    return tuple(values)


def _acknowledged_obligations(
    unresolved_codes: tuple[str, ...],
    requested_codes: tuple[str, ...],
) -> tuple[str, ...]:
    if len(set(requested_codes)) != len(requested_codes):
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.invalid_request",
            "Acknowledged obligation codes must not contain duplicates.",
        )
    unresolved = set(unresolved_codes)
    if any(code not in unresolved for code in requested_codes):
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.invalid_request",
            "Only exact unresolved Composition obligation codes may be acknowledged.",
        )
    requested = set(requested_codes)
    return tuple(code for code in unresolved_codes if code in requested)


def _one_record(
    records: tuple[object, ...],
    record_type: type[T],
    predicate: Callable[[T], bool],
    message: str,
) -> T:
    matches = tuple(
        item
        for item in records
        if isinstance(item, record_type) and predicate(item)
    )
    if len(matches) != 1:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.source_context_invalid",
            message,
        )
    return matches[0]


def _source_observation(
    preparation: WorkingCompositionPreparation,
    selection_id: str,
    candidate_id: str,
    publication_id: str,
) -> WorkingCompositionSourceObservation:
    matches = tuple(
        item
        for item in preparation.source_observations
        if item.selection_id == selection_id
        and item.candidate_id == candidate_id
        and item.publication_id == publication_id
    )
    if len(matches) != 1:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.source_context_invalid",
            "Exact frozen source-currentness observation is unavailable.",
        )
    return matches[0]


def _content_class(artifact: SourceArtifactReference) -> str:
    return _CONTENT_CLASS_BY_ARTIFACT_KIND.get(
        artifact.artifact_kind, artifact.artifact_kind
    )


def _audience_prohibits(
    rule: WorkingCompositionAudienceSummary,
    content_class: str,
) -> bool:
    if content_class in rule.prohibited_content_classes:
        return True
    return bool(
        rule.allowed_content_classes
        and content_class not in rule.allowed_content_classes
    )


def _entry_semantic_value(
    *,
    preparation: WorkingCompositionPreparation,
    section_id: str,
    section_order: int,
    position_in_section: int,
    placement_id: str,
    selection_id: str,
    candidate_id: str,
    candidate_evaluation_id: str,
    publication_id: str,
    producer_module_id: str,
    projection_kind: str,
    projection_contract_version: str,
    artifact: SourceArtifactReference | None,
) -> dict[str, object]:
    return {
        "contract_version": CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        "portfolio_id": preparation.portfolio_id,
        "portfolio_subject_id": preparation.portfolio_subject_id,
        "profile_binding_id": preparation.profile_binding_id,
        "profile_revision_id": preparation.profile_revision_id,
        "profile_revision_number": preparation.profile_revision_number,
        "composition_revision": preparation.current_composition_revision,
        "section_id": section_id,
        "section_order": section_order,
        "position_in_section": position_in_section,
        "placement_id": placement_id,
        "selection_id": selection_id,
        "candidate_id": candidate_id,
        "candidate_evaluation_id": candidate_evaluation_id,
        "source_publication_id": publication_id,
        "producer_module_id": producer_module_id,
        "projection_kind": projection_kind,
        "projection_contract_version": projection_contract_version,
        "source_artifact": (
            None
            if artifact is None
            else {
                "artifact_id": artifact.artifact_id,
                "artifact_kind": artifact.artifact_kind,
                "representation_kind": artifact.representation_kind,
                "media_type": artifact.media_type,
                "source_locator": artifact.source_locator,
                "native_revision": artifact.native_revision,
                "source_digest": (
                    None
                    if artifact.source_digest is None
                    else {
                        "algorithm": artifact.source_digest.algorithm,
                        "value": artifact.source_digest.value,
                    }
                ),
                "byte_size": artifact.byte_size,
                "language": artifact.language,
                "accessibility_relationship": artifact.accessibility_relationship,
            }
        ),
    }


def _target_path(
    *,
    section_order: int,
    position_in_section: int,
    semantic_value: dict[str, object],
    media_type: str,
) -> str:
    token = _hash_value(_PATH_ID_DOMAIN, semantic_value)[:16]
    suffix = ""
    if media_type != SNAPSHOT_DEFERRED_SOURCE_MEDIA_TYPE:
        suffix = _MEDIA_SUFFIX_BY_TYPE.get(media_type, "")
    return (
        f"section-{section_order:02d}/"
        f"{position_in_section:02d}-entry-{token}{suffix}"
    )


def _probe_entry(
    *,
    semantic_value: dict[str, object],
    section_id: str,
    section_order: int,
    position_in_section: int,
    placement_id: str,
    selection: PortfolioSelection,
    candidate: PortfolioCandidate,
    evaluation: CandidateEvaluation,
    artifact: SourceArtifactReference,
) -> SnapshotEntryPlan:
    endpoint = candidate.source_endpoint
    target = _target_path(
        section_order=section_order,
        position_in_section=position_in_section,
        semantic_value=semantic_value,
        media_type=artifact.media_type,
    )
    return SnapshotEntryPlan(
        entry_plan_id=f"entry_probe_{_hash_value(_ENTRY_ID_DOMAIN, semantic_value)}",
        plan_position=1,
        section_id=section_id,
        ordinal=position_in_section,
        semantic_role=_content_class(artifact),
        materialization_kind="copied_source",
        content_class=_content_class(artifact),
        selection_id=selection.selection_id,
        placement_id=placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_publication_id=endpoint.core_publication.publication_id,
        producer_module_id=endpoint.producer_source.producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=(
            endpoint.producer_source.projection_contract_version
        ),
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=target,
        media_type=artifact.media_type,
    )


def _final_entry_id(
    semantic_value: dict[str, object],
    *,
    materialization_kind: str,
    provider_disposition: str,
    provider_id: str | None,
    provider_version: str | None,
    omission_reason: str | None,
) -> str:
    value = {
        "semantic": semantic_value,
        "materialization_kind": materialization_kind,
        "provider_disposition": provider_disposition,
        "provider_id": provider_id,
        "provider_version": provider_version,
        "permitted_omission_reason": omission_reason,
    }
    return f"entry_plan_{_hash_value(_ENTRY_ID_DOMAIN, value)}"


def _planned_source_item(
    *,
    records: tuple[object, ...],
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
    required_review_ids: tuple[str, ...],
    source_providers: SnapshotSourceProviderRegistry,
    section: WorkingCompositionSectionSummary,
    placement: WorkingCompositionPlacementSummary,
    plan_position: int,
    position_in_section: int,
) -> tuple[CurrentPortfolioPlannedItem, tuple[str, ...], tuple[str, ...]]:
    placement_id = placement.placement_id
    selection_id = placement.selection_id
    candidate_id = placement.candidate_id
    selection = _one_record(
        records,
        PortfolioSelection,
        lambda item: item.selection_id == selection_id,
        "Exact frozen Selection is unavailable for Current Portfolio planning.",
    )
    assert isinstance(selection, PortfolioSelection)
    if selection.candidate_id != candidate_id:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.source_context_invalid",
            "Frozen Placement and Selection Candidate identities do not match.",
        )
    candidate = _one_record(
        records,
        PortfolioCandidate,
        lambda item: item.candidate_id == candidate_id,
        "Exact frozen Candidate is unavailable for Current Portfolio planning.",
    )
    assert isinstance(candidate, PortfolioCandidate)
    evaluation = _one_record(
        records,
        CandidateEvaluation,
        lambda item: item.candidate_evaluation_id
        == selection.candidate_evaluation_id,
        "Exact frozen Candidate Evaluation is unavailable for Current Portfolio "
        "planning.",
    )
    assert isinstance(evaluation, CandidateEvaluation)
    if candidate.candidate_evaluation_id != evaluation.candidate_evaluation_id:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.source_context_invalid",
            "Frozen Candidate and Selection Evaluation identities do not match.",
        )

    endpoint = candidate.source_endpoint
    publication_id = endpoint.core_publication.publication_id
    producer_module_id = endpoint.producer_source.producer_module_id
    projection_contract_version = endpoint.producer_source.projection_contract_version
    artifact = endpoint.source_artifact
    projection_kind = (
        endpoint.producer_source.source_record_kind
        if artifact is None
        else artifact.representation_kind
    )
    observation = _source_observation(
        preparation, selection_id, candidate_id, publication_id
    )
    display_label = placement.display_title or placement.candidate_display_snapshot

    semantic_value = _entry_semantic_value(
        preparation=preparation,
        section_id=section.section_id,
        section_order=section.order,
        position_in_section=position_in_section,
        placement_id=placement_id,
        selection_id=selection_id,
        candidate_id=candidate_id,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        publication_id=publication_id,
        producer_module_id=producer_module_id,
        projection_kind=projection_kind,
        projection_contract_version=projection_contract_version,
        artifact=artifact,
    )

    blockers: list[str] = []
    warnings: list[str] = []
    if observation.current_use_state != "current":
        warnings.append("source_current_use_attention")

    if artifact is None:
        blockers.append("source_artifact_unavailable")
        entry_plan_id = _final_entry_id(
            semantic_value,
            materialization_kind="reference_only",
            provider_disposition="source_artifact_unavailable",
            provider_id=None,
            provider_version=None,
            omission_reason=None,
        )
        return (
            CurrentPortfolioPlannedItem(
                entry_plan_id=entry_plan_id,
                plan_position=plan_position,
                section_id=section.section_id,
                section_label=section.label,
                section_order=section.order,
                position_in_section=position_in_section,
                placement_id=placement_id,
                selection_id=selection_id,
                candidate_id=candidate_id,
                candidate_evaluation_id=evaluation.candidate_evaluation_id,
                source_publication_id=publication_id,
                producer_module_id=producer_module_id,
                projection_kind=projection_kind,
                projection_contract_version=projection_contract_version,
                source_artifact=None,
                source_current_use_state=observation.current_use_state,
                content_class="source_evidence",
                materialization_kind="reference_only",
                provider_disposition="source_artifact_unavailable",
                provider_id=None,
                provider_version=None,
                provider_support_key=None,
                provider_concrete_media_types=(),
                target_relative_path=None,
                media_type=None,
                export_file=False,
                permitted_omission_reason=None,
                display_label=display_label,
                explanation=(
                    "Exact source Artifact is unavailable; first-party planning "
                    "cannot construct a canonical source Entry."
                ),
                entry_plan=None,
            ),
            tuple(warnings),
            tuple(blockers),
        )

    content_class = _content_class(artifact)
    materialization_kind = "reference_only"
    provider_disposition = "reference_only_no_exact_provider"
    provider_id: str | None = None
    provider_version: str | None = None
    provider_support_key: tuple[str, ...] | None = None
    provider_concrete_media_types: tuple[str, ...] = ()
    omission_reason: str | None = None
    explanation = (
        "Reference only because no exact byte-capable Snapshot source provider "
        "is configured; no file will appear in the directory Export."
    )

    if _audience_prohibits(rule, content_class):
        provider_disposition = "audience_prohibited"
        omission_reason = "audience_prohibited"
        explanation = (
            "Explicit audience-prohibited omission; source provenance remains "
            "represented and no Export file is planned."
        )
    elif producer_module_id == "scoreform" and artifact.artifact_kind == (
        "assessment_summary"
    ):
        provider_disposition = "reference_only_by_producer_contract"
        explanation = (
            "ScoreForm assessment summary is reference only by released producer "
            "contract; Snapshot provenance is preserved and no Export file is planned."
        )
    elif producer_module_id not in _BYTE_CAPABLE_FIRST_PARTY_PRODUCERS:
        provider_disposition = "reference_only_by_first_party_policy"
        explanation = (
            "This producer has no first-party byte-materialization policy in the "
            "Current Portfolio task; exact provenance remains reference only."
        )
    else:
        probe = _probe_entry(
            semantic_value=semantic_value,
            section_id=section.section_id,
            section_order=section.order,
            position_in_section=position_in_section,
            placement_id=placement_id,
            selection=selection,
            candidate=candidate,
            evaluation=evaluation,
            artifact=artifact,
        )
        try:
            provider = source_providers.select(probe)
        except SnapshotMaterializationError as error:
            if error.code == "snapshot.source_provider_missing":
                pass
            elif error.code == "snapshot.source_provider_conflict":
                provider_disposition = "source_provider_conflict"
                blockers.append("source_provider_conflict")
                explanation = (
                    "Multiple exact Snapshot source providers match this source "
                    "contract; first-party planning fails closed."
                )
            else:
                raise
        else:
            descriptor = provider.descriptor
            materialization_kind = "copied_source"
            provider_disposition = "exact_provider"
            provider_id = descriptor.provider_id
            provider_version = descriptor.provider_version
            provider_support_key = descriptor.support_key
            provider_concrete_media_types = descriptor.concrete_media_types
            explanation = (
                "Exact byte-capable Snapshot source provider matched; producer "
                "Artifact authorization remains deferred to execution."
            )

    entry_plan_id = _final_entry_id(
        semantic_value,
        materialization_kind=materialization_kind,
        provider_disposition=provider_disposition,
        provider_id=provider_id,
        provider_version=provider_version,
        omission_reason=omission_reason,
    )
    target_relative_path = None
    media_type = None
    export_file = False
    if materialization_kind == "copied_source":
        target_relative_path = _target_path(
            section_order=section.order,
            position_in_section=position_in_section,
            semantic_value=semantic_value,
            media_type=artifact.media_type,
        )
        media_type = artifact.media_type
        export_file = True

    entry_plan = SnapshotEntryPlan(
        entry_plan_id=entry_plan_id,
        plan_position=plan_position,
        section_id=section.section_id,
        ordinal=position_in_section,
        semantic_role=content_class,
        materialization_kind=materialization_kind,
        content_class=content_class,
        selection_id=selection.selection_id,
        placement_id=placement_id,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_publication_id=publication_id,
        producer_module_id=producer_module_id,
        projection_kind=artifact.representation_kind,
        projection_contract_version=projection_contract_version,
        source_artifact=artifact,
        producer_source_digest_claim=artifact.source_digest,
        target_relative_path=target_relative_path,
        media_type=media_type,
        required_review_ids=required_review_ids,
        permitted_omission_reason=omission_reason,
    )
    return (
        CurrentPortfolioPlannedItem(
            entry_plan_id=entry_plan_id,
            plan_position=plan_position,
            section_id=None if section is None else section.section_id,
            section_label=None if section is None else section.label,
            section_order=None if section is None else section.order,
            position_in_section=position_in_section,
            placement_id=placement_id,
            selection_id=selection.selection_id,
            candidate_id=candidate.candidate_id,
            candidate_evaluation_id=evaluation.candidate_evaluation_id,
            source_publication_id=publication_id,
            producer_module_id=producer_module_id,
            projection_kind=artifact.representation_kind,
            projection_contract_version=projection_contract_version,
            source_artifact=artifact,
            source_current_use_state=observation.current_use_state,
            content_class=content_class,
            materialization_kind=materialization_kind,
            provider_disposition=provider_disposition,
            provider_id=provider_id,
            provider_version=provider_version,
            provider_support_key=provider_support_key,
            provider_concrete_media_types=provider_concrete_media_types,
            target_relative_path=target_relative_path,
            media_type=media_type,
            export_file=export_file,
            permitted_omission_reason=omission_reason,
            display_label=display_label,
            explanation=explanation,
            entry_plan=entry_plan,
        ),
        tuple(warnings),
        tuple(blockers),
    )


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _exact_frozen_reflection(
    records: tuple[object, ...],
    preparation: WorkingCompositionPreparation,
    reflection_id: str,
    reflection_revision: int,
) -> PortfolioReflection:
    reflection = _one_record(
        records,
        PortfolioReflection,
        lambda item: item.reflection_id == reflection_id
        and item.reflection_revision == reflection_revision,
        "Exact frozen Portfolio Reflection revision is unavailable.",
    )
    assert isinstance(reflection, PortfolioReflection)
    expected_profile = (
        preparation.profile_revision_id,
        preparation.profile_revision_number,
    )
    actual_profile = (
        reflection.profile_revision.portfolio_profile_id,
        reflection.profile_revision.profile_revision,
    )
    if (
        reflection.portfolio_id != preparation.portfolio_id
        or reflection.portfolio_subject_id != preparation.portfolio_subject_id
        or reflection.profile_binding_id != preparation.profile_binding_id
        or actual_profile != expected_profile
    ):
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.reflection_context_invalid",
            "Frozen Portfolio Reflection belongs to another Portfolio/Profile context.",
        )
    return reflection


def _reflection_requirement(
    preparation: WorkingCompositionPreparation,
    reflection: PortfolioReflection,
) -> WorkingCompositionRequirementSummary:
    requirements = tuple(
        item
        for item in preparation.requirements
        if item.requirement_id == reflection.reflection_requirement_id
        and item.requirement_kind == "reflection"
    )
    if len(requirements) != 1:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.reflection_context_invalid",
            "Frozen Portfolio Reflection requirement does not resolve uniquely.",
        )
    return requirements[0]


def _reflection_section(
    preparation: WorkingCompositionPreparation,
    requirement: WorkingCompositionRequirementSummary,
) -> WorkingCompositionSectionSummary | None:
    if requirement.scope_kind != "section":
        return None
    if requirement.scope_reference is None:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.reflection_context_invalid",
            "Section-scoped Reflection requirement lacks an exact section reference.",
        )
    matches = tuple(
        section
        for section in preparation.sections
        if section.section_id == requirement.scope_reference
    )
    if len(matches) != 1:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.reflection_context_invalid",
            "Frozen Portfolio Reflection requirement references an unavailable "
            "section.",
        )
    return matches[0]


@dataclass(frozen=True, slots=True)
class _FrozenReflectionContext:
    reflection: PortfolioReflection
    requirement: WorkingCompositionRequirementSummary
    section: WorkingCompositionSectionSummary | None


def _frozen_reflection_contexts(
    records: tuple[object, ...],
    preparation: WorkingCompositionPreparation,
) -> tuple[_FrozenReflectionContext, ...]:
    values: list[_FrozenReflectionContext] = []
    seen: set[tuple[str, int]] = set()
    for reference in preparation.payload.included_curation_revisions:
        if reference.record_kind != "reflection":
            continue
        key = (reference.record_id, reference.revision)
        if key in seen:
            raise CurrentPortfolioBuildError(
                "current_portfolio_build.reflection_context_invalid",
                "Frozen Working Composition repeats a Reflection revision.",
            )
        seen.add(key)
        reflection = _exact_frozen_reflection(
            records,
            preparation,
            reference.record_id,
            reference.revision,
        )
        requirement = _reflection_requirement(preparation, reflection)
        values.append(
            _FrozenReflectionContext(
                reflection=reflection,
                requirement=requirement,
                section=_reflection_section(preparation, requirement),
            )
        )
    return tuple(values)

def _reflection_semantic_value(
    *,
    preparation: WorkingCompositionPreparation,
    requirement: WorkingCompositionRequirementSummary,
    section: WorkingCompositionSectionSummary | None,
    position_in_section: int | None,
    reflection: PortfolioReflection,
) -> dict[str, object]:
    return {
        "contract_version": CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        "portfolio_id": preparation.portfolio_id,
        "portfolio_subject_id": preparation.portfolio_subject_id,
        "profile_binding_id": preparation.profile_binding_id,
        "profile_revision_id": preparation.profile_revision_id,
        "profile_revision_number": preparation.profile_revision_number,
        "composition_revision": preparation.current_composition_revision,
        "requirement_scope_kind": requirement.scope_kind,
        "requirement_scope_reference": requirement.scope_reference,
        "section_id": None if section is None else section.section_id,
        "section_order": None if section is None else section.order,
        "position_in_section": position_in_section,
        "reflection_id": reflection.reflection_id,
        "reflection_revision": reflection.reflection_revision,
        "reflection_requirement_id": reflection.reflection_requirement_id,
        "prompt_id": reflection.prompt_id,
        "prompt_version": reflection.prompt_version,
        "prompt_snapshot_sha256": _text_sha256(reflection.prompt_snapshot),
        "target_scope": reflection.target_scope,
        "target_references": [asdict(item) for item in reflection.target_references],
        "content_mode": reflection.content_mode,
        "content_format": reflection.content_format,
        "language": reflection.language,
        "content_sha256": _text_sha256(reflection.content),
        "renderer_id": CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
        "renderer_version": CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
        "renderer_contract_version": (
            CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
        ),
        "renderer_configuration_sha256": (
            current_portfolio_reflection_configuration_digest().value
        ),
        "renderer_template_sha256": None,
    }


def _reflection_entry_id(
    semantic_value: dict[str, object],
    *,
    supported: bool,
    audience_prohibited: bool,
) -> str:
    value = {
        "semantic": semantic_value,
        "materialization_kind": "generated_vitrine",
        "supported": supported,
        "audience_prohibited": audience_prohibited,
    }
    return f"entry_plan_{_hash_value(_ENTRY_ID_DOMAIN, value)}"


def _reflection_target_path(
    *,
    section_order: int,
    position_in_section: int,
    semantic_value: dict[str, object],
) -> str:
    token = _hash_value(_PATH_ID_DOMAIN, semantic_value)[:16]
    return (
        f"section-{section_order:02d}/"
        f"{position_in_section:02d}-reflection-{token}.txt"
    )


def _planned_reflection_item(
    *,
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
    required_review_ids: tuple[str, ...],
    requirement: WorkingCompositionRequirementSummary,
    section: WorkingCompositionSectionSummary | None,
    reflection: PortfolioReflection,
    plan_position: int,
    position_in_section: int | None,
) -> tuple[CurrentPortfolioGeneratedReflection, tuple[str, ...]]:
    semantic_value = _reflection_semantic_value(
        preparation=preparation,
        requirement=requirement,
        section=section,
        position_in_section=position_in_section,
        reflection=reflection,
    )
    content_supported = current_portfolio_reflection_supported(reflection)
    placement_supported = section is not None and position_in_section is not None
    audience_prohibited = _audience_prohibits(rule, "reflection")
    blockers: list[str] = []
    explanations: list[str] = []
    if not placement_supported:
        blockers.append("unsupported_reflection_placement")
        explanations.append(
            "Frozen Reflection requirement is not exact section-scoped; the "
            "first-party planner will not invent a Snapshot section or placement."
        )
    if audience_prohibited:
        blockers.append("reflection_audience_prohibited")
        explanations.append(
            "Exact audience policy prohibits Reflection content, and the existing "
            "generated-Vitrine Entry contract cannot fabricate a source-backed "
            "omission."
        )
    if not content_supported:
        blockers.append("unsupported_reflection_rendering")
        explanations.append(
            "Frozen Reflection content mode or format is unsupported by the exact "
            "first-party renderer; no reinterpretation or dereference is allowed."
        )
    if not blockers:
        explanations.append(
            "Exact frozen inline Reflection content will be rendered by Vitrine "
            "as deterministic UTF-8 bytes."
        )
    explanation = " ".join(explanations)

    entry_plan_id = _reflection_entry_id(
        semantic_value,
        supported=content_supported and placement_supported,
        audience_prohibited=audience_prohibited,
    )
    configuration = current_portfolio_reflection_configuration_digest()
    target_relative_path: str | None = None
    media_type: str | None = None
    output_byte_size: int | None = None
    output_sha256: str | None = None
    export_file = False
    entry_plan: SnapshotEntryPlan | None = None
    if content_supported and placement_supported and not audience_prohibited:
        assert section is not None
        assert position_in_section is not None
        payload = current_portfolio_reflection_bytes(reflection)
        target_relative_path = _reflection_target_path(
            section_order=section.order,
            position_in_section=position_in_section,
            semantic_value=semantic_value,
        )
        media_type = CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE
        output_byte_size = len(payload)
        output_sha256 = current_portfolio_reflection_output_digest(reflection).value
        export_file = True
        entry_plan = SnapshotEntryPlan(
            entry_plan_id=entry_plan_id,
            plan_position=plan_position,
            section_id=section.section_id,
            ordinal=position_in_section,
            semantic_role="reflection",
            materialization_kind="generated_vitrine",
            content_class="reflection",
            target_relative_path=target_relative_path,
            media_type=media_type,
            renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
            renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
            renderer_contract_version=(
                CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
            ),
            renderer_configuration_digest=configuration,
            renderer_template_digest=None,
            input_references=(
                SnapshotInputReference(
                    record_type="portfolio_reflection",
                    record_id=reflection.reflection_id,
                    record_revision=reflection.reflection_revision,
                ),
            ),
            required_review_ids=required_review_ids,
        )

    return (
        CurrentPortfolioGeneratedReflection(
            entry_plan_id=entry_plan_id,
            plan_position=plan_position,
            section_id=None if section is None else section.section_id,
            section_label=None if section is None else section.label,
            section_order=None if section is None else section.order,
            position_in_section=position_in_section,
            reflection_id=reflection.reflection_id,
            reflection_revision=reflection.reflection_revision,
            reflection_requirement_id=reflection.reflection_requirement_id,
            prompt_id=reflection.prompt_id,
            prompt_version=reflection.prompt_version,
            prompt_snapshot_sha256=_text_sha256(reflection.prompt_snapshot),
            target_scope=reflection.target_scope,
            target_references=reflection.target_references,
            content_mode=reflection.content_mode,
            content_format=reflection.content_format,
            language=reflection.language,
            content_sha256=_text_sha256(reflection.content),
            content_class="reflection",
            materialization_kind="generated_vitrine",
            renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
            renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
            renderer_contract_version=(
                CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
            ),
            renderer_configuration_sha256=configuration.value,
            renderer_template_sha256=None,
            target_relative_path=target_relative_path,
            media_type=media_type,
            output_byte_size=output_byte_size,
            output_sha256=output_sha256,
            export_file=export_file,
            supported=(
                content_supported and placement_supported and not audience_prohibited
            ),
            explanation=explanation,
            entry_plan=entry_plan,
        ),
        tuple(blockers),
    )


def _planned_items(
    *,
    records: tuple[object, ...],
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
    required_reviews: tuple[CurrentPortfolioRequiredReview, ...],
    source_providers: SnapshotSourceProviderRegistry,
) -> tuple[
    tuple[CurrentPortfolioPlannedItem, ...],
    tuple[CurrentPortfolioGeneratedReflection, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    items: list[CurrentPortfolioPlannedItem] = []
    reflections: list[CurrentPortfolioGeneratedReflection] = []
    warnings: list[str] = []
    blockers: list[str] = []
    review_ids = _required_review_ids(required_reviews)
    reflection_contexts = _frozen_reflection_contexts(records, preparation)
    plan_position = 0
    for section in preparation.sections:
        position_in_section = 0
        for placement in section.placements:
            plan_position += 1
            position_in_section += 1
            item, item_warnings, item_blockers = _planned_source_item(
                records=records,
                preparation=preparation,
                rule=rule,
                required_review_ids=review_ids,
                source_providers=source_providers,
                section=section,
                placement=placement,
                plan_position=plan_position,
                position_in_section=position_in_section,
            )
            items.append(item)
            for warning in item_warnings:
                if warning not in warnings:
                    warnings.append(warning)
            for blocker in item_blockers:
                if blocker not in blockers:
                    blockers.append(blocker)
        for context in reflection_contexts:
            if context.section != section:
                continue
            plan_position += 1
            position_in_section += 1
            generated, reflection_blockers = _planned_reflection_item(
                preparation=preparation,
                rule=rule,
                required_review_ids=review_ids,
                requirement=context.requirement,
                section=section,
                reflection=context.reflection,
                plan_position=plan_position,
                position_in_section=position_in_section,
            )
            reflections.append(generated)
            for blocker in reflection_blockers:
                if blocker not in blockers:
                    blockers.append(blocker)

    for context in reflection_contexts:
        if context.section is not None:
            continue
        plan_position += 1
        generated, reflection_blockers = _planned_reflection_item(
            preparation=preparation,
            rule=rule,
            required_review_ids=review_ids,
            requirement=context.requirement,
            section=None,
            reflection=context.reflection,
            plan_position=plan_position,
            position_in_section=None,
        )
        reflections.append(generated)
        for blocker in reflection_blockers:
            if blocker not in blockers:
                blockers.append(blocker)

    return (
        tuple(items),
        tuple(reflections),
        tuple(warnings),
        tuple(blockers),
    )

def _directory_export_preview(
    items: tuple[CurrentPortfolioPlannedItem, ...],
    generated_reflections: tuple[CurrentPortfolioGeneratedReflection, ...],
) -> CurrentPortfolioDirectoryExportPreview:
    ordered: list[tuple[int, str, bool]] = []
    ordered.extend(
        (item.plan_position, item.entry_plan_id, item.export_file) for item in items
    )
    ordered.extend(
        (item.plan_position, item.entry_plan_id, item.export_file)
        for item in generated_reflections
    )
    ordered.sort(key=lambda item: item[0])
    included = tuple(entry_id for _, entry_id, export_file in ordered if export_file)
    excluded = tuple(
        entry_id for _, entry_id, export_file in ordered if not export_file
    )
    semantic = {
        "export_format": CURRENT_PORTFOLIO_EXPORT_FORMAT,
        "export_contract_version": CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        "included_entry_plan_ids": included,
        "excluded_entry_plan_ids": excluded,
    }
    return CurrentPortfolioDirectoryExportPreview(
        export_plan_id=f"export_plan_{_hash_value(_EXPORT_ID_DOMAIN, semantic)}",
        export_format=CURRENT_PORTFOLIO_EXPORT_FORMAT,
        export_contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        included_entry_plan_ids=included,
        excluded_entry_plan_ids=excluded,
        configuration_sha256=_hash_value(_EXPORT_CONFIG_DOMAIN, semantic),
    )


def _planned_item_fingerprint_value(
    item: CurrentPortfolioPlannedItem,
) -> dict[str, object]:
    return {
        "entry_plan_id": item.entry_plan_id,
        "plan_position": item.plan_position,
        "section_id": item.section_id,
        "section_order": item.section_order,
        "position_in_section": item.position_in_section,
        "placement_id": item.placement_id,
        "selection_id": item.selection_id,
        "candidate_id": item.candidate_id,
        "candidate_evaluation_id": item.candidate_evaluation_id,
        "source_publication_id": item.source_publication_id,
        "producer_module_id": item.producer_module_id,
        "projection_kind": item.projection_kind,
        "projection_contract_version": item.projection_contract_version,
        "source_artifact_id": (
            None if item.source_artifact is None else item.source_artifact.artifact_id
        ),
        "source_current_use_state": item.source_current_use_state,
        "content_class": item.content_class,
        "materialization_kind": item.materialization_kind,
        "provider_disposition": item.provider_disposition,
        "provider_id": item.provider_id,
        "provider_version": item.provider_version,
        "provider_support_key": item.provider_support_key,
        "provider_concrete_media_types": item.provider_concrete_media_types,
        "target_relative_path": item.target_relative_path,
        "media_type": item.media_type,
        "export_file": item.export_file,
        "permitted_omission_reason": item.permitted_omission_reason,
    }


def _generated_reflection_fingerprint_value(
    item: CurrentPortfolioGeneratedReflection,
) -> dict[str, object]:
    return {
        "entry_plan_id": item.entry_plan_id,
        "plan_position": item.plan_position,
        "section_id": item.section_id,
        "section_order": item.section_order,
        "position_in_section": item.position_in_section,
        "reflection_id": item.reflection_id,
        "reflection_revision": item.reflection_revision,
        "reflection_requirement_id": item.reflection_requirement_id,
        "prompt_id": item.prompt_id,
        "prompt_version": item.prompt_version,
        "prompt_snapshot_sha256": item.prompt_snapshot_sha256,
        "target_scope": item.target_scope,
        "target_references": [asdict(value) for value in item.target_references],
        "content_mode": item.content_mode,
        "content_format": item.content_format,
        "language": item.language,
        "content_sha256": item.content_sha256,
        "content_class": item.content_class,
        "materialization_kind": item.materialization_kind,
        "renderer_id": item.renderer_id,
        "renderer_version": item.renderer_version,
        "renderer_contract_version": item.renderer_contract_version,
        "renderer_configuration_sha256": item.renderer_configuration_sha256,
        "renderer_template_sha256": item.renderer_template_sha256,
        "target_relative_path": item.target_relative_path,
        "media_type": item.media_type,
        "output_byte_size": item.output_byte_size,
        "output_sha256": item.output_sha256,
        "export_file": item.export_file,
        "supported": item.supported,
    }


def _preparation_fingerprint(
    *,
    preparation: WorkingCompositionPreparation,
    rule: WorkingCompositionAudienceSummary,
    audience_context: CurrentPortfolioAudienceContextResolution,
    snapshot_series: CurrentPortfolioSnapshotSeriesResolution,
    required_reviews: tuple[CurrentPortfolioRequiredReview, ...],
    acknowledged_obligation_codes: tuple[str, ...],
    planned_items: tuple[CurrentPortfolioPlannedItem, ...],
    generated_reflections: tuple[CurrentPortfolioGeneratedReflection, ...],
    directory_export: CurrentPortfolioDirectoryExportPreview,
) -> str:
    value = {
        "contract_version": CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        "observed_state_revision": preparation.observed_state_revision,
        "working_composition": {
            "preparation_fingerprint": preparation.preparation_fingerprint,
            "disposition": preparation.disposition,
            "composition_pointer_revision": (
                preparation.observed_composition_pointer_revision
            ),
            "composition_revision": preparation.current_composition_revision,
        },
        "portfolio_id": preparation.portfolio_id,
        "portfolio_subject_id": preparation.portfolio_subject_id,
        "profile_binding_id": preparation.profile_binding_id,
        "profile_revision": {
            "portfolio_profile_id": preparation.profile_revision_id,
            "profile_revision": preparation.profile_revision_number,
        },
        "audience_rule": asdict(rule),
        "audience_context": asdict(audience_context),
        "snapshot_series": asdict(snapshot_series),
        "required_reviews": [asdict(item) for item in required_reviews],
        "acknowledged_obligation_codes": list(acknowledged_obligation_codes),
        "planned_items": [
            _planned_item_fingerprint_value(item) for item in planned_items
        ],
        "generated_reflections": [
            _generated_reflection_fingerprint_value(item)
            for item in generated_reflections
        ],
        "directory_export": asdict(directory_export),
    }
    return _hash_value(CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION, value)


def prepare_current_portfolio_build(
    workspace_root: str | Path,
    portfolio_id: str,
    *,
    audience_rule_id: str,
    audience_context_id: str | None = None,
    snapshot_series_id: str | None = None,
    acknowledged_obligation_codes: tuple[str, ...] = (),
    source_providers: SnapshotSourceProviderRegistry | None = None,
) -> CurrentPortfolioBuildPreparation:
    """Prepare exact current curation and deterministic first-party plan semantics.

    This boundary is intentionally read-only. Provider matching consults only
    configured Vitrine provider descriptors; it never resolves or reads source
    bytes and never requests Snapshot-build or producer-Artifact authority.
    """
    if not portfolio_id or not audience_rule_id:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.invalid_request",
            "Portfolio ID and audience rule ID are required.",
        )

    working = prepare_working_composition(workspace_root, portfolio_id)
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.context_not_found",
            "Vitrine canonical state is unavailable for Current Portfolio preparation.",
        ) from error
    if current.state_revision != working.observed_state_revision:
        raise CurrentPortfolioBuildError(
            "current_portfolio_build.state_changed",
            "Vitrine state changed after Working Composition preparation.",
        )

    rule = _selected_audience_rule(working, audience_rule_id)
    audience_context = _resolve_audience_context(
        records, working, rule, audience_context_id
    )
    snapshot_series = _resolve_snapshot_series(
        records, working, rule, audience_context, snapshot_series_id
    )
    required_reviews = _required_reviews(working, rule)
    missing_review_classes = tuple(
        item.review_class for item in required_reviews if not item.satisfied
    )
    unresolved_codes = working.payload.unresolved_obligation_codes
    acknowledged_codes = _acknowledged_obligations(
        unresolved_codes, acknowledged_obligation_codes
    )
    acknowledgement_complete = acknowledged_codes == unresolved_codes
    providers = source_providers or SnapshotSourceProviderRegistry()
    (
        planned_items,
        generated_reflections,
        plan_warnings,
        plan_blockers,
    ) = _planned_items(
        records=records,
        preparation=working,
        rule=rule,
        required_reviews=required_reviews,
        source_providers=providers,
    )
    directory_export = _directory_export_preview(
        planned_items, generated_reflections
    )

    blockers: list[str] = []
    if working.disposition != "reuse_exact_current":
        blockers.append("working_composition_requires_freeze")
    if working.unplaced_selection_ids:
        blockers.append("unplaced_selections")
    if audience_context.disposition == "requires_choice":
        blockers.append("audience_context_choice_required")
    if (
        snapshot_series.disposition == "requires_choice"
        and not snapshot_series.resolution_deferred_for_audience_context
    ):
        blockers.append("snapshot_series_choice_required")
    if missing_review_classes:
        blockers.append("missing_required_reviews")
    if unresolved_codes and not acknowledgement_complete:
        blockers.append("unresolved_obligations_acknowledgement_required")
    for blocker in plan_blockers:
        if blocker not in blockers:
            blockers.append(blocker)
    warnings: list[str] = []
    if unresolved_codes:
        warnings.append("unresolved_composition_obligations_present")
    if snapshot_series.resolution_deferred_for_audience_context:
        warnings.append("snapshot_series_resolution_deferred")
    for warning in plan_warnings:
        if warning not in warnings:
            warnings.append(warning)

    fingerprint = _preparation_fingerprint(
        preparation=working,
        rule=rule,
        audience_context=audience_context,
        snapshot_series=snapshot_series,
        required_reviews=required_reviews,
        acknowledged_obligation_codes=acknowledged_codes,
        planned_items=planned_items,
        generated_reflections=generated_reflections,
        directory_export=directory_export,
    )
    return CurrentPortfolioBuildPreparation(
        contract_version=CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
        observed_state_revision=working.observed_state_revision,
        portfolio_id=working.portfolio_id,
        portfolio_subject_id=working.portfolio_subject_id,
        profile_binding_id=working.profile_binding_id,
        profile_revision_id=working.profile_revision_id,
        profile_revision_number=working.profile_revision_number,
        current_composition_pointer_revision=(
            working.observed_composition_pointer_revision
        ),
        current_composition_revision=working.current_composition_revision,
        working_composition_preparation_fingerprint=working.preparation_fingerprint,
        working_composition_disposition=working.disposition,
        composition_inventory=working.payload,
        sections=working.sections,
        selections=working.selections,
        unplaced_selection_ids=working.unplaced_selection_ids,
        selected_audience_rule=rule,
        audience_context=audience_context,
        snapshot_series=snapshot_series,
        required_reviews=required_reviews,
        applicable_review_decisions=working.reviews,
        missing_required_review_classes=missing_review_classes,
        unresolved_obligation_codes=unresolved_codes,
        acknowledged_obligation_codes=acknowledged_codes,
        obligation_acknowledgement_complete=acknowledgement_complete,
        planned_items=planned_items,
        generated_reflections=generated_reflections,
        directory_export=directory_export,
        warnings=tuple(warnings),
        blocking_reasons=tuple(blockers),
        preparation_fingerprint=fingerprint,
    )


__all__ = [
    "CURRENT_PORTFOLIO_BUILD_BLOCKING_REASONS",
    "CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION",
    "CURRENT_PORTFOLIO_BUILD_ERROR_CODES",
    "CURRENT_PORTFOLIO_EXPORT_FORMAT",
    "CurrentPortfolioAudienceContextResolution",
    "CurrentPortfolioBuildError",
    "CurrentPortfolioBuildPreparation",
    "CurrentPortfolioDirectoryExportPreview",
    "CurrentPortfolioGeneratedReflection",
    "CurrentPortfolioPlannedItem",
    "CurrentPortfolioRequiredReview",
    "CurrentPortfolioSnapshotSeriesResolution",
    "prepare_current_portfolio_build",
]
