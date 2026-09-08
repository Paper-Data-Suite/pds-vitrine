"""Read-only preparation for exact Working Portfolio Composition creation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from vitrine.curation_services import (
    CurationAuthorityGate,
    CurationMutationResult,
    CurationWorkflowError,
    WorkingCompositionDerivation,
    WorkingCompositionSourceCurrentness,
    create_working_composition,
    derive_working_composition,
    observe_working_composition_source,
)
from vitrine.curation_state import CurationState, project_curation_state
from vitrine.models import (
    ActorAttribution,
    CurationRevisionRef,
    CurationTargetRef,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSelection,
    ProfileSectionDefinition,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

WORKING_COMPOSITION_CONTRACT_VERSION: Final[str] = (
    "vitrine_guided_working_composition_v1"
)

REQUIREMENT_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "satisfied_current_curation",
        "unresolved_missing",
        "optional_absent",
        "conditional_unresolved",
        "prohibited_clear",
        "audience_stage",
        "not_machine_evaluable",
    }
)

WORKING_COMPOSITION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "working_composition.invalid_request",
        "working_composition.context_not_found",
        "working_composition.state_changed",
        "working_composition.composition_pointer_changed",
        "working_composition.source_state_changed",
        "working_composition.preparation_mismatch",
    }
)


class WorkingCompositionError(RuntimeError):
    """Expected guided Working Composition failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in WORKING_COMPOSITION_ERROR_CODES:
            raise ValueError(f"unsupported Working Composition error code: {code}")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class WorkingCompositionPayloadPreview:
    selection_ids: tuple[str, ...]
    placement_ids: tuple[str, ...]
    arrangement_ids: tuple[str, ...]
    included_rationale_ids: tuple[str, ...]
    included_curation_revisions: tuple[CurationRevisionRef, ...]
    applicable_review_decision_ids: tuple[str, ...]
    related_profile_requirement_ids: tuple[str, ...]
    unresolved_obligation_codes: tuple[str, ...]
    coherence_state: str


@dataclass(frozen=True, slots=True)
class WorkingCompositionPlacementSummary:
    placement_id: str
    selection_id: str
    candidate_id: str
    candidate_display_snapshot: str
    candidate_condition_state: str
    unresolved_condition_codes: tuple[str, ...]
    section_id: str
    display_title: str | None
    display_caption: str | None


@dataclass(frozen=True, slots=True)
class WorkingCompositionSectionSummary:
    section_id: str
    label: str
    purpose: str
    order: int
    obligation: str
    minimum_placements: int
    maximum_placements: int | None
    active_placement_count: int
    current_arrangement_id: str | None
    current_arrangement_revision: int | None
    current_arrangement_pointer_revision: int | None
    placements: tuple[WorkingCompositionPlacementSummary, ...]


@dataclass(frozen=True, slots=True)
class WorkingCompositionSelectionSummary:
    selection_id: str
    candidate_id: str
    candidate_display_snapshot: str
    candidate_condition_state: str
    unresolved_condition_codes: tuple[str, ...]
    placement_ids: tuple[str, ...]
    section_ids: tuple[str, ...]
    is_placed: bool


@dataclass(frozen=True, slots=True)
class WorkingCompositionRequirementSummary:
    requirement_id: str
    title: str
    statement: str
    requirement_kind: str
    obligation: str
    scope_kind: str
    scope_reference: str | None
    satisfaction_class: str
    status: str
    related_to_frozen_inventory: bool
    associated_unresolved_obligation_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in REQUIREMENT_STATUSES:
            raise ValueError("unsupported Working Composition requirement status")




@dataclass(frozen=True, slots=True)
class WorkingCompositionSourceObservation:
    selection_id: str
    candidate_id: str
    publication_id: str
    series_head_publication_id: str | None
    observed_series_state: str
    observed_withdrawal_state: str
    current_use_state: str


@dataclass(frozen=True, slots=True)
class WorkingCompositionReviewSummary:
    curation_review_decision_id: str
    decision: str
    approval_requirement_id: str | None
    target_scope: str
    target_references: tuple[CurationTargetRef, ...]
    required_follow_up_codes: tuple[str, ...]
    requires_attention: bool


@dataclass(frozen=True, slots=True)
class WorkingCompositionAudienceSummary:
    audience_rule_id: str
    audience_class: str
    purpose: str
    allowed_content_classes: tuple[str, ...]
    prohibited_content_classes: tuple[str, ...]
    required_review_classes: tuple[str, ...]
    presentation_class: str
    retention_policy_reference: str | None


@dataclass(frozen=True, slots=True)
class WorkingCompositionPreparation:
    contract_version: str
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision_id: str
    profile_revision_number: int
    observed_composition_pointer_revision: int | None
    current_composition_revision: int | None
    predicted_composition_revision: int
    predecessor_composition_revision: int | None
    predicted_composition_pointer_revision: int
    disposition: str
    payload: WorkingCompositionPayloadPreview
    sections: tuple[WorkingCompositionSectionSummary, ...]
    selections: tuple[WorkingCompositionSelectionSummary, ...]
    unplaced_selection_ids: tuple[str, ...]
    requirements: tuple[WorkingCompositionRequirementSummary, ...]
    source_observations: tuple[WorkingCompositionSourceObservation, ...]
    reviews: tuple[WorkingCompositionReviewSummary, ...]
    audience_rules: tuple[WorkingCompositionAudienceSummary, ...]
    requested_composition_note: str | None
    composition_note_will_persist: bool
    preparation_fingerprint: str


def _payload_preview(
    derivation: WorkingCompositionDerivation,
) -> WorkingCompositionPayloadPreview:
    return WorkingCompositionPayloadPreview(
        selection_ids=derivation.selection_ids,
        placement_ids=derivation.placement_ids,
        arrangement_ids=derivation.arrangement_ids,
        included_rationale_ids=derivation.included_rationale_ids,
        included_curation_revisions=derivation.included_curation_revisions,
        applicable_review_decision_ids=derivation.applicable_review_decision_ids,
        related_profile_requirement_ids=derivation.related_profile_requirement_ids,
        unresolved_obligation_codes=derivation.unresolved_obligation_codes,
        coherence_state=derivation.coherence_state,
    )


def _exact_profile(
    state: CurationState,
    derivation: WorkingCompositionDerivation,
) -> PortfolioProfileRevision:
    matches = tuple(
        item
        for item in state.profile_revisions
        if item.portfolio_profile_id == derivation.profile_revision_id
        and item.profile_revision == derivation.profile_revision_number
    )
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Exact bound Profile Revision is unavailable for Composition preparation.",
            stage="preparation",
        )
    return matches[0]


def _candidate(
    state: CurationState,
    selection: PortfolioSelection,
) -> PortfolioCandidate:
    matches = tuple(
        item for item in state.candidates if item.candidate_id == selection.candidate_id
    )
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.candidate_not_found",
            "Composition Selection Candidate does not resolve uniquely.",
            stage="preparation",
        )
    return matches[0]


def _selection_conditions(
    state: CurationState,
    selection_id: str,
) -> tuple[str, ...]:
    heads = state.selection_heads(selection_id)
    if len(heads) != 1:
        raise CurationWorkflowError(
            "curation.composition_inconsistent",
            "Composition Selection lifecycle does not resolve uniquely.",
            stage="preparation",
        )
    return heads[0].unresolved_condition_codes


def _placement_summary(
    state: CurationState,
    placement: PortfolioPlacement,
) -> WorkingCompositionPlacementSummary:
    selections = tuple(
        item for item in state.selections if item.selection_id == placement.selection_id
    )
    if len(selections) != 1:
        raise CurationWorkflowError(
            "curation.selection_not_found",
            "Composition Placement Selection does not resolve uniquely.",
            stage="preparation",
        )
    selection = selections[0]
    candidate = _candidate(state, selection)
    presentation = placement.presentation
    return WorkingCompositionPlacementSummary(
        placement_id=placement.placement_id,
        selection_id=selection.selection_id,
        candidate_id=candidate.candidate_id,
        candidate_display_snapshot=candidate.display_snapshot,
        candidate_condition_state=candidate.condition_state,
        unresolved_condition_codes=_selection_conditions(state, selection.selection_id),
        section_id=placement.section_id,
        display_title=None if presentation is None else presentation.display_title,
        display_caption=None if presentation is None else presentation.display_caption,
    )


def _section_summaries(
    state: CurationState,
    profile: PortfolioProfileRevision,
    derivation: WorkingCompositionDerivation,
) -> tuple[WorkingCompositionSectionSummary, ...]:
    placement_by_id = {item.placement_id: item for item in state.placements}
    summaries: list[WorkingCompositionSectionSummary] = []
    for section in profile.sections:
        active = state.active_placements(
            portfolio_id=derivation.portfolio_id,
            profile_binding_id=derivation.profile_binding_id,
            section_id=section.section_id,
        )
        heads = state.arrangement_pointer_heads(
            derivation.portfolio_id,
            derivation.profile_binding_id,
            section.section_id,
        )
        if len(heads) > 1:
            raise CurationWorkflowError(
                "curation.arrangement_conflict",
                "Section Arrangement pointer is conflicted during "
                "Composition preparation.",
                stage="preparation",
            )
        pointer = heads[0] if heads else None
        arrangement = state.current_arrangement(
            derivation.portfolio_id,
            derivation.profile_binding_id,
            section.section_id,
        )
        if active and arrangement is None:
            raise CurationWorkflowError(
                "curation.arrangement_incomplete",
                "Active Placements require one exact current Arrangement.",
                stage="preparation",
            )
        ordered_ids = () if arrangement is None else arrangement.placement_ids
        if set(ordered_ids) != {item.placement_id for item in active}:
            raise CurationWorkflowError(
                "curation.arrangement_incomplete",
                "Current Arrangement must cover the exact active section Placements.",
                stage="preparation",
            )
        placements = tuple(
            _placement_summary(state, placement_by_id[placement_id])
            for placement_id in ordered_ids
        )
        summaries.append(
            WorkingCompositionSectionSummary(
                section_id=section.section_id,
                label=section.label,
                purpose=section.purpose,
                order=section.order,
                obligation=section.obligation,
                minimum_placements=section.minimum_placements,
                maximum_placements=section.maximum_placements,
                active_placement_count=len(active),
                current_arrangement_id=(
                    None if arrangement is None else arrangement.arrangement_id
                ),
                current_arrangement_revision=(
                    None if arrangement is None else arrangement.arrangement_revision
                ),
                current_arrangement_pointer_revision=(
                    None if pointer is None else pointer.pointer_revision
                ),
                placements=placements,
            )
        )
    return tuple(summaries)


def _selection_summaries(
    state: CurationState,
    profile: PortfolioProfileRevision,
    derivation: WorkingCompositionDerivation,
) -> tuple[WorkingCompositionSelectionSummary, ...]:
    selection_by_id = {item.selection_id: item for item in state.selections}
    active_placements = state.active_placements(
        portfolio_id=derivation.portfolio_id,
        profile_binding_id=derivation.profile_binding_id,
    )
    section_order = {item.section_id: item.order for item in profile.sections}
    summaries: list[WorkingCompositionSelectionSummary] = []
    for selection_id in derivation.selection_ids:
        selection = selection_by_id.get(selection_id)
        if selection is None:
            raise CurationWorkflowError(
                "curation.selection_not_found",
                "Composition Selection does not resolve uniquely.",
                stage="preparation",
            )
        candidate = _candidate(state, selection)
        placements = tuple(
            item
            for item in active_placements
            if item.selection_id == selection.selection_id
        )
        ordered_placement_ids = tuple(
            item
            for item in derivation.placement_ids
            if any(placement.placement_id == item for placement in placements)
        )
        section_ids = tuple(
            sorted(
                {item.section_id for item in placements},
                key=lambda section_id: section_order[section_id],
            )
        )
        summaries.append(
            WorkingCompositionSelectionSummary(
                selection_id=selection.selection_id,
                candidate_id=candidate.candidate_id,
                candidate_display_snapshot=candidate.display_snapshot,
                candidate_condition_state=candidate.condition_state,
                unresolved_condition_codes=_selection_conditions(
                    state, selection.selection_id
                ),
                placement_ids=ordered_placement_ids,
                section_ids=section_ids,
                is_placed=bool(ordered_placement_ids),
            )
        )
    return tuple(summaries)


def _current_reflection_requirement_ids(
    state: CurationState,
    derivation: WorkingCompositionDerivation,
) -> frozenset[str]:
    values: set[str] = set()
    for reflection_id in {item.reflection_id for item in state.reflections}:
        heads = state.reflection_heads(reflection_id)
        if len(heads) == 1:
            reflection = heads[0]
            if (
                reflection.portfolio_id == derivation.portfolio_id
                and reflection.profile_binding_id == derivation.profile_binding_id
            ):
                values.add(reflection.reflection_requirement_id)
    return frozenset(values)


def _approved_requirement_ids(
    state: CurationState,
    derivation: WorkingCompositionDerivation,
) -> frozenset[str]:
    applicable = set(derivation.applicable_review_decision_ids)
    approved: set[str] = set()
    for item in state.reviews:
        requirement_id = item.approval_requirement_id
        if (
            item.curation_review_decision_id in applicable
            and requirement_id is not None
            and item.decision in {"approved", "acknowledged", "waived"}
        ):
            approved.add(requirement_id)
    return frozenset(approved)


def _associated_codes(
    requirement: PortfolioProfileRequirement,
    status: str,
    unresolved_codes: frozenset[str],
) -> tuple[str, ...]:
    candidates: list[str] = []
    if status in {"unresolved_missing", "conditional_unresolved"}:
        if requirement.requirement_kind == "section":
            candidates.append("section_minimum_missing")
        elif requirement.requirement_kind == "reflection":
            candidates.append("reflection_required")
        elif requirement.requirement_kind == "approval":
            candidates.append("approval_required")
        if requirement.obligation == "conditional":
            candidates.append("conditional_requirement_unresolved")
    return tuple(code for code in candidates if code in unresolved_codes)


def _requirement_status(
    requirement: PortfolioProfileRequirement,
    *,
    sections: dict[str, ProfileSectionDefinition],
    placement_counts: dict[str, int],
    current_reflections: frozenset[str],
    approved_requirements: frozenset[str],
) -> str:
    if requirement.requirement_kind == "audience":
        return "audience_stage"

    if requirement.requirement_kind == "section":
        section = (
            None
            if requirement.scope_reference is None
            else sections.get(requirement.scope_reference)
        )
        if requirement.satisfaction_class != "placement_cardinality" or section is None:
            return "not_machine_evaluable"
        count = placement_counts.get(section.section_id, 0)
        if requirement.obligation == "prohibited":
            return "prohibited_clear"
        if requirement.obligation == "conditional" and count == 0:
            return "conditional_unresolved"
        if count < section.minimum_placements:
            if requirement.obligation == "optional":
                return "optional_absent"
            return "unresolved_missing"
        if requirement.obligation == "optional" and count == 0:
            return "optional_absent"
        return "satisfied_current_curation"

    if requirement.requirement_kind == "reflection":
        if requirement.satisfaction_class != "reflection_presence":
            return "not_machine_evaluable"
        if requirement.requirement_id in current_reflections:
            return "satisfied_current_curation"
        if requirement.obligation == "required":
            return "unresolved_missing"
        if requirement.obligation == "optional":
            return "optional_absent"
        if requirement.obligation == "conditional":
            return "conditional_unresolved"
        return "not_machine_evaluable"

    if requirement.requirement_kind == "approval":
        if requirement.satisfaction_class != "curation_review":
            return "not_machine_evaluable"
        if requirement.requirement_id in approved_requirements:
            return "satisfied_current_curation"
        if requirement.obligation == "required":
            return "unresolved_missing"
        if requirement.obligation == "optional":
            return "optional_absent"
        if requirement.obligation == "conditional":
            return "conditional_unresolved"
        return "not_machine_evaluable"

    if requirement.obligation == "conditional":
        return "conditional_unresolved"
    return "not_machine_evaluable"


def _requirement_summaries(
    state: CurationState,
    profile: PortfolioProfileRevision,
    derivation: WorkingCompositionDerivation,
) -> tuple[WorkingCompositionRequirementSummary, ...]:
    requirements = tuple(
        item
        for item in state.profile_requirements
        if item.portfolio_profile_id == profile.portfolio_profile_id
        and item.profile_revision == profile.profile_revision
    )
    sections = {item.section_id: item for item in profile.sections}
    placement_counts = {
        section.section_id: len(
            state.active_placements(
                portfolio_id=derivation.portfolio_id,
                profile_binding_id=derivation.profile_binding_id,
                section_id=section.section_id,
            )
        )
        for section in profile.sections
    }
    current_reflections = _current_reflection_requirement_ids(state, derivation)
    approved_requirements = _approved_requirement_ids(state, derivation)
    related = frozenset(derivation.related_profile_requirement_ids)
    unresolved_codes = frozenset(derivation.unresolved_obligation_codes)
    summaries: list[WorkingCompositionRequirementSummary] = []
    for requirement in requirements:
        status = _requirement_status(
            requirement,
            sections=sections,
            placement_counts=placement_counts,
            current_reflections=current_reflections,
            approved_requirements=approved_requirements,
        )
        summaries.append(
            WorkingCompositionRequirementSummary(
                requirement_id=requirement.requirement_id,
                title=requirement.title,
                statement=requirement.statement,
                requirement_kind=requirement.requirement_kind,
                obligation=requirement.obligation,
                scope_kind=requirement.scope_kind,
                scope_reference=requirement.scope_reference,
                satisfaction_class=requirement.satisfaction_class,
                status=status,
                related_to_frozen_inventory=requirement.requirement_id in related,
                associated_unresolved_obligation_codes=_associated_codes(
                    requirement, status, unresolved_codes
                ),
            )
        )
    return tuple(summaries)



def _source_observations(
    workspace_root: str | Path,
    state: CurationState,
    derivation: WorkingCompositionDerivation,
) -> tuple[WorkingCompositionSourceObservation, ...]:
    selection_by_id = {item.selection_id: item for item in state.selections}
    observations: list[WorkingCompositionSourceObservation] = []
    for selection_id in derivation.selection_ids:
        selection = selection_by_id.get(selection_id)
        if selection is None:
            raise CurationWorkflowError(
                "curation.selection_not_found",
                "Composition Selection does not resolve uniquely.",
                stage="preparation",
            )
        candidate = _candidate(state, selection)
        observed: WorkingCompositionSourceCurrentness = (
            observe_working_composition_source(
                workspace_root,
                selection_id=selection.selection_id,
                candidate=candidate,
            )
        )
        observations.append(
            WorkingCompositionSourceObservation(
                selection_id=observed.selection_id,
                candidate_id=observed.candidate_id,
                publication_id=observed.publication_id,
                series_head_publication_id=observed.series_head_publication_id,
                observed_series_state=observed.observed_series_state,
                observed_withdrawal_state=observed.observed_withdrawal_state,
                current_use_state=observed.current_use_state,
            )
        )
    return tuple(observations)


def _review_summaries(
    state: CurationState,
    derivation: WorkingCompositionDerivation,
) -> tuple[WorkingCompositionReviewSummary, ...]:
    by_id = {
        item.curation_review_decision_id: item
        for item in state.reviews
        if item.portfolio_id == derivation.portfolio_id
        and item.profile_binding_id == derivation.profile_binding_id
    }
    summaries: list[WorkingCompositionReviewSummary] = []
    for review_id in derivation.applicable_review_decision_ids:
        review = by_id.get(review_id)
        if review is None:
            raise CurationWorkflowError(
                "curation.composition_inconsistent",
                "Applicable Composition Review does not resolve uniquely.",
                stage="preparation",
            )
        summaries.append(
            WorkingCompositionReviewSummary(
                curation_review_decision_id=review.curation_review_decision_id,
                decision=review.decision,
                approval_requirement_id=review.approval_requirement_id,
                target_scope=review.target_scope,
                target_references=review.target_references,
                required_follow_up_codes=review.required_follow_up_codes,
                requires_attention=(
                    review.decision in {"rejected", "changes_requested"}
                    or bool(review.required_follow_up_codes)
                ),
            )
        )
    return tuple(summaries)


def _audience_summaries(
    profile: PortfolioProfileRevision,
) -> tuple[WorkingCompositionAudienceSummary, ...]:
    return tuple(
        WorkingCompositionAudienceSummary(
            audience_rule_id=rule.audience_rule_id,
            audience_class=rule.audience_class,
            purpose=rule.purpose,
            allowed_content_classes=rule.allowed_content_classes,
            prohibited_content_classes=rule.prohibited_content_classes,
            required_review_classes=rule.required_review_classes,
            presentation_class=rule.presentation_class,
            retention_policy_reference=rule.retention_policy_reference,
        )
        for rule in profile.audience_rules
    )


def _preparation_fingerprint(
    derivation: WorkingCompositionDerivation,
    payload: WorkingCompositionPayloadPreview,
    source_observations: tuple[WorkingCompositionSourceObservation, ...],
    composition_note: str | None,
) -> str:
    note_to_persist = (
        None if derivation.disposition == "reuse_exact_current" else composition_note
    )
    value = {
        "contract_version": WORKING_COMPOSITION_CONTRACT_VERSION,
        "portfolio_id": derivation.portfolio_id,
        "portfolio_subject_id": derivation.portfolio_subject_id,
        "profile_binding_id": derivation.profile_binding_id,
        "profile_revision": {
            "portfolio_profile_id": derivation.profile_revision_id,
            "profile_revision": derivation.profile_revision_number,
        },
        "observed_state_revision": derivation.state_revision,
        "observed_composition_pointer_revision": (
            derivation.observed_composition_pointer_revision
        ),
        "current_composition_revision": derivation.current_composition_revision,
        "predicted_composition_revision": derivation.predicted_composition_revision,
        "predicted_composition_pointer_revision": (
            derivation.predicted_composition_pointer_revision
        ),
        "disposition": derivation.disposition,
        "payload": asdict(payload),
        "source_observations": [asdict(item) for item in source_observations],
        "composition_note_to_persist": note_to_persist,
    }
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def prepare_working_composition(
    workspace_root: str | Path,
    portfolio_id: str,
    *,
    composition_note: str | None = None,
) -> WorkingCompositionPreparation:
    """Prepare one exact current curation state without writing canonical state."""
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Vitrine canonical state is unavailable for Composition preparation.",
            stage="preparation",
        ) from error

    derivation = derive_working_composition(
        workspace_root,
        portfolio_id=portfolio_id,
        expected_state_revision=current.state_revision,
    )
    state = project_curation_state(records)
    profile = _exact_profile(state, derivation)
    sections = _section_summaries(state, profile, derivation)
    selections = _selection_summaries(state, profile, derivation)
    requirements = _requirement_summaries(state, profile, derivation)
    source_observations = _source_observations(
        workspace_root, state, derivation
    )
    reviews = _review_summaries(state, derivation)
    audience_rules = _audience_summaries(profile)
    payload = _payload_preview(derivation)
    fingerprint = _preparation_fingerprint(
        derivation, payload, source_observations, composition_note
    )
    return WorkingCompositionPreparation(
        contract_version=WORKING_COMPOSITION_CONTRACT_VERSION,
        observed_state_revision=derivation.state_revision,
        portfolio_id=derivation.portfolio_id,
        portfolio_subject_id=derivation.portfolio_subject_id,
        profile_binding_id=derivation.profile_binding_id,
        profile_revision_id=derivation.profile_revision_id,
        profile_revision_number=derivation.profile_revision_number,
        observed_composition_pointer_revision=(
            derivation.observed_composition_pointer_revision
        ),
        current_composition_revision=derivation.current_composition_revision,
        predicted_composition_revision=derivation.predicted_composition_revision,
        predecessor_composition_revision=(
            derivation.predecessor_composition_revision
        ),
        predicted_composition_pointer_revision=(
            derivation.predicted_composition_pointer_revision
        ),
        disposition=derivation.disposition,
        payload=payload,
        sections=sections,
        selections=selections,
        unplaced_selection_ids=tuple(
            item.selection_id for item in selections if not item.is_placed
        ),
        requirements=requirements,
        source_observations=source_observations,
        reviews=reviews,
        audience_rules=audience_rules,
        requested_composition_note=composition_note,
        composition_note_will_persist=(
            derivation.disposition != "reuse_exact_current"
        ),
        preparation_fingerprint=fingerprint,
    )


def _derivation_from_preparation(
    preparation: WorkingCompositionPreparation,
) -> WorkingCompositionDerivation:
    return WorkingCompositionDerivation(
        state_revision=preparation.observed_state_revision,
        portfolio_id=preparation.portfolio_id,
        portfolio_subject_id=preparation.portfolio_subject_id,
        profile_binding_id=preparation.profile_binding_id,
        profile_revision_id=preparation.profile_revision_id,
        profile_revision_number=preparation.profile_revision_number,
        observed_composition_pointer_revision=(
            preparation.observed_composition_pointer_revision
        ),
        current_composition_revision=preparation.current_composition_revision,
        predicted_composition_revision=preparation.predicted_composition_revision,
        predecessor_composition_revision=(
            preparation.predecessor_composition_revision
        ),
        predicted_composition_pointer_revision=(
            preparation.predicted_composition_pointer_revision
        ),
        disposition=preparation.disposition,
        selection_ids=preparation.payload.selection_ids,
        placement_ids=preparation.payload.placement_ids,
        arrangement_ids=preparation.payload.arrangement_ids,
        included_rationale_ids=preparation.payload.included_rationale_ids,
        included_curation_revisions=(
            preparation.payload.included_curation_revisions
        ),
        applicable_review_decision_ids=(
            preparation.payload.applicable_review_decision_ids
        ),
        related_profile_requirement_ids=(
            preparation.payload.related_profile_requirement_ids
        ),
        unresolved_obligation_codes=(
            preparation.payload.unresolved_obligation_codes
        ),
        coherence_state=preparation.payload.coherence_state,
    )


def _source_currentness_from_preparation(
    preparation: WorkingCompositionPreparation,
) -> tuple[WorkingCompositionSourceCurrentness, ...]:
    return tuple(
        WorkingCompositionSourceCurrentness(
            selection_id=item.selection_id,
            candidate_id=item.candidate_id,
            publication_id=item.publication_id,
            series_head_publication_id=item.series_head_publication_id,
            observed_series_state=item.observed_series_state,
            observed_withdrawal_state=item.observed_withdrawal_state,
            current_use_state=item.current_use_state,
        )
        for item in preparation.source_observations
    )


def freeze_prepared_working_composition(
    workspace_root: str | Path,
    preparation: WorkingCompositionPreparation,
    *,
    created_by: ActorAttribution,
    authority_gate: CurationAuthorityGate,
) -> CurationMutationResult:
    """Freeze only the exact transient preparation the caller reviewed."""
    if preparation.contract_version != WORKING_COMPOSITION_CONTRACT_VERSION:
        raise WorkingCompositionError(
            "working_composition.invalid_request",
            "Working Composition preparation contract is unsupported.",
        )
    if len(preparation.preparation_fingerprint) != 64:
        raise WorkingCompositionError(
            "working_composition.invalid_request",
            "Working Composition preparation fingerprint is invalid.",
        )

    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise WorkingCompositionError(
            "working_composition.context_not_found",
            "Vitrine canonical state is unavailable for prepared freeze.",
        ) from error
    if current.state_revision != preparation.observed_state_revision:
        raise WorkingCompositionError(
            "working_composition.state_changed",
            "Vitrine state changed after Working Composition preparation.",
        )

    state = project_curation_state(records)
    pointer_heads = state.composition_pointer_heads(
        preparation.portfolio_id, preparation.profile_binding_id
    )
    if len(pointer_heads) > 1:
        raise WorkingCompositionError(
            "working_composition.composition_pointer_changed",
            "Working Composition pointer is conflicted after preparation.",
        )
    observed_pointer = pointer_heads[0].pointer_revision if pointer_heads else None
    if observed_pointer != preparation.observed_composition_pointer_revision:
        raise WorkingCompositionError(
            "working_composition.composition_pointer_changed",
            "Working Composition pointer changed after preparation.",
        )

    try:
        derivation = derive_working_composition(
            workspace_root,
            portfolio_id=preparation.portfolio_id,
            expected_state_revision=preparation.observed_state_revision,
        )
    except CurationWorkflowError as error:
        if error.code == "curation.state_conflict":
            raise WorkingCompositionError(
                "working_composition.state_changed",
                "Vitrine state changed after Working Composition preparation.",
            ) from error
        if error.code == "curation.composition_pointer_conflict":
            raise WorkingCompositionError(
                "working_composition.composition_pointer_changed",
                "Working Composition pointer changed after preparation.",
            ) from error
        raise

    expected_derivation = _derivation_from_preparation(preparation)
    if derivation != expected_derivation:
        raise WorkingCompositionError(
            "working_composition.preparation_mismatch",
            "Current curation no longer matches the reviewed preparation.",
        )

    profile = _exact_profile(state, derivation)
    payload = _payload_preview(derivation)
    current_sources = _source_observations(workspace_root, state, derivation)
    if current_sources != preparation.source_observations:
        raise WorkingCompositionError(
            "working_composition.source_state_changed",
            "Core Publication state changed after Working Composition preparation.",
        )
    fingerprint = _preparation_fingerprint(
        derivation,
        payload,
        current_sources,
        preparation.requested_composition_note,
    )
    if fingerprint != preparation.preparation_fingerprint:
        raise WorkingCompositionError(
            "working_composition.preparation_mismatch",
            "Working Composition preparation fingerprint no longer matches.",
        )

    _section_summaries(state, profile, derivation)
    _selection_summaries(state, profile, derivation)
    _requirement_summaries(state, profile, derivation)
    _review_summaries(state, derivation)
    _audience_summaries(profile)

    try:
        return create_working_composition(
            workspace_root,
            portfolio_id=preparation.portfolio_id,
            created_by=created_by,
            expected_state_revision=preparation.observed_state_revision,
            expected_composition_pointer_revision=(
                preparation.observed_composition_pointer_revision
            ),
            authority_gate=authority_gate,
            composition_note=preparation.requested_composition_note,
            expected_derivation=expected_derivation,
            expected_source_observations=(
                _source_currentness_from_preparation(preparation)
            ),
        )
    except CurationWorkflowError as error:
        if error.code == "curation.state_conflict":
            raise WorkingCompositionError(
                "working_composition.state_changed",
                "Vitrine state changed before prepared Composition commit.",
            ) from error
        if error.code == "curation.composition_pointer_conflict":
            raise WorkingCompositionError(
                "working_composition.composition_pointer_changed",
                "Working Composition pointer changed before commit.",
            ) from error
        if error.code == "curation.composition_preparation_mismatch":
            raise WorkingCompositionError(
                "working_composition.preparation_mismatch",
                "Prepared Composition changed before canonical commit.",
            ) from error
        raise


__all__ = [
    "REQUIREMENT_STATUSES",
    "WORKING_COMPOSITION_CONTRACT_VERSION",
    "WORKING_COMPOSITION_ERROR_CODES",
    "WorkingCompositionAudienceSummary",
    "WorkingCompositionError",
    "WorkingCompositionPayloadPreview",
    "WorkingCompositionPlacementSummary",
    "WorkingCompositionPreparation",
    "WorkingCompositionRequirementSummary",
    "WorkingCompositionReviewSummary",
    "WorkingCompositionSectionSummary",
    "WorkingCompositionSelectionSummary",
    "WorkingCompositionSourceObservation",
    "freeze_prepared_working_composition",
    "prepare_working_composition",
]
