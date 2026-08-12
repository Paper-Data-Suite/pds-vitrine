"""Pure projection and validation for additive Vitrine curation workflow history."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from vitrine.models import (
    CandidateEvaluation,
    CurationAnnotation,
    CurationRationale,
    CurationReviewDecision,
    PlacementLifecycleEvent,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileBinding,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioReflection,
    PortfolioSelection,
    SectionArrangementPointerRevision,
    SectionArrangementRevision,
    SelectionDecision,
    SelectionLifecycleEvent,
    SelectionProposal,
    ValidationIssue,
    VitrineRecord,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
    WorkingPortfolioCompositionRevision,
)


def _issue(
    code: str,
    message: str,
    record_type: str | None = None,
    record_id: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        record_type=record_type,
        record_id=record_id,
    )


def _cycle_representatives(predecessors: dict[str, str | None]) -> tuple[str, ...]:
    representatives: set[str] = set()
    for start in sorted(predecessors):
        path: list[str] = []
        positions: dict[str, int] = {}
        current: str | None = start
        while current is not None and current in predecessors:
            if current in positions:
                representatives.add(min(path[positions[current] :]))
                break
            positions[current] = len(path)
            path.append(current)
            current = predecessors[current]
    return tuple(sorted(representatives))


def _revision_cycle_representatives(
    predecessors: dict[tuple[str, int], tuple[str, int] | None],
) -> tuple[tuple[str, int], ...]:
    representatives: set[tuple[str, int]] = set()
    for start in sorted(predecessors):
        path: list[tuple[str, int]] = []
        positions: dict[tuple[str, int], int] = {}
        current: tuple[str, int] | None = start
        while current is not None and current in predecessors:
            if current in positions:
                representatives.add(min(path[positions[current] :]))
                break
            positions[current] = len(path)
            path.append(current)
            current = predecessors[current]
    return tuple(sorted(representatives))


@dataclass(frozen=True, slots=True)
class CurationState:
    portfolios: tuple[Portfolio, ...]
    profile_revisions: tuple[PortfolioProfileRevision, ...]
    profile_bindings: tuple[PortfolioProfileBinding, ...]
    profile_requirements: tuple[PortfolioProfileRequirement, ...]
    candidate_evaluations: tuple[CandidateEvaluation, ...]
    candidates: tuple[PortfolioCandidate, ...]
    selections: tuple[PortfolioSelection, ...]
    placements: tuple[PortfolioPlacement, ...]
    arrangements: tuple[SectionArrangementRevision, ...]
    compositions: tuple[WorkingPortfolioCompositionRevision, ...]
    proposals: tuple[SelectionProposal, ...]
    decisions: tuple[SelectionDecision, ...]
    selection_events: tuple[SelectionLifecycleEvent, ...]
    placement_events: tuple[PlacementLifecycleEvent, ...]
    arrangement_pointers: tuple[SectionArrangementPointerRevision, ...]
    rationales: tuple[CurationRationale, ...]
    annotations: tuple[CurationAnnotation, ...]
    reflections: tuple[PortfolioReflection, ...]
    reviews: tuple[CurationReviewDecision, ...]
    composition_inventories: tuple[WorkingPortfolioCompositionInventory, ...]
    composition_pointers: tuple[WorkingPortfolioCompositionPointerRevision, ...]

    def selection_heads(self, selection_id: str) -> tuple[SelectionLifecycleEvent, ...]:
        events = tuple(item for item in self.selection_events if item.selection_id == selection_id)
        predecessors = {item.predecessor_event_id for item in events if item.predecessor_event_id}
        return tuple(
            sorted(
                (item for item in events if item.selection_lifecycle_event_id not in predecessors),
                key=lambda item: item.selection_lifecycle_event_id,
            )
        )

    def selection_status(self, selection_id: str) -> str:
        heads = self.selection_heads(selection_id)
        if not heads:
            return "legacy_unmanaged"
        if len(heads) != 1:
            return "conflict"
        return heads[0].event_kind

    def active_selections(
        self, *, portfolio_id: str | None = None, profile_binding_id: str | None = None
    ) -> tuple[PortfolioSelection, ...]:
        values = (
            item
            for item in self.selections
            if self.selection_status(item.selection_id) == "activated"
            and (portfolio_id is None or item.portfolio_id == portfolio_id)
            and (profile_binding_id is None or item.profile_binding_id == profile_binding_id)
        )
        return tuple(sorted(values, key=lambda item: item.selection_id))

    def placement_heads(self, placement_id: str) -> tuple[PlacementLifecycleEvent, ...]:
        events = tuple(item for item in self.placement_events if item.placement_id == placement_id)
        predecessors = {item.predecessor_event_id for item in events if item.predecessor_event_id}
        return tuple(
            sorted(
                (item for item in events if item.placement_lifecycle_event_id not in predecessors),
                key=lambda item: item.placement_lifecycle_event_id,
            )
        )

    def placement_status(self, placement_id: str) -> str:
        heads = self.placement_heads(placement_id)
        if not heads:
            return "legacy_unmanaged"
        if len(heads) != 1:
            return "conflict"
        return heads[0].event_kind

    def active_placements(
        self,
        *,
        portfolio_id: str | None = None,
        profile_binding_id: str | None = None,
        section_id: str | None = None,
    ) -> tuple[PortfolioPlacement, ...]:
        values = (
            item
            for item in self.placements
            if self.placement_status(item.placement_id) == "activated"
            and (portfolio_id is None or item.portfolio_id == portfolio_id)
            and (profile_binding_id is None or item.profile_binding_id == profile_binding_id)
            and (section_id is None or item.section_id == section_id)
        )
        return tuple(sorted(values, key=lambda item: item.placement_id))

    def arrangement_pointer_heads(
        self, portfolio_id: str, profile_binding_id: str, section_id: str
    ) -> tuple[SectionArrangementPointerRevision, ...]:
        values = tuple(
            item
            for item in self.arrangement_pointers
            if item.portfolio_id == portfolio_id
            and item.profile_binding_id == profile_binding_id
            and item.section_id == section_id
        )
        successor_keys = {
            (item.arrangement_pointer_id, item.predecessor_pointer_revision)
            for item in values
            if item.predecessor_pointer_revision is not None
        }
        return tuple(
            sorted(
                (
                    item
                    for item in values
                    if (item.arrangement_pointer_id, item.pointer_revision)
                    not in successor_keys
                ),
                key=lambda item: (item.arrangement_pointer_id, item.pointer_revision),
            )
        )

    def current_arrangement(
        self, portfolio_id: str, profile_binding_id: str, section_id: str
    ) -> SectionArrangementRevision | None:
        heads = self.arrangement_pointer_heads(portfolio_id, profile_binding_id, section_id)
        if len(heads) != 1:
            return None
        pointer = heads[0]
        return next(
            (item for item in self.arrangements if item.arrangement_id == pointer.arrangement_id),
            None,
        )

    def annotation_heads(self, annotation_id: str) -> tuple[CurationAnnotation, ...]:
        values = tuple(item for item in self.annotations if item.annotation_id == annotation_id)
        predecessors = {
            item.predecessor_annotation_revision
            for item in values
            if item.predecessor_annotation_revision is not None
        }
        return tuple(
            sorted(
                (item for item in values if item.annotation_revision not in predecessors),
                key=lambda item: item.annotation_revision,
            )
        )

    def reflection_heads(self, reflection_id: str) -> tuple[PortfolioReflection, ...]:
        values = tuple(item for item in self.reflections if item.reflection_id == reflection_id)
        predecessors = {
            item.predecessor_reflection_revision
            for item in values
            if item.predecessor_reflection_revision is not None
        }
        return tuple(
            sorted(
                (item for item in values if item.reflection_revision not in predecessors),
                key=lambda item: item.reflection_revision,
            )
        )

    def composition_pointer_heads(
        self, portfolio_id: str, profile_binding_id: str
    ) -> tuple[WorkingPortfolioCompositionPointerRevision, ...]:
        values = tuple(
            item
            for item in self.composition_pointers
            if item.portfolio_id == portfolio_id
            and item.profile_binding_id == profile_binding_id
        )
        successor_keys = {
            (item.composition_pointer_id, item.predecessor_pointer_revision)
            for item in values
            if item.predecessor_pointer_revision is not None
        }
        return tuple(
            sorted(
                (
                    item
                    for item in values
                    if (item.composition_pointer_id, item.pointer_revision)
                    not in successor_keys
                ),
                key=lambda item: (item.composition_pointer_id, item.pointer_revision),
            )
        )

    def current_composition(
        self, portfolio_id: str, profile_binding_id: str
    ) -> WorkingPortfolioCompositionRevision | None:
        heads = self.composition_pointer_heads(portfolio_id, profile_binding_id)
        if len(heads) != 1:
            return None
        revision = heads[0].composition_revision
        return next(
            (
                item
                for item in self.compositions
                if item.portfolio_id == portfolio_id
                and item.profile_binding_id == profile_binding_id
                and item.composition_revision == revision
            ),
            None,
        )


def project_curation_state(records: Iterable[VitrineRecord]) -> CurationState:
    values = tuple(records)
    return CurationState(
        portfolios=tuple(item for item in values if isinstance(item, Portfolio)),
        profile_revisions=tuple(
            item for item in values if isinstance(item, PortfolioProfileRevision)
        ),
        profile_bindings=tuple(
            item for item in values if isinstance(item, PortfolioProfileBinding)
        ),
        profile_requirements=tuple(
            item for item in values if isinstance(item, PortfolioProfileRequirement)
        ),
        candidate_evaluations=tuple(
            item for item in values if isinstance(item, CandidateEvaluation)
        ),
        candidates=tuple(item for item in values if isinstance(item, PortfolioCandidate)),
        selections=tuple(item for item in values if isinstance(item, PortfolioSelection)),
        placements=tuple(item for item in values if isinstance(item, PortfolioPlacement)),
        arrangements=tuple(
            item for item in values if isinstance(item, SectionArrangementRevision)
        ),
        compositions=tuple(
            item
            for item in values
            if isinstance(item, WorkingPortfolioCompositionRevision)
        ),
        proposals=tuple(item for item in values if isinstance(item, SelectionProposal)),
        decisions=tuple(item for item in values if isinstance(item, SelectionDecision)),
        selection_events=tuple(
            item for item in values if isinstance(item, SelectionLifecycleEvent)
        ),
        placement_events=tuple(
            item for item in values if isinstance(item, PlacementLifecycleEvent)
        ),
        arrangement_pointers=tuple(
            item
            for item in values
            if isinstance(item, SectionArrangementPointerRevision)
        ),
        rationales=tuple(item for item in values if isinstance(item, CurationRationale)),
        annotations=tuple(item for item in values if isinstance(item, CurationAnnotation)),
        reflections=tuple(item for item in values if isinstance(item, PortfolioReflection)),
        reviews=tuple(item for item in values if isinstance(item, CurationReviewDecision)),
        composition_inventories=tuple(
            item
            for item in values
            if isinstance(item, WorkingPortfolioCompositionInventory)
        ),
        composition_pointers=tuple(
            item
            for item in values
            if isinstance(item, WorkingPortfolioCompositionPointerRevision)
        ),
    )


def _target_exists(state: CurationState, target_kind: str, target_id: str, revision: int | None) -> bool:
    if target_kind == "selection_proposal":
        return revision is None and any(item.selection_proposal_id == target_id for item in state.proposals)
    if target_kind == "selection":
        return revision is None and any(item.selection_id == target_id for item in state.selections)
    if target_kind == "placement":
        return revision is None and any(item.placement_id == target_id for item in state.placements)
    if target_kind == "arrangement":
        return revision is None and any(item.arrangement_id == target_id for item in state.arrangements)
    if target_kind == "annotation":
        return revision is not None and any(
            item.annotation_id == target_id and item.annotation_revision == revision
            for item in state.annotations
        )
    if target_kind == "reflection":
        return revision is not None and any(
            item.reflection_id == target_id and item.reflection_revision == revision
            for item in state.reflections
        )
    if target_kind == "composition":
        return revision is not None and any(
            item.portfolio_id == target_id and item.composition_revision == revision
            for item in state.compositions
        )
    if target_kind == "portfolio":
        return revision is None and any(item.portfolio_id == target_id for item in state.portfolios)
    if target_kind in {"section", "checkpoint"}:
        return revision is None
    return False


def collect_curation_state_issues(state: CurationState) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    candidates = {item.candidate_id: item for item in state.candidates}
    evaluations = {
        item.candidate_evaluation_id: item for item in state.candidate_evaluations
    }
    selections = {item.selection_id: item for item in state.selections}
    placements = {item.placement_id: item for item in state.placements}
    arrangements = {item.arrangement_id: item for item in state.arrangements}
    bindings = {item.profile_binding_id: item for item in state.profile_bindings}
    profiles = {
        (item.portfolio_profile_id, item.profile_revision): item
        for item in state.profile_revisions
    }
    requirements = {
        (item.portfolio_profile_id, item.profile_revision, item.requirement_id): item
        for item in state.profile_requirements
    }
    proposals = {item.selection_proposal_id: item for item in state.proposals}
    decisions = {item.selection_decision_id: item for item in state.decisions}
    rationales = {item.rationale_id: item for item in state.rationales}

    # Proposal chains and exact Candidate/Profile context.
    proposal_successors: dict[str, list[str]] = defaultdict(list)
    for proposal in state.proposals:
        candidate = candidates.get(proposal.candidate_id)
        evaluation = evaluations.get(proposal.candidate_evaluation_id)
        if candidate is None or evaluation is None:
            issues.append(
                _issue(
                    "curation.proposal_candidate_missing",
                    "Proposal Candidate or Evaluation does not exist.",
                    proposal.record_type,
                    proposal.selection_proposal_id,
                )
            )
        elif (
            proposal.portfolio_id,
            proposal.portfolio_subject_id,
            proposal.profile_binding_id,
            proposal.profile_revision,
            proposal.candidate_evaluation_id,
        ) != (
            candidate.portfolio_id,
            candidate.portfolio_subject_id,
            candidate.profile_binding_id,
            candidate.profile_revision,
            candidate.candidate_evaluation_id,
        ):
            issues.append(
                _issue(
                    "curation.proposal_context_mismatch",
                    "Proposal context differs from the exact Candidate context.",
                    proposal.record_type,
                    proposal.selection_proposal_id,
                )
            )
        else:
            if not set(proposal.proposed_section_ids).issubset(candidate.eligible_section_ids):
                issues.append(
                    _issue(
                        "curation.proposal_section_ineligible",
                        "Proposal identifies a section not permitted by the Candidate.",
                        proposal.record_type,
                        proposal.selection_proposal_id,
                    )
                )
            if proposal.candidate_condition_state_snapshot != candidate.condition_state:
                issues.append(
                    _issue(
                        "curation.proposal_condition_mismatch",
                        "Proposal condition snapshot differs from the exact Candidate.",
                        proposal.record_type,
                        proposal.selection_proposal_id,
                    )
                )
        binding = bindings.get(proposal.profile_binding_id)
        profile = (
            None
            if binding is None
            else profiles.get(
                (
                    binding.profile_revision.portfolio_profile_id,
                    binding.profile_revision.profile_revision,
                )
            )
        )
        if binding is None or binding.profile_revision != proposal.profile_revision or profile is None:
            issues.append(
                _issue(
                    "curation.proposal_profile_mismatch",
                    "Proposal Profile Binding/Revision is invalid.",
                    proposal.record_type,
                    proposal.selection_proposal_id,
                )
            )
        elif not set(proposal.proposed_section_ids).issubset(
            {item.section_id for item in profile.sections if item.obligation != "prohibited"}
        ):
            issues.append(
                _issue(
                    "curation.proposal_section_invalid",
                    "Proposal section does not resolve to a permitted exact Profile section.",
                    proposal.record_type,
                    proposal.selection_proposal_id,
                )
            )
        for requirement_id in proposal.intended_profile_requirement_ids:
            if (
                proposal.profile_revision.portfolio_profile_id,
                proposal.profile_revision.profile_revision,
                requirement_id,
            ) not in requirements:
                issues.append(
                    _issue(
                        "curation.proposal_requirement_missing",
                        "Proposal references a missing exact Profile requirement.",
                        proposal.record_type,
                        proposal.selection_proposal_id,
                    )
                )
        if proposal.rationale_id is not None and proposal.rationale_id not in rationales:
            issues.append(
                _issue(
                    "curation.proposal_rationale_missing",
                    "Proposal rationale does not exist.",
                    proposal.record_type,
                    proposal.selection_proposal_id,
                )
            )
        if proposal.predecessor_proposal_id is not None:
            proposal_predecessor = proposals.get(proposal.predecessor_proposal_id)
            if proposal_predecessor is None:
                issues.append(
                    _issue(
                        "curation.proposal_predecessor_missing",
                        "Proposal predecessor does not exist.",
                        proposal.record_type,
                        proposal.selection_proposal_id,
                    )
                )
            elif (
                proposal_predecessor.portfolio_id,
                proposal_predecessor.profile_binding_id,
                proposal_predecessor.candidate_id,
            ) != (
                proposal.portfolio_id,
                proposal.profile_binding_id,
                proposal.candidate_id,
            ):
                issues.append(
                    _issue(
                        "curation.proposal_predecessor_mismatch",
                        "Proposal predecessor belongs to another curation context.",
                        proposal.record_type,
                        proposal.selection_proposal_id,
                    )
                )
            proposal_successors[proposal.predecessor_proposal_id].append(
                proposal.selection_proposal_id
            )
    for proposal_predecessor_id, proposal_successor_ids in sorted(
        proposal_successors.items()
    ):
        if len(proposal_successor_ids) > 1:
            issues.append(
                _issue(
                    "curation.proposal_branch",
                    "Proposal predecessor has more than one successor.",
                    "selection_proposal",
                    proposal_predecessor_id,
                )
            )
    proposal_predecessors = {
        item.selection_proposal_id: item.predecessor_proposal_id for item in state.proposals
    }
    for representative in _cycle_representatives(proposal_predecessors):
        issues.append(
            _issue(
                "curation.proposal_cycle",
                "Proposal predecessor chain contains a cycle.",
                "selection_proposal",
                representative,
            )
        )

    # Decisions are singular per exact Proposal and accepted decisions bind exact Selection.
    decisions_by_proposal: dict[str, list[SelectionDecision]] = defaultdict(list)
    for decision in state.decisions:
        decisions_by_proposal[decision.selection_proposal_id].append(decision)
        decision_proposal = proposals.get(decision.selection_proposal_id)
        if decision_proposal is None:
            issues.append(
                _issue(
                    "curation.decision_proposal_missing",
                    "Selection Decision Proposal does not exist.",
                    decision.record_type,
                    decision.selection_decision_id,
                )
            )
            continue
        if decision.rationale_id is not None and decision.rationale_id not in rationales:
            issues.append(
                _issue(
                    "curation.decision_rationale_missing",
                    "Selection Decision rationale does not exist.",
                    decision.record_type,
                    decision.selection_decision_id,
                )
            )
        if decision.decision == "accepted":
            selected = selections.get(decision.resulting_selection_id or "")
            if selected is None:
                issues.append(
                    _issue(
                        "curation.decision_selection_missing",
                        "Accepted Selection Decision has no exact resulting Selection.",
                        decision.record_type,
                        decision.selection_decision_id,
                    )
                )
            elif (
                selected.portfolio_id,
                selected.portfolio_subject_id,
                selected.profile_binding_id,
                selected.profile_revision,
                selected.candidate_id,
                selected.candidate_evaluation_id,
            ) != (
                decision_proposal.portfolio_id,
                decision_proposal.portfolio_subject_id,
                decision_proposal.profile_binding_id,
                decision_proposal.profile_revision,
                decision_proposal.candidate_id,
                decision_proposal.candidate_evaluation_id,
            ):
                issues.append(
                    _issue(
                        "curation.decision_selection_mismatch",
                        "Accepted Selection does not match its exact Proposal.",
                        decision.record_type,
                        decision.selection_decision_id,
                    )
                )
    for proposal_id, proposal_decisions in sorted(decisions_by_proposal.items()):
        if len(proposal_decisions) > 1:
            issues.append(
                _issue(
                    "curation.proposal_already_decided",
                    "Proposal has more than one immutable Decision.",
                    "selection_proposal",
                    proposal_id,
                )
            )

    # Selection lifecycle chains and active uniqueness.
    selection_events = {
        item.selection_lifecycle_event_id: item for item in state.selection_events
    }
    selection_event_successors: dict[str, list[str]] = defaultdict(list)
    for event in state.selection_events:
        if event.selection_id not in selections:
            issues.append(
                _issue(
                    "curation.selection_event_selection_missing",
                    "Selection lifecycle event references a missing Selection.",
                    event.record_type,
                    event.selection_lifecycle_event_id,
                )
            )
        if event.predecessor_event_id is not None:
            selection_predecessor_event = selection_events.get(
                event.predecessor_event_id
            )
            if selection_predecessor_event is None:
                issues.append(
                    _issue(
                        "curation.selection_event_predecessor_missing",
                        "Selection lifecycle predecessor does not exist.",
                        event.record_type,
                        event.selection_lifecycle_event_id,
                    )
                )
            elif selection_predecessor_event.selection_id != event.selection_id:
                issues.append(
                    _issue(
                        "curation.selection_event_predecessor_mismatch",
                        "Selection lifecycle predecessor belongs to another Selection.",
                        event.record_type,
                        event.selection_lifecycle_event_id,
                    )
                )
            elif selection_predecessor_event.event_kind != "activated":
                issues.append(
                    _issue(
                        "curation.selection_lifecycle_transition_invalid",
                        "Terminal Selection lifecycle events must follow activation directly.",
                        event.record_type,
                        event.selection_lifecycle_event_id,
                    )
                )
            selection_event_successors[event.predecessor_event_id].append(
                event.selection_lifecycle_event_id
            )
        if event.basis_selection_decision_id is not None:
            basis = decisions.get(event.basis_selection_decision_id)
            if basis is None or basis.resulting_selection_id != event.selection_id:
                issues.append(
                    _issue(
                        "curation.selection_activation_basis_invalid",
                        "Selection activation basis does not resolve to its accepted Decision.",
                        event.record_type,
                        event.selection_lifecycle_event_id,
                    )
                )
        for successor_id in event.successor_selection_ids:
            if successor_id not in selections:
                issues.append(
                    _issue(
                        "curation.selection_successor_missing",
                        "Selection replacement/supersession successor does not exist.",
                        event.record_type,
                        event.selection_lifecycle_event_id,
                    )
                )
    for selection_predecessor_event_id, selection_successor_event_ids in sorted(
        selection_event_successors.items()
    ):
        if len(selection_successor_event_ids) > 1:
            issues.append(
                _issue(
                    "curation.selection_lifecycle_branch",
                    "Selection lifecycle event has more than one successor.",
                    "selection_lifecycle_event",
                    selection_predecessor_event_id,
                )
            )
    selection_event_predecessors = {
        item.selection_lifecycle_event_id: item.predecessor_event_id
        for item in state.selection_events
    }
    for representative in _cycle_representatives(selection_event_predecessors):
        issues.append(
            _issue(
                "curation.selection_lifecycle_cycle",
                "Selection lifecycle predecessor chain contains a cycle.",
                "selection_lifecycle_event",
                representative,
            )
        )
    for selection in state.selections:
        if len(state.selection_heads(selection.selection_id)) > 1:
            issues.append(
                _issue(
                    "curation.selection_lifecycle_conflict",
                    "Selection has multiple lifecycle heads.",
                    selection.record_type,
                    selection.selection_id,
                )
            )
    active_selection_keys: dict[tuple[str, str, str], str] = {}
    for selection in state.active_selections():
        key = (selection.portfolio_id, selection.profile_binding_id, selection.candidate_id)
        prior = active_selection_keys.get(key)
        if prior is not None:
            issues.append(
                _issue(
                    "curation.selection_duplicate_active",
                    "Candidate has more than one active Selection in one Binding.",
                    selection.record_type,
                    selection.selection_id,
                )
            )
        active_selection_keys[key] = selection.selection_id

    # Placement lifecycle and exact active Selection context.
    placement_events = {
        item.placement_lifecycle_event_id: item for item in state.placement_events
    }
    placement_event_successors: dict[str, list[str]] = defaultdict(list)
    for placement_event in state.placement_events:
        if placement_event.placement_id not in placements:
            issues.append(
                _issue(
                    "curation.placement_event_placement_missing",
                    "Placement lifecycle event references a missing Placement.",
                    placement_event.record_type,
                    placement_event.placement_lifecycle_event_id,
                )
            )
        if placement_event.predecessor_event_id is not None:
            placement_predecessor_event = placement_events.get(
                placement_event.predecessor_event_id
            )
            if placement_predecessor_event is None:
                issues.append(
                    _issue(
                        "curation.placement_event_predecessor_missing",
                        "Placement lifecycle predecessor does not exist.",
                        placement_event.record_type,
                        placement_event.placement_lifecycle_event_id,
                    )
                )
            elif placement_predecessor_event.placement_id != placement_event.placement_id:
                issues.append(
                    _issue(
                        "curation.placement_event_predecessor_mismatch",
                        "Placement lifecycle predecessor belongs to another Placement.",
                        placement_event.record_type,
                        placement_event.placement_lifecycle_event_id,
                    )
                )
            elif placement_predecessor_event.event_kind != "activated":
                issues.append(
                    _issue(
                        "curation.placement_lifecycle_transition_invalid",
                        "Terminal Placement lifecycle events must follow activation directly.",
                        placement_event.record_type,
                        placement_event.placement_lifecycle_event_id,
                    )
                )
            placement_event_successors[placement_event.predecessor_event_id].append(
                placement_event.placement_lifecycle_event_id
            )
        if placement_event.successor_placement_id is not None and placement_event.successor_placement_id not in placements:
            issues.append(
                _issue(
                    "curation.placement_successor_missing",
                    "Replacement Placement successor does not exist.",
                    placement_event.record_type,
                    placement_event.placement_lifecycle_event_id,
                )
            )
    for placement_predecessor_event_id, placement_successor_event_ids in sorted(
        placement_event_successors.items()
    ):
        if len(placement_successor_event_ids) > 1:
            issues.append(
                _issue(
                    "curation.placement_lifecycle_branch",
                    "Placement lifecycle event has more than one successor.",
                    "placement_lifecycle_event",
                    placement_predecessor_event_id,
                )
            )
    placement_event_predecessors = {
        item.placement_lifecycle_event_id: item.predecessor_event_id
        for item in state.placement_events
    }
    for representative in _cycle_representatives(placement_event_predecessors):
        issues.append(
            _issue(
                "curation.placement_lifecycle_cycle",
                "Placement lifecycle predecessor chain contains a cycle.",
                "placement_lifecycle_event",
                representative,
            )
        )
    active_placement_keys: dict[tuple[str, str, str, str], str] = {}
    for placement in state.active_placements():
        selected = selections.get(placement.selection_id)
        if selected is None or state.selection_status(placement.selection_id) != "activated":
            issues.append(
                _issue(
                    "curation.placement_selection_inactive",
                    "Active Placement requires an active managed Selection.",
                    placement.record_type,
                    placement.placement_id,
                )
            )
            continue
        candidate = candidates.get(selected.candidate_id)
        if candidate is None or placement.section_id not in candidate.eligible_section_ids:
            issues.append(
                _issue(
                    "curation.placement_section_ineligible",
                    "Active Placement section is not Candidate-eligible.",
                    placement.record_type,
                    placement.placement_id,
                )
            )
        active_placement_key = (
            placement.portfolio_id,
            placement.profile_binding_id,
            placement.selection_id,
            placement.section_id,
        )
        if active_placement_key in active_placement_keys:
            issues.append(
                _issue(
                    "curation.placement_duplicate_active",
                    "Selection has duplicate active Placements in one section.",
                    placement.record_type,
                    placement.placement_id,
                )
            )
        active_placement_keys[active_placement_key] = placement.placement_id

    # Explicit Arrangement pointer revision chains and complete active-section membership.
    arrangement_pointer_groups: dict[
        tuple[str, str, str, str], list[SectionArrangementPointerRevision]
    ] = defaultdict(list)
    for arrangement_pointer in state.arrangement_pointers:
        arrangement_pointer_group_key = (
            arrangement_pointer.arrangement_pointer_id,
            arrangement_pointer.portfolio_id,
            arrangement_pointer.profile_binding_id,
            arrangement_pointer.section_id,
        )
        arrangement_pointer_groups[arrangement_pointer_group_key].append(
            arrangement_pointer
        )
        arrangement = arrangements.get(arrangement_pointer.arrangement_id)
        if arrangement is None or (
            arrangement.portfolio_id,
            arrangement.profile_binding_id,
            arrangement.section_id,
        ) != (arrangement_pointer.portfolio_id, arrangement_pointer.profile_binding_id, arrangement_pointer.section_id):
            issues.append(
                _issue(
                    "curation.arrangement_pointer_target_invalid",
                    "Arrangement pointer target does not resolve in the exact section context.",
                    arrangement_pointer.record_type,
                    f"{arrangement_pointer.arrangement_pointer_id}:{arrangement_pointer.pointer_revision}",
                )
            )
    for arrangement_group_key, arrangement_pointer_group in sorted(
        arrangement_pointer_groups.items()
    ):
        arrangement_by_revision = {
            item.pointer_revision: item for item in arrangement_pointer_group
        }
        arrangement_successor_counts: dict[int, int] = defaultdict(int)
        for arrangement_pointer in arrangement_pointer_group:
            predecessor_revision = arrangement_pointer.predecessor_pointer_revision
            if predecessor_revision is not None:
                arrangement_predecessor_pointer = arrangement_by_revision.get(
                    predecessor_revision
                )
                if arrangement_predecessor_pointer is None:
                    issues.append(
                        _issue(
                            "curation.arrangement_pointer_predecessor_missing",
                            "Arrangement pointer predecessor revision does not exist.",
                            arrangement_pointer.record_type,
                            f"{arrangement_pointer.arrangement_pointer_id}:{arrangement_pointer.pointer_revision}",
                        )
                    )
                arrangement_successor_counts[predecessor_revision] += 1
        if any(count > 1 for count in arrangement_successor_counts.values()):
            issues.append(
                _issue(
                    "curation.arrangement_pointer_branch",
                    "Arrangement pointer revision has more than one successor.",
                    "section_arrangement_pointer_revision",
                    arrangement_group_key[0],
                )
            )
    section_contexts = {
        (item.portfolio_id, item.profile_binding_id, item.section_id)
        for item in state.arrangement_pointers
    } | {
        (item.portfolio_id, item.profile_binding_id, item.section_id)
        for item in state.active_placements()
    }
    for portfolio_id, binding_id, section_id in sorted(section_contexts):
        arrangement_heads = state.arrangement_pointer_heads(
            portfolio_id, binding_id, section_id
        )
        if len(arrangement_heads) != 1:
            issues.append(
                _issue(
                    "curation.arrangement_pointer_conflict",
                    "Section has multiple or no explicit Arrangement pointer heads.",
                    "section_arrangement_pointer_revision",
                    f"{portfolio_id}:{binding_id}:{section_id}",
                )
            )
            continue
        arrangement = state.current_arrangement(portfolio_id, binding_id, section_id)
        if arrangement is None:
            continue
        expected = tuple(
            item.placement_id
            for item in state.active_placements(
                portfolio_id=portfolio_id,
                profile_binding_id=binding_id,
                section_id=section_id,
            )
        )
        if set(arrangement.placement_ids) != set(expected) or len(arrangement.placement_ids) != len(expected):
            issues.append(
                _issue(
                    "curation.arrangement_incomplete",
                    "Current Arrangement does not contain exactly the active section Placements.",
                    arrangement.record_type,
                    arrangement.arrangement_id,
                )
            )

    # Rationale predecessor chains, exact targets, and requirement references.
    rationale_successors: dict[str, list[str]] = defaultdict(list)
    for rationale in state.rationales:
        if not _target_exists(state, rationale.target_kind, rationale.target_id, None):
            issues.append(
                _issue(
                    "curation.rationale_target_invalid",
                    "Curation rationale target does not resolve.",
                    rationale.record_type,
                    rationale.rationale_id,
                )
            )
        binding = bindings.get(rationale.profile_binding_id)
        if binding is None or binding.portfolio_id != rationale.portfolio_id:
            issues.append(
                _issue(
                    "curation.rationale_context_mismatch",
                    "Curation rationale Portfolio/Profile Binding context is invalid.",
                    rationale.record_type,
                    rationale.rationale_id,
                )
            )
        elif any(
            (
                binding.profile_revision.portfolio_profile_id,
                binding.profile_revision.profile_revision,
                requirement_id,
            )
            not in requirements
            for requirement_id in rationale.profile_requirement_ids
        ):
            issues.append(
                _issue(
                    "curation.rationale_requirement_missing",
                    "Curation rationale references a missing exact Profile requirement.",
                    rationale.record_type,
                    rationale.rationale_id,
                )
            )
        if rationale.predecessor_rationale_id is not None:
            rationale_predecessor = rationales.get(rationale.predecessor_rationale_id)
            if rationale_predecessor is None:
                issues.append(
                    _issue(
                        "curation.rationale_predecessor_missing",
                        "Curation rationale predecessor does not exist.",
                        rationale.record_type,
                        rationale.rationale_id,
                    )
                )
            elif (
                rationale_predecessor.portfolio_id,
                rationale_predecessor.profile_binding_id,
                rationale_predecessor.target_kind,
                rationale_predecessor.target_id,
                rationale_predecessor.action_kind,
            ) != (
                rationale.portfolio_id,
                rationale.profile_binding_id,
                rationale.target_kind,
                rationale.target_id,
                rationale.action_kind,
            ):
                issues.append(
                    _issue(
                        "curation.rationale_predecessor_mismatch",
                        "Curation rationale predecessor belongs to different action provenance.",
                        rationale.record_type,
                        rationale.rationale_id,
                    )
                )
            rationale_successors[rationale.predecessor_rationale_id].append(
                rationale.rationale_id
            )
    for predecessor_id, successor_ids in sorted(rationale_successors.items()):
        if len(successor_ids) > 1:
            issues.append(
                _issue(
                    "curation.rationale_branch",
                    "Curation rationale predecessor has more than one successor.",
                    "curation_rationale",
                    predecessor_id,
                )
            )
    rationale_predecessors = {
        item.rationale_id: item.predecessor_rationale_id for item in state.rationales
    }
    for representative in _cycle_representatives(rationale_predecessors):
        issues.append(
            _issue(
                "curation.rationale_cycle",
                "Curation rationale predecessor chain contains a cycle.",
                "curation_rationale",
                representative,
            )
        )

    # Annotation and Reflection revision chains/targets/Profile requirements.
    for annotation in state.annotations:
        for target in annotation.target_references:
            if not _target_exists(
                state, target.target_kind, target.target_id, target.target_revision
            ):
                issues.append(
                    _issue(
                        "curation.annotation_target_invalid",
                        "Annotation target does not resolve.",
                        annotation.record_type,
                        f"{annotation.annotation_id}:{annotation.annotation_revision}",
                    )
                )
        if annotation.predecessor_annotation_revision is not None and not any(
            item.annotation_id == annotation.annotation_id
            and item.annotation_revision == annotation.predecessor_annotation_revision
            for item in state.annotations
        ):
            issues.append(
                _issue(
                    "curation.annotation_predecessor_missing",
                    "Annotation predecessor revision does not exist.",
                    annotation.record_type,
                    f"{annotation.annotation_id}:{annotation.annotation_revision}",
                )
            )
    annotation_predecessors = {
        (item.annotation_id, item.annotation_revision): (
            None
            if item.predecessor_annotation_revision is None
            else (item.annotation_id, item.predecessor_annotation_revision)
        )
        for item in state.annotations
    }
    for annotation_id, revision in _revision_cycle_representatives(annotation_predecessors):
        issues.append(
            _issue(
                "curation.annotation_revision_cycle",
                "Annotation revision chain contains a cycle.",
                "curation_annotation",
                f"{annotation_id}:{revision}",
            )
        )
    for annotation_id in sorted({item.annotation_id for item in state.annotations}):
        if len(state.annotation_heads(annotation_id)) > 1:
            issues.append(
                _issue(
                    "curation.annotation_revision_conflict",
                    "Annotation series has multiple revision heads.",
                    "curation_annotation",
                    annotation_id,
                )
            )

    for reflection in state.reflections:
        requirement_key = (
            reflection.profile_revision.portfolio_profile_id,
            reflection.profile_revision.profile_revision,
            reflection.reflection_requirement_id,
        )
        requirement = requirements.get(requirement_key)
        if requirement is None or requirement.requirement_kind != "reflection":
            issues.append(
                _issue(
                    "curation.reflection_requirement_missing",
                    "Reflection exact Profile requirement is missing or not a Reflection requirement.",
                    reflection.record_type,
                    f"{reflection.reflection_id}:{reflection.reflection_revision}",
                )
            )
        for target in reflection.target_references:
            if not _target_exists(
                state, target.target_kind, target.target_id, target.target_revision
            ):
                issues.append(
                    _issue(
                        "curation.reflection_target_invalid",
                        "Reflection target does not resolve.",
                        reflection.record_type,
                        f"{reflection.reflection_id}:{reflection.reflection_revision}",
                    )
                )
        if reflection.predecessor_reflection_revision is not None and not any(
            item.reflection_id == reflection.reflection_id
            and item.reflection_revision == reflection.predecessor_reflection_revision
            for item in state.reflections
        ):
            issues.append(
                _issue(
                    "curation.reflection_predecessor_missing",
                    "Reflection predecessor revision does not exist.",
                    reflection.record_type,
                    f"{reflection.reflection_id}:{reflection.reflection_revision}",
                )
            )
    reflection_predecessors = {
        (item.reflection_id, item.reflection_revision): (
            None
            if item.predecessor_reflection_revision is None
            else (item.reflection_id, item.predecessor_reflection_revision)
        )
        for item in state.reflections
    }
    for reflection_id, revision in _revision_cycle_representatives(reflection_predecessors):
        issues.append(
            _issue(
                "curation.reflection_revision_cycle",
                "Reflection revision chain contains a cycle.",
                "portfolio_reflection",
                f"{reflection_id}:{revision}",
            )
        )
    for reflection_id in sorted({item.reflection_id for item in state.reflections}):
        if len(state.reflection_heads(reflection_id)) > 1:
            issues.append(
                _issue(
                    "curation.reflection_revision_conflict",
                    "Reflection series has multiple revision heads.",
                    "portfolio_reflection",
                    reflection_id,
                )
            )

    # Review exact targets and exact approval requirement semantics.
    for review in state.reviews:
        for target in review.target_references:
            if not _target_exists(
                state, target.target_kind, target.target_id, target.target_revision
            ):
                issues.append(
                    _issue(
                        "curation.review_target_invalid",
                        "Curation Review target does not resolve.",
                        review.record_type,
                        review.curation_review_decision_id,
                    )
                )
        if review.approval_requirement_id is not None:
            review_requirement_key = (
                review.profile_revision.portfolio_profile_id,
                review.profile_revision.profile_revision,
                review.approval_requirement_id,
            )
            requirement = requirements.get(review_requirement_key)
            if requirement is None or requirement.requirement_kind != "approval":
                issues.append(
                    _issue(
                        "curation.review_requirement_missing",
                        "Curation Review approval requirement is missing or not an approval requirement.",
                        review.record_type,
                        review.curation_review_decision_id,
                    )
                )

    review_by_id = {item.curation_review_decision_id: item for item in state.reviews}
    review_successors: dict[str, list[str]] = defaultdict(list)
    for review in state.reviews:
        if review.predecessor_review_decision_id is None:
            continue
        review_predecessor = review_by_id.get(review.predecessor_review_decision_id)
        if review_predecessor is None:
            issues.append(
                _issue(
                    "curation.review_predecessor_missing",
                    "Curation Review predecessor does not exist.",
                    review.record_type,
                    review.curation_review_decision_id,
                )
            )
        elif (
            review_predecessor.portfolio_id,
            review_predecessor.profile_binding_id,
            review_predecessor.target_scope,
            review_predecessor.target_references,
        ) != (
            review.portfolio_id,
            review.profile_binding_id,
            review.target_scope,
            review.target_references,
        ):
            issues.append(
                _issue(
                    "curation.review_predecessor_mismatch",
                    "Curation Review predecessor targets different curation state.",
                    review.record_type,
                    review.curation_review_decision_id,
                )
            )
        review_successors[review.predecessor_review_decision_id].append(
            review.curation_review_decision_id
        )
    for predecessor_id, successor_ids in sorted(review_successors.items()):
        if len(successor_ids) > 1:
            issues.append(
                _issue(
                    "curation.review_branch",
                    "Curation Review predecessor has more than one successor.",
                    "curation_review_decision",
                    predecessor_id,
                )
            )
    review_predecessors = {
        item.curation_review_decision_id: item.predecessor_review_decision_id
        for item in state.reviews
    }
    for representative in _cycle_representatives(review_predecessors):
        issues.append(
            _issue(
                "curation.review_cycle",
                "Curation Review predecessor chain contains a cycle.",
                "curation_review_decision",
                representative,
            )
        )

    # Composition Inventory is a one-to-one additive freeze over the existing Composition.
    inventory_keys: set[tuple[str, int]] = set()
    for inventory in state.composition_inventories:
        inventory_key = (inventory.portfolio_id, inventory.composition_revision)
        if inventory_key in inventory_keys:
            issues.append(
                _issue(
                    "curation.composition_inventory_duplicate",
                    "Composition has more than one curation inventory.",
                    inventory.record_type,
                    f"{inventory_key[0]}:{inventory_key[1]}",
                )
            )
        inventory_keys.add(inventory_key)
        composition = next(
            (
                item
                for item in state.compositions
                if item.portfolio_id == inventory.portfolio_id
                and item.composition_revision == inventory.composition_revision
            ),
            None,
        )
        if composition is None or (
            composition.profile_binding_id,
            composition.profile_revision,
        ) != (inventory.profile_binding_id, inventory.profile_revision):
            issues.append(
                _issue(
                    "curation.composition_inventory_mismatch",
                    "Composition curation inventory does not match its exact Composition.",
                    inventory.record_type,
                    f"{inventory.portfolio_id}:{inventory.composition_revision}",
                )
            )
        for rationale_id in inventory.included_rationale_ids:
            if rationale_id not in rationales:
                issues.append(
                    _issue(
                        "curation.composition_rationale_missing",
                        "Composition inventory references a missing rationale.",
                        inventory.record_type,
                        f"{inventory.portfolio_id}:{inventory.composition_revision}",
                    )
                )
        for revision_ref in inventory.included_curation_revisions:
            if revision_ref.record_kind == "annotation":
                exists = any(
                    item.annotation_id == revision_ref.record_id
                    and item.annotation_revision == revision_ref.revision
                    for item in state.annotations
                )
            else:
                exists = any(
                    item.reflection_id == revision_ref.record_id
                    and item.reflection_revision == revision_ref.revision
                    for item in state.reflections
                )
            if not exists:
                issues.append(
                    _issue(
                        "curation.composition_curation_revision_missing",
                        "Composition inventory references a missing Annotation/Reflection revision.",
                        inventory.record_type,
                        f"{inventory.portfolio_id}:{inventory.composition_revision}",
                    )
                )
        for review_id in inventory.applicable_review_decision_ids:
            if not any(item.curation_review_decision_id == review_id for item in state.reviews):
                issues.append(
                    _issue(
                        "curation.composition_review_missing",
                        "Composition inventory references a missing Review Decision.",
                        inventory.record_type,
                        f"{inventory.portfolio_id}:{inventory.composition_revision}",
                    )
                )
        for requirement_id in inventory.related_profile_requirement_ids:
            requirement_key = (
                inventory.profile_revision.portfolio_profile_id,
                inventory.profile_revision.profile_revision,
                requirement_id,
            )
            if requirement_key not in requirements:
                issues.append(
                    _issue(
                        "curation.composition_requirement_missing",
                        "Composition inventory references a missing exact Profile requirement.",
                        inventory.record_type,
                        f"{inventory.portfolio_id}:{inventory.composition_revision}",
                    )
                )

    # Explicit Composition current pointer revision chains.
    composition_pointer_groups: dict[
        tuple[str, str, str], list[WorkingPortfolioCompositionPointerRevision]
    ] = defaultdict(list)
    for composition_pointer in state.composition_pointers:
        composition_pointer_group_key = (
            composition_pointer.composition_pointer_id,
            composition_pointer.portfolio_id,
            composition_pointer.profile_binding_id,
        )
        composition_pointer_groups[composition_pointer_group_key].append(
            composition_pointer
        )
        target_exists = any(
            item.portfolio_id == composition_pointer.portfolio_id
            and item.profile_binding_id == composition_pointer.profile_binding_id
            and item.composition_revision == composition_pointer.composition_revision
            for item in state.compositions
        )
        inventory_exists = any(
            item.portfolio_id == composition_pointer.portfolio_id
            and item.profile_binding_id == composition_pointer.profile_binding_id
            and item.composition_revision == composition_pointer.composition_revision
            for item in state.composition_inventories
        )
        if not target_exists or not inventory_exists:
            issues.append(
                _issue(
                    "curation.composition_pointer_target_invalid",
                    "Composition pointer target and exact curation inventory must both resolve.",
                    composition_pointer.record_type,
                    f"{composition_pointer.composition_pointer_id}:{composition_pointer.pointer_revision}",
                )
            )
    for composition_group_key, composition_pointer_group in sorted(
        composition_pointer_groups.items()
    ):
        composition_by_revision = {
            item.pointer_revision: item for item in composition_pointer_group
        }
        composition_successor_counts: dict[int, int] = defaultdict(int)
        for composition_pointer in composition_pointer_group:
            predecessor_revision = composition_pointer.predecessor_pointer_revision
            if predecessor_revision is not None:
                if predecessor_revision not in composition_by_revision:
                    issues.append(
                        _issue(
                            "curation.composition_pointer_predecessor_missing",
                            "Composition pointer predecessor revision does not exist.",
                            composition_pointer.record_type,
                            f"{composition_pointer.composition_pointer_id}:{composition_pointer.pointer_revision}",
                        )
                    )
                composition_successor_counts[predecessor_revision] += 1
        if any(count > 1 for count in composition_successor_counts.values()):
            issues.append(
                _issue(
                    "curation.composition_pointer_branch",
                    "Composition pointer revision has more than one successor.",
                    "working_portfolio_composition_pointer_revision",
                    composition_group_key[0],
                )
            )
    composition_contexts = {
        (item.portfolio_id, item.profile_binding_id) for item in state.composition_pointers
    }
    for portfolio_id, binding_id in sorted(composition_contexts):
        composition_heads = state.composition_pointer_heads(portfolio_id, binding_id)
        if len(composition_heads) != 1:
            issues.append(
                _issue(
                    "curation.composition_pointer_conflict",
                    "Working Portfolio has multiple or no Composition pointer heads.",
                    "working_portfolio_composition_pointer_revision",
                    f"{portfolio_id}:{binding_id}",
                )
            )

    return tuple(
        sorted(
            issues,
            key=lambda item: (
                item.code,
                item.record_type or "",
                item.record_id or "",
                item.message,
            ),
        )
    )


def validate_curation_state(state: CurationState) -> None:
    issues = collect_curation_state_issues(state)
    if issues:
        from vitrine.models.errors import VitrineRecordGraphError

        raise VitrineRecordGraphError(issues)


__all__ = [
    "CurationState",
    "collect_curation_state_issues",
    "project_curation_state",
    "validate_curation_state",
]
