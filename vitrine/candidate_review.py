"""Guided Candidate review projection and exact curation orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vitrine.candidate_inbox import (
    CandidateInboxDetail,
    CandidateInboxQuery,
    CandidateInboxResult,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.curation_services import (
    CurationAuthorityGate,
    CurationMutationResult,
    create_annotation,
    create_reflection,
    decide_selection_proposal,
    place_selection,
    reject_candidate_directly,
    replace_selection,
    review_curation_target,
    revise_annotation,
    revise_reflection,
    select_candidate_directly,
    withdraw_selection,
)
from vitrine.curation_state import CurationState, project_curation_state
from vitrine.models import (
    ActorAttribution,
    CandidateAvailabilityObservation,
    CandidateSourceEndpoint,
    CurationTargetRef,
    PlacementPresentation,
    SelectionProposal,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

CANDIDATE_REVIEW_CONTRACT_VERSION: Final[str] = "vitrine_guided_candidate_review_v1"
CANDIDATE_REVIEW_DECISIONS: Final[frozenset[str]] = frozenset({"select", "decline"})
CANDIDATE_REVIEW_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "candidate_review.invalid_request",
        "candidate_review.not_selectable",
        "candidate_review.action_not_available",
        "candidate_review.state_changed",
        "candidate_review.state_invalid",
    }
)


class CandidateReviewError(RuntimeError):
    """Expected guided-review orchestration failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in CANDIDATE_REVIEW_ERROR_CODES:
            raise ValueError(f"unsupported Candidate review error code: {code}")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CandidateReviewActorSummary:
    actor_kind: str
    actor_id: str
    owning_system: str
    role_snapshot: str | None


@dataclass(frozen=True, slots=True)
class CandidateReviewSubjectRelationshipSummary:
    assertion_id: str
    subject_link_id: str
    source_subject_kind: str
    source_subject_id: str
    relationship_kind: str


@dataclass(frozen=True, slots=True)
class CandidateReviewAvailabilitySummary:
    dimension: str
    outcome: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateReviewSourceSummary:
    core_publication_id: str
    observed_series_state: str
    observed_withdrawal_state: str
    producer_module_id: str
    source_record_kind: str
    source_record_id: str
    native_revision: str | int | None
    artifact_id: str | None
    artifact_kind: str | None
    representation_kind: str | None
    subject_relationships: tuple[CandidateReviewSubjectRelationshipSummary, ...]


@dataclass(frozen=True, slots=True)
class CandidateReviewSectionSummary:
    section_id: str
    label: str
    obligation: str
    minimum_placements: int
    maximum_placements: int | None
    active_placement_count: int
    arrangement_pointer_revision: int | None
    arrangement_pointer_conflict: bool
    relevant_profile_requirement_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateReviewProfileRequirementSummary:
    requirement_id: str
    requirement_kind: str
    obligation: str
    title: str
    statement: str
    scope_kind: str
    satisfaction_class: str
    scope_reference: str | None


@dataclass(frozen=True, slots=True)
class CandidateReviewProposalDecisionSummary:
    selection_decision_id: str
    decision: str
    authority_reference: str
    matched_profile_requirement_ids: tuple[str, ...]
    condition_codes: tuple[str, ...]
    rationale_id: str | None
    resulting_selection_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateReviewProposalSummary:
    selection_proposal_id: str
    proposer: CandidateReviewActorSummary
    proposal_origin: str
    proposed_section_ids: tuple[str, ...]
    intended_profile_requirement_ids: tuple[str, ...]
    candidate_condition_state_snapshot: str
    rationale_id: str | None
    predecessor_proposal_id: str | None
    decisions: tuple[CandidateReviewProposalDecisionSummary, ...]

    @property
    def undecided(self) -> bool:
        return not self.decisions


@dataclass(frozen=True, slots=True)
class CandidateReviewPlacementSummary:
    placement_id: str
    selection_id: str
    section_id: str
    section_label: str
    lifecycle_state: str


@dataclass(frozen=True, slots=True)
class CandidateReviewSelectionSummary:
    selection_id: str
    candidate_evaluation_id: str
    selected_by: CandidateReviewActorSummary
    lifecycle_state: str
    proposal_ids: tuple[str, ...]
    decision_ids: tuple[str, ...]
    unresolved_condition_codes: tuple[str, ...]
    active_placement_ids: tuple[str, ...]
    historical_placement_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateReviewAnnotationSummary:
    annotation_id: str
    annotation_revision: int
    purpose: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    author: CandidateReviewActorSummary
    predecessor_annotation_revision: int | None


@dataclass(frozen=True, slots=True)
class CandidateReviewReflectionSummary:
    reflection_id: str
    reflection_revision: int
    reflection_requirement_id: str
    prompt_id: str
    prompt_version: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    author: CandidateReviewActorSummary
    predecessor_reflection_revision: int | None


@dataclass(frozen=True, slots=True)
class CandidateReviewReviewSummary:
    curation_review_decision_id: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    decision: str
    reviewed_by: CandidateReviewActorSummary
    approval_requirement_id: str | None
    required_follow_up_codes: tuple[str, ...]
    predecessor_review_decision_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateReviewDetail:
    contract_version: str
    observed_state_revision: int
    inbox_detail: CandidateInboxDetail
    selectable: bool
    current_review_evaluation_id: str | None
    curation_provenance_evaluation_id: str | None
    current_evaluation_differs_from_curation_provenance: bool
    evaluation_reason_codes: tuple[str, ...]
    availability_observations: tuple[CandidateReviewAvailabilitySummary, ...]
    source: CandidateReviewSourceSummary | None
    profile_requirement_ids: tuple[str, ...]
    profile_requirements: tuple[CandidateReviewProfileRequirementSummary, ...]
    sections: tuple[CandidateReviewSectionSummary, ...]
    proposals: tuple[CandidateReviewProposalSummary, ...]
    selections: tuple[CandidateReviewSelectionSummary, ...]
    placements: tuple[CandidateReviewPlacementSummary, ...]
    annotations: tuple[CandidateReviewAnnotationSummary, ...]
    reflections: tuple[CandidateReviewReflectionSummary, ...]
    reviews: tuple[CandidateReviewReviewSummary, ...]


@dataclass(frozen=True, slots=True)
class CandidateReviewActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    portfolio_profile_id: str
    profile_revision: int
    candidate_id: str
    current_review_evaluation_id: str | None
    curation_provenance_evaluation_id: str
    candidate_condition: str
    stale_state: str | None
    stale_reason_codes: tuple[str, ...]
    decision: str
    selection_proposal_id: str | None
    proposed_section_ids: tuple[str, ...]
    intended_profile_requirement_ids: tuple[str, ...]
    operation: str
    confirmation_phrase: str
    condition_acknowledgement_required: bool


@dataclass(frozen=True, slots=True)
class CandidateReviewArrangementPointerObservation:
    section_id: str
    pointer_revision: int | None


@dataclass(frozen=True, slots=True)
class CandidateReviewPlacementActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    portfolio_id: str
    candidate_id: str
    current_review_evaluation_id: str | None
    curation_provenance_evaluation_id: str
    selection_id: str
    selection_evaluation_id: str
    section_id: str
    section_label: str
    active_placement_count: int
    maximum_placements: int | None
    expected_arrangement_pointer_revision: int | None
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class CandidateReviewWithdrawalActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    portfolio_id: str
    candidate_id: str
    current_review_evaluation_id: str | None
    curation_provenance_evaluation_id: str
    selection_id: str
    selection_evaluation_id: str
    active_placement_ids: tuple[str, ...]
    affected_section_ids: tuple[str, ...]
    arrangement_pointers: tuple[CandidateReviewArrangementPointerObservation, ...]
    reason: str
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class CandidateReviewReplacementDisposition:
    placement_id: str
    source_section_id: str
    target_section_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateReviewReplacementActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    successor_entry_id: str
    portfolio_id: str
    selection_id: str
    candidate_id: str
    current_review_evaluation_id: str | None
    curation_provenance_evaluation_id: str
    successor_candidate_id: str
    successor_current_review_evaluation_id: str | None
    successor_curation_provenance_evaluation_id: str
    successor_candidate_condition: str
    successor_stale_state: str | None
    successor_stale_reason_codes: tuple[str, ...]
    proposed_section_ids: tuple[str, ...]
    placement_dispositions: tuple[CandidateReviewReplacementDisposition, ...]
    arrangement_pointers: tuple[CandidateReviewArrangementPointerObservation, ...]
    reason: str
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class CandidateReviewAnnotationActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    portfolio_id: str
    action: str
    annotation_id: str | None
    expected_annotation_revision: int | None
    purpose: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    content: str
    language: str
    content_format: str
    intended_presentation_class: str | None
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class CandidateReviewReflectionActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    portfolio_id: str
    action: str
    reflection_id: str | None
    expected_reflection_revision: int | None
    reflection_requirement_id: str
    prompt_id: str
    prompt_version: str
    prompt_snapshot: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    content: str
    content_mode: str
    language: str
    content_format: str
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class CandidateReviewCurationReviewActionPlan:
    contract_version: str
    observed_state_revision: int
    entry_id: str
    portfolio_id: str
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    decision: str
    reason: str
    approval_requirement_id: str | None
    required_follow_up_codes: tuple[str, ...]
    predecessor_review_decision_id: str | None
    confirmation_phrase: str


def _actor_summary(actor: ActorAttribution) -> CandidateReviewActorSummary:
    return CandidateReviewActorSummary(
        actor_kind=actor.actor_kind,
        actor_id=actor.actor_id,
        owning_system=actor.owning_system,
        role_snapshot=actor.role_snapshot,
    )


def _availability_summary(
    observation: CandidateAvailabilityObservation,
) -> CandidateReviewAvailabilitySummary:
    return CandidateReviewAvailabilitySummary(
        dimension=observation.dimension,
        outcome=observation.outcome,
        reason_codes=observation.reason_codes,
    )


def _source_summary(
    endpoint: CandidateSourceEndpoint | None,
) -> CandidateReviewSourceSummary | None:
    if endpoint is None:
        return None
    publication = endpoint.core_publication
    producer = endpoint.producer_source
    artifact = endpoint.source_artifact
    return CandidateReviewSourceSummary(
        core_publication_id=publication.publication_id,
        observed_series_state=publication.observed_series_state,
        observed_withdrawal_state=publication.observed_withdrawal_state,
        producer_module_id=producer.producer_module_id,
        source_record_kind=producer.source_record_kind,
        source_record_id=producer.source_record_id,
        native_revision=producer.native_revision,
        artifact_id=None if artifact is None else artifact.artifact_id,
        artifact_kind=None if artifact is None else artifact.artifact_kind,
        representation_kind=(
            None if artifact is None else artifact.representation_kind
        ),
        subject_relationships=tuple(
            CandidateReviewSubjectRelationshipSummary(
                assertion_id=item.assertion_id,
                subject_link_id=item.subject_link_id,
                source_subject_kind=item.source_subject_kind,
                source_subject_id=item.source_subject_id,
                relationship_kind=item.relationship_kind,
            )
            for item in endpoint.subject_relationship_assertions
        ),
    )


def _load_curation_state(
    workspace_root: str | Path,
    expected_state_revision: int,
) -> CurationState:
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (
        VitrineStorageNotFoundError,
        VitrineStorageError,
        OSError,
    ) as error:
        raise CandidateReviewError(
            "candidate_review.state_invalid",
            "Canonical Vitrine state became unavailable during Candidate review.",
        ) from error
    if current.state_revision != expected_state_revision:
        raise CandidateReviewError(
            "candidate_review.state_changed",
            "Portfolio state changed after Candidate review began; review it again.",
        )
    return project_curation_state(records)


def _section_summaries(
    detail: CandidateInboxDetail,
    curation: CurationState,
) -> tuple[CandidateReviewSectionSummary, ...]:
    item = detail.item
    profile = detail.profile_revision
    sections_by_id = {section.section_id: section for section in profile.sections}
    values: list[CandidateReviewSectionSummary] = []
    for section_id in item.eligible_section_ids:
        section = sections_by_id.get(section_id)
        if section is None:
            raise CandidateReviewError(
                "candidate_review.state_invalid",
                "Candidate eligibility references an unavailable Profile section.",
            )
        active = curation.active_placements(
            portfolio_id=item.portfolio_id,
            profile_binding_id=item.profile_binding_id,
            section_id=section_id,
        )
        pointer_heads = curation.arrangement_pointer_heads(
            item.portfolio_id,
            item.profile_binding_id,
            section_id,
        )
        requirement_ids = tuple(
            sorted(
                requirement.requirement_id
                for requirement in curation.profile_requirements
                if requirement.portfolio_profile_id == profile.portfolio_profile_id
                and requirement.profile_revision == profile.profile_revision
                and requirement.scope_reference == section_id
            )
        )
        values.append(
            CandidateReviewSectionSummary(
                section_id=section.section_id,
                label=section.label,
                obligation=section.obligation,
                minimum_placements=section.minimum_placements,
                maximum_placements=section.maximum_placements,
                active_placement_count=len(active),
                arrangement_pointer_revision=(
                    pointer_heads[0].pointer_revision
                    if len(pointer_heads) == 1
                    else None
                ),
                arrangement_pointer_conflict=len(pointer_heads) > 1,
                relevant_profile_requirement_ids=requirement_ids,
            )
        )
    return tuple(values)


def _proposal_decisions(
    curation: CurationState,
    proposal: SelectionProposal,
) -> tuple[CandidateReviewProposalDecisionSummary, ...]:
    decisions = tuple(
        sorted(
            (
                item
                for item in curation.decisions
                if item.selection_proposal_id == proposal.selection_proposal_id
            ),
            key=lambda item: item.selection_decision_id,
        )
    )
    return tuple(
        CandidateReviewProposalDecisionSummary(
            selection_decision_id=item.selection_decision_id,
            decision=item.decision,
            authority_reference=item.authority_reference,
            matched_profile_requirement_ids=item.matched_profile_requirement_ids,
            condition_codes=item.condition_codes,
            rationale_id=item.rationale_id,
            resulting_selection_id=item.resulting_selection_id,
        )
        for item in decisions
    )


def _proposal_summaries(
    detail: CandidateInboxDetail,
    curation: CurationState,
) -> tuple[CandidateReviewProposalSummary, ...]:
    candidate = detail.candidate
    if candidate is None:
        return ()
    proposals = tuple(
        sorted(
            (
                item
                for item in curation.proposals
                if item.portfolio_id == candidate.portfolio_id
                and item.profile_binding_id == candidate.profile_binding_id
                and item.candidate_id == candidate.candidate_id
            ),
            key=lambda item: item.selection_proposal_id,
        )
    )
    return tuple(
        CandidateReviewProposalSummary(
            selection_proposal_id=item.selection_proposal_id,
            proposer=_actor_summary(item.proposer),
            proposal_origin=item.proposal_origin,
            proposed_section_ids=item.proposed_section_ids,
            intended_profile_requirement_ids=item.intended_profile_requirement_ids,
            candidate_condition_state_snapshot=(
                item.candidate_condition_state_snapshot
            ),
            rationale_id=item.rationale_id,
            predecessor_proposal_id=item.predecessor_proposal_id,
            decisions=_proposal_decisions(curation, item),
        )
        for item in proposals
    )


def _placement_summaries(
    detail: CandidateInboxDetail,
    curation: CurationState,
) -> tuple[CandidateReviewPlacementSummary, ...]:
    selection_ids = {item.selection_id for item in detail.selection_history}
    if not selection_ids:
        return ()
    section_labels = {
        section.section_id: section.label
        for section in detail.profile_revision.sections
    }
    values = tuple(
        sorted(
            (
                item
                for item in curation.placements
                if item.selection_id in selection_ids
            ),
            key=lambda item: item.placement_id,
        )
    )
    return tuple(
        CandidateReviewPlacementSummary(
            placement_id=item.placement_id,
            selection_id=item.selection_id,
            section_id=item.section_id,
            section_label=section_labels.get(item.section_id, item.section_id),
            lifecycle_state=curation.placement_status(item.placement_id),
        )
        for item in values
    )


def _selection_provenance(
    curation: CurationState,
    selection_id: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    decisions = tuple(
        sorted(
            (
                item
                for item in curation.decisions
                if item.resulting_selection_id == selection_id
            ),
            key=lambda item: item.selection_decision_id,
        )
    )
    decision_ids = tuple(item.selection_decision_id for item in decisions)
    proposal_ids = tuple(
        sorted({item.selection_proposal_id for item in decisions})
    )
    return proposal_ids, decision_ids


def _selection_condition_codes(
    curation: CurationState,
    selection_id: str,
) -> tuple[str, ...]:
    heads = curation.selection_heads(selection_id)
    if len(heads) != 1:
        return ()
    return heads[0].unresolved_condition_codes


def _selection_summaries(
    detail: CandidateInboxDetail,
    curation: CurationState,
    placements: tuple[CandidateReviewPlacementSummary, ...],
) -> tuple[CandidateReviewSelectionSummary, ...]:
    placement_status = {item.placement_id: item.lifecycle_state for item in placements}
    values: list[CandidateReviewSelectionSummary] = []
    for selection in detail.selection_history:
        proposal_ids, decision_ids = _selection_provenance(
            curation,
            selection.selection_id,
        )
        selection_placements = tuple(
            item
            for item in placements
            if item.selection_id == selection.selection_id
        )
        active_placement_ids = tuple(
            item.placement_id
            for item in selection_placements
            if placement_status[item.placement_id] == "activated"
        )
        historical_placement_ids = tuple(
            item.placement_id
            for item in selection_placements
            if item.placement_id not in active_placement_ids
        )
        values.append(
            CandidateReviewSelectionSummary(
                selection_id=selection.selection_id,
                candidate_evaluation_id=selection.candidate_evaluation_id,
                selected_by=_actor_summary(selection.selected_by),
                lifecycle_state=curation.selection_status(selection.selection_id),
                proposal_ids=proposal_ids,
                decision_ids=decision_ids,
                unresolved_condition_codes=_selection_condition_codes(
                    curation,
                    selection.selection_id,
                ),
                active_placement_ids=active_placement_ids,
                historical_placement_ids=historical_placement_ids,
            )
        )
    return tuple(values)


def _relevant_target_ids(
    proposals: tuple[CandidateReviewProposalSummary, ...],
    selections: tuple[CandidateReviewSelectionSummary, ...],
    placements: tuple[CandidateReviewPlacementSummary, ...],
) -> dict[str, set[str]]:
    return {
        "selection_proposal": {
            item.selection_proposal_id for item in proposals
        },
        "selection": {item.selection_id for item in selections},
        "placement": {item.placement_id for item in placements},
    }


def _targets_candidate(
    targets: tuple[CurationTargetRef, ...],
    relevant_ids: dict[str, set[str]],
) -> bool:
    return any(
        target.target_id in relevant_ids.get(target.target_kind, set())
        for target in targets
    )


def _annotation_summaries(
    curation: CurationState,
    relevant_ids: dict[str, set[str]],
) -> tuple[CandidateReviewAnnotationSummary, ...]:
    values = tuple(
        sorted(
            (
                item
                for item in curation.annotations
                if _targets_candidate(item.target_references, relevant_ids)
            ),
            key=lambda item: (item.annotation_id, item.annotation_revision),
        )
    )
    return tuple(
        CandidateReviewAnnotationSummary(
            annotation_id=item.annotation_id,
            annotation_revision=item.annotation_revision,
            purpose=item.purpose,
            target_scope=item.target_scope,
            target_references=item.target_references,
            author=_actor_summary(item.author),
            predecessor_annotation_revision=(
                item.predecessor_annotation_revision
            ),
        )
        for item in values
    )


def _reflection_summaries(
    curation: CurationState,
    relevant_ids: dict[str, set[str]],
) -> tuple[CandidateReviewReflectionSummary, ...]:
    values = tuple(
        sorted(
            (
                item
                for item in curation.reflections
                if _targets_candidate(item.target_references, relevant_ids)
            ),
            key=lambda item: (item.reflection_id, item.reflection_revision),
        )
    )
    return tuple(
        CandidateReviewReflectionSummary(
            reflection_id=item.reflection_id,
            reflection_revision=item.reflection_revision,
            reflection_requirement_id=item.reflection_requirement_id,
            prompt_id=item.prompt_id,
            prompt_version=item.prompt_version,
            target_scope=item.target_scope,
            target_references=item.target_references,
            author=_actor_summary(item.author),
            predecessor_reflection_revision=(
                item.predecessor_reflection_revision
            ),
        )
        for item in values
    )


def _review_summaries(
    curation: CurationState,
    relevant_ids: dict[str, set[str]],
    annotations: tuple[CandidateReviewAnnotationSummary, ...],
    reflections: tuple[CandidateReviewReflectionSummary, ...],
) -> tuple[CandidateReviewReviewSummary, ...]:
    expanded_ids = {
        kind: set(values) for kind, values in relevant_ids.items()
    }
    expanded_ids["annotation"] = {item.annotation_id for item in annotations}
    expanded_ids["reflection"] = {item.reflection_id for item in reflections}
    values = tuple(
        sorted(
            (
                item
                for item in curation.reviews
                if _targets_candidate(item.target_references, expanded_ids)
            ),
            key=lambda item: item.curation_review_decision_id,
        )
    )
    return tuple(
        CandidateReviewReviewSummary(
            curation_review_decision_id=item.curation_review_decision_id,
            target_scope=item.target_scope,
            target_references=item.target_references,
            decision=item.decision,
            reviewed_by=_actor_summary(item.reviewed_by),
            approval_requirement_id=item.approval_requirement_id,
            required_follow_up_codes=item.required_follow_up_codes,
            predecessor_review_decision_id=(
                item.predecessor_review_decision_id
            ),
        )
        for item in values
    )


def _profile_requirement_summaries(
    detail: CandidateInboxDetail,
    curation: CurationState,
) -> tuple[CandidateReviewProfileRequirementSummary, ...]:
    profile = detail.profile_revision
    values = tuple(
        sorted(
            (
                item
                for item in curation.profile_requirements
                if item.portfolio_profile_id == profile.portfolio_profile_id
                and item.profile_revision == profile.profile_revision
            ),
            key=lambda item: item.requirement_id,
        )
    )
    return tuple(
        CandidateReviewProfileRequirementSummary(
            requirement_id=item.requirement_id,
            requirement_kind=item.requirement_kind,
            obligation=item.obligation,
            title=item.title,
            statement=item.statement,
            scope_kind=item.scope_kind,
            satisfaction_class=item.satisfaction_class,
            scope_reference=item.scope_reference,
        )
        for item in values
    )


def list_candidate_review_entries(
    workspace_root: str | Path,
    query: CandidateInboxQuery | None = None,
) -> CandidateInboxResult:
    """List guided-review entries using the authoritative Candidate Inbox."""

    return list_candidate_inbox(workspace_root, query)


def get_candidate_review_detail(
    workspace_root: str | Path,
    entry_id: str,
) -> CandidateReviewDetail:
    """Project one exact persisted inbox entry plus related curation history."""

    inbox_detail = get_candidate_inbox_detail(workspace_root, entry_id)
    curation = _load_curation_state(
        workspace_root,
        inbox_detail.observed_state_revision,
    )
    item = inbox_detail.item
    candidate = inbox_detail.candidate
    evaluation = inbox_detail.evaluation
    current_review_evaluation_id = item.current_evaluation_id
    curation_provenance_evaluation_id = (
        None if candidate is None else candidate.candidate_evaluation_id
    )
    endpoint = (
        evaluation.source_endpoint
        if evaluation is not None and evaluation.source_endpoint is not None
        else (None if candidate is None else candidate.source_endpoint)
    )
    sections = _section_summaries(inbox_detail, curation)
    profile_requirements = _profile_requirement_summaries(inbox_detail, curation)
    proposals = _proposal_summaries(inbox_detail, curation)
    placements = _placement_summaries(inbox_detail, curation)
    selections = _selection_summaries(inbox_detail, curation, placements)
    relevant_ids = _relevant_target_ids(proposals, selections, placements)
    annotations = _annotation_summaries(curation, relevant_ids)
    reflections = _reflection_summaries(curation, relevant_ids)
    reviews = _review_summaries(
        curation,
        relevant_ids,
        annotations,
        reflections,
    )
    return CandidateReviewDetail(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=inbox_detail.observed_state_revision,
        inbox_detail=inbox_detail,
        selectable=candidate is not None,
        current_review_evaluation_id=current_review_evaluation_id,
        curation_provenance_evaluation_id=curation_provenance_evaluation_id,
        current_evaluation_differs_from_curation_provenance=(
            current_review_evaluation_id is not None
            and curation_provenance_evaluation_id is not None
            and current_review_evaluation_id
            != curation_provenance_evaluation_id
        ),
        evaluation_reason_codes=(
            () if evaluation is None else evaluation.reason_codes
        ),
        availability_observations=(
            ()
            if evaluation is None
            else tuple(
                _availability_summary(observation)
                for observation in evaluation.availability_observations
            )
        ),
        source=_source_summary(endpoint),
        profile_requirement_ids=tuple(
            item.requirement_id for item in profile_requirements
        ),
        profile_requirements=profile_requirements,
        sections=sections,
        proposals=proposals,
        selections=selections,
        placements=placements,
        annotations=annotations,
        reflections=reflections,
        reviews=reviews,
    )


def _validated_identifiers(
    values: tuple[str, ...],
    *,
    field_name: str,
    nonempty: bool,
) -> tuple[str, ...]:
    result = tuple(values)
    if nonempty and not result:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} must identify at least one exact value.",
        )
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} must contain nonempty identifiers.",
        )
    if len(set(result)) != len(result):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} must not contain duplicates.",
        )
    return result


def plan_candidate_decision(
    workspace_root: str | Path,
    *,
    entry_id: str,
    decision: str,
    proposed_section_ids: tuple[str, ...] = (),
    intended_profile_requirement_ids: tuple[str, ...] = (),
    selection_proposal_id: str | None = None,
) -> CandidateReviewActionPlan:
    """Plan one exact accept/decline action without writing canonical state."""

    if decision not in CANDIDATE_REVIEW_DECISIONS:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Candidate review decision must be select or decline.",
        )
    if selection_proposal_id is not None and (
        not isinstance(selection_proposal_id, str)
        or not selection_proposal_id.strip()
    ):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "selection_proposal_id must be a nonempty identifier when provided.",
        )

    detail = get_candidate_review_detail(workspace_root, entry_id)
    candidate = detail.inbox_detail.candidate
    item = detail.inbox_detail.item
    if candidate is None or detail.curation_provenance_evaluation_id is None:
        raise CandidateReviewError(
            "candidate_review.not_selectable",
            "This persisted Candidate inbox entry is reviewable but not selectable.",
        )

    pending = tuple(proposal for proposal in detail.proposals if proposal.undecided)
    proposal: CandidateReviewProposalSummary | None = None
    if selection_proposal_id is not None:
        if proposed_section_ids or intended_profile_requirement_ids:
            raise CandidateReviewError(
                "candidate_review.invalid_request",
                "Existing Proposal decisions use the Proposal's exact stored intent.",
            )
        proposal = next(
            (
                value
                for value in pending
                if value.selection_proposal_id == selection_proposal_id
            ),
            None,
        )
        if proposal is None:
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "The exact undecided Selection Proposal is unavailable; review again.",
            )
        sections = proposal.proposed_section_ids
        requirement_ids = proposal.intended_profile_requirement_ids
        operation = "decide_selection"
    else:
        if pending:
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "An undecided Selection Proposal already exists; choose its exact identity.",
            )
        if item.selected_state == "selected":
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "Candidate already has an active Selection; use Selection management instead.",
            )
        sections = _validated_identifiers(
            proposed_section_ids,
            field_name="proposed_section_ids",
            nonempty=True,
        )
        requirement_ids = _validated_identifiers(
            intended_profile_requirement_ids,
            field_name="intended_profile_requirement_ids",
            nonempty=False,
        )
        eligible_sections = {value.section_id for value in detail.sections}
        if not set(sections).issubset(eligible_sections):
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "Candidate is not eligible for every exact proposed section.",
            )
        if not set(requirement_ids).issubset(detail.profile_requirement_ids):
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "One or more exact Profile requirement IDs are unavailable.",
            )
        operation = "direct_select" if decision == "select" else "direct_decline"

    return CandidateReviewActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=item.entry_id,
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        profile_binding_id=item.profile_binding_id,
        portfolio_profile_id=item.portfolio_profile_id,
        profile_revision=item.profile_revision,
        candidate_id=candidate.candidate_id,
        current_review_evaluation_id=detail.current_review_evaluation_id,
        curation_provenance_evaluation_id=(
            detail.curation_provenance_evaluation_id
        ),
        candidate_condition=candidate.condition_state,
        stale_state=item.stale_state,
        stale_reason_codes=item.stale_reason_codes,
        decision=decision,
        selection_proposal_id=(
            None if proposal is None else proposal.selection_proposal_id
        ),
        proposed_section_ids=sections,
        intended_profile_requirement_ids=requirement_ids,
        operation=operation,
        confirmation_phrase=(
            "SELECT CANDIDATE" if decision == "select" else "DECLINE CANDIDATE"
        ),
        condition_acknowledgement_required=(
            decision == "select"
            and candidate.condition_state != "ready_for_consideration"
        ),
    )


def _validated_reason(value: str, *, field_name: str = "reason") -> str:
    if not isinstance(value, str):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} must be text.",
        )
    text = value.strip()
    if not text or len(text) > 4000:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} must contain 1 to 4000 characters.",
        )
    return text


def _require_plan_contract(contract_version: str) -> None:
    if contract_version != CANDIDATE_REVIEW_CONTRACT_VERSION:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Candidate review action plan contract is unsupported.",
        )


def _active_selection_summary(
    detail: CandidateReviewDetail,
    selection_id: str,
) -> CandidateReviewSelectionSummary:
    selection = next(
        (item for item in detail.selections if item.selection_id == selection_id),
        None,
    )
    if selection is None or selection.lifecycle_state != "activated":
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "The exact active Selection is unavailable; review Candidate state again.",
        )
    return selection


def _candidate_section_summary(
    detail: CandidateReviewDetail,
    section_id: str,
) -> CandidateReviewSectionSummary:
    section = next(
        (item for item in detail.sections if item.section_id == section_id),
        None,
    )
    if section is None:
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "The exact section is not eligible for this Candidate.",
        )
    if section.arrangement_pointer_conflict:
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "The section Arrangement pointer is conflicted; resolve it before curating.",
        )
    return section


def execute_candidate_decision(
    workspace_root: str | Path,
    plan: CandidateReviewActionPlan,
    *,
    actor: ActorAttribution,
    authority_gate: CurationAuthorityGate,
    rationale_text: str | None = None,
) -> CurationMutationResult:
    """Execute one previously reviewed exact Candidate decision plan."""

    _require_plan_contract(plan.contract_version)
    if plan.operation == "direct_select":
        return select_candidate_directly(
            workspace_root,
            portfolio_id=plan.portfolio_id,
            candidate_id=plan.candidate_id,
            selected_by=actor,
            proposed_section_ids=plan.proposed_section_ids,
            intended_profile_requirement_ids=plan.intended_profile_requirement_ids,
            rationale_text=rationale_text,
            expected_state_revision=plan.observed_state_revision,
            authority_gate=authority_gate,
        )
    if plan.operation == "direct_decline":
        return reject_candidate_directly(
            workspace_root,
            portfolio_id=plan.portfolio_id,
            candidate_id=plan.candidate_id,
            rejected_by=actor,
            proposed_section_ids=plan.proposed_section_ids,
            intended_profile_requirement_ids=plan.intended_profile_requirement_ids,
            rationale_text=rationale_text,
            expected_state_revision=plan.observed_state_revision,
            authority_gate=authority_gate,
        )
    if plan.operation == "decide_selection" and plan.selection_proposal_id is not None:
        return decide_selection_proposal(
            workspace_root,
            portfolio_id=plan.portfolio_id,
            selection_proposal_id=plan.selection_proposal_id,
            decision="accepted" if plan.decision == "select" else "rejected",
            decided_by=actor,
            rationale_text=rationale_text,
            expected_state_revision=plan.observed_state_revision,
            authority_gate=authority_gate,
        )
    raise CandidateReviewError(
        "candidate_review.invalid_request",
        "Candidate review action plan cannot be executed.",
    )


def plan_selection_placement(
    workspace_root: str | Path,
    *,
    entry_id: str,
    selection_id: str,
    section_id: str,
) -> CandidateReviewPlacementActionPlan:
    """Plan one explicit Placement without mutating canonical state."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    candidate = detail.inbox_detail.candidate
    if candidate is None or detail.curation_provenance_evaluation_id is None:
        raise CandidateReviewError(
            "candidate_review.not_selectable",
            "This Candidate inbox entry has no selectable Candidate.",
        )
    selection = _active_selection_summary(detail, selection_id)
    section = _candidate_section_summary(detail, section_id)
    if any(
        placement.selection_id == selection.selection_id
        and placement.section_id == section.section_id
        and placement.lifecycle_state == "activated"
        for placement in detail.placements
    ):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Selection already has an active Placement in this exact section.",
        )
    if (
        section.maximum_placements is not None
        and section.active_placement_count >= section.maximum_placements
    ):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "The exact section is already at its Placement maximum.",
        )
    return CandidateReviewPlacementActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        candidate_id=candidate.candidate_id,
        current_review_evaluation_id=detail.current_review_evaluation_id,
        curation_provenance_evaluation_id=detail.curation_provenance_evaluation_id,
        selection_id=selection.selection_id,
        selection_evaluation_id=selection.candidate_evaluation_id,
        section_id=section.section_id,
        section_label=section.label,
        active_placement_count=section.active_placement_count,
        maximum_placements=section.maximum_placements,
        expected_arrangement_pointer_revision=section.arrangement_pointer_revision,
        confirmation_phrase="PLACE SELECTION",
    )


def execute_selection_placement(
    workspace_root: str | Path,
    plan: CandidateReviewPlacementActionPlan,
    *,
    placed_by: ActorAttribution,
    authority_gate: CurationAuthorityGate,
    presentation: PlacementPresentation | None = None,
) -> CurationMutationResult:
    """Execute one exact Placement plan through the canonical curation service."""

    _require_plan_contract(plan.contract_version)
    return place_selection(
        workspace_root,
        portfolio_id=plan.portfolio_id,
        selection_id=plan.selection_id,
        section_id=plan.section_id,
        placed_by=placed_by,
        expected_state_revision=plan.observed_state_revision,
        expected_arrangement_pointer_revision=plan.expected_arrangement_pointer_revision,
        authority_gate=authority_gate,
        presentation=presentation,
    )


def plan_selection_withdrawal(
    workspace_root: str | Path,
    *,
    entry_id: str,
    selection_id: str,
    reason: str,
) -> CandidateReviewWithdrawalActionPlan:
    """Plan append-preserving withdrawal of one exact active Selection."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    candidate = detail.inbox_detail.candidate
    if candidate is None or detail.curation_provenance_evaluation_id is None:
        raise CandidateReviewError(
            "candidate_review.not_selectable",
            "This Candidate inbox entry has no selectable Candidate.",
        )
    selection = _active_selection_summary(detail, selection_id)
    active_placements = tuple(
        item
        for item in detail.placements
        if item.selection_id == selection.selection_id
        and item.lifecycle_state == "activated"
    )
    section_ids = tuple(sorted({item.section_id for item in active_placements}))
    pointers = tuple(
        CandidateReviewArrangementPointerObservation(
            section_id=section_id,
            pointer_revision=_candidate_section_summary(
                detail, section_id
            ).arrangement_pointer_revision,
        )
        for section_id in section_ids
    )
    return CandidateReviewWithdrawalActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        candidate_id=candidate.candidate_id,
        current_review_evaluation_id=detail.current_review_evaluation_id,
        curation_provenance_evaluation_id=detail.curation_provenance_evaluation_id,
        selection_id=selection.selection_id,
        selection_evaluation_id=selection.candidate_evaluation_id,
        active_placement_ids=tuple(item.placement_id for item in active_placements),
        affected_section_ids=section_ids,
        arrangement_pointers=pointers,
        reason=_validated_reason(reason),
        confirmation_phrase="WITHDRAW SELECTION",
    )


def execute_selection_withdrawal(
    workspace_root: str | Path,
    plan: CandidateReviewWithdrawalActionPlan,
    *,
    withdrawn_by: ActorAttribution,
    authority_gate: CurationAuthorityGate,
) -> CurationMutationResult:
    """Execute one exact withdrawal plan without recomputing observed pointers."""

    _require_plan_contract(plan.contract_version)
    return withdraw_selection(
        workspace_root,
        portfolio_id=plan.portfolio_id,
        selection_id=plan.selection_id,
        withdrawn_by=withdrawn_by,
        expected_state_revision=plan.observed_state_revision,
        expected_pointer_revisions={
            item.section_id: item.pointer_revision for item in plan.arrangement_pointers
        },
        authority_gate=authority_gate,
        reason=plan.reason,
    )


def _replacement_pointer_observations(
    detail: CandidateReviewDetail,
    successor_detail: CandidateReviewDetail,
    section_ids: tuple[str, ...],
) -> tuple[CandidateReviewArrangementPointerObservation, ...]:
    values: list[CandidateReviewArrangementPointerObservation] = []
    for section_id in section_ids:
        section = next(
            (item for item in detail.sections if item.section_id == section_id),
            None,
        )
        if section is None:
            section = next(
                (
                    item
                    for item in successor_detail.sections
                    if item.section_id == section_id
                ),
                None,
            )
        if section is None:
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "An affected replacement section is unavailable; review again.",
            )
        if section.arrangement_pointer_conflict:
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "An affected replacement section has a conflicted Arrangement pointer.",
            )
        values.append(
            CandidateReviewArrangementPointerObservation(
                section_id=section.section_id,
                pointer_revision=section.arrangement_pointer_revision,
            )
        )
    return tuple(values)


def plan_selection_replacement(
    workspace_root: str | Path,
    *,
    entry_id: str,
    selection_id: str,
    successor_entry_id: str,
    proposed_section_ids: tuple[str, ...],
    placement_dispositions: Mapping[str, str | None],
    reason: str,
) -> CandidateReviewReplacementActionPlan:
    """Plan one explicit Selection replacement and every Placement disposition."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    successor_detail = get_candidate_review_detail(workspace_root, successor_entry_id)
    if detail.observed_state_revision != successor_detail.observed_state_revision:
        raise CandidateReviewError(
            "candidate_review.state_changed",
            "Portfolio state changed while replacement Candidates were reviewed.",
        )
    current_item = detail.inbox_detail.item
    successor_item = successor_detail.inbox_detail.item
    if (
        current_item.portfolio_id != successor_item.portfolio_id
        or current_item.profile_binding_id != successor_item.profile_binding_id
        or current_item.portfolio_profile_id != successor_item.portfolio_profile_id
        or current_item.profile_revision != successor_item.profile_revision
    ):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Replacement Candidate must use the same Portfolio and exact Profile context.",
        )
    candidate = detail.inbox_detail.candidate
    successor = successor_detail.inbox_detail.candidate
    if (
        candidate is None
        or successor is None
        or detail.curation_provenance_evaluation_id is None
        or successor_detail.curation_provenance_evaluation_id is None
    ):
        raise CandidateReviewError(
            "candidate_review.not_selectable",
            "Replacement requires two exact positive Candidate entries.",
        )
    if candidate.candidate_id == successor.candidate_id:
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "A Selection cannot be replaced by its currently selected Candidate.",
        )
    selection = _active_selection_summary(detail, selection_id)
    if any(item.lifecycle_state == "activated" for item in successor_detail.selections):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Successor Candidate already has an active Selection.",
        )
    proposed_sections = _validated_identifiers(
        proposed_section_ids,
        field_name="proposed_section_ids",
        nonempty=True,
    )
    successor_sections = {item.section_id for item in successor_detail.sections}
    if not set(proposed_sections).issubset(successor_sections):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Replacement Proposal includes a section not eligible for the successor.",
        )
    active_placements = tuple(
        item
        for item in detail.placements
        if item.selection_id == selection.selection_id
        and item.lifecycle_state == "activated"
    )
    dispositions = dict(placement_dispositions)
    if set(dispositions) != {item.placement_id for item in active_placements}:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Replacement requires one explicit disposition for every active Placement.",
        )
    normalized: list[CandidateReviewReplacementDisposition] = []
    migrated_sections: list[str] = []
    for placement in active_placements:
        target = dispositions[placement.placement_id]
        if target is not None and (not isinstance(target, str) or not target.strip()):
            raise CandidateReviewError(
                "candidate_review.invalid_request",
                "Replacement target section IDs must be nonempty when provided.",
            )
        if target is not None and target not in successor_sections:
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "A migrated Placement target is not eligible for the successor Candidate.",
            )
        if target is not None:
            migrated_sections.append(target)
        normalized.append(
            CandidateReviewReplacementDisposition(
                placement_id=placement.placement_id,
                source_section_id=placement.section_id,
                target_section_id=target,
            )
        )
    if len(migrated_sections) != len(set(migrated_sections)):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Replacement cannot migrate multiple Placements into one exact section.",
        )
    affected_sections = tuple(
        sorted(
            {item.section_id for item in active_placements}
            | set(migrated_sections)
        )
    )
    pointers = _replacement_pointer_observations(
        detail, successor_detail, affected_sections
    )
    return CandidateReviewReplacementActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=current_item.entry_id,
        successor_entry_id=successor_item.entry_id,
        portfolio_id=current_item.portfolio_id,
        selection_id=selection.selection_id,
        candidate_id=candidate.candidate_id,
        current_review_evaluation_id=detail.current_review_evaluation_id,
        curation_provenance_evaluation_id=detail.curation_provenance_evaluation_id,
        successor_candidate_id=successor.candidate_id,
        successor_current_review_evaluation_id=(
            successor_detail.current_review_evaluation_id
        ),
        successor_curation_provenance_evaluation_id=(
            successor_detail.curation_provenance_evaluation_id
        ),
        successor_candidate_condition=successor.condition_state,
        successor_stale_state=successor_item.stale_state,
        successor_stale_reason_codes=successor_item.stale_reason_codes,
        proposed_section_ids=proposed_sections,
        placement_dispositions=tuple(normalized),
        arrangement_pointers=pointers,
        reason=_validated_reason(reason),
        confirmation_phrase="REPLACE SELECTION",
    )


def execute_selection_replacement(
    workspace_root: str | Path,
    plan: CandidateReviewReplacementActionPlan,
    *,
    replaced_by: ActorAttribution,
    authority_gate: CurationAuthorityGate,
) -> CurationMutationResult:
    """Execute one exact replacement plan without recomputing dispositions."""

    _require_plan_contract(plan.contract_version)
    return replace_selection(
        workspace_root,
        portfolio_id=plan.portfolio_id,
        selection_id=plan.selection_id,
        successor_candidate_id=plan.successor_candidate_id,
        replaced_by=replaced_by,
        placement_dispositions={
            item.placement_id: item.target_section_id
            for item in plan.placement_dispositions
        },
        expected_state_revision=plan.observed_state_revision,
        expected_pointer_revisions={
            item.section_id: item.pointer_revision for item in plan.arrangement_pointers
        },
        authority_gate=authority_gate,
        reason=plan.reason,
        proposed_section_ids=plan.proposed_section_ids,
    )


def _validated_text(
    value: str,
    *,
    field_name: str,
    maximum: int,
) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} must be nonempty trimmed text.",
        )
    if len(value) > maximum:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            f"{field_name} exceeds its supported length.",
        )
    return value


def _validated_optional_text(
    value: str | None,
    *,
    field_name: str,
    maximum: int,
) -> str | None:
    if value is None:
        return None
    return _validated_text(value, field_name=field_name, maximum=maximum)


def _validated_target_references(
    values: tuple[CurationTargetRef, ...],
) -> tuple[CurationTargetRef, ...]:
    result = tuple(values)
    if not result or any(not isinstance(item, CurationTargetRef) for item in result):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "target_references must contain exact CurationTargetRef values.",
        )
    if len(set(result)) != len(result):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "target_references must not contain duplicates.",
        )
    return result


def _target_exists_in_context(
    detail: CandidateReviewDetail,
    curation: CurationState,
    target: CurationTargetRef,
) -> bool:
    item = detail.inbox_detail.item
    portfolio_id = item.portfolio_id
    binding_id = item.profile_binding_id
    if target.target_kind == "selection":
        return target.target_revision is None and any(
            value.selection_id == target.target_id
            and value.portfolio_id == portfolio_id
            and value.profile_binding_id == binding_id
            for value in curation.selections
        )
    if target.target_kind == "placement":
        return target.target_revision is None and any(
            value.placement_id == target.target_id
            and value.portfolio_id == portfolio_id
            and value.profile_binding_id == binding_id
            for value in curation.placements
        )
    if target.target_kind == "selection_proposal":
        return target.target_revision is None and any(
            value.selection_proposal_id == target.target_id
            and value.portfolio_id == portfolio_id
            and value.profile_binding_id == binding_id
            for value in curation.proposals
        )
    if target.target_kind == "section":
        return target.target_revision is None and any(
            value.section_id == target.target_id
            for value in detail.inbox_detail.profile_revision.sections
        )
    if target.target_kind == "arrangement":
        return target.target_revision is None and any(
            value.arrangement_id == target.target_id
            and value.portfolio_id == portfolio_id
            and value.profile_binding_id == binding_id
            for value in curation.arrangements
        )
    if target.target_kind == "annotation":
        return target.target_revision is not None and any(
            value.annotation_id == target.target_id
            and value.annotation_revision == target.target_revision
            and value.portfolio_id == portfolio_id
            and value.profile_binding_id == binding_id
            for value in curation.annotations
        )
    if target.target_kind == "reflection":
        return target.target_revision is not None and any(
            value.reflection_id == target.target_id
            and value.reflection_revision == target.target_revision
            and value.portfolio_id == portfolio_id
            and value.profile_binding_id == binding_id
            for value in curation.reflections
        )
    if target.target_kind == "composition":
        return target.target_revision is not None and any(
            value.portfolio_id == target.target_id == portfolio_id
            and value.profile_binding_id == binding_id
            and value.composition_revision == target.target_revision
            for value in curation.compositions
        )
    if target.target_kind == "portfolio":
        return target.target_revision is None and target.target_id == portfolio_id
    return False


def _candidate_relevant_target(
    detail: CandidateReviewDetail,
    target: CurationTargetRef,
) -> bool:
    if target.target_kind == "selection":
        return target.target_id in {item.selection_id for item in detail.selections}
    if target.target_kind == "placement":
        return target.target_id in {item.placement_id for item in detail.placements}
    if target.target_kind == "selection_proposal":
        return target.target_id in {
            item.selection_proposal_id for item in detail.proposals
        }
    if target.target_kind == "section":
        return target.target_id in {item.section_id for item in detail.sections}
    if target.target_kind == "annotation":
        return any(
            item.annotation_id == target.target_id
            and item.annotation_revision == target.target_revision
            for item in detail.annotations
        )
    if target.target_kind == "reflection":
        return any(
            item.reflection_id == target.target_id
            and item.reflection_revision == target.target_revision
            for item in detail.reflections
        )
    if target.target_kind == "portfolio":
        return target.target_id == detail.inbox_detail.item.portfolio_id
    return False


def _require_guided_targets(
    detail: CandidateReviewDetail,
    curation: CurationState,
    targets: tuple[CurationTargetRef, ...],
    *,
    require_candidate_relevance: bool = True,
) -> tuple[CurationTargetRef, ...]:
    values = _validated_target_references(targets)
    if any(not _target_exists_in_context(detail, curation, item) for item in values):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "One or more targets are not exact current Portfolio/Profile targets.",
        )
    if require_candidate_relevance and not any(
        _candidate_relevant_target(detail, item) for item in values
    ):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "The target set is not connected to this Candidate review entry.",
        )
    return values


def _require_annotation_scope(
    target_scope: str,
    targets: tuple[CurationTargetRef, ...],
) -> None:
    expected = {
        "selection": "selection",
        "placement": "placement",
        "section": "section",
    }.get(target_scope)
    if target_scope == "comparison_set":
        if len(targets) < 2 or any(
            item.target_kind != "selection" for item in targets
        ):
            raise CandidateReviewError(
                "candidate_review.invalid_request",
                "comparison_set Annotation requires at least two exact Selections.",
            )
        return
    if expected is None or len(targets) != 1 or targets[0].target_kind != expected:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Annotation scope and exact target references do not agree.",
        )


def _require_reflection_scope(
    target_scope: str,
    targets: tuple[CurationTargetRef, ...],
) -> None:
    expected = {
        "selection": "selection",
        "placement": "placement",
        "section": "section",
        "portfolio": "portfolio",
    }.get(target_scope)
    if target_scope == "comparison_set":
        if (
            len(targets) < 2
            or any(item.target_kind != "selection" for item in targets)
            or any(item.semantic_role is None for item in targets)
        ):
            raise CandidateReviewError(
                "candidate_review.invalid_request",
                "comparison_set Reflection requires two or more Selection targets "
                "with explicit semantic roles.",
            )
        return
    if expected is None or len(targets) != 1 or targets[0].target_kind != expected:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Reflection scope and exact target references do not agree.",
        )


def _require_profile_requirement(
    detail: CandidateReviewDetail,
    requirement_id: str,
    *,
    requirement_kind: str,
) -> CandidateReviewProfileRequirementSummary:
    match = next(
        (
            item
            for item in detail.profile_requirements
            if item.requirement_id == requirement_id
            and item.requirement_kind == requirement_kind
        ),
        None,
    )
    if match is None:
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            f"Exact Profile {requirement_kind} requirement is unavailable.",
        )
    return match


def plan_annotation_creation(
    workspace_root: str | Path,
    *,
    entry_id: str,
    purpose: str,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    content: str,
    language: str = "en",
    content_format: str = "plain_text",
    intended_presentation_class: str | None = None,
) -> CandidateReviewAnnotationActionPlan:
    """Plan one new bounded Annotation over exact reviewed curation targets."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    curation = _load_curation_state(workspace_root, detail.observed_state_revision)
    targets = _require_guided_targets(detail, curation, target_references)
    _require_annotation_scope(target_scope, targets)
    return CandidateReviewAnnotationActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        action="create",
        annotation_id=None,
        expected_annotation_revision=None,
        purpose=_validated_text(purpose, field_name="purpose", maximum=128),
        target_scope=target_scope,
        target_references=targets,
        content=_validated_text(content, field_name="content", maximum=12000),
        language=_validated_text(language, field_name="language", maximum=64),
        content_format=_validated_text(
            content_format, field_name="content_format", maximum=128
        ),
        intended_presentation_class=_validated_optional_text(
            intended_presentation_class,
            field_name="intended_presentation_class",
            maximum=128,
        ),
        confirmation_phrase="SAVE ANNOTATION",
    )


def plan_annotation_revision(
    workspace_root: str | Path,
    *,
    entry_id: str,
    annotation_id: str,
    content: str,
    purpose: str | None = None,
    target_scope: str | None = None,
    target_references: tuple[CurationTargetRef, ...] | None = None,
    language: str | None = None,
    content_format: str | None = None,
    intended_presentation_class: str | None = None,
) -> CandidateReviewAnnotationActionPlan:
    """Plan a successor Annotation revision from one exact current head."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    curation = _load_curation_state(workspace_root, detail.observed_state_revision)
    heads = curation.annotation_heads(annotation_id)
    if len(heads) != 1:
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Annotation does not have one exact current revision head.",
        )
    prior = heads[0]
    if not any(
        item.annotation_id == prior.annotation_id
        and item.annotation_revision == prior.annotation_revision
        for item in detail.annotations
    ):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Annotation is not connected to this Candidate review entry.",
        )
    scope = prior.target_scope if target_scope is None else target_scope
    targets = (
        prior.target_references
        if target_references is None
        else _require_guided_targets(detail, curation, target_references)
    )
    if target_references is None:
        _require_guided_targets(detail, curation, targets)
    _require_annotation_scope(scope, targets)
    return CandidateReviewAnnotationActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        action="revise",
        annotation_id=prior.annotation_id,
        expected_annotation_revision=prior.annotation_revision,
        purpose=(
            prior.purpose
            if purpose is None
            else _validated_text(purpose, field_name="purpose", maximum=128)
        ),
        target_scope=scope,
        target_references=targets,
        content=_validated_text(content, field_name="content", maximum=12000),
        language=(
            prior.language
            if language is None
            else _validated_text(language, field_name="language", maximum=64)
        ),
        content_format=(
            prior.content_format
            if content_format is None
            else _validated_text(
                content_format, field_name="content_format", maximum=128
            )
        ),
        intended_presentation_class=(
            prior.intended_presentation_class
            if intended_presentation_class is None
            else _validated_optional_text(
                intended_presentation_class,
                field_name="intended_presentation_class",
                maximum=128,
            )
        ),
        confirmation_phrase="SAVE ANNOTATION",
    )


def execute_annotation_action(
    workspace_root: str | Path,
    plan: CandidateReviewAnnotationActionPlan,
    *,
    author: ActorAttribution,
    authority_gate: CurationAuthorityGate,
) -> CurationMutationResult:
    """Execute an exact Annotation plan without refreshing targets or revision."""

    _require_plan_contract(plan.contract_version)
    if plan.action == "create":
        return create_annotation(
            workspace_root,
            portfolio_id=plan.portfolio_id,
            purpose=plan.purpose,
            target_scope=plan.target_scope,
            target_references=plan.target_references,
            author=author,
            content=plan.content,
            expected_state_revision=plan.observed_state_revision,
            authority_gate=authority_gate,
            language=plan.language,
            content_format=plan.content_format,
            intended_presentation_class=plan.intended_presentation_class,
        )
    if (
        plan.action != "revise"
        or plan.annotation_id is None
        or plan.expected_annotation_revision is None
    ):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Annotation action plan is incomplete.",
        )
    return revise_annotation(
        workspace_root,
        portfolio_id=plan.portfolio_id,
        annotation_id=plan.annotation_id,
        expected_annotation_revision=plan.expected_annotation_revision,
        author=author,
        content=plan.content,
        expected_state_revision=plan.observed_state_revision,
        authority_gate=authority_gate,
        purpose=plan.purpose,
        target_scope=plan.target_scope,
        target_references=plan.target_references,
        language=plan.language,
        content_format=plan.content_format,
        intended_presentation_class=plan.intended_presentation_class,
    )


def plan_reflection_creation(
    workspace_root: str | Path,
    *,
    entry_id: str,
    reflection_requirement_id: str,
    prompt_id: str,
    prompt_version: str,
    prompt_snapshot: str,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    content: str,
    content_mode: str = "inline_text",
    language: str = "en",
    content_format: str = "plain_text",
) -> CandidateReviewReflectionActionPlan:
    """Plan one new Reflection against an exact bound Profile requirement."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    _require_profile_requirement(
        detail, reflection_requirement_id, requirement_kind="reflection"
    )
    curation = _load_curation_state(workspace_root, detail.observed_state_revision)
    targets = _require_guided_targets(
        detail,
        curation,
        target_references,
        require_candidate_relevance=target_scope != "portfolio",
    )
    _require_reflection_scope(target_scope, targets)
    if content_mode not in {
        "inline_text",
        "structured_response",
        "external_reference",
    }:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Reflection content_mode is not supported.",
        )
    return CandidateReviewReflectionActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        action="create",
        reflection_id=None,
        expected_reflection_revision=None,
        reflection_requirement_id=reflection_requirement_id,
        prompt_id=_validated_text(prompt_id, field_name="prompt_id", maximum=128),
        prompt_version=_validated_text(
            prompt_version, field_name="prompt_version", maximum=128
        ),
        prompt_snapshot=_validated_text(
            prompt_snapshot, field_name="prompt_snapshot", maximum=4000
        ),
        target_scope=target_scope,
        target_references=targets,
        content=_validated_text(content, field_name="content", maximum=16000),
        content_mode=_validated_text(
            content_mode, field_name="content_mode", maximum=128
        ),
        language=_validated_text(language, field_name="language", maximum=64),
        content_format=_validated_text(
            content_format, field_name="content_format", maximum=128
        ),
        confirmation_phrase="SAVE REFLECTION",
    )


def plan_reflection_revision(
    workspace_root: str | Path,
    *,
    entry_id: str,
    reflection_id: str,
    content: str,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    prompt_snapshot: str | None = None,
    target_scope: str | None = None,
    target_references: tuple[CurationTargetRef, ...] | None = None,
) -> CandidateReviewReflectionActionPlan:
    """Plan a successor Reflection revision from one exact current head."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    curation = _load_curation_state(workspace_root, detail.observed_state_revision)
    heads = curation.reflection_heads(reflection_id)
    if len(heads) != 1:
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Reflection does not have one exact current revision head.",
        )
    prior = heads[0]
    if not any(
        item.reflection_id == prior.reflection_id
        and item.reflection_revision == prior.reflection_revision
        for item in detail.reflections
    ):
        raise CandidateReviewError(
            "candidate_review.action_not_available",
            "Reflection is not connected to this Candidate review entry.",
        )
    _require_profile_requirement(
        detail, prior.reflection_requirement_id, requirement_kind="reflection"
    )
    scope = prior.target_scope if target_scope is None else target_scope
    targets = (
        prior.target_references
        if target_references is None
        else _require_guided_targets(
            detail,
            curation,
            target_references,
            require_candidate_relevance=scope != "portfolio",
        )
    )
    if target_references is None:
        _require_guided_targets(
            detail,
            curation,
            targets,
            require_candidate_relevance=scope != "portfolio",
        )
    _require_reflection_scope(scope, targets)
    return CandidateReviewReflectionActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        action="revise",
        reflection_id=prior.reflection_id,
        expected_reflection_revision=prior.reflection_revision,
        reflection_requirement_id=prior.reflection_requirement_id,
        prompt_id=(
            prior.prompt_id
            if prompt_id is None
            else _validated_text(prompt_id, field_name="prompt_id", maximum=128)
        ),
        prompt_version=(
            prior.prompt_version
            if prompt_version is None
            else _validated_text(
                prompt_version, field_name="prompt_version", maximum=128
            )
        ),
        prompt_snapshot=(
            prior.prompt_snapshot
            if prompt_snapshot is None
            else _validated_text(
                prompt_snapshot, field_name="prompt_snapshot", maximum=4000
            )
        ),
        target_scope=scope,
        target_references=targets,
        content=_validated_text(content, field_name="content", maximum=16000),
        content_mode=prior.content_mode,
        language=prior.language,
        content_format=prior.content_format,
        confirmation_phrase="SAVE REFLECTION",
    )


def execute_reflection_action(
    workspace_root: str | Path,
    plan: CandidateReviewReflectionActionPlan,
    *,
    author: ActorAttribution,
    authority_gate: CurationAuthorityGate,
) -> CurationMutationResult:
    """Execute an exact Reflection plan without changing requirement or targets."""

    _require_plan_contract(plan.contract_version)
    if plan.action == "create":
        return create_reflection(
            workspace_root,
            portfolio_id=plan.portfolio_id,
            reflection_requirement_id=plan.reflection_requirement_id,
            prompt_id=plan.prompt_id,
            prompt_version=plan.prompt_version,
            prompt_snapshot=plan.prompt_snapshot,
            author=author,
            target_scope=plan.target_scope,
            target_references=plan.target_references,
            content=plan.content,
            expected_state_revision=plan.observed_state_revision,
            authority_gate=authority_gate,
            content_mode=plan.content_mode,
            language=plan.language,
            content_format=plan.content_format,
        )
    if (
        plan.action != "revise"
        or plan.reflection_id is None
        or plan.expected_reflection_revision is None
    ):
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Reflection action plan is incomplete.",
        )
    return revise_reflection(
        workspace_root,
        portfolio_id=plan.portfolio_id,
        reflection_id=plan.reflection_id,
        expected_reflection_revision=plan.expected_reflection_revision,
        author=author,
        content=plan.content,
        expected_state_revision=plan.observed_state_revision,
        authority_gate=authority_gate,
        prompt_id=plan.prompt_id,
        prompt_version=plan.prompt_version,
        prompt_snapshot=plan.prompt_snapshot,
        target_scope=plan.target_scope,
        target_references=plan.target_references,
    )


def plan_curation_review(
    workspace_root: str | Path,
    *,
    entry_id: str,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    decision: str,
    reason: str,
    approval_requirement_id: str | None = None,
    required_follow_up_codes: tuple[str, ...] = (),
    predecessor_review_decision_id: str | None = None,
) -> CandidateReviewCurationReviewActionPlan:
    """Plan one explicit curation Review over exact immutable targets."""

    detail = get_candidate_review_detail(workspace_root, entry_id)
    curation = _load_curation_state(workspace_root, detail.observed_state_revision)
    targets = _require_guided_targets(detail, curation, target_references)
    if approval_requirement_id is not None:
        _require_profile_requirement(
            detail, approval_requirement_id, requirement_kind="approval"
        )
    if predecessor_review_decision_id is not None:
        predecessor = next(
            (
                item
                for item in curation.reviews
                if item.curation_review_decision_id == predecessor_review_decision_id
                and item.portfolio_id == detail.inbox_detail.item.portfolio_id
                and item.profile_binding_id == detail.inbox_detail.item.profile_binding_id
            ),
            None,
        )
        if predecessor is None:
            raise CandidateReviewError(
                "candidate_review.action_not_available",
                "Predecessor curation Review is unavailable in the exact context.",
            )
    if decision not in {
        "approved",
        "rejected",
        "changes_requested",
        "acknowledged",
        "waived",
    }:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Curation Review decision is not supported.",
        )
    follow_up_codes = _validated_identifiers(
        required_follow_up_codes,
        field_name="required_follow_up_codes",
        nonempty=False,
    )
    return CandidateReviewCurationReviewActionPlan(
        contract_version=CANDIDATE_REVIEW_CONTRACT_VERSION,
        observed_state_revision=detail.observed_state_revision,
        entry_id=detail.inbox_detail.item.entry_id,
        portfolio_id=detail.inbox_detail.item.portfolio_id,
        target_scope=_validated_text(
            target_scope, field_name="target_scope", maximum=128
        ),
        target_references=targets,
        decision=_validated_text(decision, field_name="decision", maximum=128),
        reason=_validated_text(reason, field_name="reason", maximum=2000),
        approval_requirement_id=approval_requirement_id,
        required_follow_up_codes=follow_up_codes,
        predecessor_review_decision_id=predecessor_review_decision_id,
        confirmation_phrase="RECORD REVIEW",
    )


def execute_curation_review(
    workspace_root: str | Path,
    plan: CandidateReviewCurationReviewActionPlan,
    *,
    reviewed_by: ActorAttribution,
    authority_gate: CurationAuthorityGate,
) -> CurationMutationResult:
    """Execute one exact curation Review plan without retargeting revisions."""

    _require_plan_contract(plan.contract_version)
    return review_curation_target(
        workspace_root,
        portfolio_id=plan.portfolio_id,
        target_scope=plan.target_scope,
        target_references=plan.target_references,
        decision=plan.decision,
        reviewed_by=reviewed_by,
        reason=plan.reason,
        expected_state_revision=plan.observed_state_revision,
        authority_gate=authority_gate,
        approval_requirement_id=plan.approval_requirement_id,
        required_follow_up_codes=plan.required_follow_up_codes,
        predecessor_review_decision_id=plan.predecessor_review_decision_id,
    )


__all__ = [
    "CANDIDATE_REVIEW_CONTRACT_VERSION",
    "CANDIDATE_REVIEW_DECISIONS",
    "CANDIDATE_REVIEW_ERROR_CODES",
    "CandidateReviewActionPlan",
    "CandidateReviewAnnotationActionPlan",
    "CandidateReviewArrangementPointerObservation",
    "CandidateReviewActorSummary",
    "CandidateReviewAnnotationSummary",
    "CandidateReviewAvailabilitySummary",
    "CandidateReviewCurationReviewActionPlan",
    "CandidateReviewDetail",
    "CandidateReviewError",
    "CandidateReviewPlacementActionPlan",
    "CandidateReviewPlacementSummary",
    "CandidateReviewProfileRequirementSummary",
    "CandidateReviewProposalDecisionSummary",
    "CandidateReviewProposalSummary",
    "CandidateReviewReplacementActionPlan",
    "CandidateReviewReplacementDisposition",
    "CandidateReviewReflectionActionPlan",
    "CandidateReviewReflectionSummary",
    "CandidateReviewReviewSummary",
    "CandidateReviewSectionSummary",
    "CandidateReviewSelectionSummary",
    "CandidateReviewSourceSummary",
    "CandidateReviewSubjectRelationshipSummary",
    "CandidateReviewWithdrawalActionPlan",
    "execute_annotation_action",
    "execute_candidate_decision",
    "execute_curation_review",
    "execute_reflection_action",
    "execute_selection_placement",
    "execute_selection_replacement",
    "execute_selection_withdrawal",
    "get_candidate_review_detail",
    "list_candidate_review_entries",
    "plan_annotation_creation",
    "plan_annotation_revision",
    "plan_candidate_decision",
    "plan_curation_review",
    "plan_reflection_creation",
    "plan_reflection_revision",
    "plan_selection_placement",
    "plan_selection_replacement",
    "plan_selection_withdrawal",
]
