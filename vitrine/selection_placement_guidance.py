"""Transient domain-correct Selection and Placement guidance.

Candidate eligibility is persisted semantic evidence. This module derives current
curation actionability without rewriting Candidate or CandidateEvaluation state.
It is intentionally read-only so teacher presentation, planners, and canonical
mutation boundaries can converge on one definition of "available now".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from vitrine.curation_state import CurationState
from vitrine.models import (
    PortfolioCandidate,
    PortfolioProfileRevision,
    PortfolioSelection,
)

SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION: Final[str] = (
    "vitrine_selection_placement_guidance_v1"
)
SELECTION_PLACEMENT_GUIDANCE_OPERATIONS: Final[frozenset[str]] = frozenset(
    {"fresh_selection", "placement", "replacement"}
)
SELECTION_PLACEMENT_UNAVAILABILITY_CODES: Final[frozenset[str]] = frozenset(
    {
        "candidate_not_semantically_eligible",
        "section_prohibited",
        "section_not_placement_bearing",
        "section_full",
        "arrangement_pointer_conflict",
        "selection_already_placed_in_section",
    }
)
SELECTION_PLACEMENT_GUIDANCE_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "selection_placement_guidance.invalid_request",
        "selection_placement_guidance.profile_mismatch",
        "selection_placement_guidance.selection_not_active",
        "selection_placement_guidance.selection_candidate_mismatch",
        "selection_placement_guidance.replacement_candidate_conflict",
        "selection_placement_guidance.replacement_release_mismatch",
        "selection_placement_guidance.section_not_actionable",
    }
)


class SelectionPlacementGuidanceError(RuntimeError):
    """Bounded read-only guidance failure."""

    def __init__(self, code: str, message: str) -> None:
        if code not in SELECTION_PLACEMENT_GUIDANCE_ERROR_CODES:
            raise ValueError(
                "unsupported Selection/Placement guidance error code: "
                f"{code}"
            )
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SelectionPlacementSectionGuidance:
    """Current actionability for one exact Profile section."""

    section_id: str
    label: str
    operation: str
    semantic_candidate_eligible: bool
    placement_bearing: bool
    obligation: str
    minimum_placements: int
    active_placement_count: int
    released_placement_count: int
    effective_placement_count: int
    maximum_placements: int | None
    remaining_capacity: int | None
    arrangement_pointer_state: str
    arrangement_pointer_revision: int | None
    current_actionable: bool
    unavailability_reason_codes: tuple[str, ...]
    relevant_profile_requirement_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SelectionPlacementGuidance:
    """Read-only actionability projection for one Candidate and operation."""

    contract_version: str
    portfolio_id: str
    profile_binding_id: str
    portfolio_profile_id: str
    profile_revision: int
    candidate_id: str
    candidate_evaluation_id: str
    operation: str
    selection_id: str | None
    releasing_placement_ids: tuple[str, ...]
    matched_profile_requirement_ids: tuple[str, ...]
    semantic_eligible_section_ids: tuple[str, ...]
    sections: tuple[SelectionPlacementSectionGuidance, ...]

    @property
    def actionable_sections(self) -> tuple[SelectionPlacementSectionGuidance, ...]:
        return tuple(item for item in self.sections if item.current_actionable)

    @property
    def actionable_section_ids(self) -> tuple[str, ...]:
        return tuple(item.section_id for item in self.actionable_sections)


def _selection_for_operation(
    curation: CurationState,
    *,
    candidate: PortfolioCandidate,
    operation: str,
    selection_id: str | None,
) -> PortfolioSelection | None:
    if operation == "fresh_selection":
        if selection_id is not None:
            raise SelectionPlacementGuidanceError(
                "selection_placement_guidance.invalid_request",
                "Fresh Selection guidance must not identify an existing Selection.",
            )
        return None

    if (
        selection_id is None
        or not isinstance(selection_id, str)
        or not selection_id.strip()
    ):
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.invalid_request",
            f"{operation} guidance requires one exact active Selection.",
        )
    matches = tuple(
        item
        for item in curation.active_selections(
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
        )
        if item.selection_id == selection_id
    )
    if len(matches) != 1:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.selection_not_active",
            "The exact Selection is not uniquely active in the Candidate "
            "Portfolio context.",
        )
    selection = matches[0]
    if operation == "placement" and selection.candidate_id != candidate.candidate_id:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.selection_candidate_mismatch",
            "Placement guidance requires the active Selection to belong to "
            "the Candidate.",
        )
    if operation == "replacement" and selection.candidate_id == candidate.candidate_id:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.replacement_candidate_conflict",
            "Replacement guidance requires a successor Candidate different "
            "from the active Selection Candidate.",
        )
    return selection


def _replacement_release_ids(
    curation: CurationState,
    *,
    candidate: PortfolioCandidate,
    operation: str,
    selection: PortfolioSelection | None,
    releasing_placement_ids: tuple[str, ...],
) -> tuple[str, ...]:
    release_ids = tuple(releasing_placement_ids)
    if len(set(release_ids)) != len(release_ids):
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.invalid_request",
            "releasing_placement_ids must not contain duplicates.",
        )
    if operation != "replacement":
        if release_ids:
            raise SelectionPlacementGuidanceError(
                "selection_placement_guidance.invalid_request",
                "Only replacement guidance may release active Placements.",
            )
        return ()
    if selection is None:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.invalid_request",
            "Replacement guidance requires one active predecessor Selection.",
        )
    active = tuple(
        item
        for item in curation.active_placements(
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
        )
        if item.selection_id == selection.selection_id
    )
    expected = {item.placement_id for item in active}
    if set(release_ids) != expected:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.replacement_release_mismatch",
            "Replacement guidance must release every active Placement of the "
            "predecessor Selection exactly once.",
        )
    return release_ids


def _relevant_requirement_ids(
    *,
    curation: CurationState,
    candidate: PortfolioCandidate,
    profile: PortfolioProfileRevision,
    section_id: str,
) -> tuple[str, ...]:
    matched = set(candidate.eligible_profile_rule_ids)
    return tuple(
        sorted(
            item.requirement_id
            for item in curation.profile_requirements
            if item.portfolio_profile_id == profile.portfolio_profile_id
            and item.profile_revision == profile.profile_revision
            and item.requirement_kind == "section"
            and item.scope_kind == "section"
            and item.scope_reference == section_id
            and item.requirement_id in matched
        )
    )


def project_selection_placement_guidance(
    *,
    candidate: PortfolioCandidate,
    profile: PortfolioProfileRevision,
    curation: CurationState,
    operation: str,
    selection_id: str | None = None,
    releasing_placement_ids: tuple[str, ...] = (),
) -> SelectionPlacementGuidance:
    """Project current section actionability without mutating canonical state.

    ``fresh_selection`` asks whether a Candidate has a current Placement path.
    ``placement`` additionally excludes a same-Selection duplicate destination.
    ``replacement`` computes capacity after every active predecessor Placement is
    released, preserving one-for-one capacity in a section that is full before
    the replacement transaction.
    """

    if operation not in SELECTION_PLACEMENT_GUIDANCE_OPERATIONS:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.invalid_request",
            "operation must be fresh_selection, placement, or replacement.",
        )
    if candidate.profile_revision != profile.reference:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.profile_mismatch",
            "Candidate and Profile Revision do not identify the same exact "
            "Profile Revision.",
        )

    selection = _selection_for_operation(
        curation,
        candidate=candidate,
        operation=operation,
        selection_id=selection_id,
    )
    if selection is not None and selection.profile_revision != profile.reference:
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.profile_mismatch",
            "Selection and Candidate guidance do not identify the same exact "
            "Profile Revision.",
        )
    release_ids = _replacement_release_ids(
        curation,
        candidate=candidate,
        operation=operation,
        selection=selection,
        releasing_placement_ids=releasing_placement_ids,
    )
    release_set = set(release_ids)
    semantic_ids = set(candidate.eligible_section_ids)
    sections: list[SelectionPlacementSectionGuidance] = []

    for section in sorted(
        profile.sections, key=lambda item: (item.order, item.section_id)
    ):
        active = curation.active_placements(
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
            section_id=section.section_id,
        )
        released_count = sum(
            1 for item in active if item.placement_id in release_set
        )
        effective_count = len(active) - released_count
        remaining = (
            None
            if section.maximum_placements is None
            else max(section.maximum_placements - effective_count, 0)
        )
        pointer_heads = curation.arrangement_pointer_heads(
            candidate.portfolio_id,
            candidate.profile_binding_id,
            section.section_id,
        )
        if not pointer_heads:
            pointer_state = "absent"
            pointer_revision = None
        elif len(pointer_heads) == 1:
            pointer_state = "current"
            pointer_revision = pointer_heads[0].pointer_revision
        else:
            pointer_state = "conflict"
            pointer_revision = None

        semantically_eligible = section.section_id in semantic_ids
        placement_bearing = (
            section.obligation != "prohibited" and section.maximum_placements != 0
        )
        reasons: list[str] = []
        if not semantically_eligible:
            reasons.append("candidate_not_semantically_eligible")
        if section.obligation == "prohibited":
            reasons.append("section_prohibited")
        if not placement_bearing:
            reasons.append("section_not_placement_bearing")
        if (
            placement_bearing
            and section.maximum_placements is not None
            and effective_count >= section.maximum_placements
        ):
            reasons.append("section_full")
        if pointer_state == "conflict":
            reasons.append("arrangement_pointer_conflict")
        if operation == "placement" and selection is not None:
            if any(item.selection_id == selection.selection_id for item in active):
                reasons.append("selection_already_placed_in_section")

        sections.append(
            SelectionPlacementSectionGuidance(
                section_id=section.section_id,
                label=section.label,
                operation=operation,
                semantic_candidate_eligible=semantically_eligible,
                placement_bearing=placement_bearing,
                obligation=section.obligation,
                minimum_placements=section.minimum_placements,
                active_placement_count=len(active),
                released_placement_count=released_count,
                effective_placement_count=effective_count,
                maximum_placements=section.maximum_placements,
                remaining_capacity=remaining,
                arrangement_pointer_state=pointer_state,
                arrangement_pointer_revision=pointer_revision,
                current_actionable=not reasons,
                unavailability_reason_codes=tuple(reasons),
                relevant_profile_requirement_ids=_relevant_requirement_ids(
                    curation=curation,
                    candidate=candidate,
                    profile=profile,
                    section_id=section.section_id,
                ),
            )
        )

    return SelectionPlacementGuidance(
        contract_version=SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION,
        portfolio_id=candidate.portfolio_id,
        profile_binding_id=candidate.profile_binding_id,
        portfolio_profile_id=profile.portfolio_profile_id,
        profile_revision=profile.profile_revision,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        operation=operation,
        selection_id=None if selection is None else selection.selection_id,
        releasing_placement_ids=release_ids,
        matched_profile_requirement_ids=candidate.eligible_profile_rule_ids,
        semantic_eligible_section_ids=candidate.eligible_section_ids,
        sections=tuple(sections),
    )


def profile_requirement_ids_for_sections(
    guidance: SelectionPlacementGuidance,
    section_ids: tuple[str, ...],
) -> tuple[str, ...]:
    """Return Candidate-matched section requirements for actionable exact targets."""

    if len(set(section_ids)) != len(section_ids):
        raise SelectionPlacementGuidanceError(
            "selection_placement_guidance.invalid_request",
            "section_ids must not contain duplicates.",
        )
    by_id = {item.section_id: item for item in guidance.sections}
    requirement_ids: set[str] = set()
    for section_id in section_ids:
        section = by_id.get(section_id)
        if section is None or not section.current_actionable:
            raise SelectionPlacementGuidanceError(
                "selection_placement_guidance.section_not_actionable",
                "Profile requirement intent may only reference currently "
                "actionable sections.",
            )
        requirement_ids.update(section.relevant_profile_requirement_ids)
    return tuple(sorted(requirement_ids))


__all__ = [
    "SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION",
    "SELECTION_PLACEMENT_GUIDANCE_ERROR_CODES",
    "SELECTION_PLACEMENT_GUIDANCE_OPERATIONS",
    "SELECTION_PLACEMENT_UNAVAILABILITY_CODES",
    "SelectionPlacementGuidance",
    "SelectionPlacementGuidanceError",
    "SelectionPlacementSectionGuidance",
    "profile_requirement_ids_for_sections",
    "project_selection_placement_guidance",
]
