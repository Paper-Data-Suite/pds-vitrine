"""Deterministic, presentation-independent read projections for user workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CandidateAvailabilityObservation,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SectionArrangementRevision,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotEdition,
    SnapshotSeries,
    VitrineRecord,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionRevision,
)
from vitrine.profile_state import project_profile_state
from vitrine.snapshot_state import project_snapshot_state
from vitrine.storage import VitrineStorageNotFoundError, load_current_records


class WorkflowViewError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CandidateSummary:
    candidate_id: str
    profile_binding_id: str
    display_snapshot: str
    condition_state: str
    eligible_section_ids: tuple[str, ...]
    active_selection_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateDetail:
    candidate_id: str
    candidate_evaluation_id: str
    portfolio_id: str
    profile_binding_id: str
    display_snapshot: str
    source_endpoint: CandidateSourceEndpoint
    eligible_section_ids: tuple[str, ...]
    condition_state: str
    evaluation_reason_codes: tuple[str, ...]
    unresolved_condition_codes: tuple[str, ...]
    availability_observations: tuple[CandidateAvailabilityObservation, ...]


@dataclass(frozen=True, slots=True)
class ArrangementView:
    portfolio_id: str
    section_id: str
    arrangement: SectionArrangementRevision | None
    pointer_revision: int | None
    placements: tuple[PortfolioPlacement, ...]


@dataclass(frozen=True, slots=True)
class CompositionView:
    composition: WorkingPortfolioCompositionRevision | None
    inventory: WorkingPortfolioCompositionInventory | None
    pointer_revision: int | None


@dataclass(frozen=True, slots=True)
class SnapshotSeriesView:
    series: SnapshotSeries
    requests: tuple[SnapshotBuildRequest, ...]
    plans: tuple[SnapshotBuildPlan, ...]
    attempts: tuple[SnapshotBuildAttempt, ...]
    attempt_results: tuple[SnapshotBuildAttemptResult, ...]
    editions: tuple[SnapshotEdition, ...]
    current_edition: SnapshotEdition | None


def _records(root: str | Path) -> tuple[VitrineRecord, ...]:
    try:
        return load_current_records(root)
    except VitrineStorageNotFoundError:
        return ()


def list_candidate_summaries(
    root: str | Path, portfolio_id: str
) -> tuple[CandidateSummary, ...]:
    records = _records(root)
    state = project_curation_state(records)
    binding = project_profile_state(records).active_binding(portfolio_id)
    active = (
        ()
        if binding is None
        else state.active_selections(
            portfolio_id=portfolio_id, profile_binding_id=binding.profile_binding_id
        )
    )
    selected = {item.candidate_id: item.selection_id for item in active}
    return tuple(
        CandidateSummary(
            item.candidate_id,
            item.profile_binding_id,
            item.display_snapshot,
            item.condition_state,
            item.eligible_section_ids,
            selected.get(item.candidate_id),
        )
        for item in sorted(
            (
                x
                for x in state.candidates
                if x.portfolio_id == portfolio_id
                and binding is not None
                and x.profile_binding_id == binding.profile_binding_id
            ),
            key=lambda x: x.candidate_id,
        )
    )


def show_candidate(root: str | Path, candidate_id: str) -> PortfolioCandidate:
    matches = tuple(
        x
        for x in _records(root)
        if isinstance(x, PortfolioCandidate) and x.candidate_id == candidate_id
    )
    if len(matches) != 1:
        raise WorkflowViewError("candidate_not_found", "Candidate not found.")
    return matches[0]


def show_candidate_detail(root: str | Path, candidate_id: str) -> CandidateDetail:
    records = _records(root)
    candidate = next(
        (
            item
            for item in records
            if isinstance(item, PortfolioCandidate)
            and item.candidate_id == candidate_id
        ),
        None,
    )
    if candidate is None:
        raise WorkflowViewError("candidate_not_found", "Candidate not found.")
    evaluation = next(
        (
            item
            for item in records
            if isinstance(item, CandidateEvaluation)
            and item.candidate_evaluation_id == candidate.candidate_evaluation_id
        ),
        None,
    )
    if evaluation is None:
        raise WorkflowViewError(
            "candidate_evaluation_not_found", "Candidate Evaluation not found."
        )
    unresolved = (
        ()
        if candidate.condition_state == "ready_for_consideration"
        else (candidate.condition_state,)
    )
    return CandidateDetail(
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        portfolio_id=candidate.portfolio_id,
        profile_binding_id=candidate.profile_binding_id,
        display_snapshot=candidate.display_snapshot,
        source_endpoint=candidate.source_endpoint,
        eligible_section_ids=candidate.eligible_section_ids,
        condition_state=candidate.condition_state,
        evaluation_reason_codes=evaluation.reason_codes,
        unresolved_condition_codes=unresolved,
        availability_observations=evaluation.availability_observations,
    )


def list_active_selections(
    root: str | Path, portfolio_id: str
) -> tuple[PortfolioSelection, ...]:
    records = _records(root)
    binding = project_profile_state(records).active_binding(portfolio_id)
    if binding is None:
        return ()
    return project_curation_state(records).active_selections(
        portfolio_id=portfolio_id, profile_binding_id=binding.profile_binding_id
    )


def show_arrangement(
    root: str | Path, portfolio_id: str, section_id: str
) -> ArrangementView:
    records = _records(root)
    binding = project_profile_state(records).active_binding(portfolio_id)
    if binding is None:
        raise WorkflowViewError(
            "profile_binding_missing", "Portfolio has no active Profile Binding."
        )
    state = project_curation_state(records)
    pointers = state.arrangement_pointer_heads(
        portfolio_id, binding.profile_binding_id, section_id
    )
    if len(pointers) > 1:
        raise WorkflowViewError(
            "arrangement_pointer_conflict", "Section Arrangement pointer is conflicted."
        )
    arrangement = state.current_arrangement(
        portfolio_id, binding.profile_binding_id, section_id
    )
    placements = state.active_placements(
        portfolio_id=portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        section_id=section_id,
    )
    by_id = {item.placement_id: item for item in placements}
    ordered = (
        placements
        if arrangement is None
        else tuple(by_id[x] for x in arrangement.placement_ids)
    )
    return ArrangementView(
        portfolio_id,
        section_id,
        arrangement,
        None if not pointers else pointers[0].pointer_revision,
        ordered,
    )


def show_composition(
    root: str | Path, portfolio_id: str, revision: int | None = None
) -> CompositionView:
    records = _records(root)
    state = project_curation_state(records)
    if revision is None:
        binding = project_profile_state(records).active_binding(portfolio_id)
        if binding is None:
            raise WorkflowViewError(
                "profile_binding_missing", "Portfolio has no active Profile Binding."
            )
        composition = state.current_composition(
            portfolio_id, binding.profile_binding_id
        )
        pointer_binding_id: str | None = binding.profile_binding_id
    else:
        matches = tuple(
            item
            for item in state.compositions
            if item.portfolio_id == portfolio_id
            and item.composition_revision == revision
        )
        if len(matches) > 1:
            raise WorkflowViewError(
                "composition_revision_ambiguous",
                "Composition revision exists under more than one Profile Binding.",
            )
        composition = matches[0] if matches else None
        pointer_binding_id = (
            None if composition is None else composition.profile_binding_id
        )
    pointers = (
        ()
        if pointer_binding_id is None
        else state.composition_pointer_heads(portfolio_id, pointer_binding_id)
    )
    if len(pointers) > 1:
        raise WorkflowViewError(
            "composition_pointer_conflict", "Composition pointer is conflicted."
        )
    inventory = (
        None
        if composition is None
        else next(
            (
                x
                for x in state.composition_inventories
                if x.portfolio_id == portfolio_id
                and x.composition_revision == composition.composition_revision
            ),
            None,
        )
    )
    return CompositionView(
        composition, inventory, None if not pointers else pointers[0].pointer_revision
    )


def list_snapshot_series(
    root: str | Path, portfolio_id: str
) -> tuple[SnapshotSeries, ...]:
    return tuple(
        sorted(
            (
                x
                for x in project_snapshot_state(_records(root)).series
                if x.portfolio_id == portfolio_id
            ),
            key=lambda x: x.snapshot_series_id,
        )
    )


def show_snapshot_series(
    root: str | Path, snapshot_series_id: str
) -> SnapshotSeriesView:
    state = project_snapshot_state(_records(root))
    series = next(
        (x for x in state.series if x.snapshot_series_id == snapshot_series_id), None
    )
    if series is None:
        raise WorkflowViewError(
            "snapshot_series_not_found", "Snapshot Series not found."
        )
    requests = tuple(
        x for x in state.requests if x.snapshot_series_id == snapshot_series_id
    )
    request_ids = {x.snapshot_build_request_id for x in requests}
    plans = tuple(x for x in state.plans if x.snapshot_build_request_id in request_ids)
    plan_ids = {x.snapshot_build_plan_id for x in plans}
    attempts = tuple(x for x in state.attempts if x.snapshot_build_plan_id in plan_ids)
    attempt_ids = {x.snapshot_build_attempt_id for x in attempts}
    return SnapshotSeriesView(
        series,
        requests,
        plans,
        attempts,
        tuple(
            x
            for x in state.attempt_results
            if x.snapshot_build_attempt_id in attempt_ids
        ),
        tuple(
            sorted(
                (
                    x
                    for x in state.editions
                    if x.snapshot_series_id == snapshot_series_id
                ),
                key=lambda x: x.edition_number,
            )
        ),
        state.current_edition(snapshot_series_id),
    )


def show_snapshot_plan(
    root: str | Path, snapshot_build_plan_id: str
) -> SnapshotBuildPlan:
    matches = tuple(
        item
        for item in _records(root)
        if isinstance(item, SnapshotBuildPlan)
        and item.snapshot_build_plan_id == snapshot_build_plan_id
    )
    if len(matches) != 1:
        raise WorkflowViewError(
            "snapshot_plan_not_found", "Snapshot Build Plan not found."
        )
    return matches[0]


__all__ = [
    "ArrangementView",
    "CandidateSummary",
    "CandidateDetail",
    "CompositionView",
    "SnapshotSeriesView",
    "WorkflowViewError",
    "list_active_selections",
    "list_candidate_summaries",
    "list_snapshot_series",
    "show_arrangement",
    "show_candidate",
    "show_candidate_detail",
    "show_composition",
    "show_snapshot_series",
    "show_snapshot_plan",
]
